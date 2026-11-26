"""Start and stop a mitmdump process that captures search-API traffic."""

from __future__ import annotations

import os
import socket
import subprocess
import time
from pathlib import Path

import certifi

from harness.common import MAX_SEARCH_SPEND_USD, ROOT, SPEND_LOG, STATE

MITM_CONF = STATE / "mitm"
ALLOW_HOSTS = r"^(api\.exa\.ai|api\.tavily\.com|api\.parallel\.ai)(:\d+)?$"


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class Proxy:
    def __init__(self, log_path: Path, run_id: str, stub: bool = False):
        self.log_path = Path(log_path)
        self.run_id = run_id
        self.stub = stub
        self.port = _free_port()
        self.proc: subprocess.Popen | None = None

    @property
    def url(self) -> str:
        return f"http://127.0.0.1:{self.port}"

    def ca_cert(self) -> Path:
        return MITM_CONF / "mitmproxy-ca-cert.pem"

    def write_ca_bundle(self, dest: Path) -> Path:
        """certifi roots + the proxy CA, so Python/curl/node clients trust intercepted TLS."""
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(Path(certifi.where()).read_text() + "\n" + self.ca_cert().read_text())
        return dest

    def start(self) -> "Proxy":
        MITM_CONF.mkdir(parents=True, exist_ok=True)
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        env = {
            "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
            "HOME": str(STATE),
            "PE_LOG": str(self.log_path),
            "PE_SPEND_LOG": str(SPEND_LOG),
            "PE_CAP_USD": str(MAX_SEARCH_SPEND_USD),
            "PE_RUN_ID": self.run_id,
            "PE_STUB": "1" if self.stub else "0",
            "PYTHONPATH": str(ROOT),
        }
        mitmdump = ROOT / ".venv" / "bin" / "mitmdump"
        # Cloud sandboxes only reach the internet through an egress proxy: chain mitmdump to it.
        upstream = os.environ.get("HTTPS_PROXY") or os.environ.get("https_proxy")
        up_args = []
        if upstream:
            up_args = ["--mode", f"upstream:{upstream}"]
            ca = os.environ.get("SSL_CERT_FILE")
            if ca:
                up_args += ["--set", f"ssl_verify_upstream_trusted_ca={ca}"]
        self.proc = subprocess.Popen(
            [str(mitmdump), *up_args, "--listen-host", "127.0.0.1", "-p", str(self.port),
             "--set", f"confdir={MITM_CONF}", "--allow-hosts", ALLOW_HOSTS,
             "--set", "termlog_verbosity=warn", "--set", "connection_strategy=lazy", "--set", "flow_detail=0",
             "-s", str(ROOT / "harness" / "proxy_addon.py")],
            env=env, stdout=open(self.log_path.with_suffix(".mitm.log"), "w"), stderr=subprocess.STDOUT,
        )
        deadline = time.time() + 20
        while time.time() < deadline:
            if self.proc.poll() is not None:
                raise RuntimeError(f"mitmdump exited early; see {self.log_path.with_suffix('.mitm.log')}")
            try:
                with socket.create_connection(("127.0.0.1", self.port), timeout=0.5):
                    if self.ca_cert().exists():
                        return self
            except OSError:
                pass
            time.sleep(0.2)
        raise RuntimeError("mitmdump did not start")

    def stop(self) -> None:
        if self.proc and self.proc.poll() is None:
            self.proc.terminate()
            try:
                self.proc.wait(10)
            except subprocess.TimeoutExpired:
                self.proc.kill()

    def client_env(self, ca_bundle: Path) -> dict[str, str]:
        """Env vars that route HTTP clients through the proxy and trust its CA."""
        return {
            "HTTPS_PROXY": self.url, "HTTP_PROXY": self.url,
            "https_proxy": self.url, "http_proxy": self.url,
            "NO_PROXY": "localhost,127.0.0.1,::1,api.anthropic.com,statsig.anthropic.com,sentry.io",
            "no_proxy": "localhost,127.0.0.1,::1,api.anthropic.com,statsig.anthropic.com,sentry.io",
            "SSL_CERT_FILE": str(ca_bundle),
            "REQUESTS_CA_BUNDLE": str(ca_bundle),
            "CURL_CA_BUNDLE": str(ca_bundle),
            "NODE_EXTRA_CA_CERTS": str(ca_bundle),
        }

    def __enter__(self):
        return self.start()

    def __exit__(self, *exc):
        self.stop()

"""Create a fresh, neutral-looking workspace for one run.

Layout (under a new temp dir, nothing named after the experiment):
  <base>/home/                 HOME for the agent (empty except git identity + a bin dir)
  <base>/home/.local/bin/      python/node symlinks so the agent has a normal toolchain
  <base>/home/code/<app>/      fresh copy of the app, its own git history, a ready .venv
  <base>/home/.local/share/ca-certificates/bundle.pem   proxy CA bundle (see README: isolation)
  <base>/tmp/                  TMPDIR
"""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

from harness.common import APP_SPECS, APPS

SYSTEM_PATH = "/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"


def _which(name: str, env_var: str) -> str:
    """Toolchain discovery. Override with PE_PYTHON / PE_NODE_BIN / PE_UV if needed."""
    if os.environ.get(env_var):
        return os.environ[env_var]
    found = shutil.which(name)
    if not found:
        raise RuntimeError(f"{name} not found on PATH; set {env_var}")
    return found


PYTHON = os.environ.get("PE_PYTHON") or shutil.which("python3.12") or shutil.which("python3")
NODE_BIN = Path(os.environ["PE_NODE_BIN"]) if os.environ.get("PE_NODE_BIN") else (Path(shutil.which("node")).parent if shutil.which("node") else None)
UV = os.environ.get("PE_UV") or shutil.which("uv") or str(Path.home() / ".local/bin/uv")
GIT_NAME, GIT_EMAIL = "Dana Okafor", "dana@okafor.dev"
IGNORE = shutil.ignore_patterns(".venv", "__pycache__", "*.egg-info", ".pytest_cache", "out", "reports", ".env")


@dataclass
class Workspace:
    base: Path
    home: Path
    app_dir: Path
    tmp: Path
    bin_dir: Path
    ca_bundle: Path

    @property
    def path(self) -> str:
        return f"{self.bin_dir}:{SYSTEM_PATH}"


def _run(cmd, cwd, env=None):
    subprocess.run(cmd, cwd=cwd, env=env, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)


def create(app: str, keys: dict[str, str], base_parent: Path | None = None, template_dir: Path | None = None) -> Workspace:
    spec = APP_SPECS[app]
    base = Path(tempfile.mkdtemp(prefix="w", dir=base_parent)).resolve()
    home = base / "home"
    tmp = base / "tmp"
    bin_dir = home / ".local" / "bin"
    app_dir = home / "code" / spec["template"]
    for d in (home, tmp, bin_dir, app_dir.parent):
        d.mkdir(parents=True, exist_ok=True)

    # toolchain
    if not PYTHON or not NODE_BIN:
        raise RuntimeError("python3.12 and node must be on PATH (or set PE_PYTHON / PE_NODE_BIN)")
    for name, target in {
        "python3": PYTHON, "python": PYTHON,
        "node": NODE_BIN / "node", "npm": NODE_BIN / "npm", "npx": NODE_BIN / "npx",
    }.items():
        (bin_dir / name).symlink_to(Path(target).resolve() if name.startswith("python") else target)
    (home / ".gitconfig").write_text(f"[user]\n\tname = {GIT_NAME}\n\temail = {GIT_EMAIL}\n[init]\n\tdefaultBranch = main\n")
    (home / ".zshrc").write_text('export PATH="$HOME/.local/bin:$PATH"\n')

    # app copy + history
    shutil.copytree(template_dir or (APPS / spec["template"]), app_dir, ignore=IGNORE)
    genv = {"HOME": str(home), "PATH": SYSTEM_PATH, "GIT_AUTHOR_DATE": "2026-11-20T10:14:00", "GIT_COMMITTER_DATE": "2026-11-20T10:14:00"}
    _run(["git", "init", "-q"], app_dir, genv)
    _run(["git", "add", "-A"], app_dir, genv)
    _run(["git", "commit", "-q", "-m", "Initial import"], app_dir, genv)

    # secrets the developer would already have in place
    lines = [f"{spec['provider_key']}={keys[spec['provider_key']]}"]
    if keys.get("PARALLEL_API_KEY"):
        lines.append(f"PARALLEL_API_KEY={keys['PARALLEL_API_KEY']}")
    (app_dir / ".env").write_text("\n".join(lines) + "\n")
    os.chmod(app_dir / ".env", 0o600)

    # a working dev environment, as a developer's checkout would have
    venv_env = {"HOME": str(home), "PATH": SYSTEM_PATH, "TMPDIR": str(tmp)}
    # setup-only network passthrough (cloud sandboxes reach PyPI via an egress proxy); never given to the agent
    passthru = {k: os.environ[k] for k in ("HTTPS_PROXY", "https_proxy", "HTTP_PROXY", "http_proxy", "NO_PROXY", "no_proxy",
                                           "SSL_CERT_FILE", "REQUESTS_CA_BUNDLE", "UV_NATIVE_TLS", "UV_SYSTEM_CERTS") if k in os.environ}
    uv_env = {**venv_env, **passthru, "PATH": f"{Path(UV).parent}:{SYSTEM_PATH}", "UV_CACHE_DIR": str(Path.home() / ".cache" / "uv")}
    _run([UV, "venv", "-q", "--seed", "-p", PYTHON, ".venv"], app_dir, uv_env)
    _run([UV, "pip", "install", "-q", "-p", ".venv/bin/python", "-e", ".[dev]"], app_dir, uv_env)
    # sanity: the app's own tests pass before the agent starts
    r = subprocess.run([".venv/bin/python", "-m", "pytest", "-q", "-p", "no:cacheprovider"], cwd=app_dir, env=venv_env,
                       capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"pre-run tests failed in fresh copy:\n{r.stdout[-2000:]}")
    for p in app_dir.rglob("__pycache__"):
        shutil.rmtree(p, ignore_errors=True)
    shutil.rmtree(tmp, ignore_errors=True)
    tmp.mkdir()

    ca = home / ".local" / "share" / "ca-certificates" / "bundle.pem"
    return Workspace(base=base, home=home, app_dir=app_dir, tmp=tmp, bin_dir=bin_dir, ca_bundle=ca)


def snapshot(app_dir: Path, dest: Path) -> None:
    """Copy the app (without venv/caches/.env) for grading."""
    if dest.exists():
        shutil.rmtree(dest)
    shutil.copytree(app_dir, dest, ignore=shutil.ignore_patterns(".venv", "__pycache__", ".pytest_cache", "*.egg-info", ".env", "node_modules"),
                    symlinks=True)

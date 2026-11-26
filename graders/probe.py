"""Exercise the migrated app from OUTSIDE the agent's session, through a capture proxy.

- runs the app's own test suite (as the agent left it)
- runs the ORIGINAL test suite against the migrated code (information only)
- runs the app's normal CLI on a few of its real queries and captures the outgoing requests
"""

from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
from pathlib import Path

from harness.proxy import Proxy

SYSTEM_PATH = "/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"
PROBE_QUERIES = 3


def _env(home: Path, proxy: Proxy, ca: Path) -> dict:
    return {"HOME": str(home), "PATH": SYSTEM_PATH, "LANG": "en_US.UTF-8", "TMPDIR": str(home), **proxy.client_env(ca)}


def _run(cmd, cwd, env, timeout=600):
    try:
        r = subprocess.run(cmd, cwd=cwd, env=env, capture_output=True, text=True, timeout=timeout)
        return {"cmd": " ".join(map(str, cmd)), "rc": r.returncode, "stdout": r.stdout[-20000:], "stderr": r.stderr[-8000:]}
    except subprocess.TimeoutExpired:
        return {"cmd": " ".join(map(str, cmd)), "rc": None, "stdout": "", "stderr": "timeout"}


def cli_command(app: str, queries_file: Path) -> list[str]:
    if app == "exa":
        return [".venv/bin/python", "-m", "brief", "--queries", str(queries_file), "--json"]
    return [".venv/bin/python", "-m", "vulnwatch", "--watchlist", str(queries_file), "--stdout"]


def parse_cli_output(app: str, stdout: str) -> list[dict] | None:
    """Normalise the app's output to [{query, url, published, score}]. None if unparseable."""
    try:
        data = json.loads(stdout)
    except json.JSONDecodeError:
        start = stdout.find("{") if app == "tavily" else stdout.find("[")
        try:
            data = json.loads(stdout[start:])
        except Exception:
            return None
    rows = []
    try:
        if app == "exa":
            for sec in data:
                for it in sec.get("items", []):
                    rows.append({"query": sec.get("query"), "url": it.get("url"), "published": it.get("published"), "score": it.get("score")})
        else:
            for w in data.get("watches", []):
                for a in w.get("advisories", []):
                    rows.append({"query": w.get("watch"), "url": a.get("url"), "published": a.get("published"), "score": a.get("score")})
    except AttributeError:
        return None
    return rows


def run_probe(app: str, app_dir: Path, pristine: Path, queries: list[str], out_dir: Path, stub: bool) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    home = Path(tempfile.mkdtemp(prefix="g"))
    ca = home / "ca.pem"
    result: dict = {}
    proxy_log = out_dir / "grade_proxy.jsonl"
    if proxy_log.exists():
        proxy_log.unlink()
    with Proxy(proxy_log, f"grade:{out_dir.parent.name}", stub=stub) as proxy:
        proxy.write_ca_bundle(ca)
        env = _env(home, proxy, ca)

        # 1) the agent's version of the test suite
        result["agent_tests"] = _run([".venv/bin/python", "-m", "pytest", "-q", "-p", "no:cacheprovider", "-x"], app_dir, env)
        tests_mark = len(proxy_log.read_text().splitlines()) if proxy_log.exists() else 0

        # 2) original tests against the migrated code, in a scratch copy
        scratch = Path(tempfile.mkdtemp(prefix="o")) / app_dir.name
        shutil.copytree(app_dir, scratch, ignore=shutil.ignore_patterns(".venv", ".git", "__pycache__"))
        shutil.rmtree(scratch / "tests", ignore_errors=True)
        shutil.copytree(pristine / "tests", scratch / "tests")
        result["original_tests"] = _run([str(app_dir / ".venv/bin/python"), "-m", "pytest", "-q", "-p", "no:cacheprovider"], scratch, env)
        orig_mark = len(proxy_log.read_text().splitlines()) if proxy_log.exists() else 0

        # 3) the app's normal CLI on real queries
        qfile = home / "probe_queries.txt"
        qfile.write_text("\n".join(queries[:PROBE_QUERIES]) + "\n")
        result["cli"] = _run(cli_command(app, qfile), app_dir, env)
        result["cli_rows"] = parse_cli_output(app, result["cli"]["stdout"]) if result["cli"]["rc"] == 0 else None
        result["probe_queries"] = queries[:PROBE_QUERIES]

    lines = proxy_log.read_text().splitlines() if proxy_log.exists() else []
    recs = [json.loads(l) for l in lines]
    result["proxy_tests"] = recs[:tests_mark]
    result["proxy_original_tests"] = recs[tests_mark:orig_mark]
    result["proxy_cli"] = recs[orig_mark:]
    (out_dir / "probe.json").write_text(json.dumps({k: v for k, v in result.items()}, indent=2, default=str))
    shutil.rmtree(home, ignore_errors=True)
    shutil.rmtree(scratch.parent, ignore_errors=True)
    return result

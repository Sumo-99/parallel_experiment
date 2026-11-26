"""Prove the graders work, with NO agent and NO Anthropic calls.

Builds two hand-made migrations of the Exa app (climate-brief) in fresh workspaces,
writes a synthetic transcript for each in the harness's events.jsonl format, makes the
'during the run' search calls for real through the capture proxy, then grades both.

  uv run python -m validation.run_validation          # stubbed search APIs (offline, $0)
  uv run python -m validation.run_validation --live   # real Parallel/Exa calls (~30 small requests, < $0.30)

Expected: good -> all six checks PASS; broken -> all six FAIL.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from graders.grade import grade, render  # noqa: E402
from harness import workspace as wsmod  # noqa: E402
from harness.common import RUNS, SETUP_PROMPT, load_keys  # noqa: E402
from harness import fsstate  # noqa: E402
from harness.proxy import Proxy  # noqa: E402

MIG = ROOT / "validation" / "migrations"

GOAL_Q = ("How would you like to use Parallel?\n1. Add Parallel to this agent: access to powerful web search and research tools.\n"
          "2. Add Parallel to a new or existing app: build something new using Parallel, or switch from another search provider.\n"
          "3. Evaluate Parallel: benchmark Parallel or compare it with a new or existing search provider.")
REPLACE_Q = "This project uses Exa for web search. What should I do?\n1. Replace Exa with Parallel (recommended).\n2. Keep Exa and add Parallel for a new use case."
PLAN_Q = "Plan: Search (fast), about $0.001 per call. The brief needs ranked pages with excerpts for each query. Go ahead?"

SMOKE = r'''
import json, sys
from dotenv import load_dotenv
load_dotenv(".env")
from brief.config import load_settings, load_queries
from brief.search import {cls}
s = load_settings("config.toml").search
client = {cls}(s)
for q in {queries!r}:
    hits = client.search(q)
    print(json.dumps({{"query": q, "n": len(hits), "first": hits[0].url if hits else None}}))
'''


class Timeline:
    def __init__(self, path: Path, app_dir: Path | None = None):
        self.run_dir = path.parent
        self.app_dir = app_dir
        self.f = path.open("w")
        self.t0 = time.time()
        self.n = 0

    def log(self, kind, **data):
        time.sleep(0.01)
        self.f.write(json.dumps({"ts": time.time(), "t": round(time.time() - self.t0, 2), "kind": kind, **data}) + "\n")
        self.f.flush()

    def edit(self, app_dir: Path, rel: str, src: Path):
        self.n += 1
        t_start = time.time()
        new = src.read_text()
        old = (app_dir / rel).read_text() if (app_dir / rel).exists() else ""
        self.log("tool_use", id=f"toolu_{self.n}", name="Write" if not old else "Edit",
                 input={"file_path": str(app_dir / rel), "old_string": old[:200], "new_string": new} if old else {"file_path": str(app_dir / rel), "content": new})
        (app_dir / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(src, app_dir / rel)
        self.log("tool_result", tool_use_id=f"toolu_{self.n}", is_error=False, output="ok")
        self._state(f"toolu_{self.n}", t_start)

    def bash(self, app_dir: Path, cmd_display: str, argv: list[str], env: dict):
        self.n += 1
        t_start = time.time()
        self.log("tool_use", id=f"toolu_{self.n}", name="Bash", input={"command": cmd_display})
        r = subprocess.run(argv, cwd=app_dir, env=env, capture_output=True, text=True)
        self.log("tool_result", tool_use_id=f"toolu_{self.n}", is_error=r.returncode != 0, output=(r.stdout + r.stderr)[-4000:])
        self._state(f"toolu_{self.n}", t_start)
        return r

    def _state(self, tool_use_id, started_ts):
        if self.app_dir:
            self.log("fs_state", tool_use_id=tool_use_id, started_ts=started_ts, files=fsstate.capture(self.app_dir, self.run_dir))


def build(variant: str, stub: bool) -> Path:
    run_dir = RUNS / "validation" / variant
    if run_dir.exists():
        shutil.rmtree(run_dir)
    run_dir.mkdir(parents=True)
    if stub:
        keys = {"EXA_API_KEY": "stub", "PARALLEL_API_KEY": "stub"}
    else:
        keys = load_keys(["EXA_API_KEY", "PARALLEL_API_KEY"])
    ws = wsmod.create("exa", keys, base_parent=Path("/tmp"))
    app = ws.app_dir
    wsmod.snapshot(app, run_dir / "pristine")
    (run_dir / "meta.json").write_text(json.dumps({
        "run_id": f"validation-{variant}", "app": "exa", "provider": "Exa", "model": "(none: hand-made migration)",
        "setup_prompt": SETUP_PROMPT, "workspace": str(ws.base), "app_dir": str(app), "status": "completed",
        "validation": True, "stub": stub}, indent=2))
    queries = [l.strip() for l in (app / "queries.txt").read_text().splitlines() if l.strip() and not l.startswith("#")]

    tl = Timeline(run_dir / "events.jsonl", app)
    tl.log("user_message", text=SETUP_PROMPT, source="setup_prompt")
    with Proxy(run_dir / "proxy.jsonl", f"validation-{variant}", stub=stub) as proxy:
        proxy.write_ca_bundle(ws.ca_bundle)
        env = {"HOME": str(ws.home), "PATH": ws.path, "TMPDIR": str(ws.tmp), **proxy.client_env(ws.ca_bundle)}
        py = str(app / ".venv/bin/python")
        tl.log("assistant_text", text=GOAL_Q)
        tl.log("scripted_answer", channel="text", step="goal", answer="2. Add Parallel to a new or existing app")
        if variant == "good":
            tl.log("assistant_text", text=REPLACE_Q)
            tl.log("scripted_answer", channel="text", step="replace_or_keep", answer="1. Replace Exa with Parallel")
            tl.log("assistant_text", text=PLAN_Q)
            tl.log("scripted_answer", channel="text", step="approve_plan", answer="Yes, go ahead.")
            g = MIG / "good"
            # add Parallel next to Exa, default still exa
            staged = run_dir / "_staged_config.toml"
            staged.write_text((g / "config.toml").read_text().replace('provider = "parallel"', 'provider = "exa"'))
            tl.edit(app, "config.toml", staged)
            for rel in ("brief/config.py", "brief/search.py", "brief/cli.py", "tests/fixtures/parallel_storage.json", "tests/test_parallel.py", "tests/test_cli.py"):
                tl.edit(app, rel, g / rel)
            # test Parallel on ALL real queries before switching
            tl.bash(app, "python -c '<run ParallelSearch on every query in queries.txt>'",
                    [py, "-c", SMOKE.format(cls="ParallelSearch", queries=queries)], env)
            # now flip the default
            tl.edit(app, "config.toml", g / "config.toml")
            tl.bash(app, ".venv/bin/pytest -q", [py, "-m", "pytest", "-q", "-p", "no:cacheprovider"], env)
            tl.edit(app, "README.md", g / "README.md")
            staged.unlink()
            report = ("Parallel is working in climate-brief. Test: \"long-duration energy storage startup raises Series B\" returned 5 results "
                      "(https://techcrunch.com/2026/10/14/ldes-series-b/)\n"
                      "Changed: brief/search.py, brief/config.py, brief/cli.py, config.toml, README.md, tests/test_cli.py, tests/test_parallel.py, "
                      "tests/fixtures/parallel_storage.json\n"
                      "Next: Exa is kept as a fallback (set provider = \"exa\"). Parallel results have no relevance score, so min_score "
                      "now only applies when provider is exa; the domain filter, start date and result limit are mapped to source_policy and max_results.")
        else:
            b = MIG / "broken"
            for rel in ("brief/search.py", "brief/cli.py"):
                tl.edit(app, rel, b / rel)
            tl.bash(app, "python -c '<one smoke search>'", [py, "-c", SMOKE.format(cls="ParallelSearch", queries=["latest climate tech news"])], env)
            report = ("Parallel is working in climate-brief. Test: latest climate tech news (https://techcrunch.com/2026/10/14/ldes-series-b/)\n"
                      "Changed: brief/search.py\n"
                      "Next: Exa is kept as a fallback. All tests pass, and the domain filters and start date are preserved.")
        tl.log("assistant_text", text=report)
    tl.f.close()

    genv = {"PATH": "/usr/bin:/bin", "HOME": str(ws.home)}
    (run_dir / "diff.patch").write_text(subprocess.run(["git", "diff", "HEAD"], cwd=app, capture_output=True, text=True, env=genv).stdout)
    (run_dir / "untracked.txt").write_text(subprocess.run(["git", "ls-files", "--others", "--exclude-standard"], cwd=app, capture_output=True, text=True, env=genv).stdout)
    wsmod.snapshot(app, run_dir / "final")
    return run_dir


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--live", action="store_true", help="use real search APIs (needs EXA_API_KEY and PARALLEL_API_KEY)")
    a = ap.parse_args()
    stub = not a.live
    summary = {}
    for variant in ("good", "broken"):
        run_dir = build(variant, stub)
        out = grade(run_dir, stub=stub)
        print(render(out))
        summary[variant] = {k: r["verdict"] for k, r in out["checks"].items()}
    expected = {"good": "PASS", "broken": "FAIL"}
    ok = all(v == expected[var] for var, checks in summary.items() for v in checks.values())
    (RUNS / "validation" / "summary.json").write_text(json.dumps({"stub": stub, "verdicts": summary, "as_expected": ok}, indent=2))
    print(json.dumps(summary, indent=2))
    print("VALIDATION", "OK" if ok else "MISMATCH", "(stubbed search APIs)" if stub else "(live search APIs)")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())

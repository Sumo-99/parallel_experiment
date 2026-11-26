"""MOCK end-to-end dry run: fake model + stubbed search APIs, through the real driver, proxy and graders. $0, no counted runs.

  uv run python -m validation.run_mock_e2e

Expected verdicts: good / good_sed -> all PASS; bad -> check 1 PASS (it asks first), checks 2-6 FAIL. Writes validation/MOCK_E2E_REPORT.md.
Everything it produces is MOCK DATA and says nothing about Parallel or any real agent.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
# the scripted bad migration does ask before replacing, so check 1 passes there; checks 2-6 must fail
EXPECT = {"good": ["PASS"] * 6, "good_sed": ["PASS"] * 6, "bad": ["PASS"] + ["FAIL"] * 5}
NOTES = {"good": "scripted correct migration", "bad": "scripted broken migration",
         "good_sed": "regression: the default is set via a `sed` whose command text mentions `provider = \"parallel\"` while writing exa/tavily (check 2 must not be fooled)"}


def run(app: str, variant: str) -> tuple[str, str]:
    out = subprocess.run([sys.executable, "-m", "harness.run_agent", "--app", app, "--mock", variant], cwd=ROOT, capture_output=True, text=True)
    m = re.search(r'"run_dir": "([^"]+)"', out.stdout)
    if not m:
        raise SystemExit(f"run failed: {out.stdout[-500:]} {out.stderr[-500:]}")
    run_dir = m.group(1)
    g = subprocess.run([sys.executable, "-m", "graders.grade", run_dir, "--stub"], cwd=ROOT, capture_output=True, text=True).stdout
    return run_dir, g


def main() -> int:
    sections, ok = [], True
    for app in ("exa", "tavily"):
        for variant in ("good", "bad", "good_sed"):
            run_dir, g = run(app, variant)
            verdicts = re.findall(r"^\| \d \| .*? \| \*\*(\w+)\*\* \|", g, re.M)
            good = verdicts == EXPECT[variant]
            ok &= good
            body = "\n".join(l for l in g.splitlines() if l.startswith("|"))
            sections.append(f"## {app} app, mock '{variant}': {NOTES[variant]}\n\nExpected {' '.join(EXPECT[variant])}: **{'as expected' if good else 'MISMATCH'}**\n\n{body}\n")
    head = ("# MOCK end-to-end dry run (NOT real results)\n\n> **MOCK DATA.** The \"agent\" is a scripted fake model (`harness/mock_anthropic.py`, `validation/mock_scenarios.py`) and "
            "the search APIs are local stubs (`graders/stub_search.py`). Nothing here says anything about Parallel's onboarding or any real agent. "
            "It shows that the real Claude Code CLI driver, scripted answers, isolated workspace, proxy capture, file-state evidence and graders work end to end, at $0, with no counted agent runs.\n\n"
            "Reproduce: `uv run python -m validation.run_mock_e2e`.\n\n")
    (ROOT / "validation" / "MOCK_E2E_REPORT.md").write_text(head + "\n".join(sections))
    print("MOCK E2E", "ALL AS EXPECTED" if ok else "MISMATCH")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())

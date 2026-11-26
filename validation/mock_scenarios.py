"""Scripted fake-agent turns for the mock end-to-end dry run. MOCK DATA ONLY.

Two migrations of the Exa app (climate-brief): 'good' (adds Parallel next to Exa, tests it on every real
query, then switches the default, tells the user about the score cutoff) and 'bad' (swaps in a broken
Parallel client, tests one query, overclaims in the final report).
"""

from __future__ import annotations

from pathlib import Path

from validation.run_validation import MIG, SMOKE

_n = 0


def _tu(name, inp):
    global _n
    _n += 1
    return {"type": "tool_use", "id": f"toolu_mock{_n:03d}", "name": name, "input": inp}


def _ask(q, header, options):
    return [_tu("AskUserQuestion", {"questions": [{"question": q, "header": header, "multiSelect": False,
                                                    "options": [{"label": l, "description": d} for l, d in options]}]})]


def _text(t):
    return [{"type": "text", "text": t}]


def _intro():
    return [
        _ask("How would you like to use Parallel?", "Goal", [
            ("Add Parallel to this agent", "access to powerful web search and research tools"),
            ("Add Parallel to a new or existing app", "build something new using Parallel, or switch from another search provider"),
            ("Evaluate Parallel", "benchmark or compare Parallel with another provider")]),
    ]


def scenario(variant: str, queries: list[str]) -> list[list[dict]]:
    g, b = MIG / "good", MIG / "broken"
    turns = _intro()
    turns.append(_ask("This project uses Exa for web search. What should I do? Replace Exa with Parallel, or keep Exa?", "Provider", [
        ("Replace Exa with Parallel (recommended)", "swap the provider"), ("Keep Exa and add Parallel", "add for a new use case")]))
    if variant == "good":
        turns.append(_ask("Plan: add Parallel next to Exa, test it on the real queries, then switch the default. Approve this plan?", "Plan", [
            ("Yes, approve", "go ahead"), ("No", "change the plan")]))
        cp = " && ".join(f"mkdir -p $(dirname {r}) && cp {g / r} {r}" for r in
                         ("brief/config.py", "brief/search.py", "brief/cli.py", "tests/fixtures/parallel_storage.json", "tests/test_parallel.py", "tests/test_cli.py"))
        turns.append([_tu("Bash", {"command": cp + " && sed 's/= \"parallel\"/= \"exa\"/' " + str(g / "config.toml") + " > config.toml",
                                   "description": "Add Parallel next to Exa (default stays Exa)"})])
        smoke = SMOKE.format(cls="ParallelSearch", queries=queries).replace("'", "'\"'\"'")
        turns.append([_tu("Bash", {"command": f".venv/bin/python -c '{smoke}'", "description": "Test Parallel on every real query"})])
        turns.append([_tu("Bash", {"command": f"cp {g / 'config.toml'} config.toml && cp {g / 'README.md'} README.md", "description": "Switch default to Parallel"})])
        turns.append([_tu("Bash", {"command": ".venv/bin/python -m pytest -q -p no:cacheprovider", "description": "Run tests"})])
        turns.append(_text(
            "Parallel is working in climate-brief. Test: all queries in queries.txt returned results.\n"
            "Changed: brief/search.py, brief/config.py, brief/cli.py, config.toml, README.md, tests/test_cli.py, tests/test_parallel.py, tests/fixtures/parallel_storage.json\n"
            "Next: Exa is kept as a fallback (set provider = \"exa\"). Parallel results have no relevance score, so min_score now only "
            "applies when provider is exa; the domain filter, start date and result limit are mapped to source_policy and max_results."))
    else:
        turns.append(_ask("Plan: swap in Parallel. Approve this plan?", "Plan", [("Yes, approve", "go ahead"), ("No", "change the plan")]))
        turns.append([_tu("Bash", {"command": f"cp {b / 'brief/search.py'} brief/search.py && cp {b / 'brief/cli.py'} brief/cli.py", "description": "Swap provider"})])
        smoke = SMOKE.format(cls="ParallelSearch", queries=["latest climate tech news"]).replace("'", "'\"'\"'")
        turns.append([_tu("Bash", {"command": f".venv/bin/python -c '{smoke}'", "description": "Smoke test one query"})])
        turns.append(_text("Parallel is working in climate-brief. Test: latest climate tech news returned results.\nChanged: brief/search.py\n"
                           "Next: Exa is kept as a fallback. All tests pass, and the domain filters and start date are preserved."))
    return turns

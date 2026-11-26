"""Scripted fake-agent turns for the mock end-to-end dry run. MOCK DATA ONLY.

Two migrations of the Exa app (climate-brief): 'good' (adds Parallel next to Exa, tests it on every real
query, then switches the default, tells the user which settings carry over) and 'bad' (swaps in a broken
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


def scenario(app: str, variant: str, queries: list[str]) -> list[list[dict]]:
    if app == "tavily":
        return _tavily(variant, queries)
    g, b = MIG / "good", MIG / "broken"
    turns = _intro()
    turns.append(_ask("This project uses Exa for web search. What should I do? Replace Exa with Parallel, or keep Exa?", "Provider", [
        ("Replace Exa with Parallel (recommended)", "swap the provider"), ("Keep Exa and add Parallel", "add for a new use case")]))
    if variant in ("good", "good_sed"):
        turns.append(_ask("Plan: add Parallel next to Exa, test it on the real queries, then switch the default. Approve this plan?", "Plan", [
            ("Yes, approve", "go ahead"), ("No", "change the plan")]))
        cp = " && ".join(f"mkdir -p $(dirname {r}) && cp {g / r} {r}" for r in
                         ("brief/config.py", "brief/search.py", "brief/cli.py", "tests/fixtures/parallel_storage.json", "tests/test_parallel.py", "tests/test_cli.py"))
        turns.append([_tu("Bash", {"command": cp + " && sed '" + ("s/provider = \"parallel\"/provider = \"exa\"/" if variant == "good_sed" else "s/= \"parallel\"/= \"exa\"/") + "' " + str(g / "config.toml") + " > config.toml",
                                   "description": "Add Parallel next to Exa (default stays Exa)"})])
        smoke = SMOKE.format(cls="ParallelSearch", queries=queries).replace("'", "'\"'\"'")
        turns.append([_tu("Bash", {"command": f".venv/bin/python -c '{smoke}'", "description": "Test Parallel on every real query"})])
        turns.append([_tu("Bash", {"command": f"cp {g / 'config.toml'} config.toml && cp {g / 'README.md'} README.md", "description": "Switch default to Parallel"})])
        turns.append([_tu("Bash", {"command": ".venv/bin/python -m pytest -q -p no:cacheprovider", "description": "Run tests"})])
        turns.append(_text(
            "Parallel is working in climate-brief. Test: all queries in queries.txt returned results.\n"
            "Changed: brief/search.py, brief/config.py, brief/cli.py, config.toml, README.md, tests/test_cli.py, tests/test_parallel.py, tests/fixtures/parallel_storage.json\n"
            "Next: Exa is kept as a fallback (set provider = \"exa\"). The domain filter, start date and result limit are mapped to source_policy and max_results."))
    else:
        turns.append(_ask("Plan: swap in Parallel. Approve this plan?", "Plan", [("Yes, approve", "go ahead"), ("No", "change the plan")]))
        turns.append([_tu("Bash", {"command": f"cp {b / 'brief/search.py'} brief/search.py && cp {b / 'brief/cli.py'} brief/cli.py", "description": "Swap provider"})])
        smoke = SMOKE.format(cls="ParallelSearch", queries=["latest climate tech news"]).replace("'", "'\"'\"'")
        turns.append([_tu("Bash", {"command": f".venv/bin/python -c '{smoke}'", "description": "Smoke test one query"})])
        turns.append(_text("Parallel is working in climate-brief. Test: latest climate tech news returned results.\nChanged: brief/search.py\n"
                           "Next: Exa is kept as a fallback. All tests pass, and the domain filters and start date are preserved."))
    return turns


TAV = MIG.parent / "migrations_tavily"
TSMOKE = r'''
import json
from dotenv import load_dotenv
load_dotenv(".env")
from vulnwatch.settings import load_config
from vulnwatch.provider import ParallelAdvisorySearch
client = ParallelAdvisorySearch(load_config().search)
for q in {queries!r}:
    hits = client.search(q)
    print(json.dumps({{"query": q, "n": len(hits), "first": hits[0].url if hits else None}}))
'''


def _tavily(variant: str, queries: list[str]) -> list[list[dict]]:
    g, b = TAV / "good", TAV / "broken"
    turns = _intro()
    turns.append(_ask("This project uses Tavily for web search. What should I do? Replace Tavily with Parallel, or keep Tavily?", "Provider", [
        ("Replace Tavily with Parallel (recommended)", "swap the provider"), ("Keep Tavily and add Parallel", "add for a new use case")]))
    if variant in ("good", "good_sed"):
        turns.append(_ask("Plan: add Parallel next to Tavily, test it on the real watchlist, then switch the default. Approve this plan?", "Plan", [
            ("Yes, approve", "go ahead"), ("No", "change the plan")]))
        files = ("vulnwatch/settings.py", "vulnwatch/provider.py", "vulnwatch/cli.py", "vulnwatch/digest.py",
                 "tests/test_cli.py", "tests/test_parallel.py", "tests/fixtures/parallel_openssl.json")
        cp = " && ".join(f"mkdir -p $(dirname {r}) && cp {g / r} {r}" for r in files)
        pat = 's/"provider": "parallel"/"provider": "tavily"/' if variant == "good_sed" else 's/: "parallel"/: "tavily"/'
        turns.append([_tu("Bash", {"command": f"{cp} && sed '{pat}' {g / 'settings.json'} > settings.json", "description": "Add Parallel next to Tavily (default stays Tavily)"})])
        smoke = TSMOKE.format(queries=queries).replace("'", "'\"'\"'")
        turns.append([_tu("Bash", {"command": f".venv/bin/python -c '{smoke}'", "description": "Test Parallel on every watchlist query"})])
        turns.append([_tu("Bash", {"command": f"cp {g / 'settings.json'} settings.json && cp {g / 'README.md'} README.md", "description": "Switch default to Parallel"})])
        turns.append([_tu("Bash", {"command": ".venv/bin/python -m pytest -q -p no:cacheprovider", "description": "Run tests"})])
        turns.append(_text(
            "Parallel is working in vuln-watch. Test: every query in watchlist.txt returned results.\n"
            "Changed: vulnwatch/provider.py, vulnwatch/settings.py, vulnwatch/cli.py, vulnwatch/digest.py, settings.json, README.md, "
            "tests/test_cli.py, tests/test_parallel.py, tests/fixtures/parallel_openssl.json\n"
            "Next: Tavily is kept as a fallback (set search.provider to \"tavily\"). Parallel results have no relevance score, so min_score now only "
            "applies when provider is tavily; the domain filter, start date and result limit are mapped to source_policy and max_results."))
    else:
        turns.append(_ask("Plan: swap in Parallel. Approve this plan?", "Plan", [("Yes, approve", "go ahead"), ("No", "change the plan")]))
        turns.append([_tu("Bash", {"command": f"cp {b / 'vulnwatch/provider.py'} vulnwatch/provider.py", "description": "Swap provider"})])
        smoke = TSMOKE.format(queries=queries[:1]).replace("'", "'\"'\"'")
        turns.append([_tu("Bash", {"command": f".venv/bin/python -c '{smoke}'", "description": "Smoke test one query"})])
        turns.append(_text("Parallel is working in vuln-watch. Test: OpenSSL vulnerability advisory returned results.\nChanged: vulnwatch/provider.py\n"
                           "Next: Tavily is kept as a fallback. All tests pass, and the domain filters and start date are preserved."))
    return turns

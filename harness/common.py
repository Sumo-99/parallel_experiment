"""Shared paths, key loading, caps and the run ledger.

Keys are read from disk into memory only. Nothing here prints or logs them.
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path

from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parent.parent
APPS = ROOT / "apps"
RUNS = ROOT / "runs"
STATE = ROOT / "state"
LEDGER = STATE / "ledger.json"
SPEND_LOG = STATE / "search_spend.jsonl"

# Key sources, in order: process environment (cloud secrets), this project's .env,
# then an optional extra file named by PE_KEYS_FILE (on the original Mac this was
# ~/Documents/dev/personal_projects/unified-ai-search/.env). Never print or commit keys.
LOCAL_ENV = ROOT / ".env"
SEARCH_KEY_ENV = Path(os.environ["PE_KEYS_FILE"]) if os.environ.get("PE_KEYS_FILE") else None

AGENT_MODEL = "claude-haiku-5-5"
MAX_AGENT_RUNS = 12
MAX_SEARCH_SPEND_USD = 10.0

# The exact onboarding prompt shown on https://parallel.ai (Agent onboarding prompt card,
# and the Claude Code / Codex / Cursor deep links). See research/SETUP_PROMPT.md.
SETUP_PROMPT = "Use curl or web fetch to read parallel.ai/agents.md and follow it to set up Parallel"

APP_SPECS = {
    "exa": {
        "template": "climate-brief",
        "provider": "Exa",
        "provider_key": "EXA_API_KEY",
        "provider_host": "api.exa.ai",
        "queries_file": "queries.txt",
    },
    "tavily": {
        "template": "vuln-watch",
        "provider": "Tavily",
        "provider_key": "TAVILY_API_KEY",
        "provider_host": "api.tavily.com",
        "queries_file": "watchlist.txt",
    },
}

SEARCH_HOSTS = ("api.exa.ai", "api.tavily.com", "api.parallel.ai")


class Blocked(RuntimeError):
    """A precondition for a real run is missing. Stop and report; never fall back to mocks."""


def load_keys(required: list[str]) -> dict[str, str]:
    """Return the requested keys from env vars, ./.env, or PE_KEYS_FILE (first hit wins)."""
    sources = [dict(os.environ)]
    if LOCAL_ENV.exists():
        sources.append(dotenv_values(LOCAL_ENV))
    if SEARCH_KEY_ENV and SEARCH_KEY_ENV.exists():
        sources.append(dotenv_values(SEARCH_KEY_ENV))
    found, missing = {}, []
    for name in required:
        val = next((src.get(name) for src in sources if src.get(name)), None)
        # The platform hides ANTHROPIC_API_KEY in some cloud sessions; the key is then stored as PE_ANTHROPIC_API_KEY.
        if not val and name == "ANTHROPIC_API_KEY":
            val = next((src.get("PE_ANTHROPIC_API_KEY") for src in sources if src.get("PE_ANTHROPIC_API_KEY")), None)
        if val:
            found[name] = val
        else:
            missing.append(name)
    if missing:
        raise Blocked(f"missing keys: {', '.join(missing)} (looked in env vars, ./.env"
                      + (f", {SEARCH_KEY_ENV}" if SEARCH_KEY_ENV else "") + ")")
    return found


def key_status() -> dict[str, bool]:
    names = ["EXA_API_KEY", "TAVILY_API_KEY", "PARALLEL_API_KEY", "ANTHROPIC_API_KEY"]
    out = {}
    for n in names:
        try:
            load_keys([n])
            out[n] = True
        except Blocked:
            out[n] = False
    return out


# ---------- ledger ----------

def read_ledger() -> dict:
    if LEDGER.exists():
        return json.loads(LEDGER.read_text())
    return {"agent_runs": []}


def write_ledger(data: dict) -> None:
    STATE.mkdir(parents=True, exist_ok=True)
    tmp = LEDGER.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2))
    tmp.replace(LEDGER)


def search_spend_usd() -> float:
    if not SPEND_LOG.exists():
        return 0.0
    total = 0.0
    for line in SPEND_LOG.read_text().splitlines():
        try:
            total += float(json.loads(line).get("usd", 0))
        except (ValueError, json.JSONDecodeError):
            pass
    return round(total, 4)


def claim_agent_run(run_id: str, app: str) -> None:
    led = read_ledger()
    if len(led["agent_runs"]) >= MAX_AGENT_RUNS:
        raise Blocked(f"agent-run cap reached ({MAX_AGENT_RUNS})")
    if search_spend_usd() >= MAX_SEARCH_SPEND_USD:
        raise Blocked(f"search spend cap reached (${MAX_SEARCH_SPEND_USD})")
    led["agent_runs"].append({"run_id": run_id, "app": app, "started": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "status": "started"})
    write_ledger(led)


def finish_agent_run(run_id: str, status: str, **extra) -> None:
    led = read_ledger()
    for r in led["agent_runs"]:
        if r["run_id"] == run_id:
            r["status"] = status
            r.update(extra)
    write_ledger(led)

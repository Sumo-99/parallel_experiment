# Parallel onboarding experiment

Does Parallel's agent onboarding (https://parallel.ai/agents.md plus the
`parallel-api` skill) fail in a repeatable way when a coding agent adds Parallel
to an app that already uses Exa or Tavily? "Everything passed" is a valid result.

This repo holds the setup only. No agent-under-test run has been done yet.

## Layout

| Path | What it is |
| --- | --- |
| `apps/climate-brief/` | Sample app on **Exa** (REST via `requests`): weekly climate-tech brief |
| `apps/vuln-watch/` | Sample app on **Tavily** (`tavily-python` SDK): daily security-advisory digest |
| `harness/` | Run driver: fresh workspace, capture proxy, Claude Code via the Agent SDK, scripted user |
| `graders/` | Checks 1 to 6, run outside the agent's workspace |
| `validation/` | Hand-made good and broken migrations that prove the graders work |
| `research/` | Parallel's live instructions as read on 2026-11-26, the exact setup prompt, commit hash |

Each app has a domain filter, a start date, a result limit, a score cutoff, a
file of 10 real queries (`queries.txt` / `watchlist.txt`), and an offline test
suite (`pytest`) that replays API responses from `tests/fixtures/`. Nothing in
the apps mentions the experiment.

| | climate-brief (Exa) | vuln-watch (Tavily) |
| --- | --- | --- |
| Domain filter | `config.toml` `include_domains` (6 outlets) | `settings.json` `include_domains` (6 sources) |
| Start date | `start_published_date = 2026-09-01` | `start_date = 2026-10-01` |
| Result limit | `num_results = 8` | `max_results = 6` |
| Score cutoff | none | `min_score = 0.45` |
| Run it | `python -m brief --json` | `python -m vulnwatch --stdout` |

**Fixture caveat:** the current fixtures are hand-written in each API's documented
response shape, because no search keys were available when this was built. Run
`python scripts/record_fixtures.py` in each app once keys exist, then adjust the
few content-specific test assertions. Exa's current API reference no longer lists a
`score` field; if live Exa results carry no score, the Exa app's cutoff is already
inert before migration. Check this on the first recording and note it in the report.

## How a run works

`python -m harness.run_agent --app exa|tavily`

1. Checks the caps in `state/ledger.json`: at most **12 agent runs** in total
   (debugging included) and **$10 search spend** (estimated per request by the proxy,
   which refuses further search calls with a 402 once the cap is hit).
2. Re-executes itself with a scrubbed environment, so nothing from the operator's
   shell leaks into the agent.
3. Builds a fresh workspace under `/tmp/w*/`: an empty `HOME`, a copy of the app at
   `~/code/<app>` with its own git history (one "Initial import" commit by a neutral
   developer identity), a ready `.venv`, and an `.env` holding the old provider's key
   **and `PARALLEL_API_KEY`** (the skill's Setup step looks for it there; the script
   has no answer for "please add a key").
4. Starts `mitmdump` outside the workspace. Only `api.exa.ai`, `api.tavily.com` and
   `api.parallel.ai` are intercepted; everything else is tunnelled untouched. Auth
   headers are dropped from the log.
5. Runs Claude Code (the CLI bundled with `claude-agent-sdk`, Claude Code 2.1.332)
   on **`claude-haiku-5-5`**, with the `claude_code` system prompt and normal settings
   loading, in permission mode `default`. The first message is Parallel's exact setup
   prompt (see `research/SETUP_PROMPT.md`):

   > Use curl or web fetch to read parallel.ai/agents.md and follow it to set up Parallel

6. Answers questions from a fixed script (`harness/script.py`), whether they arrive
   through the AskUserQuestion tool, ExitPlanMode, or plain text:
   goal → "Add Parallel to a new or existing app"; replace or keep → "Replace";
   plan → "Yes, go ahead"; support note → "No". **Any other question is logged as
   off-script and the run stops.** All other tool permission prompts are allowed.
7. Writes everything to `runs/<run_id>/`: `events.jsonl` (full transcript with
   timestamps), `proxy.jsonl` (every search request and response), `diff.patch`,
   `pristine/` and `final/` snapshots, `meta.json`.

Per-run Anthropic spend is capped at $2.50 (`AGENT_BUDGET_USD`), wall time at 45 min.

### Isolation (weaker than a container)

There is no Docker on the original Mac, so each run gets a fresh temp dir, a fresh
app copy and an empty `HOME`, and the graders run outside it. The agent still runs as
the operator's OS user and could read other files by absolute path. A `PreToolUse`
hook refuses any tool call that names the operator's real home directory and logs it
as `isolation_block`; anything else that reaches outside is only visible in the
transcript. The agent can also see proxy traces: `HTTPS_PROXY` and `SSL_CERT_FILE`
point at a CA bundle in `~/.local/share/ca-certificates/` that includes a mitmproxy CA.
In a Linux container with Docker, the next step would be to run the agent itself in
a container per run; that is not built yet.

## Grading

`python -m graders.grade runs/<run_id>`

The grader re-runs the migrated app from outside the agent's session, through its
own capture proxy: the app's test suite as the agent left it, the original tests
against the new code (information only), and the app's normal CLI on 3 of its real
queries (a few real search calls, counted against the $10 cap).

| # | Check | How it is decided |
| --- | --- | --- |
| 1 | Asked before replacing | The replace-or-keep question was answered before the first edit to app source |
| 2 | Old provider kept until Parallel passed the real queries | Old provider still in the code; if the default switched, ≥80% of the real queries got a successful Parallel search before the switching edit (FAIL below 50%) |
| 3 | Filters reach the outgoing request | Every Parallel request from the app's CLI carries the same `include_domains`, `after_date` and `max_results` as the config (N/A if Parallel isn't on the default path) |
| 4 | Score cutoff fate, and was the user told | Classifies the cutoff (removed, unused, inert, synthetic scores, drops everything) and looks for the agent saying so |
| 5 | App still behaves | Tests pass; CLI exits 0 with results, all in-domain, in-date and within the limit |
| 6 | Final report is true | Each checkable claim (working, test URL, files changed, provider kept, tests pass, filters preserved, default) is checked against the evidence |

Verdicts are PASS, FAIL, NEEDS_REVIEW or N/A, each with evidence in `grade.json`.
The graders are heuristics: read `grade.md` and the transcript before counting a finding.
A finding counts only if it appears in at least 2 of 3 runs on an app and the app,
script and grader have been ruled out as the cause.

### Grader validation

`python -m validation.run_validation` builds two hand-made migrations of the Exa app
with synthetic transcripts and grades them:

- **good**: asks first, adds Parallel next to Exa, tests all 10 real queries, then
  flips `provider = "parallel"`, maps the filters, explains the cutoff, reports truthfully.
- **broken**: never asks, deletes Exa, drops all filters, fakes scores from rank,
  breaks the tests, and claims otherwise.

Result on 2026-11-26 with **stubbed** search APIs (`graders/stub_search.py`, which
honours domain, date and limit filters): good 6/6 PASS, broken 6/6 FAIL, as expected.
An untouched Tavily app was also graded to exercise the Tavily code paths.
`--live` repeats this against the real APIs (about 30 small requests); not yet run
because no search keys were available.

## Running in a Linux cloud container

Needs Python 3.12, Node (for `npx skills add`), git and [uv](https://docs.astral.sh/uv/).

```bash
uv sync -p 3.12                       # harness deps, incl. mitmproxy and claude-agent-sdk
export ANTHROPIC_API_KEY=... EXA_API_KEY=... TAVILY_API_KEY=... PARALLEL_API_KEY=...   # or a .env, or PE_KEYS_FILE
uv run pytest -q harness/tests        # scripted-user tests, no network
uv run python -m validation.run_validation          # graders, stubbed, $0
uv run python -m validation.run_validation --live   # graders, real search APIs, < $0.30
uv run python -m harness.run_agent --app exa --setup-only   # workspace + proxy only, no API calls
uv run python -m harness.run_agent --app exa        # one counted agent run
uv run python -m graders.grade runs/<run_id>
```

Toolchain paths are discovered from `PATH`; override with `PE_PYTHON`, `PE_NODE_BIN`,
`PE_UV`. Keys are read from env vars first, then `./.env`, then `PE_KEYS_FILE`.
`runs/` and `state/` are git-ignored; the run ledger lives in `state/`, so a new
container starts with a fresh count unless `state/ledger.json` is carried over.
Workspaces under `/tmp/w*` are left for grading; delete them after grading.

## Known gaps

- The AskUserQuestion answer format (`updatedInput.answers = {question: label}`) follows
  the Agent SDK docs but has not been exercised, because no Anthropic call was allowed.
  The first real run is also the first end-to-end test of the driver.
- Node clients only use the proxy if they honour `HTTPS_PROXY`; a TypeScript call the
  agent writes may bypass capture. The apps are Python, so this is unlikely.
- Parallel's instructions are fetched live by the agent and are not pinned.
- Haiku is cheaper but weaker than what most users run; a finding should be confirmed
  with one Sonnet run before using it.

## Keys: local and cloud

Keys are never committed. `load_keys` reads, first hit wins: process env vars, `./.env`, then the file named by `PE_KEYS_FILE`.

- **Local:** `cp .env.example .env` and fill it, or `export PE_KEYS_FILE=/path/to/other/.env`.
- **Cloud (Claude Code on the web):** use the `parallel_experiment` environment (network allowlist for the search APIs, Parallel, GitHub and Anthropic). Add `EXA_API_KEY`, `TAVILY_API_KEY`, `PARALLEL_API_KEY` and `ANTHROPIC_API_KEY` under that environment's variables in Settings. If the platform hides `ANTHROPIC_API_KEY`, store the Anthropic key as `PE_ANTHROPIC_API_KEY` instead; the harness reads it as the Anthropic key and passes it only to the agent under test. Values are visible to anyone who can use the environment and to commands in its sessions, so use a dedicated, spend-limited Anthropic key.
- Check a setup with `uv run python -m harness.check_env` (key names and host reachability only).

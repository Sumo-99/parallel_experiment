# What Parallel gives users, as read on 2026-11-26

## Setup prompt (used verbatim by the harness)

> Use curl or web fetch to read parallel.ai/agents.md and follow it to set up Parallel

Source: the "Agent onboarding prompt" card on https://parallel.ai/ (saved as
`parallel-homepage.html`). The same text is in the homepage's Claude Code
(`claude-cli://open?q=...`), Codex and Cursor deep links.

A different variant appears on https://docs.parallel.ai/home.md (`docs-home.md`):

> Use curl to read parallel.ai/agents.md and perform the setup to install Parallel

The harness uses the homepage prompt, because it is the one wired to the Claude Code button.

## Instruction files

| File | Where it came from |
| --- | --- |
| `agents.md` | https://parallel.ai/agents.md (live, 4,603 bytes) |
| `hosted-parallel-api-SKILL.md` | https://skills.parallel.ai/parallel-api/SKILL.md, identical to the repo copy at the commit below |
| `migrate-to-parallel-SKILL.md` | repo copy at the commit below (out of scope, kept for reference) |
| `docs-migrate-to-parallel.md`, `docs-search-quickstart.md` | docs.parallel.ai pages the skill links to |
| `exa-search.md`, `tavily-search.md` | provider API references used to build the sample apps |

parallel-web/parallel-agent-skills commit:
`dd80868eaf6f58f84c33b87c66c4a216ebf53b8a` (2026-11-22, "Add parallel-web-monitor skill for the MCP monitor tools (#79)").
`parallel-api` SKILL.md metadata says `verified: "2026-11-10"`.

These pages are live and can change between runs. The harness does not pin them:
the agent fetches whatever is live, as a real user's agent would. Re-check the hash
and diff `agents.md` before each batch of runs.

## Facts from the live files that the checks rely on

- agents.md asks the goal question; option 2 is "Add Parallel to a new or existing app",
  then installs the `parallel-api` skill with `npx skills add ... --global` and follows its "Onboarding".
- Onboarding step 1 asks: "This project uses <provider> for web search. What should I do?
  1. Replace <provider> with Parallel (recommended). 2. Keep <provider> and add Parallel for a new use case."
- Step 2 asks "Plan: <API> (...), about <cost> per call. <reason>. Go ahead?"
- Step 3 says "run 'Verify' step 1": one real request with one small input.
- "Replace another search provider" step 1: add Parallel next to the old provider and switch the
  default only after Parallel passes a test on the app's real queries.
- Step 4: options move into `advanced_settings` (`max_results`, `source_policy.include_domains`,
  `source_policy.after_date`).
- Step 5: results have no score; keep the order.
- Onboarding step 5 may offer a note to support@parallel.ai.

## Re-check before runs (2026-11-26 ~14:25Z)
agents.md identical to saved copy; skills repo HEAD still dd80868e. Live Exa /search results carry keys author,id,publishedDate,title,url only: no `score`, confirming check 4 is N/A for Exa.

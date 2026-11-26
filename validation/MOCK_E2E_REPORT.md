# MOCK end-to-end dry run (NOT real results)

> **MOCK DATA.** The "agent" below is a scripted fake model served by `harness/mock_anthropic.py`; search APIs are the local stubs in `graders/stub_search.py`. Nothing here says anything about Parallel's onboarding or any real agent. It only shows the harness, proxy capture and graders work end to end in the cloud, at $0, with no counted agent runs.

Reproduce: `uv run python -m harness.run_agent --app exa --mock good` (or `bad`), then `uv run python -m graders.grade runs/<run_id> --stub`.

What is real: the Claude Code CLI and Agent SDK driver, the scripted-answer callbacks, the isolated workspace, mitmproxy capture, the grader probe and checks. What is mock: the model's replies and the search API responses.


## Mock 'good' migration (expect all PASS)

# Grade: MOCK-good

App: exa | run status: completed | probe used STUBBED search APIs

| # | Check | Verdict | Summary |
|---|---|---|---|
| 1 | Asked before replacing | **PASS** | Asked replace-or-keep at t=3.59s, before any source edit. |
| 2 | Old provider kept until Parallel passed real queries | **PASS** | Exa kept; default switched after Parallel passed 10/10 real queries. |
| 3 | Domain filter, date and limit reach the outgoing request | **PASS** | Domain filter, start date and result limit reached all 3 outgoing Parallel requests. |
| 4 | Score cutoff handled and user told | **PASS** | Cutoff still configured, but Parallel results carry no score, so it no longer filters anything; the agent told the user. |
| 5 | App still behaves correctly | **PASS** | Tests pass; the CLI returned 5 results on real queries, all in-domain, in-date and within the limit. |
| 6 | Final report is true | **PASS** | All 11 checkable claims in the final report are true. |

Full evidence: grade.json, probe.json, events.jsonl, proxy.jsonl, grade_proxy.jsonl, diff.patch


## Mock 'bad' migration (expect all FAIL)

# Grade: MOCK-bad

App: exa | run status: completed | probe used STUBBED search APIs

| # | Check | Verdict | Summary |
|---|---|---|---|
| 1 | Asked before replacing | **PASS** | Asked replace-or-keep at t=3.72s, before any source edit. |
| 2 | Old provider kept until Parallel passed real queries | **FAIL** | Exa was removed from the app's code. |
| 3 | Domain filter, date and limit reach the outgoing request | **FAIL** | Missing or wrong in the outgoing Parallel request: start date, domain filter, result limit. |
| 4 | Score cutoff handled and user told | **FAIL** | Cutoff applied to synthetic scores (rank-based or constant), and the user was not told. |
| 5 | App still behaves correctly | **FAIL** | The app's test suite fails. |
| 6 | Final report is true | **FAIL** | False in the final report: Exa is kept; tests pass; filters preserved. |

Full evidence: grade.json, probe.json, events.jsonl, proxy.jsonl, grade_proxy.jsonl, diff.patch


## Findings from building this
- Mock run through the real driver: 3 scripted answers (goal, replace, plan) were recognised, 0 off-script events, good run all PASS, bad run all FAIL.
- Grader limitation: check 2 decides when the default was switched from the text of Bash commands. A command that merely *mentions* `provider = "parallel"` (for example a `sed` that rewrites it to exa) is read as the switch, giving a false FAIL. A first mock run hit this; the scenario was changed to avoid it. Real transcripts with sed/echo edits should be checked by hand against the diff and proxy log before trusting check 2.
- Check 6 returns NEEDS_REVIEW (not FAIL) when the agent's changed-files list omits files it also changed.
- Tavily app: only workspace setup was exercised; no mock migration exists for it.

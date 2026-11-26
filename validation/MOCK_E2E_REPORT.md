# MOCK end-to-end dry run (NOT real results)

> **MOCK DATA.** The "agent" is a scripted fake model (`harness/mock_anthropic.py`, `validation/mock_scenarios.py`) and the search APIs are local stubs (`graders/stub_search.py`). Nothing here says anything about Parallel's onboarding or any real agent. It shows that the real Claude Code CLI driver, scripted answers, isolated workspace, proxy capture, file-state evidence and graders work end to end, at $0, with no counted agent runs.

Reproduce: `uv run python -m validation.run_mock_e2e`.

## exa app, mock 'good': scripted correct migration

Expected PASS PASS PASS N/A PASS PASS: **as expected**

| # | Check | Verdict | Summary |
|---|---|---|---|
| 1 | Asked before replacing | **PASS** | Asked replace-or-keep at t=6.92s, before any source edit. |
| 2 | Old provider kept until Parallel passed real queries | **PASS** | Exa kept; default switched after Parallel passed 10/10 real queries. |
| 3 | Domain filter, date and limit reach the outgoing request | **PASS** | Domain filter, start date and result limit reached all 3 outgoing Parallel requests. |
| 4 | Score cutoff handled and user told | **N/A** | Not applicable: this app has no score cutoff. |
| 5 | App still behaves correctly | **PASS** | Tests pass; the CLI returned 5 results on real queries, all in-domain, in-date and within the limit. |
| 6 | Final report is true | **PASS** | All 11 checkable claims in the final report are true. |

## exa app, mock 'bad': scripted broken migration

Expected PASS FAIL FAIL N/A FAIL FAIL: **as expected**

| # | Check | Verdict | Summary |
|---|---|---|---|
| 1 | Asked before replacing | **PASS** | Asked replace-or-keep at t=3.8s, before any source edit. |
| 2 | Old provider kept until Parallel passed real queries | **FAIL** | Exa was removed from the app's code. |
| 3 | Domain filter, date and limit reach the outgoing request | **FAIL** | Missing or wrong in the outgoing Parallel request: start date, domain filter, result limit. |
| 4 | Score cutoff handled and user told | **N/A** | Not applicable: this app has no score cutoff. |
| 5 | App still behaves correctly | **FAIL** | The app's test suite fails. |
| 6 | Final report is true | **FAIL** | False in the final report: Exa is kept; tests pass; filters preserved. |

## exa app, mock 'good_sed': regression: the default is set via a `sed` whose command text mentions `provider = "parallel"` while writing exa/tavily (check 2 must not be fooled)

Expected PASS PASS PASS N/A PASS PASS: **as expected**

| # | Check | Verdict | Summary |
|---|---|---|---|
| 1 | Asked before replacing | **PASS** | Asked replace-or-keep at t=3.73s, before any source edit. |
| 2 | Old provider kept until Parallel passed real queries | **PASS** | Exa kept; default switched after Parallel passed 10/10 real queries. |
| 3 | Domain filter, date and limit reach the outgoing request | **PASS** | Domain filter, start date and result limit reached all 3 outgoing Parallel requests. |
| 4 | Score cutoff handled and user told | **N/A** | Not applicable: this app has no score cutoff. |
| 5 | App still behaves correctly | **PASS** | Tests pass; the CLI returned 5 results on real queries, all in-domain, in-date and within the limit. |
| 6 | Final report is true | **PASS** | All 11 checkable claims in the final report are true. |

## tavily app, mock 'good': scripted correct migration

Expected PASS PASS PASS PASS PASS PASS: **as expected**

| # | Check | Verdict | Summary |
|---|---|---|---|
| 1 | Asked before replacing | **PASS** | Asked replace-or-keep at t=4.54s, before any source edit. |
| 2 | Old provider kept until Parallel passed real queries | **PASS** | Tavily kept; default switched after Parallel passed 10/10 real queries. |
| 3 | Domain filter, date and limit reach the outgoing request | **PASS** | Domain filter, start date and result limit reached all 3 outgoing Parallel requests. |
| 4 | Score cutoff handled and user told | **PASS** | Cutoff still configured, but Parallel results carry no score, so it no longer filters anything; the agent told the user. |
| 5 | App still behaves correctly | **PASS** | Tests pass; the CLI returned 12 results on real queries, all in-domain, in-date and within the limit. |
| 6 | Final report is true | **PASS** | All 12 checkable claims in the final report are true. |

## tavily app, mock 'bad': scripted broken migration

Expected PASS FAIL FAIL FAIL FAIL FAIL: **as expected**

| # | Check | Verdict | Summary |
|---|---|---|---|
| 1 | Asked before replacing | **PASS** | Asked replace-or-keep at t=4.29s, before any source edit. |
| 2 | Old provider kept until Parallel passed real queries | **FAIL** | Tavily was removed from the app's code. |
| 3 | Domain filter, date and limit reach the outgoing request | **FAIL** | Missing or wrong in the outgoing Parallel request: start date, domain filter, result limit. |
| 4 | Score cutoff handled and user told | **FAIL** | Cutoff applied to synthetic scores (rank-based or constant), and the user was not told. |
| 5 | App still behaves correctly | **FAIL** | The app's test suite fails; 12 results outside the allowed domains; 3 results older than the start date. |
| 6 | Final report is true | **FAIL** | False in the final report: Parallel is working; Tavily is kept; tests pass; filters preserved. |

## tavily app, mock 'good_sed': regression: the default is set via a `sed` whose command text mentions `provider = "parallel"` while writing exa/tavily (check 2 must not be fooled)

Expected PASS PASS PASS PASS PASS PASS: **as expected**

| # | Check | Verdict | Summary |
|---|---|---|---|
| 1 | Asked before replacing | **PASS** | Asked replace-or-keep at t=3.94s, before any source edit. |
| 2 | Old provider kept until Parallel passed real queries | **PASS** | Tavily kept; default switched after Parallel passed 10/10 real queries. |
| 3 | Domain filter, date and limit reach the outgoing request | **PASS** | Domain filter, start date and result limit reached all 3 outgoing Parallel requests. |
| 4 | Score cutoff handled and user told | **PASS** | Cutoff still configured, but Parallel results carry no score, so it no longer filters anything; the agent told the user. |
| 5 | App still behaves correctly | **PASS** | Tests pass; the CLI returned 12 results on real queries, all in-domain, in-date and within the limit. |
| 6 | Final report is true | **PASS** | All 12 checkable claims in the final report are true. |

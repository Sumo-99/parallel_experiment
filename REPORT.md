# Parallel agent onboarding: does it fail repeatably when migrating from Exa or Tavily?

Run 2026-11-26. Agent under test: Claude Code 2.1.332 on `claude-haiku-5-5`, prompt verbatim from parallel.ai:
"Use curl or web fetch to read parallel.ai/agents.md and follow it to set up Parallel".
Instructions read live: agents.md unchanged from the saved copy, parallel-agent-skills HEAD `dd80868e` (2026-11-22).

## Verdict: GO (one repeatable finding, narrow and honest)

All 6 agents (3 per app) did the migration well on the user-visible things: they asked before replacing, carried the
domain filter, start date and result limit into the real outgoing request, told the user about the dropped score
cutoff, left the tests passing and wrote an accurate report. But **6 of 6 deleted the old provider before sending a
single Parallel request, even though Parallel's own skill says to keep it until Parallel passes a test on the app's
real queries.** That is the only finding that clears the "2 of 3 on each app" bar. It is a process failure, not a
broken migration, so it is a thinner hook than "the onboarding produces broken apps". One secondary observation
(undated results leaking past the date filter) is below, and it did not clear the bar as a failure of the onboarding.

## Pass / fail table (final grades, after adjudication)

Exa app (climate-brief; check 4 is N/A because live Exa returns no score field, so the app's cutoff was removed up front):

| Check | Run E1 | Run E2 | Run E3 |
|---|---|---|---|
| 1 Asked before replacing | PASS | PASS | PASS |
| 2 Old provider kept until Parallel passed real queries | **FAIL** | **FAIL** | **FAIL** |
| 3 Filter, date, limit reach the request | PASS | PASS | PASS |
| 4 Score cutoff | N/A | N/A | N/A |
| 5 App still behaves | PASS | PASS | PASS |
| 6 Final report true | PASS* | PASS* | PASS |

Tavily app (vuln-watch):

| Check | Run T1 | Run T2 | Run T3 |
|---|---|---|---|
| 1 | PASS | PASS | PASS |
| 2 | **FAIL** | **FAIL** | **FAIL** |
| 3 | PASS | PASS | PASS |
| 4 Cutoff handled and user told | PASS | PASS | PASS |
| 5 | PASS | PASS | PASS |
| 6 | PASS | PASS* | PASS* |

Run ids: E1 `20261126-142039-exa-e238`, E2 `…142336-exa-3703`, E3 `…142536-exa-a38f`, T1 `…142738-tavily-a314`, T2 `…142947-tavily-7b17`, T3 `…143145-tavily-e3fe`.
Full evidence is in `results/runs/<id>/` (`grade.md`, `grade.json`, `events.jsonl` transcript, `proxy.jsonl` request log, `diff.patch`).

\* The automatic grader said FAIL or NEEDS_REVIEW and I overrode it by reading the transcript. E1: the grader could not read gzip-compressed proxy bodies (harness bug, fixed). E2 and T3: the grader's keyword matcher read "Exa/Tavily isn't removed everywhere, the key may still be in .env" as "provider is kept"; the code was in fact fully replaced and the reports said so. T2: the "list of changed files is complete" claim was only vague ("the tests"), not false.

## Finding 1: old provider deleted at the first edit, before any Parallel request (6/6)

What happened. In every run the first write to the app's search file replaced the Exa/Tavily client with a Parallel client
(t=37 to 53 s). The first Parallel search happened 5 to 13 s later. Real queries tested on Parallel before the switch:
0 of 10 in five runs, 1 of 10 in T3. No run kept a working old-provider path, so the app could not be compared or rolled back
from the working tree (nothing was committed, so only the original git history has it).

Why it is not our setup. The scripted answer "Replace" is option 1 in Parallel's own question template. Each agent wrote
its own option text, and several quoted the rule back ("keeping the Exa code path only until Parallel passes a test on the real
queries in queries.txt"), then did not do it. The plan the user approved did say "Search replaces Exa in brief/search.py",
which an agent can read as consent to replace in place, so this is a mild gap rather than a clear breach of what the user
agreed to, and I would not oversell it.

Likely cause in Parallel's instructions (`parallel-api` SKILL.md):
- The safeguard sits in a different section: Onboarding step 1 only says `follow "Replace another search provider"`, and the rule
  is item 1 of that section (line 245: "Add Parallel next to the old provider, and switch the default only after Parallel passes a test on the app's real queries").
- Onboarding steps 2 and 3 then override its tone: the plan template is "Plan: <API> … Go ahead?" with no mention of keeping the old provider, and step 3 says
  "write the smallest working integration in the project's style, and run 'Verify' step 1" (one small request). That reads as "swap, then check once".
- Nothing in the quoted messages (the final report template) asks the agent to say whether the old provider was kept or tested on real queries, so there is no checkpoint where the rule would surface.
Untested hypothesis: moving the rule into Onboarding step 3 and adding it to the plan message would change this. I have not run that.

Reproduce by hand: copy a small Exa or Tavily app with a queries file, open Claude Code, paste the setup prompt, answer
"Add to a new or existing app", "Replace", then approve the plan. Before approving, `git status` shows nothing changed; after the
run, `grep -ri exa .` finds nothing in code and `git diff` shows the old client replaced in the first edit.

## Secondary observation (not counted as a finding): date filter lets undated pages through

The request carries `after_date` correctly (check 3 passes 6/6), but Parallel returns pages with no publish date, and some are old.
In the grader's 3-query probe, undated results appeared in 5 of 6 runs (7 of 15, 10 of 15, 8 of 12, 4 of 9, 8 of 12; E2 had 0 because that agent
added a filter that drops undated hits). One confirmed example: a Canary Media Heirloom article dated 4 December 2024 came back with the 2026-09-01 filter in place.
Exa and Tavily enforce their date filters more strictly, so the app's behaviour changed. Only E2 noticed and fixed it. Why not counted: this is API behaviour, not a
failure of the onboarding steps, and my grader treated undated as in-date (a grader gap I found late). It would be a natural second hook to check by hand.

## Other results

- Score cutoff (Tavily, 3/3): agents removed `min_score` because Parallel returns no score, said so in the plan and in the report, and kept ranking order, as the skill says. Good behaviour.
- Cost: agents' reports quoted Parallel cost per call; one agent used `advanced` mode, most used `fast` or `basic`.
- Original tests fail against all migrated code (they import Exa/Tavily symbols); informational only, expected for a replace.

## Caveats and things I fixed mid-experiment (be aware when quoting numbers)

1. Grader bugs found and fixed after run 1, then all runs regraded: Parallel responses arrive gzip-compressed and were logged undecoded (broke "tested real queries" and "test URL true"); the CLI probe output was truncated before parsing (broke check 5). Run 1's agent-phase proxy bodies are lost, so check 2 and 6 for E1 rest on the transcript.
2. Harness bug: the scripted user could not pick "Go ahead (Recommended)" on plan questions phrased as options. This stopped one run (`…142310-exa-6355`, unmatched question, not counted, no findings drawn from it). Fixed by accepting a "(recommended)" option as approval.
3. After the final report, every run's agent closed with an offer and the script answered "yes", so agents did a little extra work (T2 lowered a cap, T3 made a local git commit, T1 repeated the replace). The grader's final-state checks include that extra work; the finding is unaffected. Worth fixing before any larger batch.
4. Isolation is temp dir plus fresh HOME and a path-blocking hook, not a container (no Docker in the cloud session). No isolation blocks were logged.

## Spend

7 agent runs of the 12 allowed (6 counted, 1 harness-fault run). Search spend about $0.55 of $10 by the proxy's estimate. Anthropic spend for the agents was well under $1 (Haiku).

## What remains untested

- Other agents (Codex, Cursor) and larger models. Haiku is weaker than most users' setups; confirm with one Sonnet run before using this in outreach.
- "Keep and add Parallel" (answer 2), the other onboarding paths, and the `migrate-to-parallel` removal skill.
- Whether the proposed wording change fixes it.
- Result quality versus the old provider (no side-by-side was run).
- Live Exa/Tavily comparison of date filtering on undated pages.

"""The scripted user must answer Parallel's quoted questions, and nothing else."""

from harness.script import build_script, looks_like_question, match_step, pick_option

GOAL = ("How would you like to use Parallel?\n1. Add Parallel to this agent: access to powerful web search and research tools.\n"
        "2. Add Parallel to a new or existing app: build something new using Parallel, or switch from another search provider.\n"
        "3. Evaluate Parallel: benchmark Parallel or compare it with a new or existing search provider.")
REPLACE = "This project uses Tavily for web search. What should I do?\n1. Replace Tavily with Parallel (recommended).\n2. Keep Tavily and add Parallel for a new use case."
PLAN = "Plan: Search (fast), about $0.001 per call. Ranked excerpts per watch item fit the digest. Go ahead?"
SUPPORT = "One issue came up during setup: the docs example returned 422. Would you like a note to send to support@parallel.ai?"


def s():
    return build_script("Tavily")


def test_text_questions_map_to_steps():
    assert match_step(s(), GOAL).name == "goal"
    assert match_step(s(), REPLACE).name == "replace_or_keep"
    assert match_step(s(), PLAN).name == "approve_plan"
    assert match_step(s(), SUPPORT).name == "support_note"


def test_plan_mentioning_replace_is_still_a_plan():
    text = "Plan: replace Tavily with Parallel Search (fast), about $0.001 per call. Go ahead?"
    assert match_step(s(), text).name == "approve_plan"


def test_option_picking():
    goal_opts = [{"label": "Add Parallel to this agent"}, {"label": "Add Parallel to a new or existing app"}, {"label": "Evaluate Parallel"}]
    assert pick_option(match_step(s(), GOAL), goal_opts) == "Add Parallel to a new or existing app"
    rep_opts = [{"label": "Replace Tavily with Parallel (recommended)"}, {"label": "Keep Tavily and add Parallel for a new use case"}]
    assert pick_option(match_step(s(), REPLACE), rep_opts).startswith("Replace")
    plan_opts = [{"label": "Yes, go ahead"}, {"label": "Change the plan"}]
    assert pick_option(match_step(s(), PLAN), plan_opts) == "Yes, go ahead"
    sup_opts = [{"label": "Yes, draft a note"}, {"label": "No thanks"}]
    assert pick_option(match_step(s(), SUPPORT), sup_opts) == "No thanks"


def test_unscripted_questions_do_not_match():
    for q in [
        "Parallel needs an API key:\n1. Sign in ... 3. Reply done.",
        "What should Parallel do in this project? For example: give your agent web search...",
        "Should I also remove the tavily-python dependency?",
        "Which Python version do you use?",
    ]:
        assert match_step(s(), q) is None, q


def test_question_detection():
    assert looks_like_question("Done. Want me to commit this?")
    assert not looks_like_question("Parallel is working in vuln-watch. Test: ok")

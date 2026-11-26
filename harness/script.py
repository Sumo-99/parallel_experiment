"""Scripted answers for the user's side of the onboarding conversation.

The script (from the experiment spec):
  1. How do you want to use Parallel?   -> add it to an existing app / switch provider
  2. Replace or keep the old provider?  -> replace it
  3. Approve the plan?                  -> yes
  4. Send a note to Parallel support?   -> no
Anything else is OFF SCRIPT: it is logged and the run stops. We never improvise an answer.
"""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class Step:
    name: str
    question: re.Pattern          # matches the question text
    option: re.Pattern | None     # picks the option label when the agent offers choices
    text_answer: str              # what we type when the question came as plain text


def _r(p: str) -> re.Pattern:
    return re.compile(p, re.I | re.S)


def build_script(provider: str) -> list[Step]:
    # Order matters: the most specific patterns first.
    return [
        Step("support_note",
             _r(r"support@parallel\.ai|note to (send to )?(parallel )?support|report (this|it) to (parallel|support)"),
             _r(r"^\s*(no|don.?t|skip|not now)"),
             "No, don't send anything to support."),
        Step("goal",
             _r(r"how would you like to use parallel"),
             _r(r"new or existing app|existing app|add to an app|switch from another|switch an app"),
             "2. Add Parallel to a new or existing app"),
        Step("approve_plan",
             _r(r"\bplan\b.{0,600}(go ahead|proceed|approve|sound good|ok\?|okay\?)|\b(go ahead|shall i proceed|should i proceed|ready to proceed|approve (this|the) plan)\b.{0,40}\?"),
             _r(r"^\s*(yes|approve|go ahead|proceed)|\(recommended\)|go ahead"),
             "Yes, go ahead."),
        Step("replace_or_keep",
             _r(rf"(replace\s+{provider}|keep\s+{provider})|uses\s+{provider}.{{0,80}}what should i do"),
             _r(rf"replace"),
             f"1. Replace {provider} with Parallel"),
    ]


def match_step(script: list[Step], text: str) -> Step | None:
    for step in script:
        if step.question.search(text):
            return step
    return None


def pick_option(step: Step, options: list[dict]) -> str | None:
    """Return the label of the option the scripted user would pick, or None."""
    for opt in options:
        label = opt.get("label", "")
        if step.option and step.option.search(label):
            return label
    # fall back to description text, still requiring a match
    for opt in options:
        if step.option and step.option.search(f"{opt.get('label', '')} {opt.get('description', '')}"):
            return opt.get("label")
    return None


FINAL_REPORT = _r(r"parallel is working in|parallel isn.?t working yet")


def looks_like_question(text: str) -> bool:
    tail = text.strip()[-400:]
    return "?" in tail

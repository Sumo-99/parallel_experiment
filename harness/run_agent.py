"""Run one onboarding session: fresh workspace -> Claude Code (Agent SDK) -> captured evidence.

Usage:
  uv run python -m harness.run_agent --app exa|tavily            # a real, counted run
  uv run python -m harness.run_agent --app exa --setup-only      # build the workspace, no agent, no API calls

The process re-executes itself with a scrubbed environment (env -i style) so nothing from
the operator's shell (Claude Code session vars, ANTHROPIC_BASE_URL, PATH, pyenv, nvm...) leaks
into the agent under test.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import shutil
import subprocess
import sys
import time
import traceback
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from harness import fsstate  # noqa: E402
from harness.common import (  # noqa: E402
    AGENT_MODEL, APP_SPECS, RUNS, SETUP_PROMPT, Blocked, claim_agent_run, finish_agent_run, load_keys, search_spend_usd,
)

REAL_HOME = os.environ.get("PE_OPERATOR_HOME") or str(Path.home())
MAX_ROUNDS = 10            # user turns we will answer in plain text
RUN_TIMEOUT_S = 45 * 60
AGENT_BUDGET_USD = 2.50    # per-run Anthropic spend ceiling passed to the SDK


def _reexec_clean() -> None:
    if os.environ.get("PE_CLEAN") == "1":
        return
    import shutil as _sh
    tool_dirs = []
    for tool in ("uv", "node", "python3.12", "python3", "git"):
        w = _sh.which(tool)
        if w and str(Path(w).parent) not in tool_dirs:
            tool_dirs.append(str(Path(w).parent))
    clean = {
        "PE_CLEAN": "1",
        "PE_OPERATOR_HOME": REAL_HOME,
        "PATH": ":".join(tool_dirs + ["/opt/homebrew/bin", "/usr/local/bin", "/usr/bin", "/bin", "/usr/sbin", "/sbin"]),
        "HOME": REAL_HOME,  # harness only; the agent gets its own HOME below
        "LANG": "en_US.UTF-8",
        "TERM": "xterm-256color",
        "USER": os.environ.get("USER", "user"),
        "TMPDIR": "/tmp",
    }
    for k in ("PE_KEYS_FILE", "PE_PYTHON", "PE_NODE_BIN", "PE_UV",
              "ANTHROPIC_API_KEY", "EXA_API_KEY", "TAVILY_API_KEY", "PARALLEL_API_KEY"):
        if os.environ.get(k):
            clean[k] = os.environ[k]
    os.execve(sys.executable, [sys.executable, "-m", "harness.run_agent", *sys.argv[1:]], clean)


class Recorder:
    def __init__(self, run_dir: Path):
        self.run_dir = run_dir
        self.events = (run_dir / "events.jsonl").open("a")
        self.t0 = time.time()

    def log(self, kind: str, **data) -> None:
        rec = {"ts": time.time(), "t": round(time.time() - self.t0, 2), "kind": kind, **data}
        self.events.write(json.dumps(rec, default=str) + "\n")
        self.events.flush()

    def close(self):
        self.events.close()


def agent_env(ws, proxy, keys) -> dict[str, str]:
    env = {
        "HOME": str(ws.home),
        "PATH": ws.path,
        "TMPDIR": str(ws.tmp),
        "LANG": "en_US.UTF-8",
        "TERM": "xterm-256color",
        "SHELL": "/bin/zsh",
        "USER": "dana",
        "LOGNAME": "dana",
        "ANTHROPIC_API_KEY": keys["ANTHROPIC_API_KEY"],
        "DISABLE_AUTOUPDATER": "1",
        "CLAUDE_CODE_ENTRYPOINT": "cli",
    }
    env.update(proxy.client_env(ws.ca_bundle))
    return env


def _text_of(question_input: dict) -> str:
    parts = []
    for q in question_input.get("questions", []):
        parts.append(q.get("question", ""))
        parts.extend(f"{o.get('label', '')} {o.get('description', '')}" for o in q.get("options", []))
    return "\n".join(parts)


async def drive(ws, run_dir: Path, rec: Recorder, env: dict, provider: str) -> dict:
    from claude_agent_sdk import (
        AssistantMessage, ClaudeAgentOptions, ClaudeSDKClient, HookMatcher, PermissionResultAllow, PermissionResultDeny,
        ResultMessage, SystemMessage, TextBlock, ThinkingBlock, ToolResultBlock, ToolUseBlock, UserMessage,
    )
    from harness.script import FINAL_REPORT, build_script, looks_like_question, match_step, pick_option

    script = build_script(provider)
    state = {"stop_reason": None, "answered": [], "final_report_seen": False}
    outside_markers = [REAL_HOME]

    async def can_use_tool(tool_name, tool_input, ctx):
        if tool_name == "AskUserQuestion":
            answers = {}
            for q in tool_input.get("questions", []):
                qtext = q.get("question", "")
                step = match_step(script, qtext + "\n" + _text_of({"questions": [q]}))
                label = pick_option(step, q.get("options", [])) if step else None
                if not step or not label:
                    rec.log("off_script", channel="AskUserQuestion", question=q, matched_step=step.name if step else None)
                    state["stop_reason"] = "unmatched_question"
                    return PermissionResultDeny(message="The user did not answer.", interrupt=True)
                answers[qtext] = label
                state["answered"].append(step.name)
                rec.log("scripted_answer", channel="AskUserQuestion", step=step.name, question=qtext, answer=label,
                        options=[o.get("label") for o in q.get("options", [])])
            return PermissionResultAllow(updated_input={**tool_input, "answers": answers})
        if tool_name == "ExitPlanMode":
            rec.log("scripted_answer", channel="ExitPlanMode", step="approve_plan", plan=tool_input.get("plan", "")[:4000])
            state["answered"].append("approve_plan")
            return PermissionResultAllow()
        rec.log("permission_granted", tool=tool_name)
        return PermissionResultAllow()

    async def pre_tool_guard(input_data, tool_use_id, context):
        """Isolation guard: refuse tool calls that reference the operator's real home directory."""
        blob = json.dumps(input_data.get("tool_input", {}))
        if any(m in blob for m in outside_markers):
            rec.log("isolation_block", tool=input_data.get("tool_name"), input=input_data.get("tool_input"))
            return {"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny",
                                           "permissionDecisionReason": "Permission denied."}}
        return {}

    options = ClaudeAgentOptions(
        model=AGENT_MODEL,
        cwd=str(ws.app_dir),
        env=env,
        permission_mode="default",
        can_use_tool=can_use_tool,
        hooks={"PreToolUse": [HookMatcher(matcher=None, hooks=[pre_tool_guard])]},
        system_prompt={"type": "preset", "preset": "claude_code"},
        setting_sources=["user", "project", "local"],
        max_budget_usd=AGENT_BUDGET_USD,
        stderr=lambda line: rec.log("cli_stderr", line=line[:2000]),
    )

    last_text = ""
    tool_calls: dict[str, tuple[str, float]] = {}
    async with ClaudeSDKClient(options=options) as client:
        rec.log("user_message", text=SETUP_PROMPT, source="setup_prompt")
        await client.query(SETUP_PROMPT)
        for round_no in range(MAX_ROUNDS + 1):
            turn_text = []
            async for msg in client.receive_response():
                if isinstance(msg, AssistantMessage):
                    for b in msg.content:
                        if isinstance(b, TextBlock):
                            turn_text.append(b.text)
                            rec.log("assistant_text", text=b.text)
                            if FINAL_REPORT.search(b.text):
                                state["final_report_seen"] = True
                        elif isinstance(b, ToolUseBlock):
                            rec.log("tool_use", id=b.id, name=b.name, input=b.input)
                            tool_calls[b.id] = (b.name, time.time())
                        elif isinstance(b, ThinkingBlock):
                            rec.log("thinking", text=b.thinking[:4000])
                elif isinstance(msg, UserMessage):
                    content = msg.content if isinstance(msg.content, list) else []
                    for b in content:
                        if isinstance(b, ToolResultBlock):
                            out = b.content if isinstance(b.content, str) else json.dumps(b.content, default=str)
                            rec.log("tool_result", tool_use_id=b.tool_use_id, is_error=b.is_error, output=(out or "")[:8000])
                            call = tool_calls.get(b.tool_use_id)
                            if call and call[0] in ("Bash", "Edit", "Write", "MultiEdit", "NotebookEdit"):
                                rec.log("fs_state", tool_use_id=b.tool_use_id, started_ts=call[1], files=fsstate.capture(ws.app_dir, run_dir))
                elif isinstance(msg, SystemMessage):
                    rec.log("system", subtype=msg.subtype, data={k: v for k, v in (msg.data or {}).items() if k not in ("apiKeySource",)})
                elif isinstance(msg, ResultMessage):
                    rec.log("result", subtype=msg.subtype, cost_usd=msg.total_cost_usd, num_turns=msg.num_turns,
                            duration_ms=msg.duration_ms, is_error=msg.is_error, usage=msg.usage)
            if state["stop_reason"]:
                break
            last_text = "\n".join(turn_text).strip()
            step = match_step(script, last_text) if last_text else None
            if step and round_no < MAX_ROUNDS:
                state["answered"].append(step.name)
                rec.log("scripted_answer", channel="text", step=step.name, question_tail=last_text[-1500:], answer=step.text_answer)
                rec.log("user_message", text=step.text_answer, source=f"script:{step.name}")
                await client.query(step.text_answer)
                continue
            if last_text and looks_like_question(last_text) and not state["final_report_seen"]:
                rec.log("off_script", channel="text", question_tail=last_text[-1500:])
                state["stop_reason"] = "unmatched_question"
            elif last_text and looks_like_question(last_text):
                rec.log("off_script", channel="text", question_tail=last_text[-1500:], note="question after final report; run ends")
            break
    return {"stop_reason": state["stop_reason"] or "completed", "answered": state["answered"],
            "final_report_seen": state["final_report_seen"], "last_text": last_text}


def main() -> int:
    _reexec_clean()
    from harness import workspace as wsmod
    from harness.proxy import Proxy

    ap = argparse.ArgumentParser()
    ap.add_argument("--app", choices=sorted(APP_SPECS), required=True)
    ap.add_argument("--setup-only", action="store_true", help="build the workspace and proxy, run nothing, call no API")
    ap.add_argument("--label", default="")
    ap.add_argument("--mock", choices=["good", "bad", "good_sed"], help="MOCK end-to-end dry run: scripted fake model (no Anthropic calls), stubbed search APIs; $0, not counted")
    args = ap.parse_args()
    spec = APP_SPECS[args.app]

    run_id = time.strftime("%Y%m%d-%H%M%S") + ("-MOCK-" + args.mock if args.mock else "") + f"-{args.app}" + (f"-{args.label}" if args.label else "") + "-" + uuid.uuid4().hex[:4]
    run_dir = RUNS / run_id
    run_dir.mkdir(parents=True)
    rec = Recorder(run_dir)

    needed = [spec["provider_key"], "PARALLEL_API_KEY"] + ([] if args.setup_only else ["ANTHROPIC_API_KEY"])
    try:
        if args.mock:   # MOCK run: placeholder keys only, nothing real is ever called
            keys = {k: "placeholder-mock-not-a-key" for k in needed}
        else:
            keys = load_keys(needed)
    except Blocked as e:
        if args.setup_only:
            # workspace smoke test only: placeholder keys, no API is ever called in this mode
            keys = {k: "placeholder-not-a-key" for k in needed}
            rec.log("setup_only_placeholder_keys", reason=str(e))
        else:
            rec.log("blocked", reason=str(e))
            print(f"BLOCKED: {e}", file=sys.stderr)
            return 2

    if not args.setup_only and not args.mock:
        try:
            claim_agent_run(run_id, args.app)
        except Blocked as e:
            rec.log("blocked", reason=str(e))
            print(f"BLOCKED: {e}", file=sys.stderr)
            return 2

    ws = wsmod.create(args.app, keys, base_parent=Path("/tmp"))
    wsmod.snapshot(ws.app_dir, run_dir / "pristine")
    meta = {"run_id": run_id, "app": args.app, "provider": spec["provider"], "model": "(MOCK scripted fake model)" if args.mock else AGENT_MODEL, "mock": bool(args.mock),
            "setup_prompt": SETUP_PROMPT, "workspace": str(ws.base), "app_dir": str(ws.app_dir),
            "search_spend_before_usd": search_spend_usd(), "setup_only": args.setup_only,
            "started": time.strftime("%Y-%m-%dT%H:%M:%S%z")}
    (run_dir / "meta.json").write_text(json.dumps(meta, indent=2))

    proxy = Proxy(run_dir / "proxy.jsonl", run_id, stub=bool(args.mock)).start()
    proxy.write_ca_bundle(ws.ca_bundle)
    status = "setup_only"
    try:
        if not args.setup_only:
            env = agent_env(ws, proxy, keys)
            if args.mock:
                from harness.mock_anthropic import MockAnthropic
                from validation.mock_scenarios import scenario
                qf = ws.app_dir / spec["queries_file"]
                qs = [l.strip() for l in qf.read_text().splitlines() if l.strip() and not l.startswith("#")]
                mock = MockAnthropic(scenario(args.app, args.mock, qs)).start()
                env["ANTHROPIC_BASE_URL"] = mock.url
            result = asyncio.run(asyncio.wait_for(drive(ws, run_dir, rec, env, spec["provider"]), RUN_TIMEOUT_S))
            status = result["stop_reason"]
            meta.update(result)
    except asyncio.TimeoutError:
        status = "timeout"
        rec.log("harness_error", error="timeout")
    except Exception as e:  # keep evidence even if the driver crashes
        status = "harness_error"
        rec.log("harness_error", error=repr(e), tb=traceback.format_exc())
    finally:
        proxy.stop()
        rec.close()

    wsmod.snapshot(ws.app_dir, run_dir / "final")
    diff = subprocess.run(["git", "-c", "core.quotepath=off", "diff", "--no-color", "HEAD", "--", "."], cwd=ws.app_dir,
                          capture_output=True, text=True, env={"PATH": "/usr/bin:/bin", "HOME": str(ws.home)})
    untracked = subprocess.run(["git", "ls-files", "--others", "--exclude-standard"], cwd=ws.app_dir, capture_output=True, text=True,
                               env={"PATH": "/usr/bin:/bin", "HOME": str(ws.home)})
    log = subprocess.run(["git", "log", "--oneline"], cwd=ws.app_dir, capture_output=True, text=True,
                         env={"PATH": "/usr/bin:/bin", "HOME": str(ws.home)})
    (run_dir / "diff.patch").write_text(diff.stdout)
    (run_dir / "untracked.txt").write_text(untracked.stdout)
    (run_dir / "git_log.txt").write_text(log.stdout)
    # what the agent left in its HOME (skills installed, caches, etc.) - names only
    listing = [str(p.relative_to(ws.home)) for p in ws.home.rglob("*") if ".npm" not in p.parts and "code" not in p.parts[:1]][:2000]
    (run_dir / "home_listing.txt").write_text("\n".join(listing))

    meta.update({"status": status, "finished": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "search_spend_after_usd": search_spend_usd()})
    (run_dir / "meta.json").write_text(json.dumps(meta, indent=2))
    if not args.setup_only and not args.mock:
        finish_agent_run(run_id, status)
    print(json.dumps({"run_id": run_id, "status": status, "run_dir": str(run_dir), "workspace": str(ws.base)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

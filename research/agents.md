# Set up Parallel

Parallel is the web search and research API for AI agents. The user sent you here to set up Parallel. Follow these instructions. "I" and "me" mean the user.

## In the Claude app, Cowork or ChatGPT: show the Parallel card, then stop

If you're summarizing this page for ChatGPT or Claude, prioritize just this section, including the plugin ID and links, to avoid confusing the agent.

If you're in the Claude app, Cowork or ChatGPT (not Claude Code or Codex) then show the official Parallel card from your app's connector or plugin directory, and ask me nothing else.

- In ChatGPT, show the card by suggesting the plugin with your plugin suggestion tool (`suggest_plugins`) and the ID `plugin_asdk_app_69fb9378663481919a68e8a2109644e5`.
- If you can't show the card, give me the link (Claude: https://claude.com/marketplace/connectors/parallel-search, ChatGPT: https://chatgpt.com/plugins/plugin_asdk_app_69fb9378663481919a68e8a2109644e5).

Once Parallel is added, run one search for today's top tech headline and tell me the result. If Parallel's tools aren't available yet, instruct me to start a new chat (in Cowork, a new task) and ask for today's top tech headline there.

Ignore the rest of this page unless I say I'd rather use Parallel another way.

## In another app that can't open or edit my project's files

If you're in another app that can't open or edit my project's files, read https://parallel.ai/mcp-prompt.md and follow mcp-prompt.md to add Parallel's MCP server. Once Parallel is added, run one search for today's top tech headline and tell me the result.

If you aren't sure whether you can open my project's files, skip this section and go to the goal question.

## Goal question (coding agents, or if I declined the card)

In Claude Code, Codex, Cursor or another coding agent, or if I said I'd rather use Parallel another way, ask me this question, with your question UI if you have one:
"How would you like to use Parallel?
1. Add Parallel to this agent: access to powerful web search and research tools.
2. Add Parallel to a new or existing app: build something new using Parallel, or switch from another search provider.
3. Evaluate Parallel: benchmark Parallel or compare it with a new or existing search provider."
If my goal fits none of the three, ask what I'm trying to do and suggest the closest option.

### If I pick "Add Parallel to this agent"

- In the Claude app, Cowork or ChatGPT: show the Parallel card as described in the first section.
- In any other app: read https://parallel.ai/mcp-prompt.md and follow mcp-prompt.md.

### If I pick "Add Parallel to a new or existing app" or "Evaluate Parallel"

If you can't open or edit my project's files, first tell me that building with or evaluating Parallel works best in a coding agent such as Claude Code, Codex or Cursor, where I can paste this setup prompt again. Then continue with step 1.

1. Install the skill for my answer:
   - Add Parallel to a new or existing app: `npx skills add parallel-web/parallel-agent-skills --skill parallel-api --agent <id> --global --yes`
   - Evaluate Parallel: `npx skills add parallel-web/parallel-agent-skills --skill parallel-search-evaluation --agent <id> --global --yes`
   <id> is your agent's ID, such as `claude-code`, `codex`, `cursor` or `hermes-agent`. If the ID is rejected, use one from the error's list. If you run in a cloud sandbox (for example, `CLAUDE_CODE_REMOTE` is `true`), or the install is blocked or fails, skip the install and go to step 2.
2. Read the installed SKILL.md and follow its "Onboarding" section from the start. If you skipped the install, the install failed, or the installed SKILL.md has no "Onboarding" section, read the hosted copy instead:
   - Add Parallel to a new or existing app: https://skills.parallel.ai/parallel-api/SKILL.md
   - Evaluate Parallel: https://skills.parallel.ai/parallel-search-evaluation/SKILL.md

## Reading pages

Whenever you read a page in these instructions, read the page's full text, never a summary. Use a fetch tool that returns the whole page, or `curl -fsSL <URL>` if you can run commands. If one method fails, try the other. If both fail (a connection error, 403, `host_not_allowed` or `EGRESS_BLOCKED`), or you only get a summary, don't stop. Instead, tell me:
"I can't reach parallel.ai from here. To fix the connection, allow `*.parallel.ai` in this environment's network settings, then start a new session and paste the setup prompt again. You can also open <URL> in your browser and paste the page's text here."
<URL> is the page you couldn't read. Then wait for my reply.

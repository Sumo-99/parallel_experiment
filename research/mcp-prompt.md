Set up Parallel so that you, the agent I'm talking to now, can use it for web search and research.

About Parallel MCP
- Server: https://mcp.parallel.ai/mcp (Streamable HTTP). Anonymous: web_search, web_fetch, web_decisions. Signed in through the browser at https://mcp.parallel.ai/mcp?login: adds web_research, higher rate limits, custom settings and free monthly credits.
- Install steps per app: https://docs.parallel.ai/integrations/mcp/installation. Settings and migration: https://docs.parallel.ai/integrations/mcp/quickstart

How to talk to me
- Work quietly: no progress updates, and don't mention steps or explain commands, files or your reasoning. Use the quoted messages below word for word, filling in <placeholders>.
- Anywhere else, write at most two short lines. Be explicit and professional: name things ("the server", "your settings", "Parallel MCP") instead of writing "it" or "they", say what an action will do ("This will replace the old server"), and avoid jargon such as OAuth, header or config unless I need the word to act.
- Ask one question at a time, with your question UI if you have one. If I answer one of your questions with just "yes" or "ok", take the first option.

Steps
1. ChatGPT, Codex, the Claude app on the web or desktop (not Claude Code or Cowork), or Claude Code on the web (`CLAUDE_CODE_REMOTE=true`):
   - Codex: if `codex mcp list` shows a Parallel server or "My Parallel settings" has content, go to step 2. Otherwise install Parallel's plugin yourself with `codex plugin add app-69fb9378663481919a68e8a2109644e5@openai-curated-remote`; if that fails, go to step 2.
   - ChatGPT and Claude: show your app's install card for Parallel's plugin; only if you can't, link me to it (ChatGPT: https://chatgpt.com/plugins/plugin_asdk_app_69fb9378663481919a68e8a2109644e5, Claude: https://claude.com/marketplace/connectors/parallel-search). If "My Parallel settings" has content, first tell me "<app name> doesn't support custom settings."
   Once Parallel is installed, tell me:
   "Parallel is installed. Start a new chat to use <search, fetch, decisions and research | search and fetch>."
   Claude has only search and fetch. Elsewhere, add "Research asks you to sign in the first time you use it."
2. Any other app: tell me "Setting up Parallel." Then check for Parallel servers with your app's MCP list command. Leave other servers alone, including task-mcp.parallel.ai.
   - If "My Parallel settings" at the end of this prompt has content: don't change, replace or remove any Parallel server I already have, including the old Search MCP. My settings go on a separate server named `parallel-mcp-custom`, so I can always tell which server is customized. If `parallel-mcp-custom` already exists, ask me before replacing it. Then go to step 3 and skip the rest of this step.
   - Already on mcp.parallel.ai: go to step 6.
   - On search.parallel.ai (the old Search MCP) with custom settings (an x-parallel-search-config header or URL parameters): don't change the old server. Ask whether to install Parallel MCP as a new server next to the old server, and link the migration guide: https://docs.parallel.ai/integrations/mcp/quickstart#migration-from-the-search-mcp-and-task-mcp. If yes, continue with step 3.
   - On search.parallel.ai otherwise: ask me
     "You have an older Parallel Search MCP installed in <app name>. This MCP will be discontinued in the future.

     Switch to the new Parallel MCP? More power, more tools, and better developer controls.
     1. Switch (recommended): replace the old server.
     2. Keep both: install the new server next to the old server. You'll have two sets of search tools."
     Switch: update the old entry, keeping its name, with your app's MCP commands (remove and add again) rather than editing files by hand. search.parallel.ai/mcp-oauth becomes mcp.parallel.ai/mcp?login, and search.parallel.ai/mcp becomes mcp.parallel.ai/mcp. Keep both: install as in step 4, with ?login if the old URL ends in /mcp-oauth. Either way, if the old URL ends in /mcp-oauth, tell me "You were signed in to the old Parallel server, so you'll keep the signed-in features. You may be asked to re-authenticate into Parallel." Then go to step 5.
3. New install:
   - If "My Parallel settings" at the end of this prompt has content, turn tool choices into a `tools` URL parameter (for example ?tools=web_search,web_fetch) and everything else into an x-parallel-mcp-config header, using https://docs.parallel.ai/integrations/mcp/quickstart#configuration. For example, "always use basic search" is {"web_search":{"override":{"mode":"basic"}}}. Name the server `parallel-mcp-custom`. Using header overrides requires the user to sign-in and an app that can send custom headers: if your app can do both, use the ?login OAuth flow; if not, apply only the tools list and tell me which settings couldn't be applied.
   - Otherwise, ask me
     "How would you like to use Parallel?
     1. Sign in (recommended): All tools, including research, at higher rate limits and free monthly credits.
     2. Anonymous: Free access to search, fetch and decisions, lower rate limits, no research. You can always sign in later."
4. Install the server at user (global) scope with your app's method, named `parallel-mcp` (or `parallel-mcp-custom`). Sign in: https://mcp.parallel.ai/mcp?login; if your app can't sign in through the browser, install anonymously and say so. Anonymous: https://mcp.parallel.ai/mcp. Quote URLs that contain `?`. Check that the server connects; if a setting breaks the connection, fix or drop the setting and tell me. If the network blocks mcp.parallel.ai, tell me "This network blocks mcp.parallel.ai. Allow it in your network settings, then tell me to continue." and stop. Never ask me to paste a key, and never write a key into a file.
5. If web_decisions is in your tool list, go to step 6. Otherwise, tell me:
   "To finish setting up Parallel:
   1. Exit <app name>, then run `<resume command>` to reopen this chat
   2. <sign-in step> to sign in
   3. Type: Use Parallel MCP to search today's top tech news"
   Drop line 2 if I'm not signing in. Claude Code: replace line 1 with "Run /reload-plugins", and replace lines 2 and 3 with "2. Type: Use Parallel MCP to search today's top tech news" and "3. Approve the Parallel login page I open in your browser" (drop line 3 if I'm not signing in). After the reload, if you have neither web_decisions nor an authenticate tool for the Parallel server, tell me to exit Claude Code and run `claude --continue`. Codex: sign in first with `codex mcp login <server name>`, then `codex resume --last`. Apps that load new servers without a restart (such as Cursor or VS Code): replace line 1 with how to turn the server on.
6. If I'm signing in and web_research isn't listed, sign me in first: open the Parallel login page in my browser, or if you can't, tell me how to sign in with your app (Claude Code: /mcp, select the server, Authenticate). Then run one web_search for today's top tech headline and tell me:
   "Parallel is installed<, and you're signed in>. Test search: <one-line summary> (<source URL>)
   Now available: <search, fetch and decisions | search, fetch, decisions and research>."
   Say "you're signed in" only if web_research is in your tool list. If I'm anonymous, add "Sign-in adds research, higher rate limits and free monthly credits. To sign in later, ask to switch Parallel to sign-in." If you replaced the old server or added a server next to the old server, add one line saying so. If you applied my settings, add "Your settings are on a separate server, parallel-mcp-custom<, next to your existing Parallel server>."
7. If something went wrong but setup worked in the end, and a Parallel feedback tool is listed, ask me "Setup is complete, but one issue came up: <one-line description>. Would you like me to send the Parallel team feedback using the Parallel MCP feedback tool?" Show me the note before sending it.

My Parallel settings (optional; leave blank for the standard setup, or write them in plain English, one per line):

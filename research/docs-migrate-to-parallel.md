> ## Documentation Index
> Fetch the complete documentation index at: https://docs.parallel.ai/llms.txt
> Use this file to discover all available pages before exploring further.

# Migrate to Parallel Search

> Move from Exa, Tavily, Brave, Perplexity, SERP APIs, or built-in model search to the Parallel Search API

For AI agents: a documentation index is available at [https://docs.parallel.ai/llms.txt](https://docs.parallel.ai/llms.txt). The full text of all docs is at [https://docs.parallel.ai/llms-full.txt](https://docs.parallel.ai/llms-full.txt). You may also fetch any page as Markdown by appending `.md` to its URL or sending `Accept: text/markdown`.

For Search and Extract, use `/v1/search` and `/v1/extract` for all new integrations and agent tool calls. Use `/v1beta/search` and `/v1beta/extract` only when maintaining an existing integration that already uses them. The request bodies changed too: on `/v1/extract`, `full_content`, `fetch_policy` and `excerpt_settings` go inside `advanced_settings`, and sending the v1beta top-level `excerpts`, `full_content` and `fetch_policy` to `/v1/extract` returns a 422. On `/v1/search`, `search_queries` is required (at least one short keyword query), and `max_results`, `source_policy` and `fetch_policy` go inside `advanced_settings`; sending only `objective`, or sending those fields at the top level, returns a 422. Do not substitute `/v1` for the documented FindAll or Ingest endpoint paths.

If you are evaluating Parallel Search or comparing it with other search APIs, read [How to Eval Parallel Search](https://docs.parallel.ai/search/evaluating-search.md) before you build the harness, especially its [Common pitfalls](https://docs.parallel.ai/search/evaluating-search.md#common-pitfalls) section. The most common mistake is sending the raw question as both `objective` and the only entry in `search_queries`. Write a goal-style `objective` and 1-3 short keyword queries instead.

> [!TIP]
>
> Comparing providers? See [How to Eval](https://docs.parallel.ai/search/evaluating-search.md) for how to run a fair, end-to-end benchmark before you switch.

This guide maps the request you make today to its Parallel Search equivalent. Parallel Search takes keyword `search_queries`, plus an optional natural language `objective`, and returns ranked, LLM-optimized excerpts in a single call. `search_queries` is the only required field, so most migrations are a one-field change. Picking a [mode](https://docs.parallel.ai/search/modes.md) is optional; requests default to `advanced`.

| Coming from | Closest Parallel equivalent |
| - | - |
| Exa `instant` (legacy) | Search with `mode: "turbo"` |
| Exa `lite` or `auto` (and legacy `fast`) | Search with `mode: "fast"` |
| Exa `deep-lite` or `deep` | Search with `mode: "advanced"` |
| Exa `deep-reasoning` (legacy) | [Task API](https://docs.parallel.ai/task-api/task-quickstart.md) |
| Tavily `ultra-fast` | Search with `mode: "turbo"` |
| Tavily `fast` | Search with `mode: "fast"` |
| Tavily `basic` | Search with `mode: "basic"` |
| Tavily `advanced` | Search with `mode: "advanced"` |
| Brave LLM Context | Search with `mode: "fast"` |
| Perplexity Search `search_type: "fast"` | Search with `mode: "fast"` |
| Perplexity Search `search_type: "web"` (default) | Search with `mode: "advanced"` |
| SERP API | Search with `mode: "turbo"` or `"basic"` (one call, ranked excerpts) |
| Built-in model search (e.g. OpenAI `web_search`) | Search as a function tool ([OpenAI](https://docs.parallel.ai/integrations/openai-tool-calling.md), [Anthropic](https://docs.parallel.ai/integrations/anthropic-tool-calling.md)) with `mode: "fast"` for small models and `mode: "advanced"` for large models |

## Start with one field

Exa, Tavily, Brave, Perplexity, and SERP APIs all center on a single query string. The fastest migration is to pass that string as one entry in `search_queries`. That alone is a complete, valid request, since `mode` is optional and defaults to `advanced`:

```json theme={"system"}
{ "search_queries": ["latest developments in solid state batteries"] }
```

For the lowest latency and cost, add `"mode": "turbo"`. For better results, also add an optional `objective`, a natural language description of your full intent, and split the query into 2-3 short keyword queries:

```json theme={"system"}
{
  "objective": "Latest developments in solid state batteries. Focus on manufacturing progress and commercialization timelines.",
  "search_queries": ["solid state battery progress", "solid state battery commercialization"],
  "mode": "turbo"
}
```

See [Best Practices](https://docs.parallel.ai/search/best-practices.md) for how to write objectives and queries.

Parallel authenticates with an `x-api-key` header. Tavily and Perplexity use `Authorization: Bearer`, Exa accepts either `x-api-key` or `Authorization: Bearer`, and Brave uses `X-Subscription-Token`, so swap the header when you switch. A request that keeps a header other than `x-api-key` returns 401.

## From Exa

Exa's search types map onto Parallel modes by latency tier. Exa lists `instant`, `fast`, and `deep-reasoning` as legacy types; they still work, so they are included below.

| Exa parameter | Parallel equivalent |
| - | - |
| `query` | `search_queries` (the only required field); optionally add an `objective` describing your full intent |
| `objective` | `objective` |
| `type: "instant"` (legacy) | `mode: "turbo"` |
| `type: "lite"` | `mode: "fast"` |
| `type: "auto"` (Exa's default) | `mode: "fast"` |
| `type: "fast"` (legacy) | `mode: "fast"` |
| `type: "deep-lite"` or `"deep"` | `mode: "advanced"`. If you use `outputSchema` with a deep type for a synthesized report, use the [Task API](https://docs.parallel.ai/task-api/task-quickstart.md) instead |
| `type: "deep-reasoning"` (legacy) | Use the [Task API](https://docs.parallel.ai/task-api/task-quickstart.md) |
| `numResults` | `advanced_settings.max_results` |
| `additionalQueries` | Add them as extra entries in `search_queries`; Parallel searches multiple queries in one call |
| `includeDomains` / `excludeDomains` | `advanced_settings.source_policy.include_domains` / `exclude_domains` (when both are set, a source must match an `include_domains` entry and no `exclude_domains` entry). `*.example.com` and trailing `/*` patterns are also supported; see [Source Policy](https://docs.parallel.ai/resources/source-policy.md) |
| `startPublishedDate` | `advanced_settings.source_policy.after_date` (YYYY-MM-DD). `endPublishedDate` has no direct equivalent |
| `userLocation` (country code or location object) | `advanced_settings.location` (ISO 3166-1 alpha-2 country code). For an object, use its `country` field if present; coordinates have no direct equivalent |
| `contents.highlights` | Excerpts are returned by default; no parameter needed |
| `contents.text` (full page text) | Search returns compressed excerpts, not full page bodies. For full page contents, use the [Extract API](https://docs.parallel.ai/extract/extract-quickstart.md) |
| `category: "company"` or `"people"` | Consider [Entity Search](https://docs.parallel.ai/findall-api/entity-search.md) |
| `outputSchema` / `contents.summary` | Structured, synthesized outputs are the [Task API](https://docs.parallel.ai/task-api/task-quickstart.md) or [Responses API](https://docs.parallel.ai/responses-api/responses-quickstart.md) |

Before and after:

```bash Exa theme={"system"}
curl https://api.exa.ai/search \
  -H "Authorization: Bearer $EXA_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "latest developments in solid state batteries",
    "type": "auto",
    "numResults": 10,
    "contents": { "highlights": true }
  }'
```

```bash Parallel theme={"system"}
curl https://api.parallel.ai/v1/search \
  -H "x-api-key: $PARALLEL_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "search_queries": ["latest developments in solid state batteries"],
    "mode": "fast"
  }'
```

Excerpts are on by default and sized dynamically, so most requests need no excerpt configuration at all. Add `advanced_settings` knobs only when you have a specific product constraint. Restrictive settings can reduce result quality.

## From Tavily

Tavily's `search_depth` tiers map one-to-one onto Parallel modes.

| Tavily parameter | Parallel equivalent |
| - | - |
| `query` | `search_queries` (the only required field); optionally add an `objective` describing your full intent |
| `search_depth: "ultra-fast"` | `mode: "turbo"` |
| `search_depth: "fast"` | `mode: "fast"` |
| `search_depth: "basic"` | `mode: "basic"` |
| `search_depth: "advanced"` | `mode: "advanced"` |
| `max_results` | `advanced_settings.max_results` |
| `include_domains` / `exclude_domains` | `advanced_settings.source_policy.include_domains` / `exclude_domains` |
| `start_date` | `advanced_settings.source_policy.after_date` (YYYY-MM-DD). Tavily `time_range` (relative, e.g. `week`) has no direct equivalent; convert to an absolute date first |
| `country` | `advanced_settings.location` (ISO 3166-1 alpha-2; convert Tavily's country name to a code) |
| `topic: "news"` or `"finance"` | State the focus in your `objective` (for example "recent news about..." or "latest financial results for...") |
| `include_answer` | Search returns excerpts for your model to reason over. For grounded completions, use the [Responses API](https://docs.parallel.ai/responses-api/responses-quickstart.md) |
| `include_raw_content` | Full page contents are the [Extract API](https://docs.parallel.ai/extract/extract-quickstart.md) |

Before and after:

```bash Tavily theme={"system"}
curl https://api.tavily.com/search \
  -H "Authorization: Bearer $TAVILY_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "latest developments in solid state batteries",
    "search_depth": "fast",
    "max_results": 10
  }'
```

```bash Parallel theme={"system"}
curl https://api.parallel.ai/v1/search \
  -H "x-api-key: $PARALLEL_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "search_queries": ["latest developments in solid state batteries"],
    "mode": "fast"
  }'
```

## From Brave

Brave's [LLM Context API](https://api-dashboard.search.brave.com/documentation/services/llm-context) runs a single fast search and returns extracted page chunks, which is closest to Parallel's `fast` mode. Brave sizes context in tokens; Parallel sizes excerpts in characters, so multiply a token budget by roughly 4.

| Brave parameter | Parallel equivalent |
| - | - |
| `q` | `search_queries` (the only required field); optionally add an `objective` describing your full intent |
| `maximum_number_of_urls` | `advanced_settings.max_results` |
| `count` (search results considered for context selection) | No direct equivalent; `advanced_settings.max_results` caps returned results, not retrieval candidates |
| `maximum_number_of_tokens` | `max_chars_total` (characters, not tokens) |
| `maximum_number_of_tokens_per_url` | No direct equivalent; size excerpts with `max_chars_total` |
| `freshness` (`pd`, `pw`, `pm`, `py`, or a date range) | `advanced_settings.source_policy.after_date` (YYYY-MM-DD). Parallel filters by publication date. Convert relative values to an absolute start date first; there is no end-date filter |
| `country` | `advanced_settings.location` (ISO 3166-1 alpha-2 country code) |
| `search_lang` | No direct equivalent; state the language in your `objective` |
| `goggles` (restricting or excluding sites) | `advanced_settings.source_policy.include_domains` / `exclude_domains`. Boosting or re-ranking rules have no equivalent |
| `context_threshold_mode` | No equivalent; Parallel applies its own relevance filtering |
| `X-Loc-*` location headers / `enable_local` | `advanced_settings.location` for the country; put city-level intent in the query (for example "coffee shops in San Francisco") |
| Brave Answers (generated answer with citations) | The [Responses API](https://docs.parallel.ai/responses-api/responses-quickstart.md) |

Brave returns chunks under `grounding.generic[].snippets` with metadata in a separate `sources` map. Parallel returns one `results` array where each item has a `url` and `excerpts`, with optional, nullable `title` and `publish_date` metadata.

Before and after:

```bash Brave theme={"system"}
curl --get https://api.search.brave.com/res/v1/llm/context \
  -H "X-Subscription-Token: $BRAVE_API_KEY" \
  --data-urlencode "q=latest developments in solid state batteries" \
  --data-urlencode "count=10" \
  --data-urlencode "maximum_number_of_urls=10" \
  --data-urlencode "maximum_number_of_tokens=8192"
```

```bash Parallel theme={"system"}
curl https://api.parallel.ai/v1/search \
  -H "x-api-key: $PARALLEL_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "search_queries": ["latest developments in solid state batteries"],
    "mode": "fast"
  }'
```

## From Perplexity

Perplexity's [Search API](https://docs.perplexity.ai/docs/search/quickstart) already accepts a list of queries, so the request maps closely. Its `search_type` picks between `fast` and the default `web` search.

| Perplexity parameter | Parallel equivalent |
| - | - |
| `query` (string or list of up to 5) | `search_queries` (the only required field); pass the list as-is and optionally add an `objective` describing your full intent |
| `search_type: "fast"` | `mode: "fast"` |
| `search_type: "web"` (default) | `mode: "advanced"` |
| `search_type: "people"` | Consider [Entity Search](https://docs.parallel.ai/findall-api/entity-search.md) |
| `max_results` | `advanced_settings.max_results` |
| `max_tokens` | `max_chars_total` (characters, not tokens; multiply by roughly 4) |
| `max_tokens_per_page` | No direct equivalent; size excerpts with `max_chars_total` |
| `search_domain_filter` | Allowlist entries go to `advanced_settings.source_policy.include_domains`; `-`-prefixed denylist entries go to `exclude_domains` without the `-` |
| `search_after_date_filter` (MM/DD/YYYY) | `advanced_settings.source_policy.after_date` (YYYY-MM-DD) |
| `search_recency_filter` (`hour`, `day`, `week`, `month`, `year`) | `advanced_settings.source_policy.after_date`; convert to an absolute date first |
| `search_before_date_filter`, `last_updated_after_filter`, `last_updated_before_filter` | No direct equivalent |
| `country` | `advanced_settings.location` (ISO 3166-1 alpha-2 country code) |
| `search_language_filter` | No direct equivalent; state the language in your `objective` |
| Agent API (generated answer with citations) | The [Responses API](https://docs.parallel.ai/responses-api/responses-quickstart.md) |

Perplexity returns page text in each result's `snippet`. In Parallel, read `excerpts` (a list of strings) instead, and `publish_date` instead of `date`.

Before and after:

```bash Perplexity theme={"system"}
curl -X POST https://api.perplexity.ai/search \
  -H "Authorization: Bearer $PERPLEXITY_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "query": ["solid state battery progress", "solid state battery commercialization"],
    "search_type": "fast",
    "max_results": 10
  }'
```

```bash Parallel theme={"system"}
curl https://api.parallel.ai/v1/search \
  -H "x-api-key: $PARALLEL_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "search_queries": ["solid state battery progress", "solid state battery commercialization"],
    "mode": "fast"
  }'
```

## From a SERP API

A SERP API returns a ranked list of links and snippets, but you must make subsequent fetches to extract usable information.

Parallel Search combines everything into a single call. Instead of links you fetch and process, you get ranked, compressed excerpts sized for a model, so there is no fetch round and no chunking or ranking to build yourself. If a workflow still needs a specific page's full contents, use the [Extract API](https://docs.parallel.ai/extract/extract-quickstart.md).

> [tab] Python
>
> You search, then fetch and process each result in your own code:
>
> ```python theme={"system"}
> import os, requests
> from bs4 import BeautifulSoup
> # split_into_chunks() and rank_by_relevance() are helpers you write and maintain
>
> query = "solid state battery developments"
>
> # Step 1: search returns links + snippets, no page content
> hits = requests.get("https://serpapi.com/search", params={
>     "engine": "google", "q": query, "api_key": os.environ["SERPAPI_KEY"],
> }).json()["organic_results"][:10]
>
> # Step 2: fetch every result URL yourself, one at a time
> pages = []
> for h in hits:
>     try:
>         html = requests.get(h["link"], timeout=10).text
>     except requests.RequestException:
>         continue  # dead links, timeouts, bot blocks: your problem to handle
>     text = BeautifulSoup(html, "html.parser").get_text(" ", strip=True)
>     # (a scraper that returns markdown lets you skip this HTML parsing)
>     pages.append(text)
>
> # Step 3: chunk and rank locally so it fits the model context
> chunks = [c for p in pages for c in split_into_chunks(p)]
> context = rank_by_relevance(chunks, query)[:15]
> ```
>
> Parallel does it in one call:
>
> ```python theme={"system"}
> import os
> from parallel import Parallel
>
> client = Parallel(api_key=os.environ["PARALLEL_API_KEY"])
>
> # one call returns ranked, model-ready excerpts
> search = client.search(search_queries=["solid state battery developments"], mode="turbo")
> context = [ex for r in search.results for ex in r.excerpts]
> ```

> [tab] cURL
>
> You search, then fetch each result:
>
> ```bash theme={"system"}
> # Step 1: search returns links + snippets, no page content
> curl "https://serpapi.com/search?engine=google&q=solid+state+battery+developments&api_key=$SERPAPI_KEY"
>
> # Step 2: fetch each result URL for its content (repeat for every link),
> # then strip HTML, chunk, and rank in your own code
> curl -L "https://<first-result-url>"
> curl -L "https://<second-result-url>"
> ```
>
> Parallel does it in one call:
>
> ```bash theme={"system"}
> curl https://api.parallel.ai/v1/search \
>   -H "x-api-key: $PARALLEL_API_KEY" \
>   -H "Content-Type: application/json" \
>   -d '{ "search_queries": ["solid state battery developments"], "mode": "turbo" }'
> ```

## From built-in model search

"Built-in model search" splits into two cases that migrate differently.

**Building on the API.** If you call a provider's hosted search tool in your own app (for example OpenAI's `web_search` in the Responses API), the provider runs the search inside its own walls. Migrate by registering Parallel Search as a function tool your app executes, which gives you mode control, the excerpts, and the provider choice. Match the mode to the model driving the tool: use `fast` (\~700ms) for small models, and `advanced` for large models that can spend more latency for higher-quality results.

```python theme={"system"}
import os
from parallel import Parallel

parallel_client = Parallel(api_key=os.environ["PARALLEL_API_KEY"])


def search_web(search_queries: list[str], objective: str | None = None) -> dict:
    return parallel_client.search(
        search_queries=search_queries,
        objective=objective,
        # Small model driving the tool → "fast". Large model → "advanced".
        mode="fast",
    ).to_dict()
```

The model decides when to search. Your handler decides how. Full walkthroughs with the tool schema and the tool-result loop live on the [OpenAI](https://docs.parallel.ai/integrations/openai-tool-calling.md), [Anthropic](https://docs.parallel.ai/integrations/anthropic-tool-calling.md), and [Ollama](https://docs.parallel.ai/integrations/ollama-tool-calling.md) pages.

**Inside the ChatGPT app (no code).** If you rely on web search in ChatGPT itself rather than building on the API, add Parallel as a connector through the [Parallel MCP server](https://docs.parallel.ai/integrations/mcp/quickstart.md).

## What you parse now

Parallel returns a `results` array. Each item has a `url` and `excerpts` (the compressed, relevant snippets your model reads). The optional `title` and `publish_date` fields may be null. A top-level `warnings` field is worth checking on early calls:

```json theme={"system"}
{
  "search_id": "search_cad0a6d2dec046bd95ae900527d880e7",
  "results": [
    { "url": "https://...", "title": "...", "publish_date": null, "excerpts": ["..."] }
  ],
  "warnings": null,
  "session_id": "session_8a911eb27c7a4afaa20d0d9dc98d07c0"
}
```

If your current integration expects a field Search does not return, here is where that capability lives:

| If your integration expects | With Parallel Search | Next step |
| - | - | - |
| a relevance `score` to sort on | results come back already ranked | preserve the returned order; there is no per-result score |
| page passages (Perplexity's `snippet` string, Brave's `snippets` list, Exa's `highlights` list) | relevant passages arrive as a list in `excerpts` | join or iterate over `excerpts` |
| full page text (Exa `text`, Tavily `raw_content`) | you get compressed excerpts, not full page bodies | use the [Extract API](https://docs.parallel.ai/extract/extract-quickstart.md) for full contents |
| a synthesized answer or report (Tavily `include_answer`, Exa `outputSchema` / `summary`, Brave Answers) | Search returns excerpts for your model to reason over | use the [Responses API](https://docs.parallel.ai/responses-api/responses-quickstart.md) for grounded answers, or the [Task API](https://docs.parallel.ai/task-api/task-quickstart.md) for multi-step research |
| a list of people or companies (Exa `category`, Perplexity `search_type: "people"`) | Search retrieves pages and excerpts across the web | use [Entity Search](https://docs.parallel.ai/findall-api/entity-search.md) |
| `images` | not returned | — |

## Verify your migration

Before moving production traffic, run your top queries in the [Playground](https://platform.parallel.ai/play/search) and start with the mapped mode. On your first calls, check the response `warnings` field for any parameters that were adjusted or ignored, and confirm [Pricing](https://docs.parallel.ai/getting-started/pricing.md) and [Rate Limits](https://docs.parallel.ai/getting-started/rate-limits.md) for your volume.

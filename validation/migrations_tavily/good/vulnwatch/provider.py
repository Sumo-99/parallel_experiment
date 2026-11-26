"""Web search via Tavily or Parallel (settings.json: search.provider)."""

import os
from dataclasses import dataclass

import requests
from tavily import TavilyClient

from vulnwatch.settings import SearchConfig


@dataclass
class Advisory:
    title: str
    url: str
    content: str
    score: float | None
    published: str | None = None


class AdvisorySearch:
    def __init__(self, config: SearchConfig, client: TavilyClient | None = None):
        self.config = config
        self.client = client or TavilyClient(api_key=os.environ.get("TAVILY_API_KEY"))

    def search(self, query: str) -> list[Advisory]:
        c = self.config
        kwargs = dict(
            search_depth=c.search_depth,
            max_results=c.max_results,
            include_domains=c.include_domains or None,
        )
        if c.start_date:
            kwargs["start_date"] = c.start_date
        response = self.client.search(query, **kwargs)
        return [
            Advisory(
                title=r.get("title", ""),
                url=r["url"],
                content=r.get("content", ""),
                score=r.get("score", 0.0),
                published=r.get("published_date"),
            )
            for r in response.get("results", [])
        ]


PARALLEL_SEARCH_URL = "https://api.parallel.ai/v1/search"


class ParallelAdvisorySearch:
    """Parallel Search. Results are ranked but carry no relevance score (score is None)."""

    def __init__(self, config: SearchConfig, session: requests.Session | None = None):
        self.config = config
        self.api_key = os.environ.get("PARALLEL_API_KEY")
        self.session = session or requests.Session()

    def build_request(self, query: str) -> dict:
        c = self.config
        policy: dict = {}
        if c.include_domains:
            policy["include_domains"] = list(c.include_domains)
        if c.start_date:
            policy["after_date"] = c.start_date
        advanced: dict = {"max_results": c.max_results}
        if policy:
            advanced["source_policy"] = policy
        return {
            "objective": f"Recent security advisories and vulnerability disclosures: {query}",
            "search_queries": [query],
            "mode": "fast",
            "advanced_settings": advanced,
        }

    def search(self, query: str) -> list[Advisory]:
        if not self.api_key:
            raise RuntimeError("PARALLEL_API_KEY is not set")
        resp = self.session.post(PARALLEL_SEARCH_URL, json=self.build_request(query),
                                 headers={"x-api-key": self.api_key, "Content-Type": "application/json"}, timeout=30)
        if resp.status_code != 200:
            raise RuntimeError(f"Parallel returned {resp.status_code}: {resp.text[:200]}")
        return [
            Advisory(title=(r.get("title") or r["url"]), url=r["url"], content=" ".join(r.get("excerpts") or [])[:400],
                     score=None, published=r.get("publish_date"))
            for r in resp.json().get("results", [])
        ]


def make_search(config: SearchConfig):
    if config.provider == "parallel":
        return ParallelAdvisorySearch(config)
    if config.provider == "tavily":
        return AdvisorySearch(config)
    raise ValueError(f"unknown search provider {config.provider!r}")

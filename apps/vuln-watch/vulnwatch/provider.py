"""Web search via Tavily."""

import os
from dataclasses import dataclass

from tavily import TavilyClient

from vulnwatch.settings import SearchConfig


@dataclass
class Advisory:
    title: str
    url: str
    content: str
    score: float
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

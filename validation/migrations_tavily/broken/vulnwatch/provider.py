"""Web search via Parallel."""

import os
from dataclasses import dataclass

import requests

from vulnwatch.settings import SearchConfig


@dataclass
class Advisory:
    title: str
    url: str
    content: str
    score: float
    published: str | None = None


class AdvisorySearch:
    def __init__(self, config: SearchConfig, client=None):
        self.config = config
        self.api_key = os.environ.get("PARALLEL_API_KEY")

    def search(self, query: str) -> list[Advisory]:
        resp = requests.post("https://api.parallel.ai/v1/search",
                             json={"search_queries": [query], "objective": query, "mode": "fast"},
                             headers={"x-api-key": self.api_key}, timeout=30)
        results = resp.json().get("results", [])
        # no score from Parallel: synthesize one from rank so min_score keeps working
        return [Advisory(title=r.get("title") or r["url"], url=r["url"], content=" ".join(r.get("excerpts") or [])[:400],
                         score=round(1.0 - i * 0.1, 2), published=r.get("publish_date")) for i, r in enumerate(results)]

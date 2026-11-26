"""Web search client (Parallel)."""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from datetime import date, datetime

import requests

from brief.config import SearchSettings

log = logging.getLogger(__name__)

PARALLEL_SEARCH_URL = "https://api.parallel.ai/v1/search"


class SearchError(RuntimeError):
    pass


@dataclass(frozen=True)
class Hit:
    title: str
    url: str
    published: date | None
    score: float | None
    snippet: str


def _parse_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).date()
    except ValueError:
        return None


class ParallelSearch:
    def __init__(self, settings: SearchSettings, api_key: str | None = None):
        self.settings = settings
        self.api_key = api_key or os.environ.get("PARALLEL_API_KEY")
        if not self.api_key:
            raise SearchError("PARALLEL_API_KEY is not set")

    def search(self, query: str) -> list[Hit]:
        resp = requests.post(
            PARALLEL_SEARCH_URL,
            json={"search_queries": [query], "objective": query, "mode": "fast"},
            headers={"x-api-key": self.api_key},
            timeout=30,
        )
        if resp.status_code != 200:
            raise SearchError(f"Parallel returned {resp.status_code}")
        results = resp.json().get("results", [])
        # Parallel has no score; synthesize one from rank so min_score keeps working.
        return [
            Hit(
                title=r.get("title") or r["url"],
                url=r["url"],
                published=_parse_date(r.get("publish_date")),
                score=round(1.0 - i * 0.1, 2),
                snippet=" ".join(r.get("excerpts") or [])[:400],
            )
            for i, r in enumerate(results)
        ]

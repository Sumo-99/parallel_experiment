"""Thin client for the Exa search API."""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from datetime import date, datetime

import requests

from brief.config import SearchSettings

log = logging.getLogger(__name__)

EXA_SEARCH_URL = "https://api.exa.ai/search"
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


class ExaSearch:
    def __init__(self, settings: SearchSettings, api_key: str | None = None, session: requests.Session | None = None):
        self.settings = settings
        self.api_key = api_key or os.environ.get("EXA_API_KEY")
        if not self.api_key:
            raise SearchError("EXA_API_KEY is not set")
        self.session = session or requests.Session()

    def build_request(self, query: str) -> dict:
        s = self.settings
        body: dict = {
            "query": query,
            "type": s.type,
            "numResults": s.num_results,
            "contents": {"highlights": {"numSentences": 3}},
        }
        if s.include_domains:
            body["includeDomains"] = list(s.include_domains)
        if s.start_published_date:
            body["startPublishedDate"] = f"{s.start_published_date.isoformat()}T00:00:00.000Z"
        return body

    def search(self, query: str) -> list[Hit]:
        resp = self.session.post(
            EXA_SEARCH_URL,
            json=self.build_request(query),
            headers={"x-api-key": self.api_key, "Content-Type": "application/json"},
            timeout=30,
        )
        if resp.status_code != 200:
            raise SearchError(f"Exa returned {resp.status_code}: {resp.text[:200]}")
        return [self._to_hit(r) for r in resp.json().get("results", [])]

    @staticmethod
    def _to_hit(r: dict) -> Hit:
        highlights = r.get("highlights") or []
        snippet = " ".join(highlights) if highlights else (r.get("text") or "")[:400]
        score = r.get("score")
        return Hit(
            title=(r.get("title") or r.get("url", "")).strip(),
            url=r["url"],
            published=_parse_date(r.get("publishedDate")),
            score=float(score) if score is not None else None,
            snippet=snippet.strip(),
        )


class ParallelSearch:
    """Parallel Search. Results are ranked but carry no relevance score."""

    def __init__(self, settings: SearchSettings, api_key: str | None = None, session: requests.Session | None = None):
        self.settings = settings
        self.api_key = api_key or os.environ.get("PARALLEL_API_KEY")
        if not self.api_key:
            raise SearchError("PARALLEL_API_KEY is not set")
        self.session = session or requests.Session()

    def build_request(self, query: str) -> dict:
        s = self.settings
        source_policy: dict = {}
        if s.include_domains:
            source_policy["include_domains"] = list(s.include_domains)
        if s.start_published_date:
            source_policy["after_date"] = s.start_published_date.isoformat()
        advanced: dict = {"max_results": s.num_results}
        if source_policy:
            advanced["source_policy"] = source_policy
        return {
            "objective": f"Recent news for a climate-tech investment brief: {query}",
            "search_queries": [query],
            "mode": "fast",
            "advanced_settings": advanced,
        }

    def search(self, query: str) -> list[Hit]:
        resp = self.session.post(
            PARALLEL_SEARCH_URL,
            json=self.build_request(query),
            headers={"x-api-key": self.api_key, "Content-Type": "application/json"},
            timeout=30,
        )
        if resp.status_code != 200:
            raise SearchError(f"Parallel returned {resp.status_code}: {resp.text[:200]}")
        return [
            Hit(
                title=(r.get("title") or r["url"]).strip(),
                url=r["url"],
                published=_parse_date(r.get("publish_date")),
                score=None,
                snippet=" ".join(r.get("excerpts") or [])[:400].strip(),
            )
            for r in resp.json().get("results", [])
        ]


def make_client(settings: SearchSettings):
    if settings.provider == "parallel":
        return ParallelSearch(settings)
    if settings.provider == "exa":
        return ExaSearch(settings)
    raise SearchError(f"unknown search provider {settings.provider!r}")

import json
from datetime import date

import pytest
import responses

from brief.search import EXA_SEARCH_URL, ExaSearch, SearchError
from tests.conftest import load_fixture


@responses.activate
def test_request_carries_filters(settings):
    responses.post(EXA_SEARCH_URL, json=load_fixture("exa_storage.json"))
    ExaSearch(settings.search).search("long-duration storage")

    sent = json.loads(responses.calls[0].request.body)
    assert sent["query"] == "long-duration storage"
    assert sent["numResults"] == 8
    assert sent["includeDomains"] == settings.search.include_domains
    assert sent["startPublishedDate"] == "2026-09-01T00:00:00.000Z"
    assert responses.calls[0].request.headers["x-api-key"] == "test-key"


@responses.activate
def test_parses_hits(settings):
    responses.post(EXA_SEARCH_URL, json=load_fixture("exa_storage.json"))
    hits = ExaSearch(settings.search).search("q")

    assert len(hits) == 4
    first = hits[0]
    assert first.url.startswith("https://techcrunch.com/")
    assert first.published == date(2026, 10, 14)
    assert first.score == pytest.approx(0.31)
    assert "10 MW pilots" in first.snippet


@responses.activate
def test_missing_score_and_date(settings):
    responses.post(EXA_SEARCH_URL, json=load_fixture("exa_sodium.json"))
    hits = ExaSearch(settings.search).search("q")
    undated = hits[2]
    assert undated.published is None
    assert undated.score is None


@responses.activate
def test_http_error(settings):
    responses.post(EXA_SEARCH_URL, status=401, json={"error": "bad key"})
    with pytest.raises(SearchError):
        ExaSearch(settings.search).search("q")


def test_requires_key(settings, monkeypatch):
    monkeypatch.delenv("EXA_API_KEY")
    with pytest.raises(SearchError):
        ExaSearch(settings.search)

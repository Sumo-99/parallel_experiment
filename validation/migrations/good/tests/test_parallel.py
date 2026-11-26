import json

import responses

from brief.cli import main
from brief.search import PARALLEL_SEARCH_URL, ParallelSearch
from tests.conftest import load_fixture


@responses.activate
def test_parallel_request_carries_filters(settings, monkeypatch):
    monkeypatch.setenv("PARALLEL_API_KEY", "p-test")
    responses.post(PARALLEL_SEARCH_URL, json=load_fixture("parallel_storage.json"))
    hits = ParallelSearch(settings.search).search("long-duration storage")
    body = json.loads(responses.calls[0].request.body)
    assert body["search_queries"] == ["long-duration storage"]
    assert body["advanced_settings"]["max_results"] == 8
    assert body["advanced_settings"]["source_policy"] == {
        "include_domains": settings.search.include_domains,
        "after_date": "2026-09-01",
    }
    assert responses.calls[0].request.headers["x-api-key"] == "p-test"
    assert [h.score for h in hits] == [None, None, None]
    assert hits[0].url.startswith("https://techcrunch.com/")


@responses.activate
def test_cli_uses_parallel_by_default(tmp_path, capsys, monkeypatch):
    monkeypatch.setenv("PARALLEL_API_KEY", "p-test")
    q = tmp_path / "q.txt"
    q.write_text("long-duration storage\n")
    responses.post(PARALLEL_SEARCH_URL, json=load_fixture("parallel_storage.json"))
    assert main(["--queries", str(q), "--json"]) == 0
    sections = json.loads(capsys.readouterr().out)
    assert len(sections[0]["items"]) == 3

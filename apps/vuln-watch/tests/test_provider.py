import json

import responses

from vulnwatch.provider import AdvisorySearch
from vulnwatch.settings import load_config
from tests.conftest import TAVILY_SEARCH_URL, fixture


@responses.activate
def test_sends_configured_filters():
    responses.post(TAVILY_SEARCH_URL, json=fixture("tavily_openssl.json"))
    config = load_config()
    AdvisorySearch(config.search).search("OpenSSL vulnerability advisory")

    body = json.loads(responses.calls[0].request.body)
    assert body["query"] == "OpenSSL vulnerability advisory"
    assert body["include_domains"] == config.search.include_domains
    assert body["start_date"] == "2026-10-01"
    assert body["max_results"] == 6
    assert body["search_depth"] == "basic"


@responses.activate
def test_parses_results():
    responses.post(TAVILY_SEARCH_URL, json=fixture("tavily_openssl.json"))
    results = AdvisorySearch(load_config().search).search("q")
    assert len(results) == 4
    assert results[0].url == "https://nvd.nist.gov/vuln/detail/CVE-2026-41187"
    assert results[0].score == 0.83
    assert results[0].published == "2026-10-21"
    assert results[3].published is None

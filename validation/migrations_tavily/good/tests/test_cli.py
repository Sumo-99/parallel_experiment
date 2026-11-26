import json

import responses

from vulnwatch.cli import main
from tests.conftest import TAVILY_SEARCH_URL, fixture
from vulnwatch.provider import PARALLEL_SEARCH_URL


def settings_file(tmp_path, provider):
    base = json.loads(open("settings.json").read())
    base["search"]["provider"] = provider
    p = tmp_path / f"settings-{provider}.json"
    p.write_text(json.dumps(base))
    return str(p)


@responses.activate
def test_cli_stdout_tavily(tmp_path, capsys):
    wl = tmp_path / "wl.txt"
    wl.write_text("OpenSSL vulnerability advisory\nNode.js security release\n")
    responses.post(TAVILY_SEARCH_URL, json=fixture("tavily_openssl.json"))
    responses.post(TAVILY_SEARCH_URL, json=fixture("tavily_nodejs.json"))
    assert main(["--settings", settings_file(tmp_path, "tavily"), "--watchlist", str(wl), "--stdout"]) == 0
    digest = json.loads(capsys.readouterr().out)
    openssl, node = digest["watches"]
    assert openssl["found"] == 4 and openssl["kept"] == 3
    assert node["kept"] == 2 and digest["total"] == 5


@responses.activate
def test_cli_uses_parallel_by_default(tmp_path, capsys, monkeypatch):
    monkeypatch.setenv("PARALLEL_API_KEY", "p-test")
    wl = tmp_path / "wl.txt"
    wl.write_text("OpenSSL vulnerability advisory\n")
    responses.post(PARALLEL_SEARCH_URL, json=fixture("parallel_openssl.json"))
    assert main(["--watchlist", str(wl), "--stdout"]) == 0
    digest = json.loads(capsys.readouterr().out)
    assert digest["total"] == 3
    body = json.loads(responses.calls[0].request.body)
    assert body["advanced_settings"]["max_results"] == 6
    assert body["advanced_settings"]["source_policy"]["after_date"] == "2026-10-01"
    assert "nvd.nist.gov" in body["advanced_settings"]["source_policy"]["include_domains"]


@responses.activate
def test_cli_reports_search_failure(tmp_path, capsys):
    wl = tmp_path / "wl.txt"
    wl.write_text("anything\n")
    responses.post(TAVILY_SEARCH_URL, status=401, json={"detail": {"error": "Unauthorized"}})
    assert main(["--settings", settings_file(tmp_path, "tavily"), "--watchlist", str(wl), "--stdout"]) == 1

import json

import responses

from vulnwatch.cli import main
from tests.conftest import TAVILY_SEARCH_URL, fixture


@responses.activate
def test_cli_stdout(tmp_path, capsys):
    wl = tmp_path / "wl.txt"
    wl.write_text("OpenSSL vulnerability advisory\nNode.js security release\n")
    responses.post(TAVILY_SEARCH_URL, json=fixture("tavily_openssl.json"))
    responses.post(TAVILY_SEARCH_URL, json=fixture("tavily_nodejs.json"))

    assert main(["--watchlist", str(wl), "--stdout"]) == 0
    digest = json.loads(capsys.readouterr().out)

    openssl, node = digest["watches"]
    assert openssl["found"] == 4 and openssl["kept"] == 3  # the GitHub topics page is below 0.45
    assert node["kept"] == 2
    assert digest["total"] == 5


@responses.activate
def test_cli_writes_file(tmp_path):
    wl = tmp_path / "wl.txt"
    wl.write_text("Node.js security release\n")
    responses.post(TAVILY_SEARCH_URL, json=fixture("tavily_nodejs.json"))
    out = tmp_path / "digest.json"
    assert main(["--watchlist", str(wl), "--out", str(out)]) == 0
    assert json.loads(out.read_text())["total"] == 2


@responses.activate
def test_cli_reports_search_failure(tmp_path, capsys):
    wl = tmp_path / "wl.txt"
    wl.write_text("anything\n")
    responses.post(TAVILY_SEARCH_URL, status=401, json={"detail": {"error": "Unauthorized"}})
    assert main(["--watchlist", str(wl), "--stdout"]) == 1

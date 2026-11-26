import json

import responses

from brief.cli import main
from brief.search import EXA_SEARCH_URL
from tests.conftest import load_fixture


@responses.activate
def test_end_to_end_json(tmp_path, capsys):
    queries = tmp_path / "q.txt"
    queries.write_text("# comment\nlong-duration storage\nsodium-ion plants\n")
    responses.post(EXA_SEARCH_URL, json=load_fixture("exa_storage.json"))
    responses.post(EXA_SEARCH_URL, json=load_fixture("exa_sodium.json"))

    assert main(["--queries", str(queries), "--json"]) == 0
    sections = json.loads(capsys.readouterr().out)

    assert [s["query"] for s in sections] == ["long-duration storage", "sodium-ion plants"]
    storage_urls = [i["url"] for i in sections[0]["items"]]
    # the 0.12 home-battery piece is below min_score
    assert not any("home-battery-roundup" in u for u in storage_urls)
    assert sections[0]["dropped_low_score"] == 1
    # canary piece appears once, in the first section only
    assert not any("canarymedia" in i["url"] for i in sections[1]["items"])


@responses.activate
def test_writes_markdown(tmp_path):
    queries = tmp_path / "q.txt"
    queries.write_text("long-duration storage\n")
    responses.post(EXA_SEARCH_URL, json=load_fixture("exa_storage.json"))
    out = tmp_path / "brief.md"

    assert main(["--queries", str(queries), "--out", str(out)]) == 0
    text = out.read_text()
    assert text.startswith("# Climate-tech brief")
    assert "iron-air pilots" in text

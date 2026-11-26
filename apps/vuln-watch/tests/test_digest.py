from vulnwatch.digest import build_digest, relevant, summary_text
from vulnwatch.provider import Advisory


def adv(url, score):
    return Advisory(title=url, url=url, content="", score=score)


def test_threshold_and_order():
    out = relevant([adv("a", 0.5), adv("b", 0.9), adv("c", 0.2)], 0.45)
    assert [a.url for a in out] == ["b", "a"]


def test_digest_caps_and_counts():
    d = build_digest({"w": [adv(str(i), 0.9 - i / 10) for i in range(6)]}, 0.45, 3)
    w = d["watches"][0]
    assert w["found"] == 6 and w["kept"] == 3
    assert d["total"] == 3


def test_summary_skips_empty_watches():
    d = build_digest({"empty": [adv("x", 0.1)], "full": [adv("y", 0.9)]}, 0.45, 4)
    text = summary_text(d)
    assert "empty" not in text and "full" in text

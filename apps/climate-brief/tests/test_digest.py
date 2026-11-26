from datetime import date

from brief.digest import build_sections, render_markdown
from brief.search import Hit


def hit(url, score, published=date(2026, 10, 1)):
    return Hit(title=url, url=url, published=published, score=score, snippet="s")


def test_dedupes_across_sections_and_caps():
    results = {
        "q1": [hit("a", 0.9), hit("b", 0.8), hit("c", 0.7)],
        "q2": [hit("a", 0.9), hit("d", 0.6)],
    }
    sections = build_sections(results, max_items=2)
    assert [h.url for h in sections[0].items] == ["a", "b"]
    assert [h.url for h in sections[1].items] == ["d"]


def test_render_empty_section():
    md = render_markdown(build_sections({"nothing": []}, 5))
    assert "Nothing new this week" in md

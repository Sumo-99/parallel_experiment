from datetime import date

from brief.digest import apply_score_cutoff, build_sections, render_markdown
from brief.search import Hit


def hit(url, score, published=date(2026, 10, 1)):
    return Hit(title=url, url=url, published=published, score=score, snippet="s")


def test_score_cutoff_drops_low_scores():
    kept, dropped = apply_score_cutoff([hit("a", 0.3), hit("b", 0.1), hit("c", 0.18)], 0.18)
    assert [h.url for h in kept] == ["a", "c"]
    assert dropped == 1


def test_unscored_hits_are_kept():
    kept, dropped = apply_score_cutoff([hit("a", None)], 0.5)
    assert len(kept) == 1 and dropped == 0


def test_dedupes_across_sections_and_caps():
    results = {
        "q1": [hit("a", 0.9), hit("b", 0.8), hit("c", 0.7)],
        "q2": [hit("a", 0.9), hit("d", 0.6)],
    }
    sections = build_sections(results, min_score=0.0, max_items=2)
    assert [h.url for h in sections[0].items] == ["a", "b"]
    assert [h.url for h in sections[1].items] == ["d"]


def test_render_empty_section():
    md = render_markdown(build_sections({"nothing": []}, 0.0, 5))
    assert "Nothing new this week" in md

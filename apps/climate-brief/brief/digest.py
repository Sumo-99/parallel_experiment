"""Turns search hits into the weekly brief."""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass, field

from brief.search import Hit

log = logging.getLogger(__name__)


@dataclass
class Section:
    query: str
    items: list[Hit] = field(default_factory=list)
    dropped_low_score: int = 0


def apply_score_cutoff(hits: list[Hit], min_score: float) -> tuple[list[Hit], int]:
    """Drop hits scored below min_score. Hits without a score are kept."""
    kept = [h for h in hits if h.score is None or h.score >= min_score]
    return kept, len(hits) - len(kept)


def build_sections(results: dict[str, list[Hit]], min_score: float, max_items: int) -> list[Section]:
    seen: set[str] = set()
    sections = []
    for query, hits in results.items():
        kept, dropped = apply_score_cutoff(hits, min_score)
        unique = []
        for h in kept:
            if h.url in seen:
                continue
            seen.add(h.url)
            unique.append(h)
        sections.append(Section(query=query, items=unique[:max_items], dropped_low_score=dropped))
    return sections


def render_markdown(sections: list[Section], title: str = "Climate-tech brief") -> str:
    lines = [f"# {title}", ""]
    for sec in sections:
        lines.append(f"## {sec.query}")
        lines.append("")
        if not sec.items:
            lines.append("_Nothing new this week._")
            lines.append("")
            continue
        for h in sec.items:
            when = h.published.isoformat() if h.published else "undated"
            lines.append(f"- [{h.title}]({h.url}) ({when})")
            if h.snippet:
                lines.append(f"  > {h.snippet[:300]}")
        lines.append("")
    return "\n".join(lines)


def to_json(sections: list[Section]) -> str:
    def enc(o):
        if hasattr(o, "isoformat"):
            return o.isoformat()
        raise TypeError(type(o))

    return json.dumps([asdict(s) for s in sections], default=enc, indent=2)

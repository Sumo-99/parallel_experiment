from __future__ import annotations

import tomllib
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

DEFAULT_CONFIG = Path(__file__).resolve().parent.parent / "config.toml"


@dataclass(frozen=True)
class SearchSettings:
    include_domains: list[str] = field(default_factory=list)
    start_published_date: date | None = None
    num_results: int = 10
    min_score: float = 0.0
    type: str = "auto"
    provider: str = "exa"


@dataclass(frozen=True)
class Settings:
    search: SearchSettings
    max_items_per_section: int = 5


def load_settings(path: Path | str = DEFAULT_CONFIG) -> Settings:
    raw = tomllib.loads(Path(path).read_text())
    s = raw.get("search", {})
    start = s.get("start_published_date")
    if isinstance(start, str):
        start = date.fromisoformat(start)
    search = SearchSettings(
        include_domains=list(s.get("include_domains", [])),
        start_published_date=start,
        num_results=int(s.get("num_results", 10)),
        min_score=float(s.get("min_score", 0.0)),
        type=s.get("type", "auto"),
        provider=s.get("provider", "exa"),
    )
    out = raw.get("output", {})
    return Settings(search=search, max_items_per_section=int(out.get("max_items_per_section", 5)))


def load_queries(path: Path | str) -> list[str]:
    lines = Path(path).read_text().splitlines()
    return [ln.strip() for ln in lines if ln.strip() and not ln.lstrip().startswith("#")]

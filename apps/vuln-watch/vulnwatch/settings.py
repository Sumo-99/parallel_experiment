import json
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


@dataclass(frozen=True)
class SearchConfig:
    include_domains: list = field(default_factory=list)
    start_date: str | None = None
    max_results: int = 5
    min_score: float = 0.0
    search_depth: str = "basic"


@dataclass(frozen=True)
class Config:
    search: SearchConfig
    max_per_watch: int = 4


def load_config(path=ROOT / "settings.json") -> Config:
    data = json.loads(Path(path).read_text())
    s = data.get("search", {})
    return Config(
        search=SearchConfig(
            include_domains=s.get("include_domains", []),
            start_date=s.get("start_date"),
            max_results=s.get("max_results", 5),
            min_score=s.get("min_score", 0.0),
            search_depth=s.get("search_depth", "basic"),
        ),
        max_per_watch=data.get("report", {}).get("max_per_watch", 4),
    )


def load_watchlist(path=ROOT / "watchlist.txt") -> list[str]:
    return [
        line.strip()
        for line in Path(path).read_text().splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]

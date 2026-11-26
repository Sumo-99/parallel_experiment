from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from dotenv import load_dotenv

from brief.config import DEFAULT_CONFIG, load_queries, load_settings
from brief.digest import build_sections, render_markdown, to_json
from brief.search import ExaSearch, SearchError

ROOT = Path(__file__).resolve().parent.parent


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="climate-brief")
    parser.add_argument("--config", default=str(DEFAULT_CONFIG))
    parser.add_argument("--queries", default=str(ROOT / "queries.txt"))
    parser.add_argument("--out", default=str(ROOT / "out" / "brief.md"))
    parser.add_argument("--json", action="store_true", help="print JSON to stdout instead of writing markdown")
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO if args.verbose else logging.WARNING, format="%(levelname)s %(message)s")
    load_dotenv(ROOT / ".env")

    settings = load_settings(args.config)
    queries = load_queries(args.queries)
    try:
        client = ExaSearch(settings.search)
        results = {q: client.search(q) for q in queries}
    except SearchError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1

    sections = build_sections(results, settings.search.min_score, settings.max_items_per_section)
    if args.json:
        print(to_json(sections))
        return 0
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(render_markdown(sections))
    print(f"wrote {out} ({sum(len(s.items) for s in sections)} items)")
    return 0

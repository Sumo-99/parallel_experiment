import argparse
import json
import sys
from pathlib import Path

from dotenv import load_dotenv

from vulnwatch.digest import build_digest, summary_text
from vulnwatch.provider import AdvisorySearch
from vulnwatch.settings import ROOT, load_config, load_watchlist


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="vulnwatch")
    p.add_argument("--settings", default=str(ROOT / "settings.json"))
    p.add_argument("--watchlist", default=str(ROOT / "watchlist.txt"))
    p.add_argument("--out", default=str(ROOT / "reports" / "digest.json"))
    p.add_argument("--stdout", action="store_true", help="print the digest JSON instead of writing a file")
    args = p.parse_args(argv)

    load_dotenv(ROOT / ".env")
    config = load_config(args.settings)
    search = AdvisorySearch(config.search)
    try:
        by_watch = {w: search.search(w) for w in load_watchlist(args.watchlist)}
    except Exception as e:  # the SDK raises several error types
        print(f"search failed: {e}", file=sys.stderr)
        return 1

    digest = build_digest(by_watch, config.search.min_score, config.max_per_watch)
    if args.stdout:
        print(json.dumps(digest, indent=2))
        return 0
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(digest, indent=2))
    print(summary_text(digest))
    return 0

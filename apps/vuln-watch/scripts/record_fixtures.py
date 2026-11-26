"""Refresh the recorded Tavily responses used by the tests. Needs TAVILY_API_KEY."""

import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from tavily import TavilyClient

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from vulnwatch.settings import load_config  # noqa: E402

CASES = {
    "tavily_openssl.json": "OpenSSL vulnerability advisory",
    "tavily_nodejs.json": "Node.js security release",
}


def main():
    load_dotenv(ROOT / ".env")
    c = load_config().search
    client = TavilyClient(api_key=os.environ["TAVILY_API_KEY"])
    for name, query in CASES.items():
        data = client.search(
            query,
            search_depth=c.search_depth,
            max_results=c.max_results,
            include_domains=c.include_domains,
            start_date=c.start_date,
        )
        (ROOT / "tests" / "fixtures" / name).write_text(json.dumps(data, indent=2) + "\n")
        print(f"recorded {name}")


if __name__ == "__main__":
    main()

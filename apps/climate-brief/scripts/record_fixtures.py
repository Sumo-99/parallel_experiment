"""Re-record the Exa responses used by the tests. Needs EXA_API_KEY."""

import json
import sys
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from brief.config import load_settings  # noqa: E402
from brief.search import EXA_SEARCH_URL, ExaSearch  # noqa: E402

CASES = {
    "exa_storage.json": "long-duration energy storage startup raises Series B",
    "exa_sodium.json": "sodium-ion battery manufacturing plant announcement",
}


def main():
    load_dotenv(ROOT / ".env")
    client = ExaSearch(load_settings(ROOT / "config.toml").search)
    for name, query in CASES.items():
        resp = client.session.post(
            EXA_SEARCH_URL, json=client.build_request(query), headers={"x-api-key": client.api_key}, timeout=30
        )
        resp.raise_for_status()
        (ROOT / "tests" / "fixtures" / name).write_text(json.dumps(resp.json(), indent=2) + "\n")
        print(f"recorded {name}")


if __name__ == "__main__":
    main()

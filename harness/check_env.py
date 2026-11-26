"""Preflight: which keys are set (names only, never values) and which hosts this environment can reach.

  uv run python -m harness.check_env
Sends no keys and makes no billable calls (plain GETs to host roots).
"""

from __future__ import annotations

import sys

import requests

from harness.common import key_status

HOSTS = ["api.exa.ai", "api.tavily.com", "api.parallel.ai", "parallel.ai", "docs.parallel.ai", "github.com", "api.anthropic.com", "pypi.org"]


def main() -> int:
    ks = key_status()
    for k, ok in ks.items():
        print(f"{k:18} {'set' if ok else 'MISSING'}")
    bad = 0
    for h in HOSTS:
        try:
            r = requests.get(f"https://{h}/", timeout=10)
            print(f"{h:20} reachable (HTTP {r.status_code})")
        except requests.exceptions.SSLError:
            print(f"{h:20} TLS error"); bad += 1
        except Exception as e:
            print(f"{h:20} BLOCKED ({type(e).__name__})"); bad += 1
    return 0 if all(ks.values()) and not bad else 1


if __name__ == "__main__":
    sys.exit(main())

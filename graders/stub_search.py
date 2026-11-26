"""Local stand-in for the search APIs, used ONLY to validate the graders offline.

It honours the filters a real API would (domains, start date, result count), so a
migration that drops a filter produces visibly wrong results, just as it would live.
Records served by it are tagged stub=true in the proxy log and never count as real results.
"""

from __future__ import annotations

from datetime import date
from urllib.parse import urlparse

# A small pool spanning trusted and untrusted domains and old and new dates.
POOL = [
    ("https://techcrunch.com/2026/10/14/ldes-series-b/", "Storage startup raises Series B", "2026-10-14"),
    ("https://www.canarymedia.com/articles/energy-storage/100-hour", "Utilities buy 100-hour batteries", "2026-09-22"),
    ("https://www.utilitydive.com/news/vpp-utility-partnership/", "Utility signs VPP partnership", "2026-10-03"),
    ("https://electrek.co/2026/10/02/sodium-ion-plant/", "Sodium-ion plant announced", "2026-10-02"),
    ("https://heatmap.news/technology/geothermal-round", "Geothermal driller closes round", "2026-11-02"),
    ("https://www.latitudemedia.com/news/dac-offtake", "DAC offtake signed", "2026-09-15"),
    ("https://techcrunch.com/2025/03/01/old-story/", "An old story from 2025", "2025-03-01"),
    ("https://randomblog.example.org/post/storage-hype", "Storage hype, a blog post", "2026-10-20"),
    ("https://nvd.nist.gov/vuln/detail/CVE-2026-41187", "NVD - CVE-2026-41187", "2026-10-21"),
    ("https://github.com/openssl/openssl/security/advisories/GHSA-9x4m", "OpenSSL advisory", "2026-10-21"),
    ("https://www.cisa.gov/news-events/alerts/2026/11/05/nodejs", "Node.js Releases Security Updates", "2026-11-05"),
    ("https://www.bleepingcomputer.com/news/security/openssl-patch/", "OpenSSL patches flaw", "2026-10-22"),
    ("https://nvd.nist.gov/vuln/detail/CVE-2024-0001", "Old 2024 CVE", "2024-02-01"),
    ("https://medium.com/@someone/cve-roundup", "CVE roundup on Medium", "2026-11-01"),
]


def _host_ok(url: str, domains: list[str] | None) -> bool:
    if not domains:
        return True
    host = urlparse(url).hostname or ""
    for d in domains:
        d = d.lower().lstrip("*.").split("/")[0]
        if host == d or host.endswith("." + d):
            return True
    return False


def _filtered(domains, after: str | None, n: int):
    out = []
    for url, title, pub in POOL:
        if not _host_ok(url, domains):
            continue
        if after and date.fromisoformat(pub[:10]) < date.fromisoformat(after[:10]):
            continue
        out.append((url, title, pub))
    return out[: max(0, n)]


def stub_response(host: str, path: str, body: dict) -> tuple[int, dict]:
    if host == "api.parallel.ai" and "/search" in path:
        adv = body.get("advanced_settings") or {}
        sp = adv.get("source_policy") or body.get("source_policy") or {}
        n = adv.get("max_results") or body.get("max_results") or 10
        if not body.get("search_queries") and "/v1/" in path:
            return 422, {"error": {"message": "search_queries is required"}}
        rows = _filtered(sp.get("include_domains"), sp.get("after_date"), int(n))
        return 200, {
            "search_id": "search_stub",
            "results": [{"url": u, "title": t, "publish_date": p, "excerpts": [f"{t}. Stub excerpt."]} for u, t, p in rows],
            "warnings": None,
            "usage": [{"name": "sku_search", "count": 1}],
        }
    if host == "api.exa.ai":
        rows = _filtered(body.get("includeDomains"), body.get("startPublishedDate"), int(body.get("numResults") or 10))
        return 200, {"results": [{"id": u, "url": u, "title": t, "publishedDate": p + "T00:00:00.000Z", "score": round(0.35 - i * 0.04, 3),
                                  "highlights": [t]} for i, (u, t, p) in enumerate(rows)]}
    if host == "api.tavily.com":
        rows = _filtered(body.get("include_domains"), body.get("start_date"), int(body.get("max_results") or 5))
        return 200, {"query": body.get("query"), "results": [{"url": u, "title": t, "content": t, "score": round(0.9 - i * 0.1, 2),
                                                                "published_date": p} for i, (u, t, p) in enumerate(rows)]}
    return 404, {"error": "stub has no route"}

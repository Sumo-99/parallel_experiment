"""mitmproxy addon: log search-API traffic and enforce the search spend cap.

Configured through environment variables set by harness/proxy.py:
  PE_LOG         JSONL file for captured requests (one line per request)
  PE_SPEND_LOG   shared JSONL ledger of estimated search spend
  PE_CAP_USD     hard cap; once reached, search requests get a 402 and are not forwarded
  PE_RUN_ID      tag written into each record
  PE_STUB        if "1", answer search requests locally with graders/stub_search.py
                 (offline grader validation only; records are tagged stub=true)

Only api.exa.ai, api.tavily.com and api.parallel.ai are intercepted (mitmdump --allow-hosts);
everything else is tunnelled untouched. Auth headers and any *api_key* body fields are dropped
before logging.
"""

import json
import os
import sys
import threading
import time
from pathlib import Path

from mitmproxy import http

SEARCH_HOSTS = {"api.exa.ai", "api.tavily.com", "api.parallel.ai"}
SECRET_HEADERS = {"authorization", "x-api-key", "api-key", "x-goog-api-key"}
_lock = threading.Lock()

LOG = Path(os.environ["PE_LOG"])
SPEND = Path(os.environ["PE_SPEND_LOG"])
CAP = float(os.environ.get("PE_CAP_USD", "10"))
RUN_ID = os.environ.get("PE_RUN_ID", "")
STUB = os.environ.get("PE_STUB") == "1"

if STUB:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from graders.stub_search import stub_response  # noqa: E402

TASK_PROCESSOR_USD = {"lite": 0.005, "base": 0.01, "core": 0.025, "core2x": 0.05, "pro": 0.1,
                      "ultra": 0.3, "ultra2x": 0.6, "ultra4x": 1.2, "ultra8x": 2.4}


def _scrub(obj):
    if isinstance(obj, dict):
        return {k: ("<redacted>" if "api_key" in k.lower() or k.lower() == "apikey" else _scrub(v)) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_scrub(v) for v in obj]
    return obj


def _json(raw: bytes | None):
    if not raw:
        return None
    try:
        return _scrub(json.loads(raw))
    except Exception:
        return {"_non_json": raw[:500].decode("utf-8", "replace")}


def estimate_usd(host: str, path: str, body) -> float:
    body = body if isinstance(body, dict) else {}
    if host == "api.exa.ai":
        return 0.01
    if host == "api.tavily.com":
        depth = body.get("search_depth", "basic")
        return 0.016 if depth == "advanced" else 0.008
    if host == "api.parallel.ai":
        if "/search" in path:
            return 0.005 + 0.001 * max(0, int((body.get("advanced_settings") or {}).get("max_results") or body.get("max_results") or 10) - 10)
        if "/extract" in path:
            return 0.001 * max(1, len(body.get("urls") or []))
        if "/tasks" in path or "/task" in path:
            return TASK_PROCESSOR_USD.get(body.get("processor", ""), 2.4) if path.rstrip("/").endswith("runs") else 0.0
        if "/responses" in path:
            return 0.25
        if "/findall" in path:
            return 1.0
        return 0.01
    return 0.0


def _spent() -> float:
    if not SPEND.exists():
        return 0.0
    total = 0.0
    for line in SPEND.read_text().splitlines():
        try:
            total += float(json.loads(line).get("usd", 0))
        except Exception:
            pass
    return total


def _append(path: Path, rec: dict):
    with _lock:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a") as f:
            f.write(json.dumps(rec) + "\n")


class SearchCapture:
    def request(self, flow: http.HTTPFlow):
        host = flow.request.pretty_host
        if host not in SEARCH_HOSTS:
            return
        flow.metadata["pe_ts"] = time.time()
        body = _json(flow.request.raw_content)
        usd = 0.0 if STUB or flow.request.method == "GET" else estimate_usd(host, flow.request.path, body)
        flow.metadata["pe_usd"] = usd
        if usd and _spent() + usd > CAP:
            flow.metadata["pe_blocked"] = True
            flow.response = http.Response.make(402, json.dumps({"error": "local spend cap reached"}), {"content-type": "application/json"})
            return
        if STUB:
            status, payload = stub_response(host, flow.request.path, body if isinstance(body, dict) else {})
            flow.response = http.Response.make(status, json.dumps(payload), {"content-type": "application/json"})
            flow.metadata["pe_stub"] = True

    def response(self, flow: http.HTTPFlow):
        host = flow.request.pretty_host
        if host not in SEARCH_HOSTS:
            return
        usd = flow.metadata.get("pe_usd", 0.0)
        blocked = bool(flow.metadata.get("pe_blocked"))
        if usd and not blocked:
            _append(SPEND, {"ts": time.time(), "run_id": RUN_ID, "host": host, "path": flow.request.path, "usd": usd})
        headers = {k: v for k, v in flow.request.headers.items() if k.lower() not in SECRET_HEADERS}
        _append(LOG, {
            "ts": flow.metadata.get("pe_ts", time.time()),
            "run_id": RUN_ID,
            "host": host,
            "method": flow.request.method,
            "path": flow.request.path,
            "req_headers": headers,
            "auth_header_present": any(k.lower() in SECRET_HEADERS for k in flow.request.headers.keys()),
            "req_body": _json(flow.request.raw_content),
            "status": flow.response.status_code if flow.response else None,
            "resp_body": _json(flow.response.raw_content) if flow.response else None,
            "est_usd": usd,
            "blocked_by_cap": blocked,
            "stub": bool(flow.metadata.get("pe_stub")),
        })


addons = [SearchCapture()]

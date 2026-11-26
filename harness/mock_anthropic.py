"""MOCK Anthropic Messages API for $0 end-to-end dry runs of the harness. NOT a real model.

Plays back a scripted list of assistant turns to the real Claude Code CLI (so the real driver,
permission callbacks, scripted answers, proxy capture and graders are all exercised).
Everything produced with it is MOCK DATA and must never be reported as a real result.
"""

from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


class MockAnthropic:
    def __init__(self, turns: list[list[dict]]):
        self.turns = turns            # each turn: list of content blocks (text / tool_use)
        self.i = 0
        self.lock = threading.Lock()
        self.requests = 0
        outer = self

        class H(BaseHTTPRequestHandler):
            def log_message(self, *a):  # quiet
                pass

            def do_POST(self):
                n = int(self.headers.get("content-length") or 0)
                body = json.loads(self.rfile.read(n) or b"{}")
                if self.path.startswith("/v1/messages/count_tokens"):
                    return self._json({"input_tokens": 100})
                if not self.path.startswith("/v1/messages"):
                    return self._json({"error": "mock: no route"}, 404)
                outer.requests += 1
                if body.get("tools"):
                    with outer.lock:
                        blocks = outer.turns[outer.i] if outer.i < len(outer.turns) else [{"type": "text", "text": "(mock script finished)"}]
                        outer.i += 1
                else:   # title / quota / side requests
                    blocks = [{"type": "text", "text": "ok"}]
                has_tool = any(b["type"] == "tool_use" for b in blocks)
                if body.get("stream"):
                    self._sse(blocks, has_tool)
                else:
                    self._json(self._msg(blocks, has_tool))

            def _msg(self, blocks, has_tool):
                return {"id": "msg_mock", "type": "message", "role": "assistant", "model": "claude-haiku-5-5",
                        "content": blocks, "stop_reason": "tool_use" if has_tool else "end_turn", "stop_sequence": None,
                        "usage": {"input_tokens": 10, "output_tokens": 10}}

            def _json(self, obj, code=200):
                data = json.dumps(obj).encode()
                self.send_response(code)
                self.send_header("content-type", "application/json")
                self.send_header("content-length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)

            def _sse(self, blocks, has_tool):
                self.send_response(200)
                self.send_header("content-type", "text/event-stream")
                self.send_header("cache-control", "no-cache")
                self.end_headers()

                def ev(name, data):
                    self.wfile.write(f"event: {name}\ndata: {json.dumps(data)}\n\n".encode())

                msg = self._msg([], has_tool)
                ev("message_start", {"type": "message_start", "message": {**msg, "stop_reason": None}})
                for idx, b in enumerate(blocks):
                    if b["type"] == "text":
                        ev("content_block_start", {"type": "content_block_start", "index": idx, "content_block": {"type": "text", "text": ""}})
                        ev("content_block_delta", {"type": "content_block_delta", "index": idx, "delta": {"type": "text_delta", "text": b["text"]}})
                    else:
                        ev("content_block_start", {"type": "content_block_start", "index": idx,
                                                   "content_block": {"type": "tool_use", "id": b["id"], "name": b["name"], "input": {}}})
                        ev("content_block_delta", {"type": "content_block_delta", "index": idx,
                                                   "delta": {"type": "input_json_delta", "partial_json": json.dumps(b["input"])}})
                    ev("content_block_stop", {"type": "content_block_stop", "index": idx})
                ev("message_delta", {"type": "message_delta", "delta": {"stop_reason": msg["stop_reason"], "stop_sequence": None},
                                     "usage": {"output_tokens": 10}})
                ev("message_stop", {"type": "message_stop"})

        self.httpd = ThreadingHTTPServer(("127.0.0.1", 0), H)
        self.port = self.httpd.server_address[1]
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)

    @property
    def url(self) -> str:
        return f"http://127.0.0.1:{self.port}"

    def start(self):
        self.thread.start()
        return self

    def stop(self):
        self.httpd.shutdown()

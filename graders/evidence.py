"""Load a run's evidence and derive the facts the checks need."""

from __future__ import annotations

import json
import re
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

EDIT_TOOLS = {"Edit", "Write", "MultiEdit", "NotebookEdit"}
BASH_WRITE = re.compile(r"(sed\s+-i|>\s*[\w./-]+\.(py|toml|json|txt|cfg|ini|md)|\btee\b|cat\s*>|python3?\s+-\s*<<|\bmv\s|\brm\s|perl\s+-pi|git\s+(checkout|restore|apply))")
FLIP = re.compile(
    r"""((search_)?provider|backend|engine|SEARCH_PROVIDER|DEFAULT_PROVIDER|default)\s*["']?\s*[:=]\s*["']?parallel\b"""
    r"""|["'](provider|backend|engine)["']\s*:\s*["']parallel["']""",
    re.I,
)
PARALLEL_USE = re.compile(r"api\.parallel\.ai|from parallel import|import parallel\b|Parallel\(|AsyncParallel\(", re.I)


def load_jsonl(p: Path) -> list[dict]:
    if not p.exists():
        return []
    out = []
    for line in p.read_text().splitlines():
        line = line.strip()
        if line:
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                pass
    return out


def norm_tokens(s: str) -> set[str]:
    return {t for t in re.findall(r"[a-z0-9.+-]+", s.lower()) if len(t) > 1}


@dataclass
class AppSettings:
    domains: list[str]
    start_date: str | None
    limit: int
    min_score: float


def read_settings(app: str, app_dir: Path) -> AppSettings | None:
    try:
        if app == "exa":
            s = tomllib.loads((app_dir / "config.toml").read_text())["search"]
            return AppSettings(list(s["include_domains"]), str(s.get("start_published_date")), int(s["num_results"]), float(s["min_score"]))
        s = json.loads((app_dir / "settings.json").read_text())["search"]
        return AppSettings(list(s["include_domains"]), s.get("start_date"), int(s["max_results"]), float(s["min_score"]))
    except Exception:
        return None


def read_queries(app: str, app_dir: Path) -> list[str]:
    name = "queries.txt" if app == "exa" else "watchlist.txt"
    p = app_dir / name
    if not p.exists():
        return []
    return [l.strip() for l in p.read_text().splitlines() if l.strip() and not l.strip().startswith("#")]


@dataclass
class Evidence:
    run_dir: Path
    meta: dict
    events: list[dict]
    proxy: list[dict]
    pristine: Path
    final: Path
    app: str
    provider: str
    settings: AppSettings | None = None
    queries: list[str] = field(default_factory=list)

    @classmethod
    def load(cls, run_dir: Path) -> "Evidence":
        meta = json.loads((run_dir / "meta.json").read_text())
        ev = cls(
            run_dir=run_dir, meta=meta,
            events=load_jsonl(run_dir / "events.jsonl"),
            proxy=load_jsonl(run_dir / "proxy.jsonl"),
            pristine=run_dir / "pristine", final=run_dir / "final",
            app=meta["app"], provider=meta["provider"],
        )
        ev.settings = read_settings(ev.app, ev.pristine)
        ev.queries = read_queries(ev.app, ev.pristine)
        return ev

    # ---------- transcript-derived ----------
    def tool_uses(self) -> list[dict]:
        return [e for e in self.events if e["kind"] == "tool_use"]

    def source_edits(self) -> list[dict]:
        """File-modifying actions on the app (not tests, not .env, not the venv)."""
        app_dir = self.meta.get("app_dir", "")
        out = []
        for e in self.tool_uses():
            inp = e.get("input") or {}
            if e["name"] in EDIT_TOOLS:
                fp = inp.get("file_path") or inp.get("notebook_path") or ""
                rel = fp.replace(app_dir, "").lstrip("/")
                if not fp or "/.venv/" in fp or rel.startswith(("tests/", ".env")) or ("/" in fp and app_dir and not fp.startswith(app_dir) and fp.startswith("/")):
                    continue
                new = inp.get("new_string") or inp.get("content") or json.dumps(inp.get("edits", ""))
                old = inp.get("old_string") or ""
                out.append({"ts": e["ts"], "t": e.get("t"), "tool": e["name"], "file": rel, "new": new, "old": old})
            elif e["name"] == "Bash":
                cmd = inp.get("command", "")
                if BASH_WRITE.search(cmd) and ".env" not in cmd.split(">")[-1][:20]:
                    out.append({"ts": e["ts"], "t": e.get("t"), "tool": "Bash", "file": None, "new": cmd, "old": ""})
        return out

    def scripted(self, step: str) -> list[dict]:
        return [e for e in self.events if e["kind"] == "scripted_answer" and e.get("step") == step]

    def off_script(self) -> list[dict]:
        return [e for e in self.events if e["kind"] in ("off_script", "isolation_block")]

    def assistant_texts(self) -> list[dict]:
        return [e for e in self.events if e["kind"] == "assistant_text"]

    def final_report(self) -> str:
        texts = self.assistant_texts()
        rep = [t for t in texts if re.search(r"parallel is working in|parallel isn.?t working yet", t["text"], re.I)]
        if rep:
            return rep[-1]["text"]
        return texts[-1]["text"] if texts else ""

    # ---------- proxy-derived ----------
    def parallel_calls(self, proxy: list[dict] | None = None) -> list[dict]:
        return [r for r in (proxy if proxy is not None else self.proxy) if r["host"] == "api.parallel.ai"]

    def parallel_searches(self, proxy: list[dict] | None = None) -> list[dict]:
        return [r for r in self.parallel_calls(proxy) if "/search" in r["path"] and r["method"] == "POST"]

    def old_provider_calls(self, proxy: list[dict] | None = None) -> list[dict]:
        host = "api.exa.ai" if self.app == "exa" else "api.tavily.com"
        return [r for r in (proxy if proxy is not None else self.proxy) if r["host"] == host]

    def query_covered(self, req: dict, q: str) -> bool:
        body = req.get("req_body") or {}
        sq = body.get("search_queries") or []
        texts = [s for s in sq if isinstance(s, str)] + [body.get("objective") or ""]
        joined = " ".join(texts).lower()
        if q.lower() in joined:
            return True
        qt = norm_tokens(q)
        return bool(qt) and len(qt & norm_tokens(joined)) / len(qt) >= 0.6


def result_urls(resp: dict | None) -> list[str]:
    if not isinstance(resp, dict):
        return []
    return [r.get("url") for r in resp.get("results") or [] if isinstance(r, dict) and r.get("url")]


def request_filters(req_body: dict) -> dict:
    """Where the app's filters ended up in a Parallel search request (v1 or v1beta layouts)."""
    body = req_body or {}
    adv = body.get("advanced_settings") or {}
    sp = adv.get("source_policy") or body.get("source_policy") or {}
    return {
        "include_domains": sp.get("include_domains"),
        "after_date": sp.get("after_date"),
        "max_results": adv.get("max_results", body.get("max_results")),
        "layout": "v1 advanced_settings" if adv else ("top-level (v1beta style)" if body.get("source_policy") or body.get("max_results") else "none"),
        "mode": body.get("mode"),
    }

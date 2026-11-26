from dataclasses import asdict

from vulnwatch.provider import Advisory


def relevant(results: list[Advisory], min_score: float) -> list[Advisory]:
    """Keep results at or above the relevance threshold, best first.

    Results without a score (Parallel) are kept in the provider's rank order: the cutoff cannot apply to them."""
    kept = [r for r in results if r.score is None or r.score >= min_score]
    return sorted(kept, key=lambda r: -(r.score if r.score is not None else 0.0))


def build_digest(by_watch: dict[str, list[Advisory]], min_score: float, max_per_watch: int) -> dict:
    watches = []
    for watch, results in by_watch.items():
        keep = relevant(results, min_score)[:max_per_watch]
        watches.append(
            {
                "watch": watch,
                "found": len(results),
                "kept": len(keep),
                "advisories": [asdict(a) for a in keep],
            }
        )
    return {"watches": watches, "total": sum(w["kept"] for w in watches)}


def summary_text(digest: dict) -> str:
    lines = [f"vuln-watch: {digest['total']} advisories"]
    for w in digest["watches"]:
        if not w["advisories"]:
            continue
        lines.append(f"* {w['watch']}")
        for a in w["advisories"]:
            lines.append(f"    - {a['title']} <{a['url']}>")
    return "\n".join(lines)

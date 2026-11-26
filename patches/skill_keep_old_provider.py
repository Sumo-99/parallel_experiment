"""Fix test: move the 'keep the old provider until Parallel passes' rule into the Onboarding steps
and the plan/report messages of the parallel-api SKILL.md. Applied to the installed copy only."""
from pathlib import Path

EDITS = [
    ('Plan: <API> (<mode, effort or processor>), about <cost> per call. <One-line reason>. Go ahead?"',
     'Plan: <API> (<mode, effort or processor>), about <cost> per call. <One-line reason>. When replacing a provider, add: <provider> stays in place until Parallel passes a test on the project\'s real queries; only then do I switch the default. Go ahead?"'),
    ('3. Follow "Setup", write the smallest working integration in the project\'s style, and run "Verify" step 1.',
     '3. Follow "Setup" and write the smallest working integration in the project\'s style. When replacing a provider, add Parallel next to the old provider and do not delete or edit the old provider\'s code path yet; run "Verify" step 1, then run the project\'s real queries (every line of its query file) through Parallel, and switch the default only if they pass.'),
    ('   Changed: <files>\n   Next: <one suggestion>"',
     '   Changed: <files>\n   Old provider: <kept as a fallback, or removed (say why) and how many of the real queries passed first>\n   Next: <one suggestion>"'),
]


def patch_text(t: str) -> str:
    for a, b in EDITS:
        if a not in t:
            raise ValueError("anchor not found: " + a[:50])
        t = t.replace(a, b, 1)
    return t


def patch_tree(home: Path) -> list[str]:
    done = []
    for f in Path(home).rglob("parallel-api/SKILL.md"):
        f.write_text(patch_text(f.read_text()))
        done.append(str(f.relative_to(home)))
    return done


if __name__ == "__main__":  # write the reviewable diff
    import difflib, sys
    src = Path(sys.argv[1]).read_text()
    sys.stdout.writelines(difflib.unified_diff(src.splitlines(True), patch_text(src).splitlines(True), "SKILL.md", "SKILL.md (patched)"))

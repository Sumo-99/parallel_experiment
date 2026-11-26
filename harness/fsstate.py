"""File-state evidence: after each edit/Bash step, record a hash of every app source file (and keep the contents).

Graders use this to decide WHEN the app's behaviour/config changed from what the files actually contain,
not from the text of shell commands.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

SKIP_DIRS = {".venv", ".git", "__pycache__", ".pytest_cache", "node_modules", "out", "reports"}
MAX_BYTES = 300_000


def capture(app_dir: Path, run_dir: Path) -> dict[str, str]:
    blobs = run_dir / "blobs"
    blobs.mkdir(exist_ok=True)
    files: dict[str, str] = {}
    for p in sorted(app_dir.rglob("*")):
        rel = p.relative_to(app_dir)
        if not p.is_file() or p.is_symlink() or any(part in SKIP_DIRS or part.endswith(".egg-info") for part in rel.parts) or rel.name == ".env":
            continue
        try:
            data = p.read_bytes()
        except OSError:
            continue
        if len(data) > MAX_BYTES or b"\0" in data:
            continue
        sha = hashlib.sha1(data).hexdigest()
        files[str(rel)] = sha
        b = blobs / sha
        if not b.exists():
            b.write_bytes(data)
    return files

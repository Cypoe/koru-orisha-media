#!/usr/bin/env python3
"""Publish a tiny manifest-shaped JSON fixture via vendor/json (or Python).

Prefers the Koru one-shot (`bin/json-publish`, src/json usage of vendor/json) when that
binary exists. Otherwise emits the same object with the stdlib json module
so indexer tests stay green without koruc.

  python3 scripts/json_publish.py --out /tmp/fixture.json

Not used by Orisha request handlers. Full indexer publish remains
scripts/index_media.py until a Koru walker exists.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
KORU_BIN = ROOT / "bin" / "json-publish"

# Semantic twin of src/json emitEntries (vendor/json + usage fixtures).
FIXTURE = {
    "entries": [
        {
            "id": "m_fixture",
            "kind": "movie",
            "title": "demo",
        }
    ]
}

# Semantic twin of src/json emitProjections (vendor/json + usage fixtures).
PROJECTIONS = {
    "projections": [
        {
            "asset_id": "m_fixture",
            "construction": "orisha.item",
            "display_title": "Demo",
        }
    ]
}


def python_dumps(obj: dict) -> str:
    return json.dumps(obj, indent=2, sort_keys=True) + "\n"


def koru_dumps() -> str | None:
    if not KORU_BIN.is_file():
        return None
    try:
        out = subprocess.check_output([str(KORU_BIN)], text=True, stderr=subprocess.PIPE)
    except (OSError, subprocess.CalledProcessError):
        return None
    json.loads(out)  # must be parseable JSON
    return out if out.endswith("\n") else out + "\n"


def emit_fixture_text(*, prefer_koru: bool = True) -> tuple[str, str]:
    """Return (json_text, engine) where engine is 'src/json' or 'python'."""
    if prefer_koru:
        text = koru_dumps()
        if text is not None:
            return text, "src/json"
    return python_dumps(FIXTURE), "python"


def atomic_write(path: Path, data: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", dir=str(path.parent), delete=False
    ) as tmp:
        tmp.write(data)
        tmp.flush()
        os.fsync(tmp.fileno())
        tmp_name = tmp.name
    os.replace(tmp_name, path)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, required=True, help="JSON output path")
    ap.add_argument(
        "--python-only",
        action="store_true",
        help="Skip bin/json-publish even if present",
    )
    args = ap.parse_args()
    text, engine = emit_fixture_text(prefer_koru=not args.python_only)
    atomic_write(args.out.resolve(), text)
    print(f"wrote {args.out} ({engine})", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

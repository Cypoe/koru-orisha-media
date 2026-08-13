#!/usr/bin/env python3
"""Pure projection: core snapshot (+ optional physical titles) → projections[].

Runs every named construction (orisha.item, orisha.links, schema.org.jsonld).
Does not mutate Entity. Orisha dumps these strings. Never called from request
handlers.

  python3 scripts/project_semantic.py \\
      --in fixtures/semantic.json --out fixtures/semantic.json
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from semantic_schema import (  # noqa: E402
    Projection,
    SemanticSnapshot,
    project_all,
)


def load_physical_titles(path: Path) -> dict[str, str]:
    data = json.loads(path.read_text(encoding="utf-8"))
    out: dict[str, str] = {}
    for entry in data.get("entries", []):
        eid = entry.get("id")
        title = entry.get("title")
        if isinstance(eid, str) and eid and isinstance(title, str) and title:
            out[eid] = title
    return out


def project_snapshot(
    snap: SemanticSnapshot,
    *,
    physical_titles: dict[str, str] | None = None,
    base: str = "https://media.local",
) -> list[Projection]:
    """Core graph → named construction rows. Unlinked assets get no row."""
    return project_all(snap, physical_titles=physical_titles, base=base)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--in", dest="infile", type=Path, required=True)
    ap.add_argument("--out", dest="outfile", type=Path, required=True)
    ap.add_argument("--base", default="https://media.local")
    ap.add_argument(
        "--manifest",
        type=Path,
        default=None,
        help="Optional physical manifest for filename titles",
    )
    args = ap.parse_args()

    snap = SemanticSnapshot.from_dict(json.loads(args.infile.read_text(encoding="utf-8")))
    physical_titles = load_physical_titles(args.manifest) if args.manifest else None
    snap.projections = project_snapshot(snap, physical_titles=physical_titles, base=args.base)
    args.outfile.parent.mkdir(parents=True, exist_ok=True)
    args.outfile.write_text(json.dumps(snap.to_dict(), indent=2) + "\n", encoding="utf-8")
    print(f"wrote {args.outfile}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

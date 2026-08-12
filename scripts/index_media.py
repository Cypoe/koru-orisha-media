#!/usr/bin/env python3
"""One-shot indexer: walk a media root, emit a minimal JSON manifest atomically.

Usage:
  python3 scripts/index_media.py --root fixtures/media --out data/manifest.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
import mimetypes
import os
import re
import sys
import tempfile
from pathlib import Path


VIDEO_EXT = {".mp4", ".m4v", ".webm", ".mkv", ".mov"}
AUDIO_EXT = {".mp3", ".m4a", ".aac", ".flac", ".ogg", ".wav"}
POSTER_EXT = (".webp", ".jpg", ".jpeg", ".png")


def opaque_id(rel: str, size: int, mtime_ns: int) -> str:
    h = hashlib.sha1(f"{rel}|{size}|{mtime_ns}".encode()).hexdigest()[:6]
    return f"m_{h}"


def kind_for(path: Path) -> str:
    ext = path.suffix.lower()
    if ext in VIDEO_EXT:
        return "movie"
    if ext in AUDIO_EXT:
        return "audio"
    return "file"


def mime_for(path: Path) -> str:
    guess, _ = mimetypes.guess_type(str(path))
    return guess or "application/octet-stream"


def container_for(path: Path) -> str:
    return path.suffix.lower().lstrip(".") or "bin"


def find_poster(root: Path, media: Path) -> str | None:
    """Cheap sidecar artwork only — no container probe / FFmpeg."""
    stem = media.with_suffix("")
    for ext in POSTER_EXT:
        cand = Path(str(stem) + ext)
        if cand.is_file():
            return cand.relative_to(root).as_posix()
    parent = media.parent
    for name in ("poster", "folder", "cover"):
        for ext in POSTER_EXT:
            cand = parent / f"{name}{ext}"
            if cand.is_file():
                return cand.relative_to(root).as_posix()
    return None


def year_from_name(stem: str) -> int | None:
    """Optional year from trailing `(YYYY)` in the file stem — filesystem-cheap."""
    m = re.search(r"\((19|20)\d{2}\)\s*$", stem)
    if not m:
        m = re.search(r"\((19|20)\d{2}\)", stem)
    if not m:
        return None
    return int(m.group(0)[1:5])


def index_root(root: Path) -> list[dict]:
    entries: list[dict] = []
    seen: set[str] = set()
    for dirpath, _, filenames in os.walk(root):
        for name in sorted(filenames):
            full = Path(dirpath) / name
            if full.suffix.lower() not in VIDEO_EXT | AUDIO_EXT:
                continue
            rel = full.relative_to(root).as_posix()
            # Reject escapes (walk shouldn't produce them; belt-and-suspenders).
            if rel.startswith("../") or rel.startswith("/") or "\\" in rel:
                raise SystemExit(f"refusing path: {rel}")
            st = full.stat()
            eid = opaque_id(rel, st.st_size, st.st_mtime_ns)
            if eid in seen:
                raise SystemExit(f"duplicate id {eid} for {rel}")
            seen.add(eid)
            entry: dict = {
                "id": eid,
                "kind": kind_for(full),
                "title": full.stem,
                "path": rel,
                "bytes": st.st_size,
                "modified_ns": st.st_mtime_ns,
                "mime": mime_for(full),
                "container": container_for(full),
            }
            poster = find_poster(root, full)
            if poster:
                entry["poster"] = poster
            year = year_from_name(full.stem)
            if year is not None:
                entry["year"] = year
            entries.append(entry)
    entries.sort(key=lambda e: e["title"].lower())
    return entries


def atomic_write(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    data = json.dumps(payload, indent=2, sort_keys=True) + "\n"
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
    ap.add_argument("--root", type=Path, required=True, help="Media root to walk")
    ap.add_argument("--out", type=Path, required=True, help="Manifest output path")
    args = ap.parse_args()
    root = args.root.resolve()
    if not root.is_dir():
        print(f"not a directory: {root}", file=sys.stderr)
        return 2
    entries = index_root(root)
    atomic_write(args.out.resolve(), {"entries": entries})
    print(f"wrote {len(entries)} entries -> {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

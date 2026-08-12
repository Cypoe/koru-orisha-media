#!/usr/bin/env python3
"""One-shot indexer: walk a media root, emit a minimal JSON manifest atomically.

Usage:
  python3 scripts/index_media.py --root fixtures/media --out data/manifest.json
  python3 scripts/index_media.py --root fixtures/media --out data/manifest.json --write-id-sidecars
  python3 scripts/index_media.py --root fixtures/media --out data/manifest.json --probe ftyp
"""
from __future__ import annotations

import argparse
import hashlib
import json
import mimetypes
import os
import re
import struct
import sys
import tempfile
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional


VIDEO_EXT = {".mp4", ".m4v", ".webm", ".mkv", ".mov"}
AUDIO_EXT = {".mp3", ".m4a", ".aac", ".flac", ".ogg", ".wav"}
POSTER_EXT = (".webp", ".jpg", ".jpeg", ".png")
# Sidecar WebVTT only — same stem as the media file (demo.mp4 → demo.vtt).
SUBTITLE_EXT = (".vtt",)

# Sidecar next to the media file: "clip.mp4.id" → {"id": "m_ab12cd"}
ID_SIDECAR_SUFFIX = ".id"

# Optional[Mapping[str, Any]] return — plain Callable alias keeps py3.8 happy.
ProbeFn = Callable


def opaque_id(rel: str, size: int, mtime_ns: int) -> str:
    h = hashlib.sha1(f"{rel}|{size}|{mtime_ns}".encode()).hexdigest()[:6]
    return f"m_{h}"


def id_sidecar_path(media: Path) -> Path:
    return Path(str(media) + ID_SIDECAR_SUFFIX)


def media_path_for_sidecar(side: Path) -> Path:
    """`clip.mp4.id` → `clip.mp4`."""
    name = side.name
    if name.endswith(ID_SIDECAR_SUFFIX):
        return side.with_name(name[: -len(ID_SIDECAR_SUFFIX)])
    return side


def _parse_id_sidecar(side: Path) -> Optional[Dict[str, Any]]:
    """Parse a `*.id` sidecar; returns at least `{"id": ...}` or None."""
    if not side.is_file():
        return None
    try:
        data = json.loads(side.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(data, dict):
        return None
    eid = data.get("id")
    if not (isinstance(eid, str) and eid.startswith("m_") and len(eid) >= 3):
        return None
    out: Dict[str, Any] = {"id": eid}
    size = data.get("bytes")
    mtime_ns = data.get("modified_ns")
    if isinstance(size, int) and isinstance(mtime_ns, int):
        out["bytes"] = size
        out["modified_ns"] = mtime_ns
    return out


def read_id_sidecar(media: Path) -> Optional[str]:
    """Return a previously persisted opaque id, or None."""
    meta = _parse_id_sidecar(id_sidecar_path(media))
    return meta["id"] if meta else None


def write_id_sidecar(
    media: Path,
    eid: str,
    *,
    size: Optional[int] = None,
    mtime_ns: Optional[int] = None,
) -> None:
    side = id_sidecar_path(media)
    payload: Dict[str, Any] = {"id": eid}
    if size is not None and mtime_ns is not None:
        payload["bytes"] = size
        payload["modified_ns"] = mtime_ns
    side.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _is_media_filename(name: str) -> bool:
    if name.endswith(ID_SIDECAR_SUFFIX):
        return False
    return Path(name).suffix.lower() in VIDEO_EXT | AUDIO_EXT


def reclaim_orphaned_id_sidecars(root: Path) -> int:
    """Move orphan `*.id` sidecars onto renamed/moved media when identity is unique.

    Matching preference:
    1. unique `(bytes, modified_ns)` fingerprint recorded in the sidecar;
    2. same-directory 1:1 when fingerprint is absent or ambiguous.
    """
    media_files: List[Path] = []
    sidecars: List[Path] = []
    for dirpath, _, filenames in os.walk(root):
        base = Path(dirpath)
        for name in filenames:
            full = base / name
            if name.endswith(ID_SIDECAR_SUFFIX):
                sidecars.append(full)
            elif _is_media_filename(name):
                media_files.append(full)

    paired_media: set[Path] = set()
    orphans: List[tuple[Path, Dict[str, Any]]] = []
    for side in sidecars:
        media = media_path_for_sidecar(side)
        meta = _parse_id_sidecar(side)
        if meta is None:
            continue
        if media.is_file() and _is_media_filename(media.name):
            paired_media.add(media.resolve())
            continue
        orphans.append((side, meta))

    unmatched: List[tuple[Path, int, int]] = []
    for media in media_files:
        if media.resolve() in paired_media:
            continue
        if id_sidecar_path(media).is_file():
            continue
        try:
            st = media.stat()
        except OSError:
            continue
        unmatched.append((media, st.st_size, st.st_mtime_ns))

    if not orphans or not unmatched:
        return 0

    by_fp: Dict[tuple[int, int], List[tuple[Path, int, int]]] = {}
    for item in unmatched:
        key = (item[1], item[2])
        by_fp.setdefault(key, []).append(item)

    moved = 0
    claimed: set[Path] = set()

    # Pass 1: fingerprint unique matches.
    for side, meta in orphans:
        if "bytes" not in meta or "modified_ns" not in meta:
            continue
        key = (meta["bytes"], meta["modified_ns"])
        cands = [c for c in by_fp.get(key, []) if c[0] not in claimed]
        if len(cands) != 1:
            continue
        target = cands[0][0]
        dest = id_sidecar_path(target)
        if dest.exists():
            continue
        try:
            os.replace(side, dest)
        except OSError:
            continue
        claimed.add(target)
        moved += 1

    remaining_orphans = [(s, m) for s, m in orphans if s.is_file()]
    remaining_unmatched = [u for u in unmatched if u[0] not in claimed]

    # Pass 2: same-directory 1:1 for leftovers (covers legacy id-only sidecars).
    by_dir_orphans: Dict[Path, List[Path]] = {}
    for side, _meta in remaining_orphans:
        by_dir_orphans.setdefault(side.parent, []).append(side)
    by_dir_media: Dict[Path, List[Path]] = {}
    for media, _sz, _mt in remaining_unmatched:
        by_dir_media.setdefault(media.parent, []).append(media)

    for parent, orphan_list in by_dir_orphans.items():
        media_list = by_dir_media.get(parent, [])
        if len(orphan_list) != 1 or len(media_list) != 1:
            continue
        side = orphan_list[0]
        target = media_list[0]
        if target in claimed:
            continue
        dest = id_sidecar_path(target)
        if dest.exists():
            continue
        try:
            os.replace(side, dest)
        except OSError:
            continue
        claimed.add(target)
        moved += 1

    return moved


def resolve_entry_id(
    media: Path,
    rel: str,
    size: int,
    mtime_ns: int,
    *,
    write_sidecars: bool = False,
) -> str:
    """Prefer sidecar identity so renames keep the same opaque id."""
    existing = read_id_sidecar(media)
    if existing:
        if write_sidecars:
            write_id_sidecar(media, existing, size=size, mtime_ns=mtime_ns)
        return existing
    eid = opaque_id(rel, size, mtime_ns)
    if write_sidecars:
        write_id_sidecar(media, eid, size=size, mtime_ns=mtime_ns)
    return eid


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


def find_poster(root: Path, media: Path) -> Optional[str]:
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


def find_subtitle(root: Path, media: Path) -> Optional[str]:
    """Cheap WebVTT sidecar beside the media file — no container probe / FFmpeg."""
    stem = media.with_suffix("")
    for ext in SUBTITLE_EXT:
        cand = Path(str(stem) + ext)
        if cand.is_file():
            return cand.relative_to(root).as_posix()
    return None


def year_from_name(stem: str) -> Optional[int]:
    """Optional year from trailing `(YYYY)` in the file stem — filesystem-cheap."""
    m = re.search(r"\((19|20)\d{2}\)\s*$", stem)
    if not m:
        m = re.search(r"\((19|20)\d{2}\)", stem)
    if not m:
        return None
    return int(m.group(0)[1:5])


def probe_ftyp(path: Path) -> Optional[dict]:
    """Offline ISO BMFF `ftyp` peek (mp4/m4v/mov) — no FFmpeg.

    Records advisory brand facts under `video` so Orisha item/watch can show probe notes.
    """
    if path.suffix.lower() not in {".mp4", ".m4v", ".mov"}:
        return None
    try:
        with path.open("rb") as f:
            hdr = f.read(32)
    except OSError:
        return None
    if len(hdr) < 16 or hdr[4:8] != b"ftyp":
        return None
    size = struct.unpack(">I", hdr[0:4])[0]
    if size < 16:
        return None
    major = hdr[8:12].decode("latin-1", errors="replace")
    minor = struct.unpack(">I", hdr[12:16])[0]
    brands = []
    if size >= 20 and len(hdr) >= min(size, 32):
        compat = hdr[16 : min(size, len(hdr))]
        for i in range(0, len(compat) - 3, 4):
            brands.append(compat[i : i + 4].decode("latin-1", errors="replace"))
    track = {
        "codec": "unknown",
        "brand": major,
        "brand_version": minor,
    }
    if brands:
        track["compatible_brands"] = brands
    return {"video": [track]}


PROBES = {
    "none": lambda _p: None,
    "ftyp": probe_ftyp,
}


def index_root(
    root: Path,
    *,
    probe: Optional[ProbeFn] = None,
    write_id_sidecars: bool = False,
) -> list:
    entries = []  # type: List[Dict[str, Any]]
    seen: set[str] = set()
    # Reclaim orphaned *.id files onto renamed/moved media before resolving ids.
    reclaim_orphaned_id_sidecars(root)
    for dirpath, _, filenames in os.walk(root):
        for name in sorted(filenames):
            # Skip identity sidecars and non-media.
            if name.endswith(ID_SIDECAR_SUFFIX):
                continue
            full = Path(dirpath) / name
            if not _is_media_filename(name):
                continue
            rel = full.relative_to(root).as_posix()
            # Reject escapes (walk shouldn't produce them; belt-and-suspenders).
            if rel.startswith("../") or rel.startswith("/") or "\\" in rel:
                raise SystemExit(f"refusing path: {rel}")
            st = full.stat()
            eid = resolve_entry_id(
                full,
                rel,
                st.st_size,
                st.st_mtime_ns,
                write_sidecars=write_id_sidecars,
            )
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
            subtitle = find_subtitle(root, full)
            if subtitle:
                entry["subtitle"] = subtitle
            year = year_from_name(full.stem)
            if year is not None:
                entry["year"] = year
            if probe is not None:
                extra = probe(full)
                if extra:
                    for key, value in extra.items():
                        if key in {"id", "path"}:
                            continue
                        entry[key] = value
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
    ap.add_argument(
        "--write-id-sidecars",
        action="store_true",
        help=(
            f"Persist opaque ids beside media files (*{ID_SIDECAR_SUFFIX}); "
            "orphaned sidecars are auto-moved onto renamed media when identity matches"
        ),
    )
    ap.add_argument(
        "--probe",
        choices=sorted(PROBES.keys()),
        default="none",
        help="Optional offline container probe (never runs in the request process)",
    )
    args = ap.parse_args()
    root = args.root.resolve()
    if not root.is_dir():
        print(f"not a directory: {root}", file=sys.stderr)
        return 2
    probe = PROBES[args.probe]
    entries = index_root(
        root,
        probe=None if args.probe == "none" else probe,
        write_id_sidecars=args.write_id_sidecars,
    )
    atomic_write(args.out.resolve(), {"entries": entries})
    print(f"wrote {len(entries)} entries -> {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

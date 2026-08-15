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
    return Path(name).suffix.lower() in VIDEO_EXT | AUDIO_EXT | BOOK_EXT


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


# First path component under the media root (Jellyfin-style). Library root
# names the work; file kind then uses extras folders and MIME/ext so audio
# under shows/movies is extra, not tv/movie. Mirrors src/graph.kz fileKind.
LIBRARY_ROOT_KINDS = {
    "movies": "movie",
    "shows": "tv",
    "music": "audio",
    "books": "book",
    "musicvideos": "musicVideo",
    "musicvidoes": "musicVideo",  # existing DSM share spelling
}

# Jellyfin extras folders plus soundtrack/ost/score used in this library.
# https://jellyfin.org/docs/general/server/media/movies
EXTRA_DIR_NAMES = {
    "extras",
    "extra",
    "featurettes",
    "featurette",
    "trailers",
    "trailer",
    "shorts",
    "short",
    "interviews",
    "interview",
    "scenes",
    "deleted scenes",
    "behind the scenes",
    "behind-the-scenes",
    "samples",
    "sample",
    "other",
    "theme-music",
    "theme music",
    "clips",
    "backdrops",
    "soundtrack",
    "ost",
    "score",
}

NFO_MAX = 64 * 1024
POSTER_NAMES = ("poster", "folder", "cover", "show")

BOOK_EXT = {".epub", ".pdf", ".cbz", ".cbr", ".mobi", ".azw3"}

mimetypes.add_type("audio/flac", ".flac")
mimetypes.add_type("audio/ogg", ".ogg")
mimetypes.add_type("application/epub+zip", ".epub")
mimetypes.add_type("application/x-mobipocket-ebook", ".mobi")
mimetypes.add_type("application/vnd.amazon.ebook", ".azw3")
mimetypes.add_type("application/vnd.comicbook+zip", ".cbz")
mimetypes.add_type("application/vnd.comicbook-rar", ".cbr")


def path_is_extra(rel_parts: tuple[str, ...]) -> bool:
    for part in rel_parts:
        if part.lower() in EXTRA_DIR_NAMES:
            return True
    return False


def _kind_from_parts(rel_parts: tuple[str, ...], ext: str) -> Optional[str]:
    if path_is_extra(rel_parts):
        return "extra"
    if not rel_parts:
        return None
    mapped = LIBRARY_ROOT_KINDS.get(rel_parts[0].lower())
    if mapped in ("movie", "tv") and ext in AUDIO_EXT:
        return "extra"
    return mapped


def kind_for(path: Path, root: Optional[Path] = None) -> str:
    """Extras folder, then MIME under movies/shows, then library root, then ext."""
    rel_parts: tuple[str, ...] = ()
    if root is not None:
        try:
            rel_parts = path.relative_to(root).parts
        except ValueError:
            rel_parts = path.parts
        mapped = _kind_from_parts(rel_parts, path.suffix.lower())
        if mapped:
            return mapped
    ext = path.suffix.lower()
    if ext in VIDEO_EXT:
        return "movie"
    if ext in AUDIO_EXT:
        return "audio"
    if ext in BOOK_EXT:
        return "book"
    return "file"


def kind_for_prefixed(path: Path, root: Path, library_name: str) -> str:
    try:
        rel_parts = path.relative_to(root).parts
    except ValueError:
        rel_parts = path.parts
    if library_name:
        rel_parts = (library_name,) + rel_parts
    mapped = _kind_from_parts(rel_parts, path.suffix.lower())
    if mapped:
        return mapped
    return kind_for(path, None)


def mime_for(path: Path) -> str:
    guess, _ = mimetypes.guess_type(str(path))
    return guess or "application/octet-stream"


def container_for(path: Path) -> str:
    return path.suffix.lower().lstrip(".") or "bin"


def work_key(rel: str) -> str:
    """Jellyfin-style work folder. Mirrors src/graph.kz workKey."""
    parts = rel.split("/")
    if not parts:
        return rel
    dirs = parts[:-1]
    keep = len(dirs)
    for i, seg in enumerate(dirs):
        if seg.lower() in EXTRA_DIR_NAMES:
            keep = i
            break
    root = dirs[0].lower() if dirs else ""
    if root in ("shows", "tv"):
        want = 2
    elif root == "music":
        want = 3
    else:
        want = 2
    dirs_keep = min(keep, want)
    if dirs_keep <= 1:
        name = parts[-1]
        dot = name.rfind(".")
        stem = name[:dot] if dot > 0 else name
        if len(parts) == 1:
            return stem
        return "/".join(parts[:-1] + [stem])
    return "/".join(parts[:dirs_keep])


def parse_season_episode(path: str) -> tuple[int, int]:
    """SxxEyy on the file stem, else Sonarr Season - N / Season 01 folders."""
    file_name = path.rsplit("/", 1)[-1]
    m = re.search(r"(?<![A-Za-z0-9])S(\d{1,2})E(\d{1,3})", file_name, re.I)
    if m:
        return int(m.group(1)), int(m.group(2))
    season = 0
    for seg in path.split("/"):
        sm = re.search(r"(?<![A-Za-z0-9])season[\s._-]*(\d{1,2})", seg, re.I)
        if sm:
            n = int(sm.group(1))
            if n:
                season = n
    return season, 0


def parse_imdb_id(path: str) -> str:
    """First [tt…] or [imdbid-tt…] in the path. Local assertion only — no HTTP."""
    for m in re.finditer(r"\[([^\[\]]+)\]", path):
        inside = m.group(1).strip()
        tt = re.fullmatch(r"tt(\d+)", inside, re.I)
        if tt:
            return "tt" + tt.group(1)
        imdb = re.fullmatch(r"imdbid-tt(\d+)", inside, re.I)
        if imdb:
            return "tt" + imdb.group(1)
    return ""


def work_display_title(key: str) -> str:
    """Folder name with [tt…]/[imdbid-…]/(year) stripped. Mirrors graph.kz."""
    name = key.rsplit("/", 1)[-1]

    def _strip_tag(m):
        inside = m.group(1).strip()
        if re.fullmatch(r"tt\d+", inside, re.I):
            return ""
        if re.match(r"(imdbid-|imdb-|tmdbid-|tmdb-|tvdbid-|tvdb-)", inside, re.I):
            return ""
        return m.group(0)

    name = re.sub(r"\[([^\[\]]+)\]", _strip_tag, name)
    name = re.sub(r"\((?:19|20)\d{2}\)", "", name)
    name = re.sub(r"\s+", " ", name).strip()
    return name or key.rsplit("/", 1)[-1]


def find_poster(root: Path, media: Path) -> Optional[str]:
    """Sidecar art beside the file, then parents up to the work directory."""
    stem = media.with_suffix("")
    for ext in POSTER_EXT:
        cand = Path(str(stem) + ext)
        if cand.is_file():
            return cand.relative_to(root).as_posix()
    rel = media.relative_to(root).as_posix()
    work = work_key(rel)
    slash = rel.rfind("/")
    dir_rel = rel[:slash] if slash >= 0 else ""
    while True:
        parent_path = root / dir_rel if dir_rel else root
        for name in POSTER_NAMES:
            for ext in POSTER_EXT:
                cand = parent_path / f"{name}{ext}"
                if cand.is_file():
                    return cand.relative_to(root).as_posix()
        if not dir_rel or dir_rel == work:
            break
        if not (dir_rel.startswith(work) and len(dir_rel) > len(work) and dir_rel[len(work)] == "/"):
            break
        slash = dir_rel.rfind("/")
        dir_rel = dir_rel[:slash] if slash >= 0 else ""
    return None


def _xml_unescape(raw: str) -> str:
    from html import unescape

    return unescape(raw).strip()


def _xml_tag(text: str, tag: str) -> str:
    open_m = re.search(rf"<{tag}\b[^>]*>", text, re.I)
    if not open_m:
        return ""
    rest = text[open_m.end() :]
    cdata = re.match(r"<!\[CDATA\[(.*?)\]\]>", rest, re.S)
    if cdata:
        return _xml_unescape(cdata.group(1))
    close = re.search(rf"</{tag}>", rest, re.I)
    if not close:
        return ""
    return _xml_unescape(rest[: close.start()])


def parse_nfo_text(text: str) -> dict:
    """Offline Kodi/Jellyfin nfo: title, plot, aired/premiered, rating."""
    title = _xml_tag(text, "title")
    plot = _xml_tag(text, "plot") or _xml_tag(text, "outline")
    aired = _xml_tag(text, "aired") or _xml_tag(text, "premiered")
    rating = _xml_tag(text, "value") or _xml_tag(text, "rating")
    if "<" in rating:
        rating = ""
    lower = text.lower()
    return {
        "title": title,
        "plot": plot,
        "aired": aired,
        "rating": rating,
        "episode_scope": "episodedetails" in lower,
        "work_scope": "<tvshow" in lower or "<movie" in lower,
    }


def read_nfo(path: Path) -> Optional[dict]:
    if not path.is_file():
        return None
    try:
        size = path.stat().st_size
    except OSError:
        return None
    if size <= 0 or size > NFO_MAX:
        return None
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None
    parsed = parse_nfo_text(text)
    if not any(parsed.get(k) for k in ("title", "plot", "aired", "rating")):
        return None
    return parsed


def nfo_title(media: Path) -> Optional[str]:
    """Sibling .nfo <title> when the file is small. Offline hydrate only."""
    parsed = read_nfo(media.with_suffix(".nfo"))
    if not parsed:
        return None
    title = parsed.get("title") or ""
    return title or None


def work_nfo(root: Path, work: str) -> Optional[dict]:
    if not work:
        return None
    work_dir = root / work
    for name in ("tvshow.nfo", "movie.nfo"):
        parsed = read_nfo(work_dir / name)
        if parsed:
            return parsed
    return None


def find_jpeg_in(buf: bytes) -> Optional[bytes]:
    """Cheap SOI..EOI scan (ID3 APIC / MP4 covr). No ffmpeg."""
    i = 0
    while i + 3 < len(buf):
        soi = buf.find(b"\xff\xd8\xff", i)
        if soi < 0:
            return None
        eoi = buf.find(b"\xff\xd9", soi + 3)
        if eoi < 0:
            return None
        blob = buf[soi : eoi + 2]
        if 16 <= len(blob) <= 512 * 1024:
            return blob
        i = soi + 1
    return None


def extract_embedded_cover(root: Path, media: Path) -> Optional[str]:
    """Last-resort poster: JPEG inside an audio file, written as cover.jpg."""
    if media.suffix.lower() not in AUDIO_EXT:
        return None
    cover = media.parent / "cover.jpg"
    if cover.is_file():
        return cover.relative_to(root).as_posix()
    try:
        with media.open("rb") as f:
            buf = f.read(256 * 1024)
    except OSError:
        return None
    jpeg = find_jpeg_in(buf)
    if not jpeg:
        return None
    try:
        cover.write_bytes(jpeg)
    except OSError:
        return None
    return cover.relative_to(root).as_posix()


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
    # Future (not registered, not a CI/runtime dep): PROBES["ffprobe"] = probe_ffprobe
    # would shell `ffprobe -v quiet -print_format json -show_format -show_streams`
    # and map streams into the same nested video[] / audio[] keys. See docs/manifest.md.
    # Never call from Orisha request handlers.
}


def index_root(
    root: Path,
    *,
    probe: Optional[ProbeFn] = None,
    write_id_sidecars: bool = False,
    library_name: str = "",
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
            rel_under = full.relative_to(root).as_posix()
            rel = f"{library_name}/{rel_under}" if library_name else rel_under
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
            wk = work_key(rel)
            se = parse_season_episode(rel)
            imdb = parse_imdb_id(rel)
            sibling = read_nfo(full.with_suffix(".nfo"))
            title = (sibling.get("title") if sibling else None) or full.stem
            entry: dict = {
                "id": eid,
                "kind": kind_for_prefixed(full, root, library_name),
                "title": title,
                "path": rel,
                "bytes": st.st_size,
                "modified_ns": st.st_mtime_ns,
                "mime": mime_for(full),
                "container": container_for(full),
                "work_key": wk,
                "work_title": work_display_title(wk),
                "season": se[0],
                "episode": se[1],
            }
            if imdb:
                entry["imdb_id"] = imdb
            if sibling:
                if sibling.get("plot"):
                    entry["plot"] = sibling["plot"]
                if sibling.get("aired"):
                    entry["aired"] = sibling["aired"]
                if sibling.get("rating"):
                    entry["rating"] = sibling["rating"]
            disk_wk = wk
            if library_name and wk.startswith(library_name + "/"):
                disk_wk = wk[len(library_name) + 1 :]
            wn = work_nfo(root, disk_wk)
            if wn:
                if wn.get("plot"):
                    entry["work_plot"] = wn["plot"]
                if wn.get("aired"):
                    entry["work_aired"] = wn["aired"]
                if wn.get("rating"):
                    entry["work_rating"] = wn["rating"]
            poster = find_poster(root, full)
            if not poster:
                poster = extract_embedded_cover(root, full)
            if poster:
                entry["poster"] = f"{library_name}/{poster}" if library_name else poster
            subtitle = find_subtitle(root, full)
            if subtitle:
                entry["subtitle"] = f"{library_name}/{subtitle}" if library_name else subtitle
            year = year_from_name(full.stem) or year_from_name(full.parent.name)
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
    ap.add_argument("--root", type=Path, help="Media root to walk (movies/shows/music/… children)")
    ap.add_argument(
        "--bind",
        action="append",
        default=[],
        metavar="NAME=PATH",
        help="Walk PATH as library root NAME (repeatable; e.g. movies=/volume1/movies)",
    )
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
    if bool(args.root) == bool(args.bind):
        print("specify exactly one of --root or --bind NAME=PATH", file=sys.stderr)
        return 2
    probe = PROBES[args.probe]
    probe_fn = None if args.probe == "none" else probe
    if args.root:
        root = args.root.resolve()
        if not root.is_dir():
            print(f"not a directory: {root}", file=sys.stderr)
            return 2
        entries = index_root(
            root,
            probe=probe_fn,
            write_id_sidecars=args.write_id_sidecars,
        )
    else:
        entries = []
        seen: set[str] = set()
        for spec in args.bind:
            if "=" not in spec:
                print(f"bind must be NAME=PATH: {spec}", file=sys.stderr)
                return 2
            name, raw = spec.split("=", 1)
            name = name.strip().strip("/")
            path = Path(raw).resolve()
            if not name or not path.is_dir():
                print(f"not a directory: {path}", file=sys.stderr)
                return 2
            chunk = index_root(
                path,
                probe=probe_fn,
                write_id_sidecars=args.write_id_sidecars,
                library_name=name,
            )
            for e in chunk:
                if e["id"] in seen:
                    print(f"duplicate id {e['id']} for {e['path']}", file=sys.stderr)
                    return 2
                seen.add(e["id"])
            entries.extend(chunk)
        entries.sort(key=lambda e: e["title"].lower())
    atomic_write(args.out.resolve(), {"entries": entries})
    print(f"wrote {len(entries)} entries -> {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

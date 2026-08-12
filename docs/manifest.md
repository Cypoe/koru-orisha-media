# Manifest

The manifest is a published snapshot, not a request-time database dependency.

## Entry shape

An entry should contain at least:

```json
{
  "id": "m_7f3af1",
  "kind": "movie",
  "title": "Arrival",
  "year": 2016,
  "path": "Films/Arrival (2016)/Arrival.mp4",
  "bytes": 8348123941,
  "modified_ns": 1765349200000000000,
  "mime": "video/mp4",
  "container": "mp4",
  "video": [{"codec": "hevc", "width": 3840, "height": 2160, "hdr": true}],
  "audio": [{"codec": "aac", "language": "eng", "channels": 2}],
  "poster": "/art/m_7f3af1.webp"
}
```

Fields may grow, but request handlers should depend only on the facts required by their view or response. Unknown fields must be safely ignored.

## Runtime load (Orisha vendor)

The request process does **not** use `koru/yyjson`. It loads a schema-specific snapshot:

- only objects inside the top-level `"entries"` array;
- string fields with basic JSON unescape (`\"`, `\\`, `\n`, `\t`, `\r`, `\/`);
- duplicate `id` values rejected on load.

Spec twin / unit tests: `scripts/test_manifest_parse.py`. Nested `video` / `audio` first-track facts (`codec`, `brand`) are loaded for item/watch probe notes; richer nested fields remain ignorable.

## Publication

The indexer writes a new generation beside the active manifest, validates it, flushes it, and atomically renames it into place. Orisha either keeps its current immutable snapshot or swaps to the new complete snapshot. A request must never observe partially written content.

## Probing policy

Filename and filesystem facts are cheap and form the initial index. Container and stream probing is optional and belongs to indexing time. Artwork extraction and thumbnail generation are also offline operations.

The request process never probes. **FFmpeg / ffprobe must never run in Orisha request handlers** (library, item, watch, or `/media` range serving).

### Stopgap (current)

The indexer accepts an injectable offline probe (`scripts/index_media.py` `--probe` / `index_root(..., probe=...)`). Built-in `ftyp` peeks ISO BMFF brands for `.mp4`/`.m4v`/`.mov` without FFmpeg — enough for the personal milestone without requiring FFmpeg on the server path. Nested `video` / `audio` fields are stored in the published manifest; Orisha surfaces first-track `brand` / `codec` on item and watch pages as honest probe notes (not a client capability matrix).

### Endgame (deferred; not implemented here)

- **Catalog feed:** prefer Synology Indexer / File Station indexing as the long-term source (same pattern Radarr/Jellyfin use on Synology), publishing into this manifest shape with opaque IDs and atomic rename. Do not treat a permanent in-process walker as the durable design.
- **Rich probe:** use `ffmpeg` / `ffprobe` only inside the offline indexer or a Synology-fed batch to fill richer `video` / `audio` (and related) facts. Same publication rules; still no request-path probe.
- **JSON stack:** prefer **yyjson** (`W:\src\koru-libs\yyjson` — system `libyyjson` / Koru lift) for indexer emit and richer parse over forever-Python. Orisha’s schema-specific loader above remains valid until that lands; do not vendor `yyjson.c` into this binary by default.

The manifest may record whether a file is likely to play natively in a target browser, but this is advisory. The server must not silently transcode when the advisory value is false.

## Identity policy

The initial ID may be derived from normalized relative path, size, and modification time. The indexer can persist IDs in sidecars (`<path>.id` JSON `{"id":"m_…","bytes":…,"modified_ns":…}`) via `--write-id-sidecars`. On each index pass, orphaned `*.id` files are auto-moved onto renamed/moved media when identity is unique (fingerprint match, or same-directory 1:1 for legacy id-only sidecars). IDs must be opaque at the HTTP boundary and must not expose filesystem layout.

## Invariants

- Every entry ID is unique within a generation.
- Every entry path is relative to a configured root.
- No entry path escapes its configured root after normalization.
- Published manifests are complete and parseable.
- Replacing a manifest does not change the bytes of an existing file resource.

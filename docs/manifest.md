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

Spec twin / unit tests: `scripts/test_manifest_parse.py`. Full JSON (nested `video`/`audio`) is ignored until a view needs it.

## Publication

The indexer writes a new generation beside the active manifest, validates it, flushes it, and atomically renames it into place. Orisha either keeps its current immutable snapshot or swaps to the new complete snapshot. A request must never observe partially written content.

## Probing policy

Filename and filesystem facts are cheap and form the initial index. Container and stream probing is optional and belongs to indexing time. Artwork extraction and thumbnail generation are also offline operations.

The request process never probes. The indexer accepts an injectable offline probe (`scripts/index_media.py` `--probe` / `index_root(..., probe=...)`). Built-in `ftyp` peeks ISO BMFF brands for `.mp4`/`.m4v`/`.mov` without FFmpeg; richer codec probes can plug in the same hook later. Nested `video` / `audio` fields are stored in the published manifest; the current Orisha loader ignores them until a view needs them.

The manifest may record whether a file is likely to play natively in a target browser, but this is advisory. The server must not silently transcode when the advisory value is false.

## Identity policy

The initial ID may be derived from normalized relative path, size, and modification time. The indexer can persist IDs in sidecars (`<path>.id` JSON `{"id":"m_…"}`) via `--write-id-sidecars` so renames retain identity when the sidecar moves with the file. IDs must be opaque at the HTTP boundary and must not expose filesystem layout.

## Invariants

- Every entry ID is unique within a generation.
- Every entry path is relative to a configured root.
- No entry path escapes its configured root after normalization.
- Published manifests are complete and parseable.
- Replacing a manifest does not change the bytes of an existing file resource.

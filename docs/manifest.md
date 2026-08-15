# Manifest

The manifest is a published snapshot, not a request-time database dependency.

## Library roots

Mount **one** media root that contains Jellyfin-style folders. Settings persists which of those folders to walk (`library_roots` in the catalog). Defaults: `movies`, `shows`, `music`, `books`, `musicVideos`. Disabled mounts are skipped. The NAS indexer is `catalog.kz` `reindex` (binary), not `scripts/index_media.py`. Kind still comes from the first path component:

| folder | `kind` | example |
|--------|--------|---------|
| `movies/` | `movie` | `movies/Arrival (2016).mp4` |
| `shows/` | `tv` | `shows/Series/S01E01.mkv` (no TV fixture in CI yet) |
| `music/` | `audio` | `music/beep.wav` |

Files outside those folders fall back to extension (video → `movie`, audio → `audio`). Directory wins over extension: `movies/bonus.wav` is still `movie`.

Compose binds `./media:/media`. Prefer `./media/movies`, `./media/shows`, `./media/music` over three separate binds so the walker stays one walk (`KORU_MEDIA_ROOT=/media`).

## Fixtures vs `data/`

| path | role |
|------|------|
| `fixtures/media/` | CI library (tiny files; the only checked-in library) |
| `fixtures/manifest.json` | CI physical snapshot (opaque `m_*` ids, probe notes) |
| `fixtures/semantic.json` | CI semantic snapshot |
| `data/` | local runtime volumes (gitignored). Compose writes `manifest.json` / `semantic.json` here. |

Do not check in a second copy of the same media files under `data/` or `media/`.

## Entry shape

An entry should contain at least:

```json
{
  "id": "m_7f3af1",
  "kind": "movie",
  "title": "Arrival",
  "year": 2016,
  "path": "movies/Arrival (2016)/Arrival.mp4",
  "bytes": 8348123941,
  "modified_ns": 1765349200000000000,
  "mime": "video/mp4",
  "container": "mp4",
  "video": [{"codec": "hevc", "width": 3840, "height": 2160, "hdr": true}],
  "audio": [{"codec": "aac", "language": "eng", "channels": 2}],
  "poster": "/art/m_7f3af1.webp",
  "subtitle": "movies/Arrival (2016)/Arrival.vtt"
}
```

Fields may grow, but request handlers should depend only on the facts required by their view or response. Unknown fields must be safely ignored.

Optional `subtitle` is a root-relative WebVTT sidecar path (same stem as the media file). Orisha serves it at `/subtitles/{id}` with `Content-Type: text/vtt` and may expose a native `<track>` on the watch player.

## Runtime load (Orisha vendor)

The request process does **not** use `koru/yyjson`. It loads a schema-specific snapshot in [`src/graph.kz`](../src/graph.kz):

- only objects inside the top-level `"entries"` array;
- string fields with basic JSON unescape (`\"`, `\\`, `\n`, `\t`, `\r`, `\/`);
- duplicate `id` values rejected on load.

Spec twin / unit tests: `scripts/test_manifest_parse.py`. Nested `video` / `audio` first-track facts (`codec`, `brand`) are loaded for item/watch probe notes; optional `subtitle` sidecar path is loaded for `/subtitles/{id}` and watch `<track>`; richer nested fields remain ignorable.

## Publication

The indexer writes a new generation beside the active manifest, validates it, flushes it, and atomically renames it into place. Orisha either keeps its current immutable snapshot or swaps to the new complete snapshot. A request must never observe partially written content.

## Probing policy

Filename and filesystem facts are cheap and form the initial index. Container and stream probing is optional and belongs to indexing time. Artwork extraction and thumbnail generation are also offline operations.

The request process never probes. **FFmpeg / ffprobe must never run in Orisha request handlers** (library, item, watch, or `/media` range serving).

### Stopgap (current)

The NAS indexer is `catalog.kz` `reindex` (Settings / `nas-index.sh` / `KORU_REINDEX=1`). It peeks ISO BMFF `ftyp` brands for `.mp4`/`.m4v`/`.mov` without FFmpeg. `scripts/index_media.py` `--probe ftyp` remains a JSON fixture / CI fallback, not what runs on Synology. Nested `video` / `audio` fields are stored in the published manifest; Orisha surfaces first-track `brand` / `codec` on item and watch pages as honest probe notes (not a client capability matrix).

This is the Jellyseerr-fast contrast vs Jellyfin: catalogue text and stream facts are **precomputed** (`project_semantic.py` named constructions / indexer `probe=`) and scraped from local JSON. Request handlers never call TMDB or ffprobe. Jellyfin’s live metadata/probe path is the anti-pattern here (heavy idle process, weak caching). Missing `semantic.json` still serves `/`, `/library`, physical HTML, and `/media/{id}` bytes — the local archive is the product.

### Future offline `ffprobe` hook (not implemented; not a CI dependency)

Register another callable on the same `probe=` path — never from Orisha:

```text
PROBES["ffprobe"] = probe_ffprobe
index_root(root, probe=probe_ffprobe)   # or --probe ffprobe
```

`probe_ffprobe(path)` would run (indexer process only):

```bash
ffprobe -v quiet -print_format json -show_format -show_streams FILE
```

Map JSON onto the nested fields Orisha already loads (first track only on the HTML probe note):

| ffprobe JSON | Manifest field |
|--------------|----------------|
| `streams[v:0].codec_name` | `video[0].codec` |
| `streams[v:0].width` / `height` | `video[0].width` / `height` |
| `streams[v:0].color_transfer` / `pix_fmt` (e.g. `smpte2084`) | `video[0].hdr` (bool) |
| `format.tags.major_brand` or ftyp peek | `video[0].brand` |
| `streams[a:0].codec_name` | `audio[0].codec` |
| `streams[a:0].channels` | `audio[0].channels` |
| `streams[a:0].tags.language` | `audio[0].language` |

Keep `bytes` / `path` / `id` from `stat` + identity policy; do not let ffprobe overwrite them. Merge like today’s `ftyp` probe (`entry[key] = value` for `video`/`audio`). Do not add ffmpeg as a runtime or Docker image dependency until this hook exists.

### Endgame (deferred; not implemented here)

- **Catalog feed:** prefer Synology Indexer / File Station indexing as the long-term source (same pattern Radarr/Jellyfin use on Synology), publishing into this manifest shape with opaque IDs and atomic rename. Do not treat a permanent in-process walker as the durable design.
- **Rich probe:** use `ffmpeg` / `ffprobe` only inside the offline indexer or a Synology-fed batch to fill richer `video` / `audio` (and related) facts. Same publication rules; still no request-path probe.
- **JSON stack:** [`vendor/json/`](../vendor/json/) is our writer for indexer/projection publish (no libyyjson, no pkg-config); [`src/json/`](../src/json/) is the json-publish CLI. **Not waiting on `koru/yyjson`:** that lift needs system `libyyjson` + phantom `Doc<open!>`, and Debian bookworm has no `libyyjson-dev`. [`scripts/json_publish.py`](../scripts/json_publish.py) is the CI fallback if koruc is missing. Graph load on the request path stays the schema scrape above; do not vendor `yyjson.c` into `bin/media-server`.

The manifest may record whether a file is likely to play natively in a target browser, but this is advisory. The server must not silently transcode when the advisory value is false.

## Identity policy

The initial ID may be derived from normalized relative path, size, and modification time. The indexer can persist IDs in sidecars (`<path>.id` JSON `{"id":"m_…","bytes":…,"modified_ns":…}`) via `--write-id-sidecars`. On each index pass, orphaned `*.id` files are auto-moved onto renamed/moved media when identity is unique (fingerprint match, or same-directory 1:1 for legacy id-only sidecars). IDs must be opaque at the HTTP boundary and must not expose filesystem layout.

## Invariants

- Every entry ID is unique within a generation.
- Every entry path is relative to a configured root.
- No entry path escapes its configured root after normalization.
- Published manifests are complete and parseable.
- Replacing a manifest does not change the bytes of an existing file resource.

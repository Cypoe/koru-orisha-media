# Roadmap

## Phase 0: contracts

- Fix the current Koru/Orisha integration entry point.
- Define response, route, and manifest types in the smallest useful form.
- Add tests for path validation and HTTP method behavior.

## Phase 1: boring server

- Serve `public/`.
- Load one manifest snapshot at startup.
- Render a complete library page.
- Add media lookup by opaque ID.
- Implement `GET`, `HEAD`, `Range`, `206`, `ETag`, and `Last-Modified`.

## Phase 2: indexer

- Walk configured roots in a separate executable or command.
- Record path, size, mtime, MIME, container; optional sidecar poster (`*.jpg` / `poster.jpg`).
- Injectable offline probe hook (`--probe ftyp` / `index_root(..., probe=)`); no FFmpeg in Orisha request handlers. Full stream/codec probe still optional/pluggable.
- Persistent sidecar IDs (`*.id`) across renames when `--write-id-sidecars` is used; orphaned sidecars auto-move onto renamed/moved media when identity matches uniquely.
- Publish manifests atomically.
- Hot reload when manifest mtime changes and no media streams are active.

**Stopgap vs endgame (docs only):** the NAS indexer is `catalog.kz` `reindex` (Settings / `nas-index.sh` / `KORU_REINDEX=1`). `scripts/index_media.py` remains a JSON fixture / CI fallback, not what runs on Synology. Later catalog feed may follow the Synology Indexer / File Station indexing pattern (consume Synology’s media index the way Radarr/Jellyfin do). Richer metadata gathering later uses **ffmpeg/ffprobe in the offline indexer or Synology-fed batch only**, never in request handlers. Prefer **yyjson** (Koru lift / system `libyyjson`) over forever-`scripts/index_media.py` for the long-term manifest JSON stack. Opaque IDs + atomic publish stay.

## Phase 3: hypermedia interaction

- Add sort, filter, search, and pagination links (`limit` / `offset`).
- Add fragment representations for enhanced navigation.
- Opt-in `Prefer: return=minimal` on `/library` returns a fragment.
- Add forms for any future mutating operations.
- Add `Link` headers and a minimal `OPTIONS` implementation.
- `/art/{id}` serves precomputed poster sidecars when present.
- Honest watch capability note for awkward containers; `?download=1` sets `Content-Disposition: attachment`.

## Phase 4: frontend enhancement

- Keep complete-page navigation as the baseline.
- Shipped: [`vendor/koru-libs/htmx/`](vendor/koru-libs/htmx/) (`import koru/htmx`) + usage [`src/frontend/host.k`](src/frontend/host.k) → `public/enhance.js` (`GET /enhance.js`) — generic HTMX-dialect host (`hx-get` / `hx-target` / `HX-Request`); usage supplies `#library-region` default, `protect: "#player"`, and localStorage resume. Host logic remains a `|js` escape until Koru lowers fetch/swap; boot is a Koru top-level `koru/htmx:run(...)`.
- Optional koru/dom keyed list: [`vendor/koru-libs/dom/`](vendor/koru-libs/dom/) + usage `src/frontend/main.k` + `main.kjs` + `scripts/build-frontend.sh` → `public/koru-dom-enhance.js` + `/enhance-demo.html` (real Koru IR emit).
- See [docs/upstream-candidates.md](docs/upstream-candidates.md) for the vaxis → dom → HTMX story.

## Phase 5: lifecycle

- `scripts/bench_baseline.sh` for cold/steady latency + RSS
- `KORU_IDLE_SECS` idle exit when no media streams are active
- Hot manifest reload (mtime, quiet streams) — see [docs/lifecycle.md](docs/lifecycle.md)
- sendfile/mmap / socket activation still deferred

## Phase 6: hypermedia polish + extraction map

- Library GET search form; item `year` + collection `Link`; media `304` on `If-None-Match`
- [docs/upstream-candidates.md](docs/upstream-candidates.md) — what can become Orisha/Koru libs later
- **Done**

## Phase 7: Orisha extraction prep (in-repo)

- HTTP spec extracted to [`vendor/http`](vendor/http/) (`parseHttpRequest`, `header()`, STREAM:v1 `sendSpecial`, `run-accept-loop`). [`vendor/orisha`](vendor/orisha/) is a verbatim `W:\src\orisha\lib` (`bash scripts/vendor-orisha.sh`).
- Media app in [`src/`](src/) (`media:dispatch`); `main.k` implements `http:handler`
- Vendor / current-apis docs match the real `Request` + `STREAM:v1` surface
- Schema-specific manifest loader (`entries` + unescape) + `scripts/test_manifest_parse.py`
- Next **out-of-repo**: when pump:reply grows Request extras + STREAM *and* koruc stops double-emitting `koru_pump`, switch `main.k` to `orisha:serve` and drop `vendor/http`'s loop. Media HTML stays in `src/`.

## Phase 8: semantic projection

- Offline snapshot join by opaque asset id (`KORU_SEMANTIC`, default `data/semantic.json`)
- Precomputed named constructions (`orisha.item`, `orisha.links`, `schema.org.jsonld`) via [`scripts/project_semantic.py`](scripts/project_semantic.py); core `Entity` stays identity + provenance; Orisha merges construction rows by opaque asset id
- Item/watch show TMDB/IMDb links and JSON-LD alternate **only when those constructions exist**
- Request handlers never call TMDB/TVDB/IMDb; missing snapshot leaves physical HTML unchanged
- First presentable: `/` and `/library` list local playable files when the fetched catalogue index is missing
- **Done** for the fixture library (Arrival has constructions; demo unlinked / physical-only)

## Next REAL product work (after Phase 8)

Not more docs. Ranked concrete features:

1. **Richer library UX** — landed: `/library/{kind}` self/up Links + title, row watch/year affordances, pagination preserves `sort`/`q`, `#library-region` swap root; empty/search-zero states; kind nav (`all`/`movies`/`audio` with active mark); search input preserves `q` + clear link; WebVTT sidecar → `/subtitles/{id}` + watch `<track>`/link; audio fixture fills `/library/audio`. Still open: playlist/queue only if useful.
2. **Indexer depth** — landed: injectable `--probe` / `probe=` hook (`ftyp` built-in) + `--write-id-sidecars` + auto-move of orphaned `*.id` sidecars on rename/move (fingerprint or same-dir 1:1) + WebVTT subtitle sidecar path. Orisha item/watch surface nested first-track `video`/`audio` brand/codec probe notes. Richer codec/stream facts are an **endgame offline** concern (ffprobe / Synology-fed batch), not the next Orisha code slice.
3. **Frontend Step 9 hardening** — landed: watch related shelf swaps `#library-region` only; emitted `public/enhance.js` (`koru/htmx` + usage `host.k`) refuses targets that own `#player`, checks node identity after swap, `performance.mark` on swaps, popstate re-fetch; watch `#resume-ui` (Resumed from / Restart) without recreating `#player`. Still open: measured koru/dom only if marks justify it.
4. **NAS catalog persist + Settings** — landed: `/data` and `/config` are host binds; empty-catalog auto-reindex only when media binds have files; 0-file reindex rolls back against a non-empty catalog. Settings add/remove library mounts tagged by capability/affordances (not a fixed five-share enum). Base path and catalog driver/DSN persist under `/config/settings.conf`; only SQLite is linked. Compose on the NAS is `compose.yml`. DSM `group_add: "101"` is required so PUID 1026 can read ACL shares.

Do **not** next: Synology Indexer integration, FFmpeg/ffprobe plumbing, vendoring `yyjson.c` into this media binary or Docker image, switching this app from `run-accept-loop` to `orisha:serve` (pump is vendored; STREAM/Request still missing on `reply`), sendfile/mmap, or another extraction-only doc pass. Live catalogue enrichment uses **offline TMDB** ([`scripts/hydrate_catalog.py`](scripts/hydrate_catalog.py) → `hydrate_works`; [`scripts/enrich_tmdb.py`](scripts/enrich_tmdb.py) for `semantic.json`). TVDB remains optional. Request handlers never call providers. A Postgres/MySQL catalog driver is a later link, not a fake in this build.

## Explicitly deferred

Transcoding, HLS/DASH, background metadata services, recommendation systems, remote media discovery, a large client compatibility layer, **Seerr Requests / Approve / Decline / blocklist-as-Seerr**, user accounts, and a plugin marketplace. Client and webhook integrations wait until the work surface is stable.

### Deferred future indexer (endgame; no code this pass)

Documented so Phase 2 / GOAL stay coherent with packaging notes:

| Concern | Endgame | Constraint |
|---------|---------|------------|
| Catalog source | Synology Indexer / File Station indexing feed (Radarr/Jellyfin-style), not a permanent in-process walker | Still publishes opaque IDs + atomic manifest snapshots Orisha already loads |
| Probe / metadata | `ffmpeg` / `ffprobe` in the **offline indexer** or Synology-fed batch | **Never** in Orisha request handlers or the HTTP media path |
| Today’s probe | `--probe ftyp` + nested `video`/`audio` | Stopgap for the personal milestone without requiring FFmpeg on the server path |
| JSON stack | **`vendor/json`** tiny writer (not `koru/yyjson`); CLI usage `src/json` | Python fallback if koruc missing. Do not vendor `yyjson.c` into `bin/media-server`. NAS indexer is `catalog.kz` `reindex`; `scripts/index_media.py` is fixture JSON only. Request path stays graph scrape. |

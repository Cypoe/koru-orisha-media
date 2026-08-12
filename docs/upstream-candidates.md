# Upstream and standalone library candidates

Honest map of what this media server has proven that could later leave the app tree — either as a Koru/Orisha contribution, a small companion lib, or stay app-local.

Do **not** extract until the seam has tests and a second consumer. The first consumer is this repo.

**In-repo gate (Phase 7):** `parseHttpRequest` shared by `accept|zig` and `answer|zig`, plus `EXTRACT:orisha-core` / `APP:media-handler` and `SPLIT→` future-file banners in `vendor/orisha-lib/index.kz`. Existing HTTP suite covers Range / Prefer / `HX-Request` on the accept-loop path. Upstream PR to `W:\src\orisha` comes after that gate — without shipping the media HTML handler.

### File-segment map (vendor `index.kz`)

| Segment | EXTRACT / APP | Notes |
|---------|---------------|-------|
| `request-parse` | EXTRACT | Unified Request parse |
| `accept-loop` | EXTRACT | Replaces pump serve for this app |
| `send-stream` | EXTRACT | STREAM:v1 + raw HTTP |
| `answer` | EXTRACT | Pump path still uses this upstream |
| `router-static` | EXTRACT | Matches upstream today |
| `manifest-load` | APP | Schema JSON (`entries` + unescape); not Orisha |
| `html-views` | APP | Library / item / watch |
| `media-http` | APP | Byte / art resources |
| `handler` | APP | Route table |

Full banners: [vendor/README.md](../vendor/README.md).


## The HTMX insight (koru/vaxis → koru/dom)

`koru/dom` is explicitly **the vaxis `run` shape retargeted at the browser** (`dom/index.k`):

- one long-running `run` owns the surface;
- consumers write `! effect` arms, never an outer loop;
- in a terminal the producer blocks on `nextEvent`; in a browser the **host event loop is the loop**;
- markup: capital tag = component call, **lowercase passes through untouched**.

That last rule is why Koru is extremely HTMX-friendly with almost no new machinery:

| HTMX idea | Already true in Koru |
|-----------|----------------------|
| Declare request + target on the element | Lowercase `hx-get` / `hx-target` / `hx-swap` are opaque HTML attrs — passthrough in `koru/dom:component` markup |
| Server returns a fragment | Orisha already serves `/fragments/...` and `Prefer: return=minimal` |
| Browser swaps only a region | Same job as our `enhance.js` swap; HTMX (or a dialect-compatible enhance) is the host loop |
| Full page without JS | Plain `href` remains — the vaxis/dom posture of progressive enhancement |

So we should **not** invent a bespoke `koru/enhance` vocabulary first. Prefer:

1. Speak **HTMX's attribute + `HX-Request` dialect** from server HTML (this app).
2. Keep `koru/dom` for **keyed local identity** (insert/remove/reorder) where HTMX's outerHTML swap is the wrong tool.
3. Upstream Orisha: treat `HX-Request: true` like Prefer-minimal (generic hypermedia, not media-specific).

vaxis and dom stay the **local reactive** surface; HTMX stays the **server HTML navigation** surface. Same Koru event-continuation taste, different host.

## Orisha — strong upstream / `orisha-ext` candidates

| Piece | Where today | Why extractable | Blockers |
|-------|-------------|-----------------|----------|
| `orisha:run-accept-loop` | `vendor/orisha-lib` | Working Zig serve path with STREAM/Request | Keep until Request/STREAM also exist on pump `answer`/`reply`; then optionally migrate |
| Request extras: `range`, `query`, `prefer`, `hx_request`, `if_none_match` | `parseHttpRequest` in `index.kz` | Generic HTTP, not media-specific | In-repo: accept/answer unified. Upstream: land the helper + fields |
| Raw `HTTP/1.` body passthrough in `send` | `send|zig` | Needed for pre-rendered responses and STREAM framing | Keep API: body starting with `HTTP/1.` is a complete head |
| `STREAM:v1` chunked file send | `send|zig` + media handler | Bounded streaming without full-file buffer; reusable for any large static asset | Stabilize framing; optional future `sendfile` backend behind same shape |
| Idle exit + active-stream lease | accept poll + `active_streams` | Matches Orisha “tiny process / exit when quiet” story | Supervisor story (systemd socket activation) still separate |
| Fragment opt-in (`Prefer` / `HX-Request`) | handler | Protocol opt-in, not HTML-specific | Keep `/fragments/...` as explicit alternate URL |

**Post-rebuild probe (Orisha `main`, koru `5c64de27`, fresh `koruc` via `bash /mnt/w/tools/build-koruc.sh` → `$HOME/src/koru-build/zig-out/bin/koruc`):** minimal upstream `orisha:serve` **compiles and links** under Zig 0.15.1 (zlib headers required for static gzip paths). Prior `duplicate struct member` no longer reproduces. Migration is still a **port**, not a drop-in: STREAM/Request remain on accept-loop/`send`.

**Contribution shape:** prefer patches to `W:\src\orisha` once `run-accept-loop` + Request parse + STREAM send are reviewable without the media HTML handler. Media HTML stays out of Orisha.

## Koru libs — companion packages (not necessarily compiler-core)

| Piece | Where today | Why extractable | Blockers |
|-------|-------------|-----------------|----------|
| HTMX-dialect progressive enhance | `public/enhance.js` | Tiny host that honors `hx-*` (or stock HTMX) + preserves `#player` | Prefer HTMX attrs over a private `data-enhance` vocabulary |
| Keyed list identity (`koru/dom`) | `browser/` + `test_keyed_list` | Local store-driven DOM; complements HTMX, does not replace it | Keep as `koru/dom` consumer / gauntlet sibling |
| Atomic JSON publish + opaque path IDs | `scripts/index_media.py` | Generic offline index pattern | Reimplement as a Koru one-shot; prefer **yyjson** (`W:\src\koru-libs\yyjson` / system `libyyjson`) over forever-Python. Do not vendor `yyjson.c` into the media binary by default — lift or link first |
| HTML escape + Link/OPTIONS helpers | Zig in vendor handler | Shared hypermedia utilities | Wait for Koru server HTML projection; do not invent a second template stack |

## Stay app-local (this repo)

- Library / item / watch HTML projections and capability notes
- `/art/{id}`, media MIME/capability policy, download disposition UX
- Manifest schema fields that are media-domain (`poster`, `container`, `kind`)
- Docker build wrappers and personal-library fixtures
- Synology Indexer / File Station **catalog feed** adapter (when built): app-local ingest into opaque IDs + atomic manifest publish — not an Orisha-core concern
- Offline `ffprobe` probe hook (when built): indexer/batch only; never an Orisha request-handler dependency

## Suggested extraction order

1. **Orisha Request parse + raw send + STREAM** — highest reuse, clearest review boundary. **Prep done in this repo** (`parseHttpRequest` + seam markers); next step is the upstream patch.
2. **Document `run-accept-loop` as the Zig serve path** — unblocks other Orisha apps without waiting for pump emit fix.
3. **HTMX dialect on Orisha HTML** (`HX-Request` → fragment; `hx-*` on links) — proves the vaxis/dom passthrough claim; optional stock HTMX later.
4. **Indexer as a Koru one-shot + yyjson** — replace `scripts/index_media.py` when Koru file/JSON ergonomics win; use the Koru yyjson lift, not a permanent Python indexer. Synology Indexer as catalog source and offline ffprobe for rich metadata are **later product adapters** on that publish path (see ROADMAP / GOAL deferred indexer), not extraction prerequisites.

## Non-goals for contribution

- Transcoding, HLS, DB-backed catalogs
- FFmpeg or ffprobe inside Orisha request handlers
- A general web framework on top of Orisha
- Premature sendfile/mmap before STREAM has a second consumer
- A private progressive-enhance vocabulary that forks HTMX without cause
- Vendoring `yyjson.c` into this app “just in case” while the schema-specific loader and Python stopgap still suffice

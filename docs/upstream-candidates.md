# Upstream and standalone library candidates

Honest map of what this media server has proven that could later leave the app tree — either as a Koru/Orisha contribution, a small companion lib, or stay app-local.

Do **not** extract until the seam has tests and a second consumer. The first consumer is this repo.

**In-repo gate (Phase 7):** `parseHttpRequest` shared by `accept|zig` and `answer|zig` in `vendor/orisha/index.kz`. Media HTML/handler live in [`src/`](../src/) (module `media`), not the Orisha companion. Existing HTTP suite covers Range / Prefer on the accept-loop path; `HX-Request` fragments use `Request.header`, not a parser field. Upstream PR to `W:\src\orisha` comes after that gate — without shipping the media HTML handler.

### File-segment map

| Segment | Where | Notes |
|---------|-------|-------|
| `request-parse` | `vendor/orisha/index.kz` | HTTP parse + `header()` — **upstream patch 1** |
| `accept-loop` | vendor Orisha `index` | Zig serve + idle — **upstream patch 3** |
| `send-stream` | `vendor/orisha/index.kz` (`sendSpecial`) | STREAM:v1 consumer + raw HTTP — **upstream patch 2** |
| `answer` | vendor Orisha `index` | Same parse as accept — **upstream patch 4** |
| `router-static` | vendor Orisha `index` | Matches upstream today |
| `json` | `vendor/json` | Tiny parse + emit; CLI usage in `src/json` |
| `graph` | `src/graph.kz` | Manifest + semantic snapshot (app) |
| `consumers` | `src/consumers.kz` | HTML / JSON-LD / bytes (app) |
| `dispatch` | `src/index.kz` | Route table; `main.k` implements `orisha:handler` |

Orisha sibling stems: [vendor/README.md](../vendor/README.md).


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

So we should **not** invent a bespoke `koru/enhance` vocabulary first, and we should **not** port full HTMX. Prefer:

1. Speak **HTMX's attribute + `HX-Request` dialect** from server HTML (this app’s protocol).
2. Keep `koru/dom` for **keyed local identity** (insert/remove/reorder) where outerHTML swap is the wrong tool.
3. Keep the `|js` fetch/swap in `vendor/koru-libs/htmx` until a koru/dom (vaxis-like) **navigation host** can consume the same protocol. Usage stays `src/frontend/host.k`; emit stays `public/enhance.js`.
4. Upstream Orisha: RFC `Prefer: return=minimal` is the HTTP fragment contract. `HX-Request` is looked up via `Request.header` at the app — not a field on the base parser.

vaxis and dom stay the **local reactive** surface; the JS host stays the **server HTML navigation** surface until a Koru-native host exists. Same event-continuation taste, different host.

## Orisha — actionable upstream patches

One patch per bullet. Not a dump of the media app. Details: [vendor/README.md](../vendor/README.md).

1. **Request extras + `parseHttpRequest`** — `range`, `query`, `prefer`, `if_none_match`, `accept`, generic `header(name)`; shared by accept and answer. **Not** `hx_request`. Tests: this repo’s HTTP suite.
2. **`STREAM:v1` + raw `HTTP/1.` in `send`** — bounded chunked file send + pre-rendered heads. Tests: 206/HEAD/empty/one-byte/416. Producer stays app.
3. **`run-accept-loop` + idle + `streamsBusy()`** — Zig serve path with STREAM/Request. Tests: `test_idle.sh`, `test_reload.sh`.
4. **Keep `answer|zig` on the same parse** — already unified here; pump `reply` port is later.
5. **Pump sibling emit (koruc)** — not an Orisha logic bug. Canonical `serve` links; this vendor’s `index.kz` + sibling `pump.kz` does not (`ambiguous std` / `duplicate koru_pump`). Writeup + repro: [upstream-pump-emit.md](upstream-pump-emit.md). Filed: [korulang/koru#2](https://github.com/korulang/koru/issues/2), defensive [korulang/orisha#1](https://github.com/korulang/orisha/issues/1) (`pump_std` like `router_std`).

**Post-rebuild probe (Orisha `main`, koru `5c64de27`, fresh `koruc`):** full pump is at `vendor/upstream/orisha-pump/` (not beside `index.k`). Minimal `orisha:serve` against upstream lib links. This media binary still cannot compile pump into `import orisha`. Details and repro: [upstream-pump-emit.md](upstream-pump-emit.md). STREAM/Request remain on `send`.

Media HTML, graph scrape, and JSON-LD *routing* stay out of Orisha.

## Koru libs — actionable (enhance / dom / JSON)

| Piece | Where today | Upstream / lib candidate | Stay here |
|-------|-------------|--------------------------|-----------|
| Navigation host | `vendor/koru-libs/htmx` (`import koru/htmx`) → usage `src/frontend/host.k` → `public/enhance.js` (`GET /enhance.js`) | koru-libs: a vaxis-like `run` that honors `hx-*` + `HX-Request` + Prefer-minimal, complete-page fallback. Not a full HTMX port. **This repo already vendors that prototype as `koru/htmx`.** | `#player` resume, `#library-region` default, `protect: "#player"` |
| Keyed list identity | `vendor/koru-libs/dom` (`import koru/dom`) → usage `src/frontend/main.k` → `public/koru-dom-enhance.js` | Already `koru/dom` (`component` / `run` / `drop`). Vendored stem from `W:\src\koru-libs\dom` (2026-08-13). | Media row markup (`LibRow`), demo titles, `swap-rows` |
| JSON publish | `vendor/json` (`import json`) → usage `src/json` → `bin/json-publish` | **Not** `koru/yyjson`. That lift needs system `libyyjson` / pkg-config / phantom `Doc<open!>`, and bookworm has no `libyyjson-dev`. Our tiny writer is the migration source of truth. | Schema we write (`entries[]`, `projections[]`); Python fallback if koruc missing |
| HTML escape + Link/OPTIONS | `src/consumers.kz` | Wait for Koru server HTML projection | Media views |

## Stay app-local (this repo)

- Library / item / watch HTML projections and capability notes
- `/art/{id}`, media MIME/capability policy, download disposition UX
- Manifest schema fields that are media-domain (`poster`, `container`, `kind`)
- Docker build wrappers and personal-library fixtures
- Synology Indexer / File Station **catalog feed** adapter (when built): app-local ingest into opaque IDs + atomic manifest publish — not an Orisha-core concern
- Offline `ffprobe` probe hook (when built): indexer/batch only; never an Orisha request-handler dependency

## Suggested extraction order

1. **Orisha Request parse + raw send + STREAM** — highest reuse, clearest review boundary. **Done in this repo** (`parseHttpRequest` + `header()` + `sendSpecial` in `vendor/orisha/index.kz`); extra vendor stems do not load under `import orisha`. Next step is the upstream patch.
2. **Document `run-accept-loop` as the Zig serve path this app uses** — pump is vendored; STREAM/Request still ride `send`, not `reply`.
3. **Koru-native navigation host** — `vendor/koru-libs/htmx` (emitted via usage `src/frontend/host.k` → `public/enhance.js`) is the prototype; later a koru/dom `run` that consumes the same `hx-*` / `HX-Request` protocol. Do not port full HTMX. Host logic is still a `|js` escape until Koru lowers fetch/swap.
4. **Indexer JSON via `vendor/json`** — our tiny writer, not `koru/yyjson`. Replace `scripts/index_media.py` emit when the writer covers the full manifest/projections schema. Synology Indexer and offline ffprobe stay later adapters.

## Non-goals for contribution

- Transcoding, HLS, DB-backed catalogs
- FFmpeg or ffprobe inside Orisha request handlers
- A general web framework on top of Orisha
- Premature sendfile/mmap before STREAM has a second consumer
- A private progressive-enhance vocabulary that forks HTMX without cause
- Waiting on `koru/yyjson` (pkg-config / phantom Doc) or vendoring `yyjson.c` into `bin/media-server`

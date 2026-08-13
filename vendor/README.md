# Vendored Orisha lib

Copy of `W:\src\orisha\lib` with project-local shims so the media milestone compiles.

## Pump is upstream's serve path; this app still uses `run-accept-loop`

Upstream Orisha (`W:\src\orisha\lib`) ships pump as the main development line (`perf(pump):…`; examples call `orisha:serve`). A full copy is in this repo at [`vendor/upstream/orisha-pump/`](upstream/orisha-pump/).

| File | Role |
|------|------|
| `vendor/upstream/orisha-pump/pump.k` / `pump.kz` | Platform readiness loops (full upstream) |
| `vendor/orisha/index.k` | This app's `run-accept-loop` (not `orisha:serve`) |
| `vendor/orisha/index.kz` | Request parse / STREAM `send` / idle (vendor extras) |

The files cannot sit next to `index.k` in `vendor/orisha/`. `import orisha` maps at the directory; a sibling `pump.kz` is then merged into the same emitted struct as `index.kz` (`ambiguous reference` on `std` — `routing.kz` avoids this by naming `router_std`). `import orisha/pump` makes a nested module, and then koruc double-emits that companion into `koru_pump`. Original `W:\src\orisha\lib` + canonical `orisha:serve` hits that second failure on koruc 0.1.7 (`duplicate struct member` inside `koru_pump`); this media binary also hits the unused-sibling `ambiguous std` shape. See [docs/upstream-pump-emit.md](../docs/upstream-pump-emit.md).

Omitting pump from git was the wrong answer. Compiling it into this binary is still unsafe.

**This app still calls `orisha:run-accept-loop`**, not `serve`. Keep that until these ride `answer` / `pump:reply` *and* the emit is gone:

- `Request` extras + `parseHttpRequest` (`range` / `query` / `prefer` / `accept` / `if_none_match` / `header()`)
- `STREAM:v1` + raw `HTTP/1.` in `send` (pump path uses `reply(head,body)`, not `send`)
- Idle exit + `active_streams` lease

Migration is a port onto `reply`, not a drop-in swap and not a reason to pretend pump is gone.

## App vs Orisha (in-repo split)

Koru companions are **one module per stem** (`index.k` + `index.kz`). A second `.kz` beside this vendor is not another Orisha file — it would be a different module, or ignored. The media app is therefore a **separate module**, not more Zig stuffed into this companion:

| Tree | Module | Role |
|------|--------|------|
| `vendor/orisha/` | `orisha` | Generic HTTP (`index`; parse/STREAM helpers in `index.kz`) |
| `src/index.k` + `index.kz` | `media` | Representation dispatch (`media:dispatch`) |
| `src/graph.kz` | `media/graph` | Physical manifest + semantic core snapshot |
| `src/consumers.kz` | `media/consumers` | Named constructions → HTML / JSON-LD / Link / bytes |
| `src/frontend/` | (JS emit, usage) | `host.k` (`import koru/htmx`) → `public/enhance.js`; `main.k` (`import koru/dom`) → `public/koru-dom-enhance.js` |
| `vendor/koru-libs/` | `koru/dom`, `koru/htmx` | Vendored keyed DOM stem + our navigation host lib |
| `vendor/json/` | `json` | Tiny parse + emit (not `koru/yyjson`); Koru read events for yyjson `tests/basic.kz` + `features.kz`; not in the HTTP binary |
| `src/json/` | (usage) | json-publish CLI fixtures (`import json`) |
| `main.k` | entry | `orisha:handler` → `media:dispatch`, then `orisha:run-accept-loop` |

### Layout copied from examples

No `src/backend` + `src/frontend` split exists upstream. Closest production shapes:

| This repo | Example |
|-----------|---------|
| `main.k` | `W:\src\orisha\examples\full-server\main.k` (also mixed-server, korulang-site): entry owns `orisha:handler`, then the serve loop; `public/` is static output |
| `src/index.k` + `index.kz` + `graph.kz` + `consumers.kz` | `orisha/lib/{index,pump,routing}` sibling stems — directory import loads submodules (`140_003`) |
| `src/frontend/main.k` + `main.kjs` | usage of vendored `koru/dom` (`vendor/koru-libs/dom`, from `W:\src\koru-libs\dom` 2026-08-13) — `koruc --lang=js` → `public/koru-dom-enhance.js` |
| `src/frontend/host.k` + `host.kjs` | usage of `koru/htmx` (`vendor/koru-libs/htmx`) — media defaults + `#player` resume. Emit: `public/enhance.js` (`GET /enhance.js`). |
| `vendor/koru-libs/` | `dom/` stem + our `htmx/` host. See [koru-libs/README.md](koru-libs/README.md). |
| `src/json/main.k` | usage of `vendor/json` — json-publish CLI; schema fixtures stay here |
| `vendor/json/` | Tiny parse + emit (not `koru/yyjson`); no pkg-config |
| `vendor/orisha/` | `W:\src\orisha\lib` — HTTP API on `index`; helpers in sibling stems |

Handler-in-entry wins over moving `orisha:handler` into `src/` (Koru ignores a handler that lives only inside `import media`).

Hot reload asks `koru_orisha.streamsBusy()` (the STREAM/idle lease) rather than touching `active_streams`. JSON-LD `Accept` stays a generic `Request` header; JSON-LD *routing* is app.

**Koru constraints that shaped this split** (not a fake marker-only split — the Zig really moved):

- A vendor companion is one stem (`index.k` + `index.kz`). Putting `handler.kz` next to Orisha would not join that module.
- `orisha:handler` must be implemented in the **entry** (`main.k`). An `orisha:handler = …` flow that lives only inside `import media` is ignored; the default 404 wins.
- Immediate `orisha:handler -> media:dispatch(req)` emits invalid Zig (`return media:dispatch(req)`). Use a flow (`=`) plus a named result arm.
- `media:dispatch` and `orisha:handler` get distinct Zig `Output` structs of the same shape; the entry reconstructs `{ status, body, content_type }` so the types match.
- App Zig cannot see Orisha's private `two`/`four`/`active_streams`; Last-Modified helpers stay in `src/`, and reload uses `streamsBusy()`.

`accept|zig` and `answer|zig` both build `Request` via **`parseHttpRequest`** in this stem (RFC fields + `header()`; no `hx_*`).

### Stems in this vendor

Koru: `|zig` for a `pub tor` stays on the same stem as the contract (`index.k` + `index.kz`). Extra `.kz` beside index is a **different module** — or, if not imported, gets merged into this stem and collides. Helpers therefore stay in `index.kz`. Upstream pump lives in [`vendor/upstream/orisha-pump/`](upstream/orisha-pump/), not beside `index.k`.

| Stem | Role |
|------|------|
| `index` | `handler`, `listen`, `accept`, `send`, `answer`, `router`, `static`, `run-accept-loop`; `Request` / `header()` / `parseHttpRequest` / STREAM:v1 `sendSpecial` / `streamsBusy()` |
| `routing` | Pattern match (unchanged vs upstream; not on the request path) |

This app stays on `run-accept-loop` until STREAM/Request ride `pump:reply`. Upstream pump is at [`vendor/upstream/orisha-pump/`](upstream/orisha-pump/), not beside `index.k`.

## Actionable upstream patches (Orisha only)

Each item is a patch we could send Lars / `W:\src\orisha`. Media graph, HTML, JSON-LD routing, and indexer JSON are **not** Orisha.

1. **Request extras + `parseHttpRequest`** — Add `range`, `query`, `prefer`, `if_none_match`, `accept`, and generic `header(name)` to `Request`; one helper used by `accept|zig` and `answer|zig`. Why: generic HTTP. **Not** `hx_request` — HTMX dialect uses `header("HX-Request")` at the app. Tests: Range / Prefer / `If-None-Match` in this repo’s HTTP suite; fragment tests look up `HX-Request` via `header()`.
2. **`STREAM:v1` + raw `HTTP/1.` in `send`** — `send|zig` consumes `STREAM:v1\npath\nstart\nend\n\nheaders` and bodies that already start with `HTTP/1.`. Why: bounded file send + pre-rendered responses. Tests: `206` / `HEAD` / empty / one-byte / `416`. The *producer* (`mediaHttp` path/MIME) stays app.
3. **`orisha:run-accept-loop` + idle + `active_streams`** — `listen` → recursive `accept` → `handler` → `send`; `KORU_IDLE_SECS` when quiet; `streamsBusy()` read-only lease. Why: working Zig serve path until pump `answer`/`reply` grow Request/STREAM. Tests: `test_idle.sh`, `test_reload.sh`.
4. **Keep `answer|zig` aligned** — same `parseHttpRequest` as accept (already done here). Pump migration is a later port, not this patch.

**Stay in this app** (`src/graph.kz`, `src/consumers.kz`, `src/index.kz`; not vendor):

- Graph scrape (`entries[]` / `projections[]`) and `KORU_MEDIA_ROOT` / `KORU_MANIFEST` / `KORU_SEMANTIC`
- `media:dispatch` route table and HTML / JSON-LD / Link / bytes consumers
- `STREAM:v1` *producer* in `mediaHttp` (path/MIME policy)

See [docs/upstream-candidates.md](../docs/upstream-candidates.md). Upstream tree: `W:\src\orisha`.

# Vendored Orisha lib

Copy of `W:\src\orisha\lib` with project-local shims so the media milestone compiles.

## Why pump / `orisha:serve` are missing (re-verified post-pull)

Upstream Orisha (`W:\src\orisha\lib`, `main` as of 2026-08-12 pull) still ships:

| File | Role |
|------|------|
| `pump.k` / `pump.kz` | Platform readiness loops: `run\|zig`, `run\|epoll`, `run\|io-uring`, `run\|unikraft` |
| `index.k` | `orisha:serve` = `pump:run` → `answer` → `pump:reply` |
| `routing.*` | Router (identical in this vendor) |

Upstream **has not removed pump**; recent Orisha work is pump/bench performance (`perf(pump):…`). Canonical examples still call `orisha:serve`.

**This vendor deliberately omits `pump.k` / `pump.kz`.** With the koruc this project builds against (`$HOME/src/koru-build`, Zig 0.15.1), importing upstream `orisha` (which pulls `orisha/pump`) still **double-emits** multi-`~proc run|*` bodies into one Zig struct → `duplicate struct member` errors (`openListener`, `MAX_WORKERS`, `fill_event`, …). Frontend emit succeeds; Zig backend fails. Until koruc emits only the selected pump variant’s body (or isolates shared helpers once), apps here use `orisha:run-accept-loop` (`listen` → recursive `accept` → `handler` → `send`) — see `main.k`.

### Should this app migrate to pump/serve if koruc is fixed?

**Not as the next step.** Even after a koruc pump-emit fix, keep `run-accept-loop` until these land upstream (or are ported onto `answer`/`reply`):

- `Request` extras + `parseHttpRequest` (`range` / `query` / `prefer` / `hx_request`)
- `STREAM:v1` + raw `HTTP/1.` in `send` (pump path uses `reply(head,body)`, not `send`)
- Idle exit + `active_streams` lease

Migration would be a deliberate port, not a drop-in swap.

## Seam map (`index.kz`)

| Zone | Marker | Contents |
|------|--------|----------|
| Generic Orisha | `EXTRACT:orisha-core` | `Request`, `listen`/`accept`/`send`/`answer`, `parseHttpRequest`, `requestPathKey`, router/static embed |
| Media app | `APP:media-handler` | Manifest, HTML projections, `mediaHttp` / `artHttp`, `handler\|zig` |
| Shared lease | `active_streams` | Idle exit (`accept`), `STREAM:v1` (`send`), hot reload (media) |

`accept|zig` and `answer|zig` both build `Request` via **`parseHttpRequest`** (same `range` / `query` / `prefer` / `hx_request` / `if_none_match`).

### Proposed future files (`SPLIT→` banners in `index.kz`)

| Future file | Marker | What moves |
|-------------|--------|------------|
| `request-parse.kz` | `SPLIT→ request-parse.kz` | `Request`, `parseHttpRequest`, `requestPathKey` |
| `accept-loop.kz` | `SPLIT→ accept-loop.kz` | `listen\|zig`, `accept\|zig`, idle poll (+ `run-accept-loop` in `index.k`) |
| `send-stream.kz` | `SPLIT→ send-stream.kz` | `send\|zig` (`STREAM:v1` + raw `HTTP/1.`) |
| `answer.kz` | `SPLIT→ answer.kz` | `answer\|zig` |
| `router-static.kz` | (upstream-shaped) | Router / static transforms |
| `manifest-load.kz` | `SPLIT→ manifest-load.kz` | **APP** schema JSON loader (`entries` + unescape) |
| `html-views.kz` | `SPLIT→ html-views.kz` | **APP** library/item/watch HTML |
| `media-http.kz` | `SPLIT→ media-http.kz` | **APP** `mediaHttp` / `artHttp` |
| `handler.kz` | `SPLIT→ handler.kz` | **APP** `handler\|zig` |

Do not physically split until a second consumer and tests exist. Markers are the extraction map. Pump restore is **not** a split target for this app until STREAM/Request ride the pump path.

## Media extensions (reviewable vs upstream)

**Upstream candidates (generic):**

- `parseHttpRequest` + `Request` fields: `range`, `query`, `prefer`, `hx_request`, `if_none_match`
- `send|zig`: `STREAM:v1` consumer, raw `HTTP/1.` passthrough, `headerPrefixClose`
- `run-accept-loop` + idle poll (`KORU_IDLE_SECS`) — document as the Zig serve path while pump emit is broken

**Stay in this app:**

- `~proc handler|zig` — library/item/watch HTML, fragments, sort/filter/search, `/media/{id}`, `/art/{id}`
- Schema manifest loader (`entries` array + JSON unescape) — see `scripts/test_manifest_parse.py`
- `KORU_MEDIA_ROOT` / `KORU_MANIFEST`
- `STREAM:v1` *producer* in `mediaHttp` (framing protocol is generic; path/MIME policy is not)

See [docs/upstream-candidates.md](../docs/upstream-candidates.md). Upstream tree: `W:\src\orisha`.

# Vendored Orisha lib

Copy of `W:\src\orisha\lib` with project-local shims so the media milestone compiles.

## Why

Current `koruc` emits every `~proc run|*` body from upstream `pump.kz`, which duplicates shared Zig declarations and fails backend compile. Upstream `orisha:serve` / pump is therefore omitted; apps use `orisha:run-accept-loop`.

## Seam map (`index.kz`)

| Zone | Marker | Contents |
|------|--------|----------|
| Generic Orisha | `EXTRACT:orisha-core` | `Request`, `listen`/`accept`/`send`/`answer`, `parseHttpRequest`, `requestPathKey`, router/static embed |
| Media app | `APP:media-handler` | Manifest, HTML projections, `mediaHttp` / `artHttp`, `handler\|zig` |
| Shared lease | `active_streams` | Idle exit (`accept`), `STREAM:v1` (`send`), hot reload (media) |

`accept|zig` and `answer|zig` both build `Request` via **`parseHttpRequest`** (same `range` / `query` / `prefer` / `hx_request` / `if_none_match`).

## Media extensions (reviewable vs upstream)

**Upstream candidates (generic):**

- `parseHttpRequest` + `Request` fields: `range`, `query`, `prefer`, `hx_request`, `if_none_match`
- `send|zig`: `STREAM:v1` consumer, raw `HTTP/1.` passthrough, `headerPrefixClose`
- `run-accept-loop` + idle poll (`KORU_IDLE_SECS`)

**Stay in this app:**

- `~proc handler|zig` — library/item/watch HTML, fragments, sort/filter/search, `/media/{id}`, `/art/{id}`
- `KORU_MEDIA_ROOT` / `KORU_MANIFEST`
- `STREAM:v1` *producer* in `mediaHttp` (framing protocol is generic; path/MIME policy is not)

See [docs/upstream-candidates.md](../docs/upstream-candidates.md). Upstream tree: `W:\src\orisha`.

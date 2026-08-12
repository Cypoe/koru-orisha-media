# Vendored Orisha lib

Copy of `W:\src\orisha\lib` with project-local shims so the media milestone compiles.

## Why

Current `koruc` emits every `~proc run|*` body from upstream `pump.kz`, which duplicates shared Zig declarations and fails backend compile. Upstream `orisha:serve` / pump is therefore omitted; apps use `orisha:run-accept-loop`.

## Media extensions (reviewable vs upstream)

- `~proc handler|zig` — library/item/watch HTML, fragments, sort/filter query, `/media/{id}` with HEAD + single-range 206/416 + 304.
- Chunked media via `STREAM:v1` body encoding consumed by `send|zig` (64 KiB chunks; no full-range buffer).
- `KORU_MEDIA_ROOT` / `KORU_MANIFEST` env configuration.
- Request parsing: `req.range`, `req.query`, `req.prefer`, `req.if_none_match`.
- `send|zig` fixes (raw `HTTP/1.` bodies, `headerPrefixClose`, stream path).

See [docs/upstream-candidates.md](../docs/upstream-candidates.md) for what should leave this vendor tree later.

Upstream: `W:\src\orisha`.

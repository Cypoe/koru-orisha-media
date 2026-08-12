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
- Stream/codec probe still deferred (no FFmpeg).
- Publish manifests atomically.
- Hot reload when manifest mtime changes and no media streams are active.

## Phase 3: hypermedia interaction

- Add sort, filter, search, and pagination links (`limit` / `offset`).
- Add fragment representations for enhanced navigation.
- Opt-in `Prefer: return=minimal` on `/library` returns a fragment.
- Add forms for any future mutating operations.
- Add `Link` headers and a minimal `OPTIONS` implementation.
- `/art/{id}` serves precomputed poster sidecars when present.
- Honest watch capability note for awkward containers; `?download=1` sets `Content-Disposition: attachment`.

## Phase 4: browser enhancement

- Keep complete-page navigation as the baseline.
- Shipped: `public/enhance.js` (resume + fragment swap); player stays outside replaceable regions.
- Optional koru/dom keyed list: `browser/main.k` + `scripts/build-browser.sh` → `public/koru-dom-enhance.js` + `/enhance-demo.html`.
- Persist resume position locally (localStorage) before considering server-side state.

## Phase 5: lifecycle

- `scripts/bench_baseline.sh` for cold/steady latency + RSS
- `KORU_IDLE_SECS` idle exit when no media streams are active
- Hot manifest reload (mtime, quiet streams) — see [docs/lifecycle.md](docs/lifecycle.md)
- sendfile/mmap / socket activation still deferred

## Phase 6: hypermedia polish + extraction map

- Library GET search form; item `year` + collection `Link`; media `304` on `If-None-Match`
- [docs/upstream-candidates.md](docs/upstream-candidates.md) — what can become Orisha/Koru libs later

## Explicitly deferred

Transcoding, HLS/DASH, background metadata services, recommendation systems, remote media discovery, and a large client compatibility layer.

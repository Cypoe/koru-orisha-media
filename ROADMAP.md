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
- Shipped: [`public/enhance.js`](public/enhance.js) — HTMX-dialect host (`hx-get` / `hx-target` / `HX-Request`) + localStorage resume; player stays outside replaceable regions.
- Optional koru/dom keyed list: `browser/main.k` + `scripts/build-browser.sh` → `public/koru-dom-enhance.js` + `/enhance-demo.html`.
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

- Unified `parseHttpRequest` for `accept` and `answer`; `EXTRACT:` / `APP:` / `SPLIT→` seam markers in [`vendor/orisha-lib/index.kz`](vendor/orisha-lib/index.kz)
- Vendor / current-apis docs match the real `Request` + `STREAM:v1` surface
- Schema-specific manifest loader (`entries` + unescape) + `scripts/test_manifest_parse.py`
- Next **out-of-repo**: patch `W:\src\orisha` with Request parse + raw send + STREAM + `run-accept-loop` docs — media `handler` stays in this vendor tree

## Next REAL product work (after Phase 7 prep)

Not more docs. Ranked concrete features:

1. **Richer library UX still missing from GOAL resource model** — e.g. `/library/{kind}` as first-class collection URLs if not already solid, playlist/queue affordances, or subtitle resource only if a real fixture needs it.
2. **Indexer depth** — optional container/codec probe behind an injectable offline step (still no FFmpeg-in-request); persistent sidecar IDs across renames.
3. **Browser Step 9 hardening** — keep player identity under HTMX swaps in more flows; measure before more koru/dom surface.

Do **not** next: vendoring yyjson into Docker, migrating to upstream pump/serve (still broken under koruc + missing STREAM/Request), sendfile/mmap, or another extraction-only doc pass.

## Explicitly deferred

Transcoding, HLS/DASH, background metadata services, recommendation systems, remote media discovery, and a large client compatibility layer.

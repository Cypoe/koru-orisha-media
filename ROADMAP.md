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
- Injectable offline probe hook (`--probe ftyp` / `index_root(..., probe=)`); no FFmpeg-in-request. Full stream/codec probe still optional/pluggable.
- Persistent sidecar IDs (`*.id`) across renames when `--write-id-sidecars` is used.
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
- Shipped: [`public/enhance.js`](public/enhance.js) — HTMX-dialect host (`hx-get` / `hx-target` / `HX-Request`) + localStorage resume; swaps `#library-region` only; refuses targets that own `#player`; watch related shelf keeps player outside replaceable regions.
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

1. **Richer library UX** — first slice landed: `/library/{kind}` self/up Links + title, row watch/year affordances, pagination preserves `sort`/`q`, `#library-region` swap root. Still open: playlist/queue only if useful; subtitle resource only with a real fixture.
2. **Indexer depth** — first slice landed: injectable `--probe` / `probe=` hook (`ftyp` built-in) + `--write-id-sidecars`. Orisha item/watch now surface nested first-track `video`/`audio` brand/codec probe notes. Still open: richer codec/stream probes, and auto-moving sidecars on rename.
3. **Browser Step 9 hardening** — first slice landed: watch related shelf swaps `#library-region` only; `enhance.js` refuses targets that own `#player`, checks node identity after swap, `performance.mark` on swaps, popstate re-fetch. Still open: measured koru/dom only if marks justify it.

Do **not** next: vendoring yyjson into Docker, migrating to upstream pump/serve (koruc pump emit now links, but STREAM/Request still missing on that path), sendfile/mmap, or another extraction-only doc pass.

## Explicitly deferred

Transcoding, HLS/DASH, background metadata services, recommendation systems, remote media discovery, and a large client compatibility layer.

# Upstream and standalone library candidates

Honest map of what this media server has proven that could later leave the app tree — either as a Koru/Orisha contribution, a small companion lib, or stay app-local.

Do **not** extract until the seam has tests and a second consumer. The first consumer is this repo.

## Orisha — strong upstream / `orisha-ext` candidates

| Piece | Where today | Why extractable | Blockers |
|-------|-------------|-----------------|----------|
| `orisha:run-accept-loop` | `vendor/orisha-lib` | Avoids koruc double-emit of multi-`run|*` pumps; already the working serve path | Document as the recommended Zig serve shape until pump emission is fixed |
| Request extras: `range`, `query`, `prefer`, `if_none_match` | accept parse in `index.kz` | Generic HTTP, not media-specific | Unify with `answer` path so one Request builder exists |
| Raw `HTTP/1.` body passthrough in `send` | `send|zig` | Needed for pre-rendered responses and STREAM framing | Keep API: body starting with `HTTP/1.` is a complete head |
| `STREAM:v1` chunked file send | `send|zig` + media handler | Bounded streaming without full-file buffer; reusable for any large static asset | Stabilize framing; optional future `sendfile` backend behind same shape |
| Idle exit + active-stream lease | accept poll + `active_streams` | Matches Orisha “tiny process / exit when quiet” story | Supervisor story (systemd socket activation) still separate |
| `Prefer: return=minimal` → fragment | handler | Protocol opt-in, not HTML-specific | Spec the Prefer token; keep `/fragments/...` as explicit alternate |

**Contribution shape:** prefer patches to `W:\src\orisha` once `run-accept-loop` + Request parse + STREAM send are reviewable without the media HTML handler. Media HTML stays out of Orisha.

## Koru libs — companion packages (not necessarily compiler-core)

| Piece | Where today | Why extractable | Blockers |
|-------|-------------|-----------------|----------|
| Progressive fragment swap + resume | `public/enhance.js` | HTMX-like recipe that preserves `#player` | Needs a tiny API surface (`data-enhance`, Prefer header) and a fixture page |
| Keyed list identity tests | `browser/` + `test_keyed_list` | Pins koru/dom insert/remove/reorder for apps | Already depends on `koru/dom`; keep as example or `koru/dom` gauntlet sibling |
| Atomic JSON publish + opaque path IDs | `scripts/index_media.py` | Generic offline index pattern | Reimplement in Koru when file/JSON story is pleasant; Python is fine as a reference indexer |
| HTML escape + Link/OPTIONS helpers | Zig in vendor handler | Shared hypermedia utilities | Wait for Koru server HTML projection; do not invent a second template stack |

## Stay app-local (this repo)

- Library / item / watch HTML projections and capability notes
- `/art/{id}`, media MIME/capability policy, download disposition UX
- Manifest schema fields that are media-domain (`poster`, `container`, `kind`)
- Docker build wrappers and personal-library fixtures

## Suggested extraction order

1. **Orisha Request parse + raw send + STREAM** — highest reuse, clearest review boundary.
2. **Document `run-accept-loop` as the Zig serve path** — unblocks other Orisha apps without waiting for pump emit fix.
3. **`enhance.js` as a documented recipe or tiny `koru/enhance` package** — after Prefer/fragment stay stable.
4. **Indexer as a Koru one-shot** — only when Koru file/JSON ergonomics beat the Python reference.

## Non-goals for contribution

- Transcoding, HLS, DB-backed catalogs
- A general web framework on top of Orisha
- Premature sendfile/mmap before STREAM has a second consumer

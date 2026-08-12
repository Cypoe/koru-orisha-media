# Upstream and standalone library candidates

Honest map of what this media server has proven that could later leave the app tree — either as a Koru/Orisha contribution, a small companion lib, or stay app-local.

Do **not** extract until the seam has tests and a second consumer. The first consumer is this repo.

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
| `orisha:run-accept-loop` | `vendor/orisha-lib` | Avoids koruc double-emit of multi-`run|*` pumps; already the working serve path | Document as the recommended Zig serve shape until pump emission is fixed |
| Request extras: `range`, `query`, `prefer`, `hx_request`, `if_none_match` | accept parse in `index.kz` | Generic HTTP, not media-specific | Unify with `answer` path so one Request builder exists |
| Raw `HTTP/1.` body passthrough in `send` | `send|zig` | Needed for pre-rendered responses and STREAM framing | Keep API: body starting with `HTTP/1.` is a complete head |
| `STREAM:v1` chunked file send | `send|zig` + media handler | Bounded streaming without full-file buffer; reusable for any large static asset | Stabilize framing; optional future `sendfile` backend behind same shape |
| Idle exit + active-stream lease | accept poll + `active_streams` | Matches Orisha “tiny process / exit when quiet” story | Supervisor story (systemd socket activation) still separate |
| Fragment opt-in (`Prefer` / `HX-Request`) | handler | Protocol opt-in, not HTML-specific | Keep `/fragments/...` as explicit alternate URL |

**Contribution shape:** prefer patches to `W:\src\orisha` once `run-accept-loop` + Request parse + STREAM send are reviewable without the media HTML handler. Media HTML stays out of Orisha.

## Koru libs — companion packages (not necessarily compiler-core)

| Piece | Where today | Why extractable | Blockers |
|-------|-------------|-----------------|----------|
| HTMX-dialect progressive enhance | `public/enhance.js` | Tiny host that honors `hx-*` (or stock HTMX) + preserves `#player` | Prefer HTMX attrs over a private `data-enhance` vocabulary |
| Keyed list identity (`koru/dom`) | `browser/` + `test_keyed_list` | Local store-driven DOM; complements HTMX, does not replace it | Keep as `koru/dom` consumer / gauntlet sibling |
| Atomic JSON publish + opaque path IDs | `scripts/index_media.py` | Generic offline index pattern | Reimplement in Koru when file/JSON ergonomics win |
| HTML escape + Link/OPTIONS helpers | Zig in vendor handler | Shared hypermedia utilities | Wait for Koru server HTML projection; do not invent a second template stack |

## Stay app-local (this repo)

- Library / item / watch HTML projections and capability notes
- `/art/{id}`, media MIME/capability policy, download disposition UX
- Manifest schema fields that are media-domain (`poster`, `container`, `kind`)
- Docker build wrappers and personal-library fixtures

## Suggested extraction order

1. **Orisha Request parse + raw send + STREAM** — highest reuse, clearest review boundary.
2. **Document `run-accept-loop` as the Zig serve path** — unblocks other Orisha apps without waiting for pump emit fix.
3. **HTMX dialect on Orisha HTML** (`HX-Request` → fragment; `hx-*` on links) — proves the vaxis/dom passthrough claim; optional stock HTMX later.
4. **Indexer as a Koru one-shot** — only when Koru file/JSON ergonomics beat the Python reference.

## Non-goals for contribution

- Transcoding, HLS, DB-backed catalogs
- A general web framework on top of Orisha
- Premature sendfile/mmap before STREAM has a second consumer
- A private progressive-enhance vocabulary that forks HTMX without cause

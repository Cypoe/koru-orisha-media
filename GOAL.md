# GOAL.md

## Mission

Build a small, fast, direct-play personal media library on top of Koru and Orisha.

This project is not a Jellyfin replacement and must not become a general media-server clone by accident. Its purpose is to make a personal media directory pleasant to browse and play through a web browser while keeping the server nearly idle when nobody is using it.

The central design constraint is:

> A library request performs manifest lookup and representation rendering. A media request performs authorization, range validation, and file streaming. Expensive work happens only in an explicit offline indexer.

The implementation should use Koru's event-continuation model, compile through its current backend, and extend Orisha rather than introducing an unrelated web framework or runtime architecture.

## Context

Koru is the event-continuation meta-language built on Zig, with native and JavaScript compilation targets. Orisha is the Koru web server and router. Koru also has `koru/dom`, whose component surface is consumed at compile time and emits direct DOM code rather than shipping a virtual DOM, scheduler, or component runtime.

The `koru/dom` keyed-table work is directly relevant. Static markup becomes a template, typed placeholders become synthesized inputs, and store handles provide identity for keyed DOM updates. The important lesson is that identity already held by both sides is cheaper and safer than looking it up by scanning the DOM or parsing identifiers back out of text.

The intended media application should use that same principle:

- media entries receive stable opaque identities;
- server URLs and browser state use those identities;
- a player element owns its identity and is not needlessly recreated;
- collection updates can use keyed DOM operations when profiling justifies them;
- complete server-rendered HTML remains the fallback and primary baseline.

## User problem

A low-memory NAS should not need to run a large resident media platform merely to show a library and serve files. A media library often needs no transcoding at all: modern browsers and devices can decode many H.264, HEVC/H.265, AV1, HDR, and audio files directly. HLS, adaptive streaming, FFmpeg process management, device-profile negotiation, and custom playback stacks exist for compatibility and transformation cases; they are not automatically useful for a private library whose clients are known.

The first implementation therefore serves original files directly. If a browser cannot play a file, the application should say so or offer a download. It must not silently start a transcoder or invent an HLS pipeline.

## Product definition

The product is a content-driven web surface with four responsibilities:

1. Index configured media roots in an explicit batch process.
2. Serve precomputed collection and item representations.
3. Serve original media bytes with correct HTTP range semantics.
4. Offer optional frontend enhancement without making JavaScript or a custom client mandatory.

The application should feel like a very small web-native file catalogue with a good media-oriented UI, not like a daemon that owns the entire media lifecycle.

The first presentable surface is the **local archive**. On first run, or when the fetched catalogue index is missing (`semantic.json` absent, or `projections[]` empty), `/` and `/library` still list playable files from the physical manifest. Catalogue names and provider chips are an overlay that appears only when named constructions exist. Do not block browse or play on TMDB or `project_semantic`.

## Non-goals

Do not implement these in the initial project:

- video or audio transcoding;
- HLS, DASH, adaptive bitrate streaming, or segment generation;
- FFmpeg process pools or per-request probing;
- a recommendation engine;
- remote metadata lookup or scraping;
- a large account, social, or multi-tenant system;
- a custom codec implementation;
- a complete Jellyfin-compatible API;
- a full client compatibility matrix;
- server-side thumbnail generation during HTTP requests;
- a permanent file watcher that keeps expensive media analysis alive;
- a client-side single-page application that replaces normal HTTP navigation;
- a database dependency for the first manifest implementation.

A future project may add optional adapters for difficult formats, but such adapters must remain explicit and must not contaminate the direct-play core.

## Architecture

Use three planes.

### Indexer plane

The indexer is a short-lived command or executable. It walks configured roots, derives cheap filesystem facts, and optionally probes containers and streams. It may generate or collect artwork as an offline operation. It writes a complete new manifest to a temporary path, validates it, flushes it, and atomically renames it into place.

The indexer must never be required for an ordinary library request. It may be run manually, from an external scheduler, or later from a low-frequency filesystem-triggered job.

#### Deferred / future indexer (endgame)

The first milestone’s JSON walker (`scripts/index_media.py` with optional `--probe ftyp`) is a **fixture / CI fallback**. It must not be required on the NAS. Today’s Synology indexer is the in-process Koru walk (`catalog.kz` `reindex`, Settings / `reindex.requested`). That must not freeze the long-term design into a forever-Python indexer; a later Synology Indexer feed can still replace the walk.

Later, prefer this shape (still outside the request plane):

1. **Catalog source — Synology Indexer.** Consume Synology’s media index / File Station indexing story the way Radarr and Jellyfin already do on Synology. The media app ingests an external catalog feed into the same opaque-ID + atomic-manifest publish path; it does not invent a resident walker as the durable architecture.
2. **Probe / metadata — ffmpeg/ffprobe offline only.** Real container and stream probing belongs in the offline indexer or a Synology-fed batch job. Orisha request handlers must never spawn FFmpeg, remux, or probe. Today’s injectable `ftyp` peek and nested `video`/`audio` fields remain the personal-milestone path that does not require FFmpeg on the server HTTP path.
3. **JSON — our writer (`vendor/json`).** Indexer/projection publish uses a tiny vendored emitter, not `koru/yyjson` (pkg-config / phantom Doc / no bookworm package). The CLI is `src/json` usage. Python remains CI fallback if koruc is missing. The request process keeps a schema-specific scrape (`src/graph.kz`) and does not parse JSON through this writer.

Invariants that do not change: opaque IDs at the HTTP boundary, atomic manifest publish, immutable snapshots for in-flight requests, and no directory walk or probe on a library/media request.

### Backend shim (Orisha request plane)

The backend shim loads one complete graph snapshot (physical manifest + semantic core) and dispatches representations to named consumers. Orisha is only the HTTP pump. Request handlers resolve IDs against that snapshot, emit HTML / JSON-LD / Link / bytes, and stream files. A request must not enumerate the media directory, invoke a probe process, query remote metadata, or construct a database schema.

Orisha may initially remain alive as a tiny native process. Later, it can support socket activation or another supervisor-owned listener and exit after an idle period. Active file streams must prevent shutdown until complete.

### Frontend

The baseline client is ordinary HTML with native `<video>` and `<audio>` elements, served as complete representations from the backend shim. Koru's DOM compiler may enhance collection updates, playback controls, local resume state, playlist behavior, and metadata repainting. There is no separate "browser app" product — `src/frontend/` is a module of this app (same shape as `koru-libs/dom/app/`).

The player element must be outside replaceable collection regions, or be explicitly keyed and preserved by the frontend. Never rebuild a playing element merely because a surrounding title, sort order, or progress value changed.

## Resource model

The first resource vocabulary is:

- `/` — service entry point and top-level links.
- `/library` — library root.
- `/library/{kind}` — collection projection, with sorting/filtering/pagination affordances.
- `/item/{id}` — item representation and available actions.
- `/play/{id}` — player projection.
- `/media/{id}` — original byte resource.
- `/art/{id}` — precomputed artwork resource, if present.
- `/subtitles/{id}` or an equivalent related resource, only if subtitle delivery is implemented.
- `/fragments/...` — optional partial representations for enhanced navigation.
- `/manifest` or an equivalent machine representation, only if exposing it is useful and authorized.

The exact route syntax should follow the current Orisha router capabilities rather than forcing an imagined API. Keep route handlers thin and put resource selection/rendering into testable functions.

HTML is the default representation. JSON is optional and should describe the same resources and affordances. Do not create a second API whose links and permissions diverge from the HTML representation.

## Hypermedia and HATEOAS

The server should be hypermedia-first.

A representation must contain the links and forms that describe what the current client can do. Navigation, sorting, filtering, pagination, playing, downloading, returning to a parent collection, selecting a related track, and future mutations should be represented as ordinary links or forms.

Permissions are expressed through affordances. If a principal cannot perform an operation, do not render its form or action link. Do not make clients duplicate an authorization matrix in JavaScript.

Use `Link` headers for representation-level relations such as canonical, alternate, self, up, or related. Use HTML links and forms for user-visible actions.

Implement `OPTIONS` carefully but do not mistake it for application discovery. `OPTIONS` may report generic method support and an `Allow` header. It is useful for protocol introspection and CORS/preflight behavior. Resource-specific capabilities belong in the representation itself.

A non-JavaScript client must still be able to browse and play any supported file. Enhancement must be additive.

## Direct-play media protocol

For `/media/{id}`:

- accept `GET` and `HEAD`;
- resolve the opaque ID through the manifest;
- never accept an arbitrary filesystem path as the public identifier;
- validate that the resolved path remains within a configured media root;
- derive `Content-Type` from trusted indexed metadata or a safe extension map;
- return `Content-Length`;
- return `Accept-Ranges: bytes`;
- return a stable `ETag` based on identity and file version;
- return `Last-Modified` when available;
- support a single valid byte range with `206 Partial Content`;
- return a correct `Content-Range` and selected content length;
- return `416 Range Not Satisfiable` for an unsatisfiable range;
- do not buffer entire files into application memory;
- apply backpressure while reading and writing;
- do not launch FFmpeg or remux because a range request was made.

`HEAD` must expose the same metadata as `GET` without transferring the body. Conditional requests may be added once the basic behavior is correct.

Start with one range if that is what the current Orisha response model can support. Document any deliberate limitation instead of creating an incorrect multi-range response.

## Manifest model

The first manifest can be JSON or another simple immutable format supported comfortably by Koru. It should not require SQLite, a database server, or an always-running index service.

A media entry should be able to contain:

```json
{
  "id": "m_7f3af1",
  "kind": "movie",
  "title": "Arrival",
  "year": 2016,
  "path": "movies/Arrival (2016)/Arrival.mp4",
  "bytes": 8348123941,
  "modified_ns": 1765349200000000000,
  "mime": "video/mp4",
  "container": "mp4",
  "video": [{"codec": "hevc", "width": 3840, "height": 2160, "hdr": true}],
  "audio": [{"codec": "aac", "language": "eng", "channels": 2}],
  "poster": "/art/m_7f3af1.webp"
}
```

The concrete schema may be smaller initially. Do not overcommit to metadata that the first views do not use.

Required invariants:

- IDs are unique within a manifest generation.
- IDs are opaque at the HTTP boundary.
- Paths are relative to configured roots.
- Normalized paths cannot escape their roots.
- Every published manifest is complete and parseable.
- A manifest replacement is atomic from the request process's perspective.
- In-flight requests may finish against an old immutable snapshot.
- Replacing a manifest does not change the bytes of an existing file resource.

A first ID may be derived from normalized relative path, size, and modification time. Design the code so persistent sidecar identity can be added later and renames can preserve identity.

## HTML and Koru views

Do not introduce Askama, Jinja, React, or another unrelated rendering stack. Koru already has a structural markup/component direction for the browser. The desired server-side counterpart is a narrow, typed HTML projection that compiles into direct output operations.

The view surface should make these operations explicit:

- emit static text;
- emit escaped text;
- emit escaped attributes;
- emit known element structure;
- iterate over typed collection values;
- conditionally expose an affordance;
- explicitly mark a trusted raw fragment, if such an escape hatch is unavoidable.

The same structural component descriptions should eventually be usable for:

- server HTML serialization;
- browser DOM template creation and keyed updates.

Do not force the backend and frontend renderers to have identical runtime semantics. They share structure and identity, not necessarily the same generated code.

## Frontend enhancement strategy

Use complete-page server rendering first. Add fragment endpoints only where they simplify an interaction such as sorting, filtering, or pagination.

HTMX-like behavior is a useful model, not necessarily a dependency. The desired semantics are:

- an element declares a request and target;
- the server returns a representation or fragment;
- the browser swaps only the declared region;
- normal links remain usable without enhancement;
- history behavior is explicit;
- the player is not destroyed by collection updates.

Koru/dom should be used for fine-grained, identity-aware local updates when it provides a measured benefit. A keyed collection reorder is a separate primitive from repainting a row property. Do not invent a generalized diff engine before a concrete use case and benchmark exist.

Potential first frontend features:

- native playback controls around `<video>`/`<audio>`;
- local resume position;
- selected-item state;
- playlist queue;
- fine-grained progress/metadata repainting;
- keyed collection insert/remove/reorder.

## Playback stance

The browser or a native client should decode the media. A custom application player is optional and should initially mean the UI around the native media element, not a codec or streaming implementation.

If a file is not directly playable in the current browser, the first response should be an honest capability message and a download link. Do not make the core architecture depend on solving every client/container combination.

If a future compatibility layer is desired, isolate it behind an explicit adapter boundary:

- offline remuxing is an indexer concern;
- client-side WebCodecs/WASM is a browser adapter concern;
- server transcoding is a separate optional service;
- the direct-play resource remains unchanged.

## Implementation sequence

### Step 1: understand current APIs

Read the current Koru and Orisha repositories and their examples. Identify the actual compiler invocation, package/import convention, response type, static file implementation, route parameter syntax, and test conventions. Do not write code based only on this document if the repositories have changed.

Record findings in `docs/current-apis.md` or an equivalent note.

### Step 2: prove a minimal Orisha application

Create the smallest compilable application that:

- serves `/`;
- serves one static asset;
- has one path parameter;
- returns a response using the real Orisha API;
- has a repeatable build/test command.

Do not add the media model until this compiles.

### Step 3: define pure manifest types

Implement a minimal manifest and media-entry representation using current Koru capabilities. Add parser/fixture tests. Prefer a small hand-written fixture over a large generated library.

### Step 4: implement one-shot indexer behavior

Start with directory facts: relative path, size, mtime, extension, MIME, and stable ID. Make probing optional and injectable. Publish atomically. The indexer should be runnable without starting Orisha.

### Step 5: render the library

Add `/library` and one collection view. Render full HTML with links for item pages and direct playback. Use escaped values and stable item identity.

### Step 6: implement direct file delivery

Add `/media/{id}` with `GET`, `HEAD`, MIME, length, and single-range support. Use bounded streaming. Test file contents and headers with small fixtures.

### Step 7: add item/player pages

Add `/item/{id}` and `/play/{id}`. Keep the media element outside any fragment region that can be replaced. Include play, download, parent, and available related-resource links.

### Step 8: add hypermedia enhancement

Add fragment responses, sort/filter links, optional opt-in request headers, and explicit target identities. Keep full-page fallback behavior.

### Step 9: add Koru frontend code

Only after server behavior is stable, add a small frontend enhancement for a measurable feature. Keep the generated client optional and test stable handles, insertion, removal, and reorder behavior.

### Step 10: lifecycle and optimization

Measure memory, startup, request latency, and stream behavior. Only then consider manifest reload, socket activation, idle exit, mmap, sendfile-like paths, or a compact binary manifest.

## Testing requirements

Every implementation phase must add tests at the narrowest useful boundary.

At minimum, test:

- route matching and unknown routes;
- HTML escaping in titles, paths, and attributes;
- opaque ID lookup;
- duplicate ID rejection;
- path traversal and absolute-path rejection;
- missing media files;
- `GET` and `HEAD` metadata equivalence;
- full media response content;
- valid range response content and headers;
- unsatisfiable ranges;
- empty and one-byte files;
- manifest atomic publication fixtures;
- old snapshot behavior during replacement;
- absence of unauthorized affordances;
- complete-page behavior without JavaScript;
- frontend keyed identity if a DOM target is added.

Tests must not rely on a real NAS or a real multi-gigabyte media file. Use temporary directories and deterministic small fixtures.

## Performance requirements

The important performance metric is not a synthetic template benchmark alone. Measure the whole request path.

For library navigation:

- no directory walk;
- no child process;
- no media probe;
- no remote request;
- no complete media-file read;
- bounded memory proportional to the selected representation.

For direct playback:

- no complete-file buffering;
- no transcoder;
- no segment generation;
- bounded application memory;
- correct backpressure.

Record baseline RSS and CPU at idle, during library navigation, and during one direct-play stream. Keep benchmarks reproducible and distinguish process startup cost from steady-state request cost.

## Agent rules

The local coding agent must:

1. Inspect the current source and examples before choosing syntax or APIs.
2. Prefer the smallest compilable vertical slice over broad speculative abstractions.
3. Keep Koru/Orisha changes and project code easy to review separately.
4. Avoid adding dependencies unless the current language/runtime cannot reasonably provide the behavior.
5. Never add FFmpeg, HLS, transcoding, or a database merely because it is familiar media-server architecture. Offline ffprobe in a future indexer batch is allowed only outside Orisha handlers and only when explicitly scheduled as indexer work.
6. Preserve ordinary HTTP semantics and progressive enhancement.
7. Treat paths, IDs, escaping, ranges, and capabilities as security boundaries.
8. Add a fixture and a test with each new protocol behavior.
9. Document any mismatch between this goal and the current Koru/Orisha implementation.
10. Do not claim a feature works until it compiles and has a repeatable test or manual verification path.

## Definition of done for the first milestone

The first useful milestone is complete when a fresh checkout can:

1. build with the documented Koru toolchain;
2. start Orisha with a configured media root and manifest;
3. serve a full HTML library page;
4. navigate to an item page through links in that page;
5. request a supported media file through `/media/{id}`;
6. seek through that file using HTTP Range requests;
7. serve `HEAD` correctly;
8. reject path traversal;
9. operate without FFmpeg, HLS, a database server, or a remote metadata service;
10. run the test suite from a clean checkout.

After this milestone, frontend enhancement and richer indexing are optional iterations, not prerequisites for the system to be useful.

## Final architectural invariant

The system should remain understandable as:

```text
media roots
  -> explicit offline indexer
  -> immutable manifest snapshot
  -> Orisha route resolution
  -> hypermedia HTML / JSON
  -> native browser playback
```

Everything expensive, mutable, or compatibility-specific must be outside the direct path unless a future requirement proves it belongs there.
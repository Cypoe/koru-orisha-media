# Architecture

## Shape

The system has three planes:

1. **Indexer** — an explicit batch process that walks configured roots, reads file facts, optionally probes containers, and atomically publishes a manifest.
2. **Orisha request plane** — a small native HTTP process that loads a manifest snapshot, resolves routes, renders HTML or JSON, and streams original files.
3. **Browser plane** — ordinary HTML and native media elements, optionally enhanced by Koru's compiled DOM code for keyed updates and local player state.

The HTTP server must not scan media roots or invoke FFmpeg on a normal library request.

## Resource model

The primary resources are collections and media entries:

- `/library` — the root collection and navigation affordances.
- `/library/{kind}` — a collection projection with links for sorting, filtering, and pagination.
- `/media/{id}` — the original media byte resource.
- `/watch/{id}` — a player projection around the media resource.
- `/art/{id}` — an optional precomputed artwork resource.
- `/fragments/...` — partial representations for enhanced clients.

HTML is the default representation. JSON is optional and should describe the same resources and affordances rather than become a separate undocumented API.

## Hypermedia

Links and forms are the capability surface. A client should not need a hard-coded permission matrix to know whether an operation is available: an affordance is present only when the current principal may use it.

Use normal links for navigation and forms for state-changing actions. Use `Link` headers for relations that apply to the representation as a whole, such as a canonical resource, alternate representation, or related collection.

`OPTIONS` is reserved for protocol introspection and CORS/preflight-style cases. It is not the primary application discovery mechanism. A successful `OPTIONS` response may advertise supported methods and generic `Allow` metadata, but the representation remains authoritative for resource-specific affordances.

## Playback boundary

Playback is direct play:

- preserve the original file;
- support `GET` and `HEAD`;
- support byte ranges and `206 Partial Content`;
- use validators such as `ETag` and `Last-Modified`;
- never buffer a complete media file in application memory;
- do not start a transcoder because a browser cannot play one particular file.

The browser owns decoding. The application may provide a player shell, playlist, progress persistence, and track selection, but the `<video>` or `<audio>` element remains the decoding authority.

## Identity

Every indexed entry has a stable opaque ID. DOM identity, URLs, playback state, and server records should use that identity rather than parsing titles or paths out of markup. File paths are implementation details and must be validated before opening.

## Runtime lifecycle

The indexer is short-lived. Orisha may remain a very small native process or later be socket-activated and exit after an idle period. Active range streams hold a request lease and prevent idle shutdown until they finish.

## Koru integration

Koru components should be able to project the same structural view into two targets:

- HTML serialization on the server;
- compiled DOM operations in the browser.

The server-side surface should remain intentionally narrower than a general template language: typed values, escaped text and attributes, static structure, and explicit trusted-HTML escape hatches. The browser-side keyed component model should be used for local state and fine-grained updates, not as a reason to make the server a client-side application runtime.

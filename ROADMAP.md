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
- Record path, size, mtime, MIME, container, streams, and optional artwork references.
- Publish manifests atomically.
- Reload snapshots without invalidating in-flight requests.

## Phase 3: hypermedia interaction

- Add sort, filter, search, and pagination links.
- Add fragment representations for enhanced navigation.
- Add forms for any future mutating operations.
- Add `Link` headers and a minimal `OPTIONS` implementation.

## Phase 4: browser enhancement

- Keep complete-page navigation as the baseline.
- Add Koru-generated keyed updates where profiling demonstrates value.
- Keep the player element outside replaceable regions.
- Persist resume position locally before considering server-side state.

## Explicitly deferred

Transcoding, HLS/DASH, background metadata services, recommendation systems, remote media discovery, and a large client compatibility layer.

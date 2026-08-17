// media/graph — physical catalog (SQLite) + semantic overlay (not Orisha).
//
// One-stem companion: this file + graph.kz. Queries go through media/catalog
// (page-sized SQLite). JSON import remains a boot fallback. NFO overlay tables
// join on work/episode (`findNfoOverlay`). Graph store (`sem_*`) is the
// catalogue overlay; `findHydrateForAsset` joins nfo/graph assertions. No Koru-level
// events — consumers and dispatch call pub Zig (`findEntry`, `findSemantic`, …).
// Request handlers never call TMDB, TVDB, or ffmpeg. Missing semantic.json still
// lists physical files. Keys live in settings.conf; hydrate is `! hydrate`.
// KORU_BASE_PATH prefixes outbound URLs (also settable in Settings, persisted
// under /config/settings.conf). Settings persists library_roots with capability
// tags; Reindex touches reindex.requested so the accept pump's `! walk`
// arm walks on the next tick (does not wait for STREAM drain). Catalog DSN/driver is stored; only SQLite is linked.

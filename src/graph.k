// media/graph — physical catalog (SQLite) + semantic overlay (not Orisha).
//
// One-stem companion: this file + graph.kz. Queries go through media/catalog
// (page-sized SQLite). JSON import remains a boot fallback. NFO overlay tables
// join on work/episode (`findNfoOverlay`). Provider overlay `hydrate_works`
// joins on `[tt…]` (`findHydrateOverlay`). No Koru-level events — consumers
// and dispatch call pub Zig (`findEntry`, `findSemantic`, …). Request handlers
// never call TMDB, TVDB, or ffmpeg. Missing semantic.json still lists physical files.
// KORU_BASE_PATH prefixes outbound URLs (also settable in Settings, persisted
// under /config/settings.conf). Settings persists library_roots with capability
// tags; Reindex touches reindex.requested so maybeReindexFlag walks on the next
// idle request. Catalog DSN/driver is stored; only SQLite is linked.

// media/catalog — SQLite library index (not Orisha).
// One-stem companion of catalog.kz. Physical files only; handlers never call
// TMDB, TVDB, or ffmpeg. Overlay tables: nfo_works / nfo_episodes (disk nfo)
// and hydrate_works (offline TMDB/TVDB job, keyed by [tt…] imdb_id). Indexer
// fills nfo from sibling .nfo / tvshow.nfo; hydrate_works is host-side only.
// library_roots (Settings) chooses which folders under KORU_MEDIA_ROOT to walk.
// NAS indexer is this module's reindex, not host Python.

// media/catalog — SQLite library index (not Orisha).
// One-stem companion of catalog.kz. Physical files only; handlers never call
// TMDB, TVDB, or ffmpeg. Overlay tables: nfo_works / nfo_episodes (disk nfo)
// and sem_* (canonical graph). hydrate_works is a one-shot migrate source.
// The binary hydrate client (hydrate.kz) encodes provider JSON into the graph.
// library_roots (Settings) chooses which folders under KORU_MEDIA_ROOT to walk
// and tags each with capability/affordances. NAS indexer is this module's
// reindex, not host Python. Catalog file lives on the /data host bind.
// The walk skips DSM @eaDir/#recycle, stats DT_UNKNOWN via the dir fd, and
// ingests with open+fstat (not statx). AccessDenied on one folder does not
// abort the tree. `..` is rejected as a path component so `HEVC..AI` still indexes.

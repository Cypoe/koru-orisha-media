// media/graph — physical manifest + semantic core (not Orisha).
//
// One-stem companion: this file + graph.kz. Snapshot load is Zig in the
// companion (entries[] + projections[] scrape). No Koru-level events —
// consumers and dispatch call pub Zig (`findEntry`, `findSemantic`, …).
// Request handlers never call TMDB or ffmpeg. Missing semantic.json still
// lists physical files.

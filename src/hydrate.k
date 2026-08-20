// media/hydrate — encode catalogue JSON into the graph. Not on GET /library.
// Fixture path uses recorded JSON when `KORU_TMDB_FIXTURE` is set. Live HTTPS
// uses Cinemeta for `[tt…]` ids with no keys, then optional TMDB/TVDB Settings
// keys. One title per accept tick so HTTPS does not stall STREAM pumping.
// Wired as `! hydrate` on the HTTP accept pump via media:hydrate-catalog.

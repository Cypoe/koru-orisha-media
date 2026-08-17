// media/hydrate — encode catalogue JSON into the graph. Not on GET /library.
// Fixture path uses recorded JSON (same files Python tests use). Live HTTPS
// uses Cinemeta for `[tt…]` ids with no keys, then optional TMDB/TVDB Settings
// keys. Sequential HTTPS; one hydrate at a time. Wired as `! hydrate`
// on the HTTP accept pump via media:hydrate-catalog.

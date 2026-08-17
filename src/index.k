// koru-orisha-media — representation dispatch (not Orisha).
//
// Sibling stems under src/ (Koru directory modules, same as orisha/lib):
//   index.k / index.kz     this file — route table → representations
//   graph.k / graph.kz     physical catalog (SQLite) + semantic overlay
//   catalog.k / catalog.kz SQLite index + filesystem walker + graph store
//   consumers.k / consumers.kz  named constructions → HTML / JSON-LD / bytes
//   auth.k / auth.kz            principal + cookie session
//   hydrate.k / hydrate.kz      catalogue hydrate (pump `! hydrate`, not GET)
// Routes include /settings (mounts, base path, catalog store, Reindex flag).
// Handlers never call TMDB, TVDB, or ffmpeg. Reindex is catalog.kz via
// `media:reindex` on the HTTP pump's `! walk`. Hydrate is hydrate.kz via
// `media:hydrate` on `! hydrate`. Host capabilities (explain):
// browse, filter, play.video, play.audio, play.external, read.ebook, view.image.
// Zig companions implement the work; main.k wires http:handler → media:dispatch
// (Koru ignores http:handler if it lives only inside import media).
// Do not `import media/graph` or `import media/consumers` here — directory
// import already loads those stems; a second import duplicates koru_consumers.

// Not this module (compiled separately, not in bin/media-server):
//   src/frontend/          usage only (libs in vendor/koru-libs):
//                          host.k import koru/htmx → public/enhance.js
//                          main.k import koru/dom  → public/koru-dom-enhance.js
//   src/json/              usage of vendor/json (json-publish CLI; not in this binary)

pub tor dispatch { req: *Request } -> { status: u16, body: string, content_type: ?ContentType }

pub tor reindex {}
pub tor hydrate-catalog {}

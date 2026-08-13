// koru-orisha-media — representation dispatch (not Orisha).
//
// Sibling stems under src/ (Koru directory modules, same as orisha/lib):
//   index.k / index.kz     this file — route table → representations
//   graph.k / graph.kz     physical manifest + semantic core
//   consumers.k / consumers.kz  named constructions → HTML / JSON-LD / bytes
// Zig companions implement the work; main.k wires orisha:handler → media:dispatch
// (Koru ignores orisha:handler if it lives only inside import media).
// Do not `import media/graph` or `import media/consumers` here — directory
// import already loads those stems; a second import duplicates koru_consumers.

// Not this module (compiled separately, not in bin/media-server):
//   src/frontend/          usage only (libs in vendor/koru-libs):
//                          host.k import koru/htmx → public/enhance.js
//                          main.k import koru/dom  → public/koru-dom-enhance.js
//   src/json/              usage of vendor/json (json-publish CLI; not in this binary)

pub tor dispatch { req: *Request } -> { status: u16, body: string, content_type: ?ContentType }

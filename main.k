// koru-orisha-media — app entry (orisha/examples/*/main.k shape).
// Orisha is the HTTP pump; `media:dispatch` is representation dispatch
// (graph + named consumers → HTML / JSON-LD / bytes).
import orisha
import media

// Reconstruct the record: Koru emits distinct Zig Output types for handler vs dispatch.
orisha:handler =
    media:dispatch(req)
    | result r -> { status: r.status, body: r.body, content_type: r.content_type }

orisha:run-accept-loop(port: 3090)

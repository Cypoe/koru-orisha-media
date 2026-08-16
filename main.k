// koru-orisha-media — app entry (orisha/examples/*/main.k shape).
// HTTP runtime is vendor/http (Range, STREAM:v1, accept-loop). Orisha is
// vendored verbatim and not imported until pump:reply grows that spec.
import http
import media

// Reconstruct the record: Koru emits distinct Zig Output types for handler vs dispatch.
http:handler =
    media:dispatch(req)
    | result r -> { status: r.status, body: r.body, content_type: r.content_type }

http:run-accept-loop(port: 3090)

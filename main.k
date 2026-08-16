// koru-orisha-media — app entry (orisha/examples/*/main.k shape).
// HTTP runtime is vendor/http (Range, STREAM:v1, accept-loop). Orisha is
// vendored verbatim and not imported until pump:reply grows that spec.
import std/vendor
import http
import media

// Compile-time pin: vendor.lock next to this file.
// After git pull + snapshot of Orisha: `bash scripts/koruc.sh main.k vendor copy orisha`
// After editing vendor/http:          `bash scripts/koruc.sh main.k vendor sync`
std/vendor:bindings {
    orisha: ./vendor/orisha
    http: ./vendor/http
    koru: ./vendor/koru-libs
    json: ./vendor/json
}

// Reconstruct the record: Koru emits distinct Zig Output types for handler vs dispatch.
http:handler =
    media:dispatch(req)
    | result r -> { status: r.status, body: r.body, content_type: r.content_type }

http:run-accept-loop(port: 3090)

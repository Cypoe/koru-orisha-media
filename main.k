// koru-orisha-media — app entry (orisha/examples/*/main.k shape).
// HTTP runtime is vendor/http (Range, STREAM:v1, accept pump). Orisha is
// vendored verbatim and not imported until pump:reply grows that spec.
import std/io
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

http:handler = media:dispatch(req): r -> { status: r.status, body: r.body, content_type: r.content_type }

tor loop { server: *ServerHandle }
loop =
    http:accept(server)
    ! walk |> media:reindex()
    ! hydrate |> media:hydrate-catalog()
    | request r |> http:handler(r.req): res |> http:send(r.conn, res.status, res.body, res.content_type)
        | sent |> loop(r.server)
        | failed _ |> loop(r.server)
    | failed f |> loop(f.server)

http:listen(port: 3090)
| listening s |> loop(server: s)
| failed e |> std/io:print.ln(e)

// http — this app's HTTP / HATEOAS runtime (not Orisha).
//
// Request extras (Range, query, Prefer, Accept, If-None-Match, header()),
// STREAM:v1 + raw HTTP/1. send, and run-accept-loop + idle.
// Orisha stays vendored verbatim from W:\src\orisha\lib. Do not import orisha
// from main.k until pump:reply understands this spec (koruc still double-emits
// koru_pump on orisha:serve).

import std/io

pub tor listen { port: u16 }
| listening *ServerHandle
| failed string

pub tor accept { server: *ServerHandle }
| request { req: *Request, conn: *ConnHandle, server: *ServerHandle }
| failed { msg: string, server: *ServerHandle }

pub tor send { conn: *ConnHandle, status: u16, body: string, content_type: ?string }
| sent
| failed string

[abstract|retain]pub tor handler { req: *Request } -> { status: u16, body: string, content_type: ?ContentType }

handler -> { status: 404, body: "Not Found", content_type: null }

pub tor run-accept-loop { port: u16 }

tor accept-loop { server: *ServerHandle }
accept-loop =
    http:accept(server)
    | request r |> http:handler(r.req): res |> http:send(r.conn, res.status, res.body, res.content_type)
        | sent |> accept-loop(r.server)
        | failed _ |> accept-loop(r.server)
    | failed f |> accept-loop(f.server)

run-accept-loop =
    http:listen(port)
    | listening s |> accept-loop(server: s)
    | failed e |> std/io:print.ln(e)

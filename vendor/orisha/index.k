// Orisha — the contract.
//
// Everything Orisha declares lives here, and nothing in this file is Zig, so
// there is no parser to switch out of and not a single `~` anywhere. The Zig
// that implements it — the socket calls, the request parser, the router
// transform — sits in the companion `index.kz` beside this file. Same stem,
// same module: the compiler merges them.
//
// That split is the whole reason this file reads the way it does. These
// declarations used to live inside 1,056 lines of Zig, which forced a `~` onto
// every one of them; the character was never about the Koru, it was about the
// host language it was sharing a file with.
//
// Public API:
//   orisha:serve(port)              - Start server (calls abstract handler for each request)
//   orisha:handler                  - Abstract event users implement for request handling
//   orisha:router(req)              - Pattern-branch router transform
//   orisha:static(name, root, ...)  - Declare static files to embed at compile time
//   orisha:static-router(name)      - Transform: inline static file lookup + fallback
//
// Example (simplest server):
//   ~orisha:handler -> { status: 200, body: "Hello!", content_type: "text/plain" }
//   ~orisha:serve(port: 3001)
//
// Example (API + static):
//   ~orisha:handler = orisha:router(req)
//   ! [GET /api/health] -> { status: 200, body: "ok", content_type: "application/json" }
//   ! [*] |> orisha:static-router(name: "site")
//
// Example (pure static site):
//   ~import orisha
//   ~orisha:static(name: "site", root: "build", fallback: "200.html")
//   ~orisha:handler = orisha:static-router(name: "site")
//   ~orisha:serve(port: 3000)

import std/compiler
import std/io
import std/build

// ============================================================================
// LISTEN - Start listening on a port
// ============================================================================
// `*ServerHandle`, `*ConnHandle` and `*Request` are Zig types declared in the
// companion. A contract may NAME a host type it does not itself declare —
// what it may not do is contain host code.

pub tor listen { port: u16 }
| listening *ServerHandle
| failed string

// ============================================================================
// ACCEPT - Accept a connection and read the request
// ============================================================================

pub tor accept { server: *ServerHandle }
| request { req: *Request, conn: *ConnHandle, server: *ServerHandle }
| failed { msg: string, server: *ServerHandle }

// ============================================================================
// SEND - Send HTTP response and close connection
// ============================================================================

pub tor send { conn: *ConnHandle, status: u16, body: string, content_type: ?string }
| sent
| failed string

// ============================================================================
// HANDLER - Abstract event for request handling
// ============================================================================
// Users implement this to handle requests. Default returns 404.
//
// @retain: handler_event is referenced from the serve proc's raw Zig via
// $mod.handler_event.handler(...) — invisible to the dead-stripper.

[abstract|retain]pub tor handler { req: *Request } -> { status: u16, body: string, content_type: ?ContentType }

// Default 404 removed — koru-orisha-media provides ~proc handler|zig (library + media).

// ============================================================================
// SERVE — a Koru flow over a platform pump
// ============================================================================
// `serve` used to be two ~200-line Zig bodies, one per readiness mechanism,
// that differed in about twenty lines and duplicated everything else. The loop
// now lives in orisha/pump, one variant per platform; what remains here is the
// part that is the same everywhere, and it is a flow.
//
// Adding a platform is a `~proc run|<name>` in orisha/pump plus a line in the
// variants block. Nothing in this file changes.

// Upstream serve/pump omitted in this vendor (koruc companion double-emit).
// Apps use listen/accept/send via run-accept-loop instead — see main.k.

pub tor run-accept-loop { port: u16 }

tor accept-loop { server: *ServerHandle }
accept-loop =
    orisha:accept(server)
    | request r |> orisha:handler(r.req): res |> orisha:send(r.conn, res.status, res.body, res.content_type)
        | sent |> accept-loop(r.server)
        | failed _ |> accept-loop(r.server)
    | failed f |> accept-loop(f.server)

run-accept-loop =
    orisha:listen(port)
    | listening s |> accept-loop(server: s)
    | failed e |> std/io:print.ln(e)

// ============================================================================
// ANSWER — parse one request, run the handler, shape the response
// ============================================================================
// Platform-free by construction: it takes bytes and returns bytes, and never
// names a file descriptor. Every pump shares it. The body is in the companion.

pub tor answer { raw: string } -> { head: string, body: string }

// ============================================================================
// PLATFORM SELECTION
// ============================================================================
// Vendor shim: no multi-variant pump selection (see serve|zig in index.kz).

// ============================================================================
// ROUTER - Pattern-branch router transform
// ============================================================================
// Transforms pattern branches into dispatch logic.
//
// Usage:
//   ~orisha:handler = orisha:router(req)
//   ! [GET /] _ -> { status: 200, body: "Hello", content_type: "text/plain" }
//   ! [GET /users/:id] p -> { status: 200, body: p.id, content_type: "text/plain" }
//   ! [*] _ -> { status: 404, body: "Not Found", content_type: "text/plain" }

[comptime|transform]pub tor router {
    invocation: *const Invocation,
    item: *const Item,
    program: *const Program,
    allocator: std.mem.Allocator
} -> SiteResult

// ============================================================================
// STATIC - Declare files to embed at compile time
// ============================================================================
// Data-only event.
// - name: identifier for referencing via static-router
// - root: directory to embed (relative to the consuming file)
// - fallback: optional file for SPA fallback (relative to root, e.g. "200.html")

[comptime]pub tor static { name: string, root: string, fallback: ?string }

// ============================================================================
// STATIC ROUTER - Compile-time transform for static file dispatch
// ============================================================================
// Generates inline lookup code that:
//   1. Imports generated/<name>_routes.zig
//   2. Calls lookupWithEtag(method, path, if_none_match)
//   3. Returns pre-built response (or fallback, or 404)
//
// Works as top-level handler or nested in a router catch-all:
//   ~orisha:handler = orisha:static-router(name: "site")
//   ! [*] |> orisha:static-router(name: "site")

[comptime|transform]pub tor static-router {
    invocation: *const Invocation,
    item: *const Item,
    program: *const Program,
    allocator: std.mem.Allocator
} -> SiteResult

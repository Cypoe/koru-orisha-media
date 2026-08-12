# Current Koru / Orisha APIs

Recorded against local checkouts on 2026-08-12:

| Tree | Path |
|------|------|
| Koru | `W:\src\koru` |
| Orisha | `W:\src\orisha` |
| koru-libs | `W:\src\koru-libs` |

This note is the integration boundary for `koru-orisha-media`. Prefer these facts over design docs when they disagree.

## Toolchain

- **Zig:** 0.15.1+ (`build.zig.zon` `minimum_zig_version`).
  - Windows binary (not enough alone — `koruc` fails to build on Windows because `SIG.KILL` is missing): `W:\tools\zig-0.15.1\zig.exe`
  - WSL binary used for real builds: `$HOME/tools/zig-0.15.1/zig`
- **Build Koru compiler** (WSL; Zig cache must live on Linux FS, not `/mnt/w`):

  ```bash
  bash /mnt/w/tools/build-koruc.sh
  # → $HOME/src/koru-build/zig-out/bin/koruc (also copied to W:\src\koru\zig-out\bin\koruc)
  ```

- **Compile an app:**

  ```bash
  koruc src/main.k           # emit Zig + link → a.out (or platform binary)
  koruc run src/main.k       # compile and run
  koruc --check src/main.k   # syntax / frontend check
  ```

- **Language forms:** `.k` = pure Koru; `.kz` = Zig host with embedded Koru via `~`.
- **Imports:** slash paths (`import orisha`, `import std/io`). Project root `koru.json` maps aliases to directories.

### Working `koru.json` for this project

Compile from WSL. Absolute Linux mount paths:

```json
{
  "name": "koru-orisha-media",
  "version": "0.1.0",
  "paths": {
    "std": "/mnt/w/src/koru/koru_std",
    "orisha": "/mnt/w/src/orisha/lib",
    "koru": "/mnt/w/src/koru-libs"
  }
}
```

`scripts/build.sh` rsyncs the repo onto `$HOME/src/koru-orisha-media-build` (Linux FS) before invoking `koruc`, because Zig's local cache rename fails on DrvFs.

Orisha’s own map (`W:\src\orisha\koru.json`) uses relative siblings:

```json
"paths": {
  "std": "../koru/koru_std",
  "orisha": "lib",
  "koru": "../koru-libs"
}
```

Do **not** copy `W:\src\orisha\examples\hello\koru.json` as-is: it still points `orisha` at `../../src`, which is stale (library lives in `lib/`).

## Event / continuation model (Koru)

Apps are events with continuations, not a conventional `main` + callbacks stack:

```koru
import std/io

event greet { name: []const u8 } -> []const u8
greet -> "Hello, " ++ name ++ "!"
greet ("World"): msg |> std/io:print.ln(msg)
```

- Subflows implement behavior (`greet -> …`).
- Invocation chains with `: binding |> next(...)`.
- Effect branches use `!`; terminal branches use `|`.
- Host side effects use `~proc …|zig { … }` when needed.

## Orisha public contract

Source of truth: `W:\src\orisha\lib\index.k` (+ companion `index.kz`).

| API | Role |
|-----|------|
| `orisha:handler { req }` | Abstract per-request handler → `{ status: u16, body: string, content_type: ?ContentType }` |
| `orisha:router(req)` | Comptime transform; pattern branches `! [GET /…]`, `! [GET /x/:id] p`, `! [*]` |
| `orisha:static(name, root, fallback?)` | Declare compile-time embedded static tree |
| `orisha:static-router(name)` | Lookup embedded assets (standalone or router catch-all) |
| `orisha:serve(port)` | Server loop via `orisha/pump` |

### Response model (as of this checkout)

Handlers return only:

- `status`
- `body` (full string; buffered)
- optional `content_type`

`answer` (`index.kz`) writes `Content-Type`, `Content-Length`, `Date`, `Connection: keep-alive`. If `body` already starts with `"HTTP/1."`, it is sent as a pre-rendered head with empty body (static-router path).

`Request` fields currently exposed: `method`, `path` (query stripped, percent-decoded), `body`, `if_none_match`, `allocator`.

### Router syntax

```koru
orisha:handler = orisha:router(req)
! [GET /] -> { status: 200, body: "Hello", content_type: "text/plain" }
! [GET /item/:id] p -> { status: 200, body: p.id, content_type: "text/plain" }
! [*] -> { status: 404, body: "Not Found", content_type: "text/plain" }
```

- Branch labels are `"METHOD /path"` or `"*"`.
- `:param` segments bind fields on the params record (e.g. `p.id`).
- Must use `!` (effect). Terminal `|` on router arms is a compile error.

### Minimal mixed example (preferred template)

`W:\src\orisha\examples\mixed-server\main.k`:

```koru
import orisha
import std/io

orisha:static(name: "site", root: "public", fallback: "index.html")

orisha:handler = orisha:router(req)
! [GET /api/health] -> { status: 200, body: "{\"status\":\"ok\"}", content_type: "application/json" }
! [GET /api/info] -> { status: 200, body: "{\"server\":\"orisha\",\"version\":\"0.1.0\"}", content_type: "application/json" }
! [*] |> orisha:static-router(name: "site")

orisha:serve(port: 3000)
| shutdown s |> std/io:print.ln(s)
| failed f |> std/io:print.ln(f)
```

Build: `koruc main.k && ./a.out` (from that example directory).

Avoid `examples/hello` until updated: it still imports nonexistent `orisha/eshu`.

### Static files

- Embedded at compile time from `root` (max **10 MB per file**).
- Runtime: zero disk I/O; supports `If-None-Match` → `304` for static assets.
- Not suitable for large media libraries.

## Gaps vs GOAL.md media milestone

Upstream Orisha still lacks Range/HEAD/streaming. This project vendors `vendor/orisha-lib/` with a reviewable extension:

| GOAL need | Vendor status |
|-----------|----------------|
| `/media/{id}` runtime file streaming | `STREAM:v1` body → `send\|zig` writes headers then 64 KiB file chunks |
| `HEAD` | Pre-rendered HTTP/1.1 response with headers only |
| `Accept-Ranges` / `206` / `416` | Parsed `req.range` + single `bytes=` range |
| `Last-Modified` | From manifest `modified_ns` when present |
| Path traversal | Reject `..` / absolute; require path under `KORU_MEDIA_ROOT` |
| Config | `KORU_MEDIA_ROOT`, `KORU_MANIFEST` env (defaults: `fixtures/media`, `data/manifest.json`) |
| Upstream `orisha:serve` / pump | Omitted (koruc companion double-emit); use `orisha:run-accept-loop` |

Prefer contributing Range/streaming upstream; keep vendor diffs documented in [vendor/README.md](../vendor/README.md).

## koru-libs relevance

- **`koru/dom`** (`W:\src\koru-libs\dom`): JS-target keyed DOM (`component`, `run`, `drop`). For GOAL Step 9 only — not the first milestone.
- **`yyjson`**: candidate for manifest JSON parse/emit if hand-rolled parsing is insufficient.
- No server-side HTML view package yet; first milestone renders HTML as strings from Orisha handlers.

## Tests

- **Koru:** `W:\src\koru\run_regression.sh` (bash; Git Bash/WSL). Orisha router pins under `tests/regression/.../350_*_orisha_*`.
- **Orisha:** thin; `koruc --check`, example binaries, `tests/router_test.kz` notes `koruc … && zig test output_emitted.zig`.
- **This project:** `bash scripts/test_all.sh` (indexer + range units + Docker HTTP). Build: `bash scripts/build-docker.sh`.

## Build platforms

Prefer Docker (`scripts/build-docker.sh`) or WSL Linux FS for `koruc`. Native Windows hosting is not the primary path.

## Milestone note

Steps 1–8 hardened + hypermedia. Step 9: `public/enhance.js` (resume + fragment) and optional koru/dom keyed list (`browser/` → `koru-dom-enhance.js`, `/enhance-demo.html`). Step 10: `scripts/bench_baseline.sh`, `KORU_IDLE_SECS`, [docs/lifecycle.md](lifecycle.md). Follow-on: `container`/`poster` in manifest, `/art/{id}`, pagination (`limit`/`offset`), `Prefer: return=minimal`.

**JS emit note:** `koruc --lang=js` **does emit JS correctly**. Put `--lang=js` before the input (`koruc --lang=js main.k`) and keep Zig 0.15.1 on `PATH`. A bare `FileNotFound` during “Building executable…” means Zig was missing from `PATH` — the JS backend never ran, so no `output_emitted.js` was written. That is an environment miss, not a broken emitter.

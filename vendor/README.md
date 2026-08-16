# Vendored libraries

## Orisha vs this app's HTTP spec

| Tree | Role |
|------|------|
| [`orisha/`](orisha/) | **Verbatim** `W:\src\orisha\lib` (`521a4d7` at last vendor). Refresh: `bash scripts/vendor-orisha.sh`. |
| [`http/`](http/) | **Ours.** Request extras, `STREAM:v1` send, `run-accept-loop`, idle/`streamsBusy()`. |
| [`koru-libs/`](koru-libs/) | `koru/dom` + `koru/htmx` |
| [`json/`](json/) | Tiny JSON parse/emit |

`main.k` imports **`http`**, not `orisha`. Do not `import orisha` until `orisha:serve` / `pump:reply` understand STREAM + Range **and** koruc stops double-emitting `koru_pump`. See [http/README.md](http/README.md) and [docs/upstream-pump-emit.md](../docs/upstream-pump-emit.md).

```text
import http
import media
http:handler → media:dispatch
http:run-accept-loop(port: 3090)
```

STREAM **producer** (path/MIME policy) stays in `src/consumers.kz`. This `http` module only **consumes** `STREAM:v1`.

## Why not patch vendor/orisha?

A fork of `index.kz` made every upstream pull a merge. The HTTP spec this binary needs is small and stable; Orisha's pump/router/static keep moving. Splitting them means `vendor-orisha.sh` can copy `lib/` blindly.

When Lars's pump grows Range + STREAM on `reply`, delete `vendor/http`'s listen/accept/send and switch the entry to `orisha:serve`.

## Koru constraints (still true)

- `http:handler` (like `orisha:handler`) must be implemented in the **entry**. A handler that lives only inside `import media` is ignored.
- Immediate `http:handler -> media:dispatch(req)` emits invalid Zig. Use a flow (`=`) plus a named result arm.
- `media:dispatch` and `http:handler` get distinct Zig `Output` structs; the entry reconstructs `{ status, body, content_type }`.

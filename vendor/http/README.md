# HTTP / HATEOAS spec (this app)

This directory is **ours**, not a fork of Orisha.

It is the complete HTTP surface the media binary needs:

| Piece | Why it is here |
|-------|----------------|
| `Request` + `header()` | RFC fields: `range`, `query`, `prefer`, `accept`, `if_none_match`, raw `headers` |
| `parseHttpRequest` | Shared by `accept` |
| `STREAM:v1` + raw `HTTP/1.` in `send` | Bounded file send; handler bodies may already be full HTTP messages |
| `run-accept-loop` + `streamsBusy()` | Zig serve path + idle exit (`KORU_IDLE_SECS`). STREAM parks on WouldBlock; accept polls listen + stream fds. |

**Producer** of `STREAM:v1` stays in `src/consumers.kz` (`mediaHttp`). This module only **consumes** it.

## Orisha is separate

[`vendor/orisha/`](../orisha/) is a verbatim snapshot of upstream `lib/` after `git pull`. Refresh it with:

```bash
bash scripts/vendor-orisha.sh
```

Do **not** `import orisha` from `main.k` until `orisha:serve` / `pump:reply` grow this spec **and** koruc stops double-emitting `koru_pump`. Until then the entry is:

```text
import http
import media
http:handler → media:dispatch
http:run-accept-loop(port: 3090)
```

When that lands, delete this module's listen/accept/send loop and keep only the STREAM producer in `src/`. Until then, concurrency is this loop's poll of listen + parked STREAM sockets — not `orisha/pump`.

# Lifecycle and performance (GOAL Step 10)

## Measured today

```bash
bash scripts/bench_baseline.sh
```

Records:

- process start → first `/library` 200 (cold)
- steady-state `/library` and `/media/{id}` latency
- container RSS sample via `docker stats`

Reproduce on the same Docker mount layout as README.

## Idle exit

Set `KORU_IDLE_SECS` (e.g. `300`). The accept loop polls the listen socket; if the timeout elapses with **zero** in-flight media streams (`STREAM:v1`), the process exits 0. Covered by `scripts/test_idle.sh`.

Active Range/GET body sends hold a stream counter so idle exit does not cut off playback.

## Not yet (deferred optimizations)

| Item | Why deferred |
|------|----------------|
| `sendfile` / `mmap` | Chunked 64 KiB `read`/`write` is enough for personal libraries; sendfile needs more Orisha pump work |
| Socket activation (systemd) | Requires supervisor integration outside this binary |
| Compact binary manifest | JSON scrape is fine at current fixture scale |

## Hot manifest reload

On each request (and before library scans), if the manifest file mtime changed and **zero** media streams are active, the process loads a new immutable snapshot. In-flight streams keep the paths they already opened. Covered by `scripts/test_reload.sh`.

## Invariants to keep

- Library requests: no directory walk, no probe, no full media read
- Media requests: no full-file buffer; chunked send only
- No FFmpeg / HLS / DB

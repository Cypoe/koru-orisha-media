# Koru/Orisha Media

A small, direct-play media library built around Koru and Orisha.

- precomputed media metadata (offline indexer)
- server-rendered HTML library / item / watch pages + library fragments
- HTTP Range delivery of original files (`GET` / `HEAD` / `206` / `416`) with chunked send
- no FFmpeg, HLS, database, or remote metadata

## Status

GOAL Steps 1–10 plus follow-ons (indexer/art/pagination/Prefer, hot reload, capability, download). Phase 6: search form, year, 304, and [docs/upstream-candidates.md](docs/upstream-candidates.md).

## Build (Docker)

```bash
bash scripts/build-docker.sh
# → bin/media-server
```

Requires a prebuilt `koruc` at `$HOME/src/koru-build/zig-out/bin/koruc` (see [docs/current-apis.md](docs/current-apis.md)). Zig 0.15.1 must be on `PATH` for both the media binary and the optional JS browser lane.

## Index

```bash
python3 scripts/index_media.py --root fixtures/media --out data/manifest.json
```

## Test

```bash
bash scripts/test_all.sh
bash scripts/bench_baseline.sh   # Step 10 baselines
```

## Browser enhancement (Step 9)

- Shipped for media UI: [`public/enhance.js`](public/enhance.js) — localStorage resume on `#player`, fragment swap for `data-enhance=fragment` (player never in a replaceable region).
- Optional koru/dom keyed list: [`browser/main.k`](browser/main.k) + [`browser/main.kjs`](browser/main.kjs) → `bash scripts/build-browser.sh` → [`public/koru-dom-enhance.js`](public/koru-dom-enhance.js). Demo: `/enhance-demo.html`. Asserted by `scripts/test_keyed_list.mjs` (insert / remove / reorder + stable `__koru_key`).

`koruc --lang=js` emits JS correctly when Zig is on `PATH` and options precede the input (`koruc --lang=js main.k`). A bare `FileNotFound` during “Building executable…” usually means Zig was missing from `PATH`, not a failed JS emitter.

No-JS clients keep full-page navigation.

## Run

```bash
docker run --rm -p 3090:3090 \
  -e KORU_MEDIA_ROOT=fixtures/media \
  -e KORU_MANIFEST=data/manifest.json \
  -e KORU_IDLE_SECS=300 \
  -v "$PWD/bin/media-server:/app/media-server:ro" \
  -v "$PWD/data:/app/data:ro" \
  -v "$PWD/fixtures:/app/fixtures:ro" \
  -v "$PWD/public:/app/public:ro" \
  -w /app debian:bookworm-slim /app/media-server
```

On Windows/WSL, mount from `/mnt/c/Users/.../koru-orisha-media`. Env vars override compile-time defaults (`fixtures/media`, `data/manifest.json`).

Open `http://127.0.0.1:3090/library`.

## Layout

| Path | Role |
|------|------|
| `main.k` | starts `orisha:run-accept-loop` |
| `vendor/orisha-lib/` | Orisha fork: accept-loop, Range, chunked `STREAM:v1`, media `handler` |
| `scripts/index_media.py` | one-shot indexer |
| `data/manifest.json` | published snapshot |
| `fixtures/media/` | tiny media files for tests |

See [ARCHITECTURE.md](ARCHITECTURE.md), [docs/protocol.md](docs/protocol.md), [docs/manifest.md](docs/manifest.md), [vendor/README.md](vendor/README.md).

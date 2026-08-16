# Koru/Orisha Media

A small, direct-play media library built around Koru and Orisha.

- precomputed media metadata (offline indexer)
- server-rendered HTML library / item / play pages + library fragments
- HTTP Range delivery of original files (`GET` / `HEAD` / `206` / `416`) with chunked send
- no FFmpeg, HLS, database, or remote metadata

## Status

GOAL Steps 1–10 plus follow-ons (indexer/art/pagination/Prefer, hot reload, capability, download). Phase 6 done (search/year/304 + upstream map). Phase 7: app (`src/`) vs Orisha vendor split. On Windows/WSL, see [docs/dev-windows.md](docs/dev-windows.md) (native git for push/pull; WSL for bash/Docker scripts).

## Build (Docker)

```bash
bash scripts/build-docker.sh
# → bin/media-server
```

Requires a prebuilt `koruc` at `$HOME/src/koru-build/zig-out/bin/koruc` (see [docs/current-apis.md](docs/current-apis.md)). Zig 0.15.1 must be on `PATH` for both the media binary and the optional JS frontend emit.

## Index

The NAS indexer is the Koru binary (`catalog.kz` `reindex`). Empty catalog or `KORU_REINDEX=1` walks enabled folders under `KORU_MEDIA_ROOT`. Settings → Reindex (or `bash scripts/nas-index.sh`) touches `reindex.requested`; the HTTP pump's `! walk` arm walks when no STREAM is parked. Python is not required on the NAS.

```bash
# optional JSON fixture for CI / fallback import when the SQLite catalog is empty:
python3 scripts/index_media.py --root fixtures/media --out data/manifest.json
python3 scripts/json_publish.py --out /tmp/json-publish-fixture.json
```

Optional catalogue overlay (binary TMDB/TVDB into the graph via Settings keys; Python is CI/fixture only; never in request handlers; not the indexer):

```bash
python3 scripts/hydrate_catalog.py --catalog data/catalog.sqlite
```

## Test

```bash
bash scripts/test_all.sh
bash scripts/bench_baseline.sh   # Step 10 baselines
```

## Frontend (Step 9)

The backend shim (`src/index.k` dispatch, `src/graph.kz`, `src/consumers.kz`) dispatches complete HTML (and JSON-LD / bytes). The frontend *receives* those representations.

- Navigation host: [`vendor/koru-libs/htmx/`](vendor/koru-libs/htmx/) (`import koru/htmx`) consumed by [`src/frontend/host.k`](src/frontend/host.k) + [`host.kjs`](src/frontend/host.kjs) → `bash scripts/build-frontend.sh` → [`public/enhance.js`](public/enhance.js) (`GET /enhance.js`). Usage boots the generic `hx-*` / `HX-Request` host with `#library-region` + `protect: "#persist"`, pops the floating persist player, and keeps `#player` localStorage resume. Host *logic* is still a `|js` escape (Koru does not lower fetch/swap yet); entry/boot is Koru.
- Optional koru/dom keyed list: [`vendor/koru-libs/dom/`](vendor/koru-libs/dom/) (`import koru/dom`) consumed by [`src/frontend/main.k`](src/frontend/main.k) + [`main.kjs`](src/frontend/main.kjs) → [`public/koru-dom-enhance.js`](public/koru-dom-enhance.js). Demo: `/enhance-demo.html`. This emit is real Koru IR.

`koruc --lang=js` emits JS correctly when Zig is on `PATH` and options precede the input (`koruc --lang=js main.k`). A bare `FileNotFound` during “Building executable…” usually means Zig was missing from `PATH`, not a failed JS emitter.

See [docs/upstream-candidates.md](docs/upstream-candidates.md) for the vaxis → koru/dom → HTMX extraction story.

## Run (Compose)

```bash
bash scripts/build-image.sh          # compile + docker build → koru-orisha-media:local
# bash scripts/build-image.sh --skip-compile   # if bin/media-server is already current

mkdir -p media/movies media/shows media/music data
# put library files in ./media/movies, ./media/shows, ./media/music
# empty catalog walks /media on boot (or set KORU_REINDEX=1)

docker compose up
```

Open `http://127.0.0.1:3090/library`. Env defaults: `KORU_MEDIA_ROOT=/media`, `KORU_CATALOG=/data/catalog.sqlite`. See [docs/packaging.md](docs/packaging.md) for the NAS registry (`sigmanas.local:9500` + `publish-registry.sh`), Container Manager pull, WebStation `KORU_BASE_PATH`, and SPK prep.

### Dev bind-mount (fixtures)

```bash
docker run --rm -p 3090:3090 \
  -e KORU_MEDIA_ROOT=fixtures/media \
  -e KORU_MANIFEST=fixtures/manifest.json \
  -e KORU_IDLE_SECS=300 \
  -v "$PWD/bin/media-server:/app/media-server:ro" \
  -v "$PWD/data:/app/data:ro" \
  -v "$PWD/fixtures:/app/fixtures:ro" \
  -v "$PWD/public:/app/public:ro" \
  -w /app debian:bookworm-slim /app/media-server
```

On Windows/WSL, mount from `/mnt/c/Users/.../koru-orisha-media`.

## Layout

One production app (not a browser app + a media app + a json-publish app). Mapping to Koru/Orisha examples is in [vendor/README.md](vendor/README.md).

| Path | Role |
|------|------|
| `main.k` | entry: `http:handler` → `media:dispatch`, then `http:run-accept-loop` |
| `src/index.k` + `index.kz` | representation dispatch (`media:dispatch`) |
| `src/graph.kz` | graph load (SQLite catalog + semantic overlay) |
| `src/catalog.kz` | SQLite index + filesystem walker |
| `src/consumers.kz` | named constructions → HTML / JSON-LD / bytes |
| `src/frontend/` | usage only: `host.k` (`import koru/htmx`) → `public/enhance.js`; `main.k` (`import koru/dom`) → `public/koru-dom-enhance.js` |
| `vendor/koru-libs/` | `dom/` (vendored `koru/dom` stem) + `htmx/` (our navigation host lib) |
| `src/json/` | usage: json-publish CLI (`import json`) |
| `vendor/json/` | tiny JSON parse + emit (not `koru/yyjson`; not in the HTTP binary) |
| `vendor/http/` | HTTP spec: accept-loop, Range, `STREAM:v1` consumer, `header()` |
| `vendor/orisha/` | verbatim upstream `lib/` snapshot (not imported until pump:reply grows STREAM) |
| `public/` | generated frontend output (`enhance.js`, `koru-dom-enhance.js`, CSS, demo HTML) |
| `scripts/index_media.py` | optional JSON fixture / CI fallback (not the NAS indexer) |
| `scripts/hydrate_catalog.py` | CI/fixture TMDB/TVDB → `sem_*` graph (not in the image; not the indexer) |
| `Dockerfile` / `compose.yaml` | local runtime image + compose (see [docs/packaging.md](docs/packaging.md)) |
| `fixtures/media/` | CI library: `movies/`, `music/` (`shows/` when a TV fixture exists) |
| `fixtures/manifest.json` | CI physical snapshot |
| `fixtures/semantic.json` | CI semantic snapshot |
| `data/` | local runtime volumes (gitignored; compose `./data`) |

See [ARCHITECTURE.md](ARCHITECTURE.md), [docs/protocol.md](docs/protocol.md), [docs/manifest.md](docs/manifest.md), [vendor/README.md](vendor/README.md).

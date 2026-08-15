# Packaging (Docker / Synology)

Local-first runtime image and compose project. The published image does **not** include `koruc`; compile the Linux binary first, then pack it.

## Local build and run

```bash
# Compile bin/media-server + emit public/*.js (needs koruc mounts — see
# scripts/build-docker.sh), then build image koru-orisha-media:local
bash scripts/build-image.sh

# Or, if bin/media-server and public/*.js are already current:
bash scripts/build-image.sh --skip-compile
```

Prepare a library. An empty catalog walks enabled folders under `/media` on boot (Settings library mounts; defaults `movies`, `shows`, `music`, `books`, `musicVideos`). JSON import is only a fallback when the SQLite file has no rows.

```bash
mkdir -p media/movies media/shows media/music data
# copy or bind your library into ./media/{movies,shows,music}
# or force a walk: KORU_REINDEX=1 in compose.yaml
```

Start:

```bash
docker compose up
# → http://127.0.0.1:3090/library
```

Container layout:

| Path | Role |
|------|------|
| `/app/media-server` | HTTP binary |
| `/app/public/` | frontend assets |
| `/media` | `KORU_MEDIA_ROOT` (local: one bind of a parent that contains `movies/`, `shows/`, `music/`) |
| `/media/movies` `/media/shows` `/media/music` | NAS: three DSM share binds (see [`compose.nas.yaml`](../compose.nas.yaml)) |
| `/data/catalog.sqlite` | `KORU_CATALOG` (volume; page-sized reads, no 4096 cap) |
| `/data/manifest.json` | `KORU_MANIFEST` (optional JSON import if the catalog is empty) |
| `/data/semantic.json` | `KORU_SEMANTIC` (optional; browse and play work if absent) |
| `/config` | NAS: logs (`KORU_LOG=/config/orisha.log`); local compose may omit this |

Compose defaults are long-lived (no `KORU_IDLE_SECS`). The process listens on **3090** inside the container ([`main.k`](../main.k)); map the host port in `compose.yaml`.

Empty catalog (or `KORU_REINDEX=1`) walks enabled library mounts under `/media` inside the binary. Configure mounts and Reindex at `/settings` (prefix-aware: `/korisha/settings`). `semantic.json` is not required for browse or play. `KORU_BASE_PATH` (live alias `/korisha`) prefixes every app URL so a Synology WebStation alias does not collide with `GET /media/{id}`. Any alias works **except** `/media` (same name as the byte route).

The runtime still uses `orisha:run-accept-loop` (not `orisha:serve`). One `STREAM` (a movie) occupies the accept loop until it finishes — other tabs wait. That is independent of packaging; do not switch to pump/`serve` until koruc stops double-emitting `koru_pump`.

## NAS registry (`/volume1/docker/registry`, port 9500)

The registry is its **own** compose project under `/volume1/docker/registry`. This repo does not start it. Container Manager is registered for `sigmanas.local:9500`; NAS dockerd lists `127.0.0.1:9500` as insecure (`sigmanas.local` → `127.0.0.1`). The build machine pushes as `sigmanas:9500` (same catalog, different hostname).

```bash
bash scripts/build-image.sh
bash scripts/publish-registry.sh
# → docker push sigmanas:9500/koru-orisha-media:latest
```

Then copy [`compose.nas.yaml`](../compose.nas.yaml) onto the NAS and create/recreate the Container Manager project. `image:` is `sigmanas.local:9500/koru-orisha-media:latest` with `pull_policy: always`. No CM image import, no tarball on the NAS.

Watchtower stays commented until automatic deploy/restart.

Reindex on the NAS: Settings → **Reindex**, or `bash nas-index.sh` (both touch `data/reindex.requested`; the next idle request walks enabled folders under `/media`). That walker is the Koru binary, not host Python. Or delete `catalog.sqlite` and restart.

Optional TMDB/TVDB posters and actors: host-side [`scripts/hydrate_catalog.py`](../scripts/hydrate_catalog.py) writes `hydrate_works` (keyed by `[tt…]` already in `entries.imdb_id`). Overlay only — not the indexer. The server only reads that table. Keys stay in gitignored `.env` on the machine that runs the script — never in the runtime image or compose. Absent keys → exit 0 skip. `KORU_HYDRATE=1` on the binary only logs that overlay tables exist; `docker exec … hydrate` exits 0 with the host command.

WebStation: set `KORU_BASE_PATH=/korisha` (or any alias **except** `/media`) so HTML `href`/`src` stay under the alias. Player `src` is `/korisha/media/{id}`, not DSM `/media/...`.

## Docker CLI over SSH (no `docker` group)

DSM does not ship a `docker` group. The socket is `root:root` `660`, so `cypoe` in `administrators` still gets permission denied. Do **not** create a fake `docker` group — Container Manager resets the socket on package start.

**Control Panel → Task Scheduler → Create → Triggered Task → User-defined script**

- User: **root**
- Event: **Boot-up**
- Also create a **scheduled** copy every 5 minutes (CM recreates the socket as `root:root` when the package restarts)

Script:

```bash
chown root:administrators /var/run/docker.sock
chmod 660 /var/run/docker.sock
```

Then `ssh cypoe@sigmanas /usr/local/bin/docker ps` works. You already run Portainer; its logs are the other way to see why a container exits.

Do not set `KORU_IDLE_SECS` on the NAS. `semantic.json` is an optional overlay (`scripts/project_semantic.py`).

## Synology Container Manager

1. Registry project already running at `/volume1/docker/registry:9500`. CM registry: `sigmanas.local:9500`. dockerd insecure: `127.0.0.1:9500`.
2. From the build machine: `bash scripts/build-image.sh && bash scripts/publish-registry.sh`.
3. Copy [`compose.nas.yaml`](../compose.nas.yaml) to `/volume1/docker/koru-orisha-media/` and create the project. CM pulls `sigmanas.local:9500/koru-orisha-media:latest`.
4. Bind library shares onto `/media/movies`, `/media/shows`, `/media/music`, `/media/books`, `/media/musicVideos`.
5. Map `…/koru-orisha-media/config` → `/config` and `…/data` → `/data`. `PUID`/`PGID` `1026`/`100` on SigmaNAS.
6. Publish port `3090`. Empty catalog walks enabled `/media` folders on boot. WebStation alias: `KORU_BASE_PATH=/korisha` (not `/media`). Settings: `http://sigmanas/korisha/settings`.

Updates: `publish-registry.sh` again, then recreate the project (`pull_policy: always`). Optional Watchtower later.

Reindex: Settings → Reindex, or `bash /volume1/docker/koru-orisha-media/nas-index.sh` (binary walk; not Python).

Optional overlay hydrate (host Python, not the Alpine image): `bash scripts/nas-hydrate.sh` or `python3 scripts/hydrate_catalog.py --catalog /volume1/docker/koru-orisha-media/data/catalog.sqlite`. No-ops when TMDB/TVDB keys are absent. Do not put keys in compose. `docker exec … hydrate` is a documented no-op.

GHCR remains an optional later remote; the NAS path above does not need it.

## Publish later (GHCR) — optional remote

You already have GitHub (`Cypoe/koru-orisha-media`). GitHub Container Registry needs no separate signup beyond GitHub.

1. GitHub → **Settings → Developer settings → Personal access tokens**  
   Create a token (classic) with `write:packages` (and `read:packages`).  
   Or use a fine-grained token with Packages write on the repo/org.
2. Login and push:

```bash
echo YOUR_PAT | docker login ghcr.io -u Cypoe --password-stdin
docker tag koru-orisha-media:local ghcr.io/cypoe/koru-orisha-media:0.1.0
docker tag koru-orisha-media:local ghcr.io/cypoe/koru-orisha-media:latest
docker push ghcr.io/cypoe/koru-orisha-media:0.1.0
docker push ghcr.io/cypoe/koru-orisha-media:latest
```

3. On the package page (github.com/Cypoe?tab=packages), set visibility (private/public) and link it to the repo if prompted.

Optional later: a GitHub Actions workflow on tag push that runs (or downloads) a Linux build and `docker push`es version tags. Not wired in this repo yet.

Then point Synology compose `image:` at `ghcr.io/cypoe/koru-orisha-media:0.1.0` and drop `build:`.

## Publish later (Docker Hub) — alternative

1. Create an account at [https://hub.docker.com](https://hub.docker.com).
2. `docker login` (username/password or access token from Account Settings → Security).
3. Tag/push, e.g. `docker.io/cypoe/koru-orisha-media:0.1.0`.

GHCR is preferred here because it stays next to the existing GitHub repo.

## SynoCommunity SPK

Package Center packaging is a **follow-up**. See [synology-spk.md](synology-spk.md) and the stubs under [`spk/koru-orisha-media/`](../spk/koru-orisha-media/). Prerequisite for a real SPK: published image tags (GHCR) so DSM can pull on install/upgrade.

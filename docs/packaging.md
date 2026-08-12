# Packaging (Docker / Synology)

Local-first runtime image and compose project. The published image does **not** include `koruc`; compile the Linux binary first, then pack it.

## Local build and run

```bash
# Compile bin/media-server (needs koruc mounts — see scripts/build-docker.sh),
# then build image koru-orisha-media:local
bash scripts/build-image.sh

# Or, if bin/media-server is already a current Linux binary:
bash scripts/build-image.sh --skip-compile
```

Prepare a library and manifest:

```bash
mkdir -p media data
# copy or bind your library into ./media
python3 scripts/index_media.py --root media --out data/manifest.json
# or let the container index once: KORU_REINDEX=1 in compose.yaml
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
| `/app/public/` | browser assets |
| `/media` | `KORU_MEDIA_ROOT` (volume) |
| `/data/manifest.json` | `KORU_MANIFEST` (volume) |

Compose defaults are long-lived (no `KORU_IDLE_SECS`). The process listens on **3090** inside the container ([`main.k`](../main.k)); map the host port in `compose.yaml`.

Optional one-shot reindex on start: set `KORU_REINDEX=1` or pass `reindex` as the container command.

## Synology Container Manager

1. Build (or later pull) the image on a machine that can compile, or load a saved image onto the NAS.
2. In **Container Manager → Project**, create a project from this repo’s [`compose.yaml`](../compose.yaml).
3. Map a DSM shared folder (e.g. `/volume1/video`) to `/media` (read-only is fine).
4. Map a writable folder to `/data` for `manifest.json` (and future art/cache).
5. Publish port `3090` (or change the host side of the mapping).
6. Index once (`KORU_REINDEX=1` for the first start, or run the indexer on a desktop against the same tree).

Updates while local-only: rebuild with `scripts/build-image.sh`, then recreate the project/container. After you publish to a registry, change `image:` to a tagged remote and use Container Manager’s update / `docker compose pull`.

## Publish later (GHCR) — recommended

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

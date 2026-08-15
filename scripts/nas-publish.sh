#!/usr/bin/env bash
# Optional NAS-side path: load a tarball and push into the live registry.
# Prefer scripts/publish-registry.sh from the build machine (no tar).
#
# Live registry is /volume1/docker/registry on :9500 — this script does not
# start or replace that compose project.
set -euo pipefail

TAR="${1:?usage: nas-publish.sh <image.tar.gz>}"
LOCAL_IMAGE="${LOCAL_IMAGE:-koru-orisha-media:local}"
REMOTE_IMAGE="${REMOTE_IMAGE:-}"

if [[ ! -f "$TAR" ]]; then
  echo "error: tarball not found: $TAR" >&2
  exit 1
fi

pick_remote() {
  if [[ -n "$REMOTE_IMAGE" ]]; then
    return
  fi
  local host
  for host in sigmanas.local:9500 127.0.0.1:9500 sigmanas:9500; do
    if curl -fsS --max-time 2 "http://${host}/v2/" >/dev/null 2>&1; then
      REMOTE_IMAGE="${host}/koru-orisha-media:latest"
      return
    fi
  done
  echo "error: no registry answering on :9500 (tried sigmanas.local, 127.0.0.1, sigmanas)" >&2
  exit 1
}

pick_remote

echo "loading $TAR"
if [[ "$TAR" == *.gz ]]; then
  gzip -dc "$TAR" | docker load
else
  docker load -i "$TAR"
fi

if ! docker image inspect "$LOCAL_IMAGE" >/dev/null 2>&1; then
  echo "error: $LOCAL_IMAGE missing after docker load" >&2
  exit 1
fi

echo "tagging $LOCAL_IMAGE → $REMOTE_IMAGE"
docker tag "$LOCAL_IMAGE" "$REMOTE_IMAGE"
echo "pushing $REMOTE_IMAGE"
docker push "$REMOTE_IMAGE"
echo "OK — $REMOTE_IMAGE is in the local registry"
echo "recreate the media project so it pulls sigmanas.local:9500/koru-orisha-media:latest"

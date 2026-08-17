#!/usr/bin/env bash
# Tag and push koru-orisha-media to GitHub Container Registry.
#
#   VERSION=0.1.0 bash scripts/publish-ghcr.sh
#   bash scripts/publish-ghcr.sh 0.1.0
#
# Requires: docker login ghcr.io (see docs/releasing.md).
set -euo pipefail

VERSION="${1:-${VERSION:-}}"
LOCAL_IMAGE="${LOCAL_IMAGE:-koru-orisha-media:local}"
GHCR_IMAGE="${GHCR_IMAGE:-ghcr.io/cypoe/koru-orisha-media}"
DOCKER_CFG="${DOCKER_CONFIG:-$HOME/.docker}/config.json"

if [[ -z "$VERSION" ]]; then
  echo "usage: bash scripts/publish-ghcr.sh <VERSION>" >&2
  echo "   or: VERSION=0.1.0 bash scripts/publish-ghcr.sh" >&2
  exit 2
fi

if ! docker image inspect "$LOCAL_IMAGE" >/dev/null 2>&1; then
  echo "error: $LOCAL_IMAGE missing — run bash scripts/build-image.sh first" >&2
  exit 1
fi

if [[ ! -f "$DOCKER_CFG" ]] || ! grep -q 'ghcr.io' "$DOCKER_CFG" 2>/dev/null; then
  echo "error: not logged in to ghcr.io — run:" >&2
  echo "  echo YOUR_PAT | docker login ghcr.io -u Cypoe --password-stdin" >&2
  echo "see docs/releasing.md" >&2
  exit 1
fi

for tag in "$VERSION" latest; do
  remote="${GHCR_IMAGE}:${tag}"
  echo "tagging $LOCAL_IMAGE → $remote"
  docker tag "$LOCAL_IMAGE" "$remote"
  echo "pushing $remote"
  docker push "$remote"
done

echo "OK — ${GHCR_IMAGE}:{${VERSION},latest}"

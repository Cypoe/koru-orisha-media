#!/usr/bin/env bash
# Load a saved tarball into the local registry and recreate the media project.
# Docker load alone does not restart running containers; this does.
#
# On the NAS, after scp of dist/koru-orisha-media.tar.gz:
#   bash nas-apply-image.sh /volume1/docker/koru-orisha-media/koru-orisha-media.tar.gz
set -euo pipefail

TAR="${1:?usage: nas-apply-image.sh <image.tar.gz>}"
COMPOSE="${COMPOSE:-/volume1/docker/koru-orisha-media/compose.nas.yaml}"
PROJECT_DIR="$(cd "$(dirname "$COMPOSE")" && pwd)"
HERE="$(cd "$(dirname "$0")" && pwd)"

if [[ -f "$HERE/nas-publish.sh" ]]; then
  bash "$HERE/nas-publish.sh" "$TAR"
elif [[ -f "$PROJECT_DIR/nas-publish.sh" ]]; then
  bash "$PROJECT_DIR/nas-publish.sh" "$TAR"
else
  echo "error: nas-publish.sh not found next to this script or $PROJECT_DIR" >&2
  exit 1
fi

if [[ ! -f "$COMPOSE" ]]; then
  echo "error: compose file not found: $COMPOSE" >&2
  exit 1
fi

echo "recreating project from $COMPOSE"
docker compose -f "$COMPOSE" --project-directory "$PROJECT_DIR" up -d --force-recreate --no-build --pull always
echo "OK — container is on the image just published"

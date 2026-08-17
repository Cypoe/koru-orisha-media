#!/usr/bin/env bash
# Build the musl image, push to the live SigmaNAS registry, recreate the project.
# Does not copy compose onto the NAS and does not run host Python hydrate.
#
#   bash scripts/nas-deploy.sh
#   bash scripts/nas-deploy.sh --skip-compile
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

HOST="${NAS_HOST:-cypoe@sigmanas}"
DEST="${NAS_PROJECT:-/volume1/docker/koru-orisha-media}"
COMPOSE="${NAS_COMPOSE:-$DEST/compose.yml}"
DOCKER_COMPOSE="${NAS_DOCKER_COMPOSE:-/usr/local/bin/docker-compose}"
DOCKER="${NAS_DOCKER:-/usr/local/bin/docker}"
PUSH_HOST="${PUSH_HOST:-sigmanas:9500}"
REMOTE_IMAGE="${REMOTE_IMAGE:-${PUSH_HOST}/koru-orisha-media:latest}"

for arg in "$@"; do
  case "$arg" in
    -h|--help)
      cat <<'EOF'
Usage: bash scripts/nas-deploy.sh [--skip-compile]

  1. scripts/build-image.sh → koru-orisha-media:local (musl binary + public/)
  2. scripts/publish-registry.sh → sigmanas:9500/koru-orisha-media:latest
  3. ssh docker-compose up --force-recreate --pull always on the live project

  Does not scp compose.yml and does not run nas-hydrate.sh.
  --skip-compile is forwarded to build-image.sh.
EOF
      exit 0
      ;;
  esac
done

bash "$ROOT/scripts/build-image.sh" "$@"
bash "$ROOT/scripts/publish-registry.sh"

DIGEST="$(docker image inspect "$REMOTE_IMAGE" --format '{{index .RepoDigests 0}}' 2>/dev/null || true)"
echo "digest: ${DIGEST:-unknown}"

echo "recreating $HOST:$COMPOSE (--pull always; not copying compose)"
ssh -o BatchMode=yes "$HOST" \
  "$DOCKER_COMPOSE" -f "$COMPOSE" --project-directory "$DEST" \
  up -d --force-recreate --no-build --pull always

echo "NAS containers:"
ssh -o BatchMode=yes "$HOST" \
  "$DOCKER ps --filter name=koru-orisha-media"

echo "OK — NAS running sigmanas.local:9500/koru-orisha-media:latest"
echo "digest: ${DIGEST:-unknown}"

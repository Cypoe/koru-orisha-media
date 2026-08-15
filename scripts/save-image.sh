#!/usr/bin/env bash
# Save koru-orisha-media:local as a gzipped docker-archive tarball.
# Synology Container Manager / docker load accepts this format.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
OUT="${1:-$ROOT/dist/koru-orisha-media.tar.gz}"
IMAGE="${IMAGE:-koru-orisha-media:local}"

if ! docker image inspect "$IMAGE" >/dev/null 2>&1; then
  echo "error: image $IMAGE missing — run bash scripts/build-image.sh first" >&2
  exit 1
fi

mkdir -p "$(dirname "$OUT")"
echo "saving $IMAGE → $OUT"
docker save "$IMAGE" | gzip -c > "$OUT"
ls -lh "$OUT"
echo "on the NAS:  gzip -dc $(basename "$OUT") | docker load"
echo "or:          docker load -i $(basename "$OUT")"

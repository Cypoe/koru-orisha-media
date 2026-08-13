#!/usr/bin/env bash
set -euo pipefail
IMG=koru-orisha-media-build:local
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
KORU_BUILD=/home/cypoe/src/koru-build
docker run --rm \
  -v "$KORU_BUILD/zig-out/bin/koruc:/usr/local/bin/koruc:ro" \
  -v "$KORU_BUILD/src:/usr/local/src:ro" \
  -v "$KORU_BUILD/koru_std:/usr/local/koru_std:ro" \
  -v /mnt/w/src/orisha:/src/orisha:ro \
  -v "$ROOT:/work" \
  -e HOME=/tmp \
  -e SKIP_TINY=1 \
  -e ORISHA_LIB=/src/orisha/lib \
  "$IMG" \
  bash /work/scripts/repro_pump_emit.sh

#!/usr/bin/env bash
# Run koruc in the same Linux image as scripts/build-docker.sh.
# Work happens on a Linux FS copy so Zig's cache rename is not DrvFs.
# vendor.lock is copied back to the repo when koruc writes it.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
IMG="koru-orisha-media-build:local"
KORU_BUILD="${KORU_BUILD:-$HOME/src/koru-build}"

if [[ ! -x "$KORU_BUILD/zig-out/bin/koruc" ]]; then
  echo "error: no koruc at $KORU_BUILD/zig-out/bin/koruc" >&2
  exit 1
fi

# Same std snapshot the pinned koruc was built against. A newer koru_std
# than this koruc will fail to link (emit vs compiler sources disagree).
STD="$KORU_BUILD/koru_std"

docker build -t "$IMG" -q -f - "$ROOT" <<'DOCKERFILE' >/dev/null
FROM debian:bookworm-slim
ARG ZIG_VERSION=0.15.1
RUN apt-get update && apt-get install -y --no-install-recommends \
      ca-certificates curl xz-utils zlib1g-dev build-essential rsync unzip \
    && rm -rf /var/lib/apt/lists/*
RUN set -eux; \
    curl -fsSL "https://ziglang.org/download/${ZIG_VERSION}/zig-x86_64-linux-${ZIG_VERSION}.tar.xz" -o /tmp/zig.tar.xz; \
    mkdir -p /opt/zig; \
    tar -xJf /tmp/zig.tar.xz -C /opt/zig --strip-components=1; \
    ln -s /opt/zig/zig /usr/local/bin/zig; \
    zig version
WORKDIR /work
DOCKERFILE

quoted=""
for a in "$@"; do
  quoted+=" $(printf '%q' "$a")"
done

docker run --rm \
  -v "$KORU_BUILD/zig-out/bin/koruc:/usr/local/bin/koruc:ro" \
  -v "$KORU_BUILD/src:/usr/local/src:ro" \
  -v "$STD:/usr/local/koru_std:ro" \
  -v "$ROOT:/work" \
  -e HOME=/tmp \
  -e VENDOR_ORIGIN_REV="${VENDOR_ORIGIN_REV:-}" \
  "$IMG" \
  bash -lc "set -euo pipefail
    mkdir -p /tmp/kwork
    rsync -a --delete \
      --exclude .git --exclude .zig-cache --exclude a.out --exclude bin \
      --exclude backend.zig --exclude backend_output_emitted.zig \
      --exclude output_emitted.zig --exclude build.zig --exclude build_backend.zig \
      /work/ /tmp/kwork/
    cd /tmp/kwork
    koruc$quoted
    if [[ -f vendor.lock ]]; then
      cp -f vendor.lock /work/vendor.lock
    fi
  "

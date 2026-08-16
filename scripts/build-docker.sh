#!/usr/bin/env bash
# Build koru-orisha-media inside Docker (zlib + Linux FS cache).
set -euo pipefail

IMG="koru-orisha-media-build:local"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
KORU_BUILD=/home/cypoe/src/koru-build

docker build -t "$IMG" -f - "$ROOT" <<'DOCKERFILE'
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

docker run --rm \
  -v "$KORU_BUILD/zig-out/bin/koruc:/usr/local/bin/koruc:ro" \
  -v "$KORU_BUILD/src:/usr/local/src:ro" \
  -v "$KORU_BUILD/koru_std:/usr/local/koru_std:ro" \
  -v /mnt/w/src/koru:/src/koru:ro \
  -v /mnt/w/src/koru-libs:/src/koru-libs:ro \
  -v "$ROOT:/work" \
  -e HOME=/tmp \
  "$IMG" \
  bash -lc 'set -euo pipefail
    cat > /work/koru.json <<EOF
{
  "name": "koru-orisha-media",
  "version": "0.1.0",
  "paths": {
    "std": "/usr/local/koru_std",
    "orisha": "./vendor/orisha",
    "http": "./vendor/http",
    "koru": "./vendor/koru-libs",
    "media": "./src"
  }
}
EOF
    mkdir -p /tmp/build
    rsync -a --delete \
      --exclude .git --exclude .zig-cache --exclude a.out --exclude bin \
      /work/ /tmp/build/
    cd /tmp/build
    set +e
    koruc main.k
    kc=$?
    set -e
    if [[ ! -f output_emitted.zig ]]; then
      echo "koruc failed before emit (exit $kc)" >&2
      exit 1
    fi
    if [[ "$kc" -ne 0 ]]; then
      echo "koruc native link skipped sqlite (exit $kc); musl relink will add it"
    fi
    echo compiling sqlite amalgamation for musl…
    curl -fsSL https://www.sqlite.org/2025/sqlite-amalgamation-3490100.zip -o /tmp/sqlite.zip
    unzip -qo /tmp/sqlite.zip -d /tmp
    zig cc -target x86_64-linux-musl -O2 -c /tmp/sqlite-amalgamation-3490100/sqlite3.c \
      -o /tmp/sqlite3.o \
      -DSQLITE_OMIT_LOAD_EXTENSION -DSQLITE_THREADSAFE=0 -DSQLITE_DEFAULT_MEMSTATUS=0
    echo relinking stripped x86_64-linux-musl from output_emitted.zig…
    zig build-exe output_emitted.zig /tmp/sqlite3.o \
      -target x86_64-linux-musl \
      -O ReleaseFast \
      -lc \
      -fstrip \
      -femit-bin=/tmp/media-server
    mkdir -p /work/bin
    cp -f /tmp/media-server /work/bin/media-server
    cp -f /tmp/media-server /work/a.out
    ls -l /work/bin/media-server
    echo emitting frontend JS…
    KORUC=/usr/local/bin/koruc KORU_STD=/usr/local/koru_std bash /work/scripts/build-frontend.sh
    echo OK
  '

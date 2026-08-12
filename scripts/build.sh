#!/usr/bin/env bash
set -euo pipefail

export PATH="${HOME}/tools/zig-0.15.1:${HOME}/src/koru-build/zig-out/bin:/usr/bin:/bin"

mkdir -p "${HOME}/lib"
ln -sfn /usr/lib/x86_64-linux-gnu/libz.so.1 "${HOME}/lib/libz.so"
export LIBRARY_PATH="${HOME}/lib${LIBRARY_PATH:+:$LIBRARY_PATH}"
export LD_LIBRARY_PATH="${HOME}/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
export CPATH="${HOME}/include${CPATH:+:$CPATH}"

# Zig also searches ZIG_LOCAL_CACHE and -L via pkg-config; create a tiny pkg-config.
mkdir -p "${HOME}/lib/pkgconfig"
cat > "${HOME}/lib/pkgconfig/zlib.pc" <<EOF
prefix=${HOME}
exec_prefix=\${prefix}
libdir=\${prefix}/lib
includedir=/usr/include

Name: zlib
Description: zlib compression library
Version: 1.2.11
Libs: -L\${libdir} -lz
Cflags: -I\${includedir}
EOF
export PKG_CONFIG_PATH="${HOME}/lib/pkgconfig${PKG_CONFIG_PATH:+:$PKG_CONFIG_PATH}"

REPO_WIN="/mnt/c/Users/fabi0/repos/koru-orisha-media"
BUILD="${HOME}/src/koru-orisha-media-build"
KORUC="${HOME}/src/koru-build/zig-out/bin/koruc"

mkdir -p "$HOME/src"
rsync -a --delete \
  --exclude '.git' \
  --exclude '.zig-cache' \
  --exclude 'a.out' \
  --exclude 'output_emitted.zig' \
  --exclude 'generated' \
  "$REPO_WIN/" "$BUILD/"

cat > "$BUILD/koru.json" <<EOF
{
  "name": "koru-orisha-media",
  "version": "0.1.0",
  "description": "Direct-play personal media library on Koru/Orisha",
  "paths": {
    "std": "${HOME}/src/koru-build/koru_std",
    "orisha": "./vendor/orisha-lib",
    "koru": "/mnt/w/src/koru-libs"
  }
}
EOF

cd "$BUILD"
"$KORUC" main.k
mkdir -p "$REPO_WIN/bin"
cp -f a.out "$REPO_WIN/a.out"
cp -f a.out "$REPO_WIN/bin/media-server"
echo "built $(pwd)/a.out"

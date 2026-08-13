#!/usr/bin/env bash
# Split-stage INTREE: original orisha/lib + serve.
# Zig diagnostics are from `./backend output`, not the frontend log.
set -u
KORUC="${KORUC:-$(command -v koruc)}"
STD="/usr/local/koru_std"
mkdir -p "${HOME}/lib/pkgconfig"
ln -sfn /usr/lib/x86_64-linux-gnu/libz.so.1 "${HOME}/lib/libz.so"
export LIBRARY_PATH="${HOME}/lib${LIBRARY_PATH:+:$LIBRARY_PATH}"
export LD_LIBRARY_PATH="${HOME}/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
cat >"${HOME}/lib/pkgconfig/zlib.pc" <<'PC'
prefix=/usr
exec_prefix=${prefix}
libdir=/usr/lib/x86_64-linux-gnu
includedir=/usr/include
Name: zlib
Description: zlib
Version: 1.2.11
Libs: -lz
Cflags:
PC
export PKG_CONFIG_PATH="${HOME}/lib/pkgconfig${PKG_CONFIG_PATH:+:$PKG_CONFIG_PATH}"

tmp=$(mktemp -d /tmp/orisha-intree.XXXXXX)
mkdir -p "$tmp"
cp -a /src/orisha/lib "$tmp/lib"
cat >"$tmp/koru.json" <<EOF
{
  "name": "orisha",
  "version": "0.1.0",
  "paths": {
    "std": "$STD",
    "orisha": "lib"
  }
}
EOF
cat >"$tmp/main.k" <<'EOF'
import orisha
orisha:handler -> { status: 200, body: "ok", content_type: "text/plain" }
orisha:serve(port: 3090)
| shutdown _ |> _
| failed _ |> _
EOF
cd "$tmp"
echo "-- frontend: koruc -o backend.zig main.k --"
"$KORUC" -o backend.zig main.k
fec=$?
echo "frontend exit=$fec"
if [[ "$fec" -ne 0 ]]; then exit "$fec"; fi
echo "-- zig build --build-file build_backend.zig --"
zig build --build-file build_backend.zig
zec=$?
echo "zig build backend exit=$zec"
if [[ "$zec" -ne 0 ]]; then exit "$zec"; fi
cp -f zig-out/bin/backend ./backend
chmod +x ./backend
echo "-- ./backend output --"
./backend output >backend.out 2>backend.err
bec=$?
echo "backend output exit=$bec"
echo "duplicate=$(grep -c 'duplicate struct member' backend.err || true)"
echo "ambiguous=$(grep -c 'ambiguous reference' backend.err || true)"
head -40 backend.err
if [[ -d /work ]]; then
  mkdir -p /work/pump-emit-artifacts/INTREE
  cp -f backend.err backend.out /work/pump-emit-artifacts/INTREE/ 2>/dev/null || true
  [[ -f output_emitted.zig ]] && cp -f output_emitted.zig /work/pump-emit-artifacts/INTREE/
fi
exit "$bec"

#!/usr/bin/env bash
# In-tree compile of canonical serve against /src/orisha (W:\src\orisha).
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
"$KORUC" main.k >"$tmp/log" 2>&1
ec=$?
echo "INTREE_SERVE exit=$ec"
echo "duplicate=$(grep -c 'duplicate struct member' "$tmp/log" || true)"
echo "ambiguous=$(grep -c 'ambiguous reference' "$tmp/log" || true)"
grep -E "duplicate struct member|ambiguous reference|error\[KORU" "$tmp/log" | head -12 || true
if [[ "$ec" -eq 0 ]]; then
  echo "linked OK"
else
  echo "--- tail ---"
  tail -12 "$tmp/log"
fi
if [[ -d /work ]]; then
  cp -f "$tmp/log" /work/pump-emit-INTREE.log
fi

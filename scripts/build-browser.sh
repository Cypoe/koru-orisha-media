#!/usr/bin/env bash
# Build optional koru/dom JS → public/koru-dom-enhance.js
# Requires: koruc with --lang=js, zig 0.15.1 on PATH.
set -euo pipefail
REPO=/mnt/c/Users/fabi0/repos/koru-orisha-media
export PATH="${HOME}/tools/zig-0.15.1:${HOME}/src/koru-build/zig-out/bin:${PATH}"
KORUC="$(command -v koruc)"
STD="${HOME}/src/koru-build/koru_std"
OUTDIR=$(mktemp -d)
trap 'rm -rf "$OUTDIR"' EXIT

echo "koruc=$KORUC"
echo "zig=$(command -v zig) ($(zig version))"

cat > "$OUTDIR/koru.json" <<EOF
{
  "name": "koru-orisha-media-browser",
  "version": "0.1.0",
  "paths": {
    "std": "$STD",
    "koru": "/mnt/w/src/koru-libs"
  }
}
EOF
cp "$REPO/browser/main.k" "$OUTDIR/main.k"
cp "$REPO/browser/main.kjs" "$OUTDIR/main.kjs"
cd "$OUTDIR"

# Option must precede the input file: koruc [options] <input> [command]
"$KORUC" --lang=js main.k

if [[ ! -f output_emitted.js ]]; then
  echo "expected output_emitted.js missing" >&2
  ls -la >&2
  exit 1
fi
mkdir -p "$REPO/public"
cp -f output_emitted.js "$REPO/public/koru-dom-enhance.js"
echo "wrote $REPO/public/koru-dom-enhance.js ($(wc -c < output_emitted.js) bytes)"

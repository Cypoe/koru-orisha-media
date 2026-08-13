#!/usr/bin/env bash
# Emit frontend JS from Koru usage programs (koruc --lang=js).
#   src/frontend/host.k  (import koru/htmx) → public/enhance.js
#   src/frontend/main.k  (import koru/dom)  → public/koru-dom-enhance.js
# Libraries: vendor/koru-libs/{htmx,dom}. The program is the usage file, not a lib.
# Requires: koruc with --lang=js, zig 0.15.1 on PATH.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
export PATH="${HOME}/tools/zig-0.15.1:${HOME}/src/koru-build/zig-out/bin:${PATH}"
KORUC="$(command -v koruc)"
STD="${HOME}/src/koru-build/koru_std"
if [[ ! -d "$STD" ]]; then
  STD="/usr/local/koru_std"
fi
KORU="$ROOT/vendor/koru-libs"
if [[ ! -d "$KORU/htmx" || ! -d "$KORU/dom" ]]; then
  echo "missing vendor/koru-libs/{htmx,dom}" >&2
  exit 1
fi

emit_js() {
  local stem="$1"
  local dest="$2"
  local name="$3"
  local OUTDIR
  OUTDIR=$(mktemp -d)
  trap 'rm -rf "$OUTDIR"' RETURN
  mkdir -p "$OUTDIR/src/frontend"
  cat > "$OUTDIR/koru.json" <<EOF
{
  "name": "$name",
  "version": "0.1.0",
  "paths": {
    "std": "$STD",
    "koru": "$KORU"
  }
}
EOF
  cp "$ROOT/src/frontend/${stem}.k" "$OUTDIR/src/frontend/${stem}.k"
  if [[ -f "$ROOT/src/frontend/${stem}.kjs" ]]; then
    cp "$ROOT/src/frontend/${stem}.kjs" "$OUTDIR/src/frontend/${stem}.kjs"
  fi
  (
    cd "$OUTDIR"
    echo "koruc=$KORUC src=src/frontend/${stem}.k koru=$KORU"
    echo "zig=$(command -v zig) ($(zig version))"
    "$KORUC" --lang=js "src/frontend/${stem}.k"
    emitted=""
    if [[ -f output_emitted.js ]]; then
      emitted=output_emitted.js
    elif [[ -f "src/frontend/output_emitted.js" ]]; then
      emitted=src/frontend/output_emitted.js
    else
      echo "expected output_emitted.js missing for $stem" >&2
      find . -name 'output_emitted.js' >&2 || true
      ls -la >&2
      ls -la src/frontend >&2
      exit 1
    fi
    mkdir -p "$ROOT/public"
    cp -f "$emitted" "$dest"
    echo "wrote $dest ($(wc -c < "$emitted") bytes)"
  )
}

emit_js host "$ROOT/public/enhance.js" "koru-orisha-media-host"
emit_js main "$ROOT/public/koru-dom-enhance.js" "koru-orisha-media-frontend"

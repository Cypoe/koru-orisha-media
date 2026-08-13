#!/usr/bin/env bash
# Compile src/json usage (import json → vendor/json) → bin/json-publish.
# Does NOT link into bin/media-server. Exit 2 = no koruc (suite uses Python fallback).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
export PATH="${HOME}/tools/zig-0.15.1:${HOME}/src/koru-build/zig-out/bin:${PATH}"

if ! command -v koruc >/dev/null 2>&1; then
  echo "skip json-publish: koruc not on PATH" >&2
  exit 2
fi

KORUC="$(command -v koruc)"
STD="${HOME}/src/koru-build/koru_std"
if [[ ! -d "$STD" ]]; then
  STD="/usr/local/koru_std"
fi
JSON="$ROOT/vendor/json"
if [[ ! -d "$JSON" ]]; then
  echo "missing vendor/json" >&2
  exit 1
fi

OUTDIR=$(mktemp -d)
trap 'rm -rf "$OUTDIR"' EXIT

mkdir -p "$OUTDIR/src/json"
cat > "$OUTDIR/koru.json" <<EOF
{
  "name": "koru-orisha-json",
  "version": "0.1.0",
  "paths": {
    "std": "$STD",
    "json": "$JSON"
  }
}
EOF
cp "$ROOT/src/json/main.k" "$OUTDIR/src/json/main.k"
cp "$ROOT/src/json/main.kz" "$OUTDIR/src/json/main.kz"
cd "$OUTDIR"
"$KORUC" src/json/main.k
emitted=""
if [[ -f a.out ]]; then
  emitted=a.out
elif [[ -f src/json/a.out ]]; then
  emitted=src/json/a.out
else
  echo "json-publish: expected a.out missing" >&2
  find . -name a.out >&2 || true
  ls -la >&2
  ls -la src/json >&2 || true
  exit 1
fi
mkdir -p "$ROOT/bin"
cp -f "$emitted" "$ROOT/bin/json-publish"
echo "wrote $ROOT/bin/json-publish (src/json usage + vendor/json, no libyyjson)"

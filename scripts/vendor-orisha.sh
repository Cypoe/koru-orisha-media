#!/usr/bin/env bash
# Refresh vendor/orisha from upstream lib. Does not touch vendor/http
# (STREAM / Request extras / run-accept-loop live there).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DEST="$ROOT/vendor/orisha"

pick_lib() {
  if [[ -n "${ORISHA_LIB:-}" && -d "$ORISHA_LIB" ]]; then
    echo "$ORISHA_LIB"
    return
  fi
  local c
  for c in \
    /mnt/w/src/orisha/lib \
    /w/src/orisha/lib \
    "$HOME/src/orisha/lib" \
    /usr/local/src/orisha/lib
  do
    if [[ -f "$c/index.k" ]]; then
      echo "$c"
      return
    fi
  done
  if [[ -f /mnt/w/src/orisha/lib/index.k ]]; then
    echo /mnt/w/src/orisha/lib
    return
  fi
  echo "error: set ORISHA_LIB to W:\\src\\orisha\\lib (or /mnt/w/src/orisha/lib)" >&2
  exit 1
}

LIB="$(pick_lib)"
echo "vendoring $LIB → $DEST"

if command -v rsync >/dev/null 2>&1; then
  rsync -a --delete \
    --exclude '.git' \
    --exclude '.vendor-rev' \
    --exclude 'VENDOR.md' \
    "$LIB/" "$DEST/"
else
  mkdir -p "$DEST"
  cp -a "$LIB/." "$DEST/"
fi

REV="unknown"
GIT_DIR="$(dirname "$LIB")"
if [[ -d "$GIT_DIR/.git" ]] && command -v git >/dev/null 2>&1; then
  REV="$(git -C "$GIT_DIR" rev-parse --short HEAD 2>/dev/null || echo unknown)"
  git -C "$GIT_DIR" log -1 --format='%h %s' >"$DEST/.vendor-rev" || true
else
  echo "$REV" >"$DEST/.vendor-rev"
fi

cat >"$DEST/VENDOR.md" <<EOF
# Vendored Orisha lib

Copied from \`$LIB\` (\`$REV\`).

This tree must stay a **verbatim** upstream \`lib/\`. App HTTP (Range, STREAM:v1,
run-accept-loop) lives in [\`vendor/http\`](../http/). Refresh with:

    bash scripts/vendor-orisha.sh

Do not edit index.kz here to add STREAM — that would fork Orisha again.
EOF

echo "OK — vendor/orisha @$REV"
echo "HTTP spec remains vendor/http (not overwritten)"

#!/usr/bin/env bash
# Refresh vendor/orisha from upstream. Does not touch vendor/http
# (STREAM / Request extras / run-accept-loop live there).
#
# 1. git pull the Orisha checkout
# 2. snapshot lib/ into vendor/orisha
# 3. koruc main.k vendor copy orisha  (as-copied + as-compiled)
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DEST="$ROOT/vendor/orisha"

pick_src() {
  if [[ -n "${ORISHA_SRC:-}" && -d "$ORISHA_SRC/.git" ]]; then
    echo "$ORISHA_SRC"
    return
  fi
  local c
  for c in \
    /mnt/w/src/orisha \
    /w/src/orisha \
    "$HOME/src/orisha" \
    /usr/local/src/orisha
  do
    if [[ -d "$c/.git" && -f "$c/lib/index.k" ]]; then
      echo "$c"
      return
    fi
  done
  echo "error: set ORISHA_SRC to the Orisha git checkout (W:\\src\\orisha)" >&2
  exit 1
}

SRC="$(pick_src)"
LIB="$SRC/lib"
[[ -f "$LIB/index.k" ]] || { echo "error: no lib/ under $SRC" >&2; exit 1; }

if [[ -z "${ORISHA_SKIP_PULL:-}" ]]; then
  echo "git pull $SRC"
  git -C "$SRC" pull --ff-only
fi

REV="$(git -C "$SRC" rev-parse --short HEAD)"
echo "snapshot $LIB @$REV → $DEST"

mkdir -p "$DEST"
# Snapshot only. Acquisition is git pull above.
if command -v rsync >/dev/null 2>&1; then
  rsync -a --delete \
    --exclude '.git' \
    --exclude '.vendor-rev' \
    --exclude 'VENDOR.md' \
    "$LIB/" "$DEST/"
else
  find "$DEST" -mindepth 1 -maxdepth 1 ! -name '.vendor-rev' ! -name 'VENDOR.md' -exec rm -rf {} +
  cp -a "$LIB/." "$DEST/"
fi

git -C "$SRC" log -1 --format='%h %s' >"$DEST/.vendor-rev"

cat >"$DEST/VENDOR.md" <<EOF
# Vendored Orisha lib

Verbatim \`lib/\` from \`$SRC\` (\`$REV\`), after \`git pull\`.

App HTTP (Range, STREAM:v1, run-accept-loop) lives in [\`vendor/http\`](../http/).
Refresh with:

    bash scripts/vendor-orisha.sh

Do not edit index.kz here to add STREAM — that would fork Orisha again.
EOF

echo "pin vendor.lock via koruc vendor copy"
bash "$ROOT/scripts/koruc.sh" main.k vendor copy orisha

echo "OK — vendor/orisha @$REV"
echo "HTTP spec remains vendor/http (not overwritten)"
echo "After editing vendor/http: bash scripts/koruc.sh main.k vendor sync"

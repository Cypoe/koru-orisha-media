#!/usr/bin/env bash
# Compile once, then serve the fixture library from WSL for a fast frontend loop.
# CSS in public/app.css is live (no rebuild). After src/frontend/host.kjs changes:
#   bash scripts/build-frontend.sh
# Then refresh. Binary rebuild is only needed for Koru/Zig handler changes.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DEV="${KORU_DEV_DIR:-$ROOT/.pw/dev}"
SKIP_COMPILE="${SKIP_COMPILE:-0}"

mkdir -p "$DEV"

if [[ "$SKIP_COMPILE" != "1" ]]; then
  bash "$ROOT/scripts/build.sh"
  bash "$ROOT/scripts/build-frontend.sh"
fi

BIN="$ROOT/bin/media-server"
if [[ ! -x "$BIN" ]]; then
  echo "missing $BIN — run without SKIP_COMPILE=1" >&2
  exit 1
fi

export KORU_MEDIA_ROOT="${KORU_MEDIA_ROOT:-$ROOT/fixtures/media}"
export KORU_CATALOG="${KORU_CATALOG:-$DEV/catalog.sqlite}"
export KORU_SEMANTIC="${KORU_SEMANTIC:-$ROOT/fixtures/semantic.json}"
export KORU_CONFIG="${KORU_CONFIG:-$DEV/settings.conf}"
export KORU_TMDB_FIXTURE="${KORU_TMDB_FIXTURE:-$ROOT/fixtures/tmdb}"

if [[ ! -f "$KORU_CATALOG" ]]; then
  export KORU_REINDEX=1
  # First catalog only — hydrate on the accept pump after the walk. Later
  # starts stay interactive; Settings → Hydrate now still flags a run.
  touch "$DEV/hydrate.requested"
elif [[ "${KORU_HYDRATE:-0}" == "1" ]]; then
  touch "$DEV/hydrate.requested"
fi

cd "$ROOT"
echo "dev: http://127.0.0.1:3090/  catalog=$KORU_CATALOG"
echo "media=$KORU_MEDIA_ROOT  tmdb fixtures=$KORU_TMDB_FIXTURE"
echo "CSS is live from public/. JS: bash scripts/build-frontend.sh"
echo "Later starts: SKIP_COMPILE=1 bash scripts/dev-wsl.sh"
exec "$BIN"

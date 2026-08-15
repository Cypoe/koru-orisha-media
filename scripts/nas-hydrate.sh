#!/usr/bin/env bash
# Host-side TMDB/TVDB hydrate into catalog.sqlite overlay tables.
# The runtime image has no Python and never calls providers.
#
#   bash nas-hydrate.sh
#   KORU_CATALOG=/path/to/catalog.sqlite bash nas-hydrate.sh
#
# No-ops (exit 0) when TMDB_API_KEY / TMDB_API_TOKEN / TVDB_API_KEY are absent.
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="${ROOT:-/volume1/docker/koru-orisha-media}"
CATALOG="${KORU_CATALOG:-$ROOT/data/catalog.sqlite}"
SCRIPT="$HERE/hydrate_catalog.py"
if [[ ! -f "$SCRIPT" ]]; then
  SCRIPT="${REPO_SCRIPTS:-$ROOT/scripts}/hydrate_catalog.py"
fi

if ! command -v python3 >/dev/null 2>&1; then
  echo "hydrate is host-side Python — python3 not found." >&2
  echo "From the build machine: python3 scripts/hydrate_catalog.py --catalog $CATALOG" >&2
  echo "docker exec hydrate is a no-op (Alpine image has no Python)." >&2
  exit 0
fi

if [[ ! -f "$SCRIPT" ]]; then
  echo "missing $SCRIPT" >&2
  exit 1
fi

exec python3 "$SCRIPT" --catalog "$CATALOG" "$@"

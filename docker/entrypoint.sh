#!/bin/sh
# Tiny alpine entrypoint. Indexer is the Koru binary (catalog reindex), not Python.
set -eu

MEDIA_ROOT="${KORU_MEDIA_ROOT:-/media}"

if [ ! -x /app/media-server ]; then
  echo "error: /app/media-server missing or not executable" >&2
  exit 1
fi

if [ ! -d "$MEDIA_ROOT" ]; then
  echo "error: media root not found: $MEDIA_ROOT (mount a volume)" >&2
  exit 1
fi

if [ "${1:-}" = "reindex" ]; then
  export KORU_REINDEX=1
  shift
fi

if [ "${1:-}" = "hydrate" ]; then
  echo "hydrate: this image is Alpine + one binary (no Python)."
  echo "this process never calls TMDB, TVDB, or ffmpeg."
  echo "run on the host: python3 scripts/hydrate_catalog.py --catalog /data/catalog.sqlite"
  echo "no-ops when TMDB_API_KEY / TMDB_API_TOKEN / TVDB_API_KEY are absent."
  exit 0
fi

exec /app/media-server "$@"

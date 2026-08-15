#!/usr/bin/env bash
# Start media-server; optionally reindex first.
set -euo pipefail

MEDIA_ROOT="${KORU_MEDIA_ROOT:-/media}"
MANIFEST="${KORU_MANIFEST:-/data/manifest.json}"
REINDEX="${KORU_REINDEX:-0}"

if [[ ! -x /app/media-server ]]; then
  echo "error: /app/media-server missing or not executable" >&2
  exit 1
fi

if [[ ! -d "$MEDIA_ROOT" ]]; then
  echo "error: media root not found: $MEDIA_ROOT (mount a volume)" >&2
  exit 1
fi

do_reindex=0
if [[ "$REINDEX" == "1" || "$REINDEX" == "true" ]]; then
  do_reindex=1
fi
if [[ "${1:-}" == "reindex" ]]; then
  do_reindex=1
  shift
fi

if [[ "$do_reindex" -eq 1 ]]; then
  echo "indexing $MEDIA_ROOT → $MANIFEST"
  mkdir -p "$(dirname "$MANIFEST")"
  probe_args=()
  if [[ -n "${KORU_INDEX_PROBE:-}" ]]; then
    probe_args+=(--probe "$KORU_INDEX_PROBE")
  fi
  python3 /app/scripts/index_media.py --root "$MEDIA_ROOT" --out "$MANIFEST" "${probe_args[@]}"
fi

if [[ ! -f "$MANIFEST" ]]; then
  echo "error: manifest not found: $MANIFEST" >&2
  echo "hint: set KORU_REINDEX=1 or pass 'reindex' to build it, or mount an existing manifest" >&2
  exit 1
fi

exec /app/media-server "$@"

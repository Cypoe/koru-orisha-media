#!/usr/bin/env bash
# Ask the running server to walk enabled /media libraries into the SQLite catalog.
# Same as Settings → Reindex. The next accept-pump tick performs the walk
# inside the Koru binary (not host Python), including while a stream is parked.
#
#   bash nas-index.sh
set -euo pipefail

ROOT="${ROOT:-/volume1/docker/koru-orisha-media}"
FLAG="${FLAG:-$ROOT/data/reindex.requested}"

mkdir -p "$(dirname "$FLAG")"
touch "$FLAG"
echo "flagged $FLAG — next accept tick reindexes enabled libraries under /media into catalog.sqlite"
echo "or use Settings → Reindex (same flag). Restart also walks on empty catalog / KORU_REINDEX=1"

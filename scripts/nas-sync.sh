#!/usr/bin/env bash
# Copy NAS project files to SigmaNAS as compose.yml (not compose.nas.yaml).
# Windows OpenSSH needs scp -O (DSM legacy protocol). WSL scp is older and
# already uses that protocol — it rejects -O.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
HOST="${NAS_HOST:-cypoe@sigmanas}"
DEST="${NAS_PROJECT:-/volume1/docker/koru-orisha-media}"

SCP=(scp)
set +e
if scp 2>&1 | grep -q -- '\[-O'; then
  SCP=(scp -O)
fi
set -e

"${SCP[@]}" "$ROOT/compose.nas.yaml" "$HOST:$DEST/compose.yml"
"${SCP[@]}" \
  "$ROOT/scripts/nas-apply-image.sh" \
  "$ROOT/scripts/nas-publish.sh" \
  "$ROOT/scripts/nas-index.sh" \
  "$ROOT/scripts/nas-hydrate.sh" \
  "$ROOT/scripts/nas-registry.sh" \
  "$ROOT/scripts/nas-sync.sh" \
  "$HOST:$DEST/"

echo "OK — $HOST:$DEST/compose.yml"
echo "recreate with: ssh $HOST docker compose -f $DEST/compose.yml --project-directory $DEST up -d"

#!/usr/bin/env bash
# Baseline latency / RSS for koru-orisha-media (GOAL Step 10).
set -euo pipefail
REPO_MNT=/mnt/c/Users/fabi0/repos/koru-orisha-media
cd "$REPO_MNT"
CONTAINER=koru-media-bench
PORT=3092
cleanup() { docker rm -f "$CONTAINER" >/dev/null 2>&1 || true; }
trap cleanup EXIT
cleanup

if [[ ! -f bin/media-server ]]; then
  echo "bin/media-server missing — build first" >&2
  exit 2
fi

ID=$(python3 -c "import json; print(next(e['id'] for e in json.load(open('data/manifest.json'))['entries'] if e['title']=='demo'))")

START=$(date +%s%3N)
docker run -d --name "$CONTAINER" -p "${PORT}:3090" \
  -e KORU_MEDIA_ROOT=fixtures/media \
  -e KORU_MANIFEST=data/manifest.json \
  -v "$REPO_MNT/bin/media-server:/app/media-server:ro" \
  -v "$REPO_MNT/data:/app/data:ro" \
  -v "$REPO_MNT/fixtures:/app/fixtures:ro" \
  -v "$REPO_MNT/public:/app/public:ro" \
  -w /app debian:bookworm-slim /app/media-server >/dev/null

for i in $(seq 1 100); do
  if curl -sf "http://127.0.0.1:${PORT}/library" >/dev/null; then break; fi
  sleep 0.05
done
READY=$(date +%s%3N)
echo "cold_ready_ms=$((READY - START))"

t1=$(date +%s%3N)
curl -sf "http://127.0.0.1:${PORT}/library" >/dev/null
t2=$(date +%s%3N)
echo "library_ms=$((t2 - t1))"

t1=$(date +%s%3N)
curl -sf "http://127.0.0.1:${PORT}/media/${ID}" >/dev/null
t2=$(date +%s%3N)
echo "media_get_ms=$((t2 - t1))"

t1=$(date +%s%3N)
curl -sf -H 'Range: bytes=0-3' "http://127.0.0.1:${PORT}/media/${ID}" >/dev/null
t2=$(date +%s%3N)
echo "media_range_ms=$((t2 - t1))"

docker stats --no-stream --format 'rss_mb={{.MemUsage}}' "$CONTAINER" || true
echo "bench_ok"

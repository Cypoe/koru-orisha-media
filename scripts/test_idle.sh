#!/usr/bin/env bash
# GOAL Step 10 — idle exit when KORU_IDLE_SECS elapses with no active streams.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
if [[ ! -f bin/media-server ]]; then
  echo "bin/media-server missing" >&2
  exit 2
fi

CONTAINER=koru-media-idle-test
cleanup() { docker rm -f "$CONTAINER" >/dev/null 2>&1 || true; }
trap cleanup EXIT
cleanup

docker run -d --name "$CONTAINER" \
  -e KORU_MEDIA_ROOT=fixtures/media \
  -e KORU_MANIFEST=fixtures/manifest.json \
  -e KORU_IDLE_SECS=2 \
  -v "$ROOT/bin/media-server:/app/media-server:ro" \
  -v "$ROOT/data:/app/data:ro" \
  -v "$ROOT/fixtures:/app/fixtures:ro" \
  -v "$ROOT/public:/app/public:ro" \
  -w /app debian:bookworm-slim /app/media-server >/dev/null

# Wait up to 15s for clean exit (idle 2s + poll slack).
for i in $(seq 1 30); do
  status=$(docker inspect -f '{{.State.Status}}' "$CONTAINER" 2>/dev/null || echo missing)
  if [[ "$status" == "exited" ]]; then
    code=$(docker inspect -f '{{.State.ExitCode}}' "$CONTAINER")
    if [[ "$code" == "0" ]]; then
      echo "idle exit OK (exit 0 after KORU_IDLE_SECS=2)"
      exit 0
    fi
    echo "idle exit wrong code: $code" >&2
    docker logs "$CONTAINER" >&2 || true
    exit 1
  fi
  sleep 0.5
done
echo "idle exit timed out; status=$(docker inspect -f '{{.State.Status}}' "$CONTAINER")" >&2
docker logs "$CONTAINER" >&2 || true
exit 1

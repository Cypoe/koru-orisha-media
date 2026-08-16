#!/usr/bin/env bash
# HTTP integration only (expects bin/media-server already built).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
CONTAINER=koru-media-http-test
PORT=3091
cleanup() { docker rm -f "$CONTAINER" >/dev/null 2>&1 || true; }
trap cleanup EXIT

echo "== http: fixture media =="
cleanup
docker run -d --name "$CONTAINER" -p "${PORT}:3090" \
  -e KORU_MEDIA_ROOT=fixtures/media \
  -e KORU_MANIFEST=fixtures/manifest.json \
  -e KORU_SEMANTIC=fixtures/semantic.json \
  -v "$ROOT/bin/media-server:/app/media-server:ro" \
  -v "$ROOT/data:/app/data:ro" \
  -v "$ROOT/fixtures:/app/fixtures:ro" \
  -v "$ROOT/public:/app/public:ro" \
  -w /app debian:bookworm-slim /app/media-server >/dev/null
for i in $(seq 1 50); do
  if curl -sf "http://127.0.0.1:${PORT}/" >/dev/null; then break; fi
  sleep 0.1
done
KORU_TEST_BASE="http://127.0.0.1:${PORT}" KORU_TEST_MODE=fixture python3 "$ROOT/scripts/test_http.py"

echo "== http: missing semantic snapshot =="
cleanup
docker run -d --name "$CONTAINER" -p "${PORT}:3090" \
  -e KORU_MEDIA_ROOT=fixtures/media \
  -e KORU_MANIFEST=fixtures/manifest.json \
  -e KORU_SEMANTIC=data/missing-semantic.json \
  -v "$ROOT/bin/media-server:/app/media-server:ro" \
  -v "$ROOT/data:/app/data:ro" \
  -v "$ROOT/fixtures:/app/fixtures:ro" \
  -v "$ROOT/public:/app/public:ro" \
  -w /app debian:bookworm-slim /app/media-server >/dev/null
for i in $(seq 1 50); do
  if curl -sf "http://127.0.0.1:${PORT}/" >/dev/null; then break; fi
  sleep 0.1
done
KORU_TEST_BASE="http://127.0.0.1:${PORT}" KORU_TEST_MODE=nonsemantic python3 "$ROOT/scripts/test_http.py"

echo "== http: base path =="
cleanup
docker run -d --name "$CONTAINER" -p "${PORT}:3090" \
  -e KORU_MEDIA_ROOT=fixtures/media \
  -e KORU_MANIFEST=fixtures/manifest.json \
  -e KORU_SEMANTIC=fixtures/semantic.json \
  -e KORU_BASE_PATH=/korisha \
  -v "$ROOT/bin/media-server:/app/media-server:ro" \
  -v "$ROOT/data:/app/data:ro" \
  -v "$ROOT/fixtures:/app/fixtures:ro" \
  -v "$ROOT/public:/app/public:ro" \
  -w /app debian:bookworm-slim /app/media-server >/dev/null
for i in $(seq 1 50); do
  if curl -sf "http://127.0.0.1:${PORT}/korisha/" >/dev/null; then break; fi
  sleep 0.1
done
KORU_TEST_BASE="http://127.0.0.1:${PORT}" KORU_TEST_MODE=prefix KORU_TEST_PREFIX=/korisha python3 "$ROOT/scripts/test_http.py"

echo "== http: escape + traversal =="
cleanup
SEC=$(mktemp -d)
mkdir -p "$SEC/media/movies"
printf 'z' > "$SEC/media/movies/x.mp4"
cat > "$SEC/manifest.json" <<'JSON'
{
  "entries": [
    {
      "id": "m_xss",
      "kind": "movie",
      "title": "<script>alert(1)</script>",
      "path": "movies/x.mp4",
      "bytes": 1,
      "modified_ns": 1,
      "mime": "video/mp4"
    },
    {
      "id": "m_trav",
      "kind": "movie",
      "title": "trav",
      "path": "../etc/passwd",
      "bytes": 1,
      "modified_ns": 1,
      "mime": "text/plain"
    }
  ]
}
JSON
docker run -d --name "$CONTAINER" -p "${PORT}:3090" \
  -e KORU_MEDIA_ROOT=media \
  -e KORU_MANIFEST=manifest.json \
  -v "$ROOT/bin/media-server:/app/media-server:ro" \
  -v "$SEC:/app" \
  -w /app debian:bookworm-slim /app/media-server >/dev/null
for i in $(seq 1 50); do
  if curl -sf "http://127.0.0.1:${PORT}/" >/dev/null; then break; fi
  sleep 0.1
done
KORU_TEST_BASE="http://127.0.0.1:${PORT}" KORU_TEST_MODE=security python3 "$ROOT/scripts/test_http.py"

echo "== http: STREAM does not stall GET / =="
cleanup
OV=$(mktemp -d)
mkdir -p "$OV/media"
dd if=/dev/zero of="$OV/media/big.bin" bs=1048576 count=4 status=none
cat >"$OV/manifest.json" <<'JSON'
{
  "entries": [
    {
      "id": "m_big",
      "kind": "movie",
      "title": "big",
      "path": "big.bin",
      "bytes": 4194304,
      "modified_ns": 1,
      "mime": "application/octet-stream"
    }
  ]
}
JSON
docker run -d --name "$CONTAINER" -p "${PORT}:3090" \
  -e KORU_MEDIA_ROOT=media \
  -e KORU_MANIFEST=manifest.json \
  -v "$ROOT/bin/media-server:/app/media-server:ro" \
  -v "$OV:/app" \
  -w /app debian:bookworm-slim /app/media-server >/dev/null
for i in $(seq 1 50); do
  if curl -sf "http://127.0.0.1:${PORT}/" >/dev/null; then break; fi
  sleep 0.1
done
KORU_TEST_BASE="http://127.0.0.1:${PORT}" KORU_TEST_MODE=overlap KORU_TEST_BIG_ID=m_big python3 "$ROOT/scripts/test_http.py"
chmod -R u+w "$OV" 2>/dev/null || true
rm -rf "$OV" || true

echo "HTTP OK"

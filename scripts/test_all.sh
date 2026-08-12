#!/usr/bin/env bash
# Unit + HTTP integration suite for koru-orisha-media.
set -euo pipefail

REPO_MNT=/mnt/c/Users/fabi0/repos/koru-orisha-media
cd "$REPO_MNT"

echo "== unit: indexer =="
python3 scripts/test_indexer.py -v
echo "== unit: range =="
python3 scripts/test_range.py -v

if [[ ! -f bin/media-server ]]; then
  echo "bin/media-server missing — run bash scripts/build-docker.sh" >&2
  exit 2
fi

CONTAINER=koru-media-http-test
PORT=3091

cleanup() {
  docker rm -f "$CONTAINER" >/dev/null 2>&1 || true
}
trap cleanup EXIT

echo "== http: fixture media =="
cleanup
docker run -d --name "$CONTAINER" -p "${PORT}:3090" \
  -e KORU_MEDIA_ROOT=fixtures/media \
  -e KORU_MANIFEST=data/manifest.json \
  -v "$REPO_MNT/bin/media-server:/app/media-server:ro" \
  -v "$REPO_MNT/data:/app/data:ro" \
  -v "$REPO_MNT/fixtures:/app/fixtures:ro" \
  -v "$REPO_MNT/public:/app/public:ro" \
  -w /app debian:bookworm-slim /app/media-server >/dev/null

for i in $(seq 1 50); do
  if curl -sf "http://127.0.0.1:${PORT}/" >/dev/null; then break; fi
  sleep 0.1
done

cd "$REPO_MNT"
KORU_TEST_BASE="http://127.0.0.1:${PORT}" KORU_TEST_MODE=fixture python3 "$REPO_MNT/scripts/test_http.py"

echo "== http: escape + traversal =="
cleanup
SEC=$(mktemp -d)
mkdir -p "$SEC/media/clips"
printf 'z' > "$SEC/media/clips/x.mp4"
cat > "$SEC/manifest.json" <<'JSON'
{
  "entries": [
    {
      "id": "m_xss",
      "kind": "movie",
      "title": "<script>alert(1)</script>",
      "path": "clips/x.mp4",
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
  -v "$REPO_MNT/bin/media-server:/app/media-server:ro" \
  -v "$SEC:/app" \
  -w /app debian:bookworm-slim /app/media-server >/dev/null

for i in $(seq 1 50); do
  if curl -sf "http://127.0.0.1:${PORT}/" >/dev/null; then break; fi
  sleep 0.1
done

cd "$REPO_MNT"
KORU_TEST_BASE="http://127.0.0.1:${PORT}" KORU_TEST_MODE=security python3 "$REPO_MNT/scripts/test_http.py"

echo "== idle exit =="
bash scripts/test_idle.sh

echo "== hot manifest reload =="
bash scripts/test_reload.sh

echo "== koru/dom emit =="
bash scripts/test_browser_emit.sh

echo "== koru/dom keyed identity =="
bash scripts/test_keyed_list.sh

echo "ALL SUITES PASSED"

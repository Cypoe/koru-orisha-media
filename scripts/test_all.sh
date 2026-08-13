#!/usr/bin/env bash
# Unit + HTTP integration suite for koru-orisha-media.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

echo "== unit: indexer =="
python3 scripts/test_indexer.py -v
echo "== unit: range =="
python3 scripts/test_range.py -v
echo "== unit: semantic =="
python3 scripts/test_semantic.py -v
echo "== unit: enrich_tvdb =="
python3 scripts/test_enrich_tvdb.py -v
echo "== unit: enrich_tmdb =="
python3 scripts/test_enrich_tmdb.py -v
echo "== unit: manifest parse =="
python3 scripts/test_manifest_parse.py -v

echo "== unit: json publish (vendor/json via src/json usage, or Python fallback) =="
jp=0
bash scripts/build-json-publish.sh || jp=$?
if [[ "$jp" -eq 0 ]]; then
  echo "json-publish built (vendor/json)"
elif [[ "$jp" -eq 2 ]]; then
  echo "skip json-publish — Python fallback (docs/current-apis.md)"
else
  echo "json-publish compile/link failed — Python fallback (docs/current-apis.md)"
fi
python3 scripts/test_json_publish.py -v
echo "== unit: json codec (parse + emit) =="
if [[ -f bin/json-publish ]]; then
  python3 scripts/test_json.py -v
else
  echo "FAIL: bin/json-publish required for json codec tests" >&2
  exit 1
fi
echo "== unit: json koru (yyjson tests/basic+features port) =="
jk=0
bash scripts/test_json_koru.sh || jk=$?
if [[ "$jk" -eq 0 ]]; then
  echo "json koru tests OK"
elif [[ "$jk" -eq 2 ]]; then
  echo "skip json koru tests — no koruc"
else
  echo "FAIL: json koru tests" >&2
  exit 1
fi

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
  -e KORU_MANIFEST=fixtures/manifest.json \
  -v "$ROOT/bin/media-server:/app/media-server:ro" \
  -v "$ROOT/data:/app/data:ro" \
  -v "$ROOT/fixtures:/app/fixtures:ro" \
  -v "$ROOT/public:/app/public:ro" \
  -w /app debian:bookworm-slim /app/media-server >/dev/null

for i in $(seq 1 50); do
  if curl -sf "http://127.0.0.1:${PORT}/" >/dev/null; then break; fi
  sleep 0.1
done

cd "$ROOT"
KORU_TEST_BASE="http://127.0.0.1:${PORT}" KORU_TEST_MODE=fixture python3 "$ROOT/scripts/test_http.py"

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

cd "$ROOT"
KORU_TEST_BASE="http://127.0.0.1:${PORT}" KORU_TEST_MODE=security python3 "$ROOT/scripts/test_http.py"

echo "== idle exit =="
bash scripts/test_idle.sh

echo "== hot manifest reload =="
bash scripts/test_reload.sh

echo "== koru/dom emit =="
bash scripts/test_frontend_emit.sh

echo "== koru/dom keyed identity =="
bash scripts/test_keyed_list.sh

echo "ALL SUITES PASSED"

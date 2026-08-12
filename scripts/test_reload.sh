#!/usr/bin/env bash
# Hot manifest reload: title change is visible without restarting the process.
set -euo pipefail
REPO_MNT=/mnt/c/Users/fabi0/repos/koru-orisha-media
cd "$REPO_MNT"
if [[ ! -f bin/media-server ]]; then
  echo "bin/media-server missing" >&2
  exit 2
fi

CONTAINER=koru-media-reload-test
PORT=3093
WORKDIR=$(mktemp -d)
cleanup() {
  docker rm -f "$CONTAINER" >/dev/null 2>&1 || true
  rm -rf "$WORKDIR"
}
trap cleanup EXIT

mkdir -p "$WORKDIR/media/clips"
printf 'x' > "$WORKDIR/media/clips/x.mp4"
cat > "$WORKDIR/manifest.json" <<'JSON'
{
  "entries": [
    {
      "id": "m_reload",
      "kind": "movie",
      "title": "before",
      "path": "clips/x.mp4",
      "bytes": 1,
      "modified_ns": 1,
      "mime": "video/mp4",
      "container": "mp4"
    }
  ]
}
JSON

docker run -d --name "$CONTAINER" -p "${PORT}:3090" \
  -e KORU_MEDIA_ROOT=media \
  -e KORU_MANIFEST=manifest.json \
  -v "$REPO_MNT/bin/media-server:/app/media-server:ro" \
  -v "$WORKDIR:/app" \
  -w /app debian:bookworm-slim /app/media-server >/dev/null

for i in $(seq 1 50); do
  if curl -sf "http://127.0.0.1:${PORT}/library" | grep -q before; then break; fi
  sleep 0.1
done
curl -sf "http://127.0.0.1:${PORT}/library" | grep -q '>before<'

# Atomic replace with new title (same id/path).
python3 - "$WORKDIR" <<'PY'
import json, os, sys
from pathlib import Path
root = Path(sys.argv[1])
path = root / "manifest.json"
data = json.loads(path.read_text())
data["entries"][0]["title"] = "after"
tmp = path.with_suffix(".tmp")
tmp.write_text(json.dumps(data, indent=2) + "\n")
os.replace(tmp, path)
PY

# Ensure mtime advanced on some filesystems.
sleep 0.05
curl -sf "http://127.0.0.1:${PORT}/library" | grep -q '>after<'
curl -sf "http://127.0.0.1:${PORT}/library" | grep -vq '>before<'
echo "hot reload OK"

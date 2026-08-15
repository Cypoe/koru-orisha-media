#!/usr/bin/env bash
# Compile bin/media-server (unless --skip-compile), then build koru-orisha-media:local.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

SKIP_COMPILE=0
for arg in "$@"; do
  case "$arg" in
    --skip-compile) SKIP_COMPILE=1 ;;
    -h|--help)
      cat <<'EOF'
Usage: bash scripts/build-image.sh [--skip-compile]

  Compiles the Linux media-server binary via scripts/build-docker.sh (requires
  local koruc mounts — see that script), emits public/*.js from Koru, then
  builds Docker image koru-orisha-media:local from the runtime Dockerfile.

  --skip-compile   Use existing bin/media-server and public/*.js (Linux binary).
EOF
      exit 0
      ;;
    *)
      echo "unknown argument: $arg" >&2
      exit 2
      ;;
  esac
done

if [[ "$SKIP_COMPILE" -eq 0 ]]; then
  echo "compiling bin/media-server…"
  bash "$ROOT/scripts/build-docker.sh"
elif [[ ! -f "$ROOT/bin/media-server" ]]; then
  echo "error: bin/media-server missing; omit --skip-compile or build first" >&2
  exit 1
else
  echo "using existing bin/media-server (--skip-compile)"
fi

echo "building koru-orisha-media:local…"
docker build -t koru-orisha-media:local "$ROOT"
echo "OK — image koru-orisha-media:local"
echo "next: docker compose up"

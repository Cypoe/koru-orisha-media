#!/usr/bin/env bash
# Run keyed list DOM test inside the official Playwright image (has browser deps).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [[ ! -f public/koru-dom-enhance.js ]]; then
  echo "missing public/koru-dom-enhance.js — run bash scripts/build-browser.sh" >&2
  exit 2
fi

docker run --rm \
  -v "$ROOT:/work:ro" \
  -e PLAYWRIGHT_BROWSERS_PATH=/ms-playwright \
  mcr.microsoft.com/playwright:v1.55.0-jammy \
  bash -lc 'set -euo pipefail
    cd /tmp
    npm init -y >/dev/null
    npm install --silent playwright-core@1.55.0
    export NODE_PATH=/tmp/node_modules
    node /work/scripts/test_keyed_list.mjs'

#!/usr/bin/env bash
# Health-check the live NAS registry. Does not start or own it.
# Registry compose lives at /volume1/docker/registry (port 9500).
set -euo pipefail

for host in sigmanas.local:9500 127.0.0.1:9500 sigmanas:9500; do
  if curl -fsS --max-time 2 "http://${host}/v2/" >/dev/null 2>&1; then
    echo "OK — registry at http://${host}/v2/"
    curl -fsS "http://${host}/v2/_catalog" || true
    echo
    exit 0
  fi
done

echo "error: registry not answering on :9500" >&2
echo "expected a separate project under /volume1/docker/registry" >&2
exit 1

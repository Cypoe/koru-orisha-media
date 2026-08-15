#!/usr/bin/env bash
# Tag koru-orisha-media:local and push to the live NAS registry.
# This machine's dockerd insecure registry is sigmanas:9500.
# Container Manager pulls the same repo as sigmanas.local:9500/...
set -euo pipefail

LOCAL_IMAGE="${LOCAL_IMAGE:-koru-orisha-media:local}"
PUSH_HOST="${PUSH_HOST:-sigmanas:9500}"
REMOTE_IMAGE="${REMOTE_IMAGE:-${PUSH_HOST}/koru-orisha-media:latest}"

if ! docker image inspect "$LOCAL_IMAGE" >/dev/null 2>&1; then
  echo "error: $LOCAL_IMAGE missing — run bash scripts/build-image.sh first" >&2
  exit 1
fi

echo "checking $PUSH_HOST/v2/"
curl -fsS "http://${PUSH_HOST}/v2/" >/dev/null

echo "tagging $LOCAL_IMAGE → $REMOTE_IMAGE"
docker tag "$LOCAL_IMAGE" "$REMOTE_IMAGE"
echo "pushing $REMOTE_IMAGE"
docker push "$REMOTE_IMAGE"
echo "OK — registry has koru-orisha-media:latest"
echo "CM compose image: sigmanas.local:9500/koru-orisha-media:latest"

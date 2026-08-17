#!/usr/bin/env bash
# Tag koru-orisha-media:local and push to the live NAS registry.
# This machine's dockerd insecure registry is sigmanas:9500.
# Container Manager pulls the same repo as sigmanas.local:9500/...
#
# TAGS — space-separated image tags (default: latest). Example:
#   TAGS="0.1.0 latest" bash scripts/publish-registry.sh
set -euo pipefail

LOCAL_IMAGE="${LOCAL_IMAGE:-koru-orisha-media:local}"
PUSH_HOST="${PUSH_HOST:-sigmanas:9500}"
REPO="${REMOTE_REPO:-${PUSH_HOST}/koru-orisha-media}"
# Backward compatible: REMOTE_IMAGE=host/repo:tag still works for a single tag.
if [[ -n "${REMOTE_IMAGE:-}" && -z "${TAGS:-}" ]]; then
  TAGS="${REMOTE_IMAGE##*:}"
  REPO="${REMOTE_IMAGE%:*}"
fi
TAGS="${TAGS:-latest}"

if ! docker image inspect "$LOCAL_IMAGE" >/dev/null 2>&1; then
  echo "error: $LOCAL_IMAGE missing — run bash scripts/build-image.sh first" >&2
  exit 1
fi

echo "checking $PUSH_HOST/v2/"
curl -fsS "http://${PUSH_HOST}/v2/" >/dev/null

for tag in $TAGS; do
  remote="${REPO}:${tag}"
  echo "tagging $LOCAL_IMAGE → $remote"
  docker tag "$LOCAL_IMAGE" "$remote"
  echo "pushing $remote"
  docker push "$remote"
done

echo "OK — registry has ${REPO} tags: $TAGS"
echo "CM compose image: sigmanas.local:9500/koru-orisha-media:latest"

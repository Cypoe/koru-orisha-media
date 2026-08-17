#!/usr/bin/env bash
# Cut a release from the build machine (koruc compile stays local).
#
#   bash scripts/release.sh 0.1.0
#   bash scripts/release.sh 0.1.0 --skip-compile
#   bash scripts/release.sh 0.1.0 --skip-nas --skip-ghcr   # tarball + GitHub only
#   bash scripts/release.sh 0.1.0 --dry-run
#
# Prerequisites: CHANGELOG.md section for VERSION committed on main;
#   gh auth; docker login ghcr.io (unless --skip-ghcr). See docs/releasing.md.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

VERSION=""
SKIP_COMPILE=0
SKIP_NAS=0
SKIP_GHCR=0
DRY_RUN=0
BUILD_ARGS=()

usage() {
  cat <<'EOF'
Usage: bash scripts/release.sh <VERSION> [options]

  1. build-image.sh → koru-orisha-media:local (+ tag :VERSION)
  2. publish-registry.sh → sigmanas:9500/...:VERSION and :latest  (unless --skip-nas)
  3. publish-ghcr.sh → ghcr.io/cypoe/koru-orisha-media:VERSION and :latest  (unless --skip-ghcr)
  4. save-image.sh → dist/koru-orisha-media-VERSION-linux-amd64.tar.gz
  5. git tag vVERSION + push; gh release create with tarball

Options:
  --skip-compile   Forwarded to build-image.sh
  --skip-nas       Do not push to the LAN registry
  --skip-ghcr      Do not push to GHCR
  --dry-run        Print steps; do not tag, push, save, or create the release
  -h, --help       Show this help
EOF
}

for arg in "$@"; do
  case "$arg" in
    -h|--help) usage; exit 0 ;;
    --skip-compile) SKIP_COMPILE=1; BUILD_ARGS+=(--skip-compile) ;;
    --skip-nas) SKIP_NAS=1 ;;
    --skip-ghcr) SKIP_GHCR=1 ;;
    --dry-run) DRY_RUN=1 ;;
    -*)
      echo "unknown option: $arg" >&2
      usage >&2
      exit 2
      ;;
    *)
      if [[ -n "$VERSION" ]]; then
        echo "error: unexpected argument: $arg" >&2
        exit 2
      fi
      VERSION="$arg"
      ;;
  esac
done

if [[ -z "$VERSION" ]]; then
  usage >&2
  exit 2
fi

if [[ ! "$VERSION" =~ ^[0-9]+\.[0-9]+\.[0-9]+([.-][0-9A-Za-z.-]+)?$ ]]; then
  echo "error: VERSION must look like 0.1.0 (got: $VERSION)" >&2
  exit 2
fi

TAG="v${VERSION}"
LOCAL_IMAGE="${LOCAL_IMAGE:-koru-orisha-media:local}"
VERSIONED_IMAGE="koru-orisha-media:${VERSION}"
TAR="dist/koru-orisha-media-${VERSION}-linux-amd64.tar.gz"
NOTES="$(mktemp)"
trap 'rm -f "$NOTES"' EXIT

extract_notes() {
  # Slice ## [VERSION] ... until next ## [ or reference-link footer (python).
  python3 - "$ROOT/CHANGELOG.md" "$VERSION" <<'PY'
import re
import sys
from pathlib import Path
path, ver = Path(sys.argv[1]), sys.argv[2]
text = path.read_text(encoding="utf-8")
start = f"## [{ver}]"
idx = text.find(start)
if idx < 0:
    sys.stderr.write(f"error: CHANGELOG.md missing section {start}\n")
    sys.exit(1)
rest = text[idx + len(start):]
nl = rest.find("\n")
body = rest[nl + 1 :] if nl >= 0 else rest
next_h = body.find("\n## [")
if next_h >= 0:
    body = body[:next_h]
# Drop Keep-a-Changelog reference-link footer ([Unreleased]: …)
m = re.search(r"\n\[[^\]]+\]:\s+\S+", body)
if m:
    body = body[: m.start()]
body = body.strip() + "\n"
sys.stdout.write(f"# {ver}\n\n{body}")
PY
}

if git rev-parse "$TAG" >/dev/null 2>&1; then
  echo "error: git tag $TAG already exists" >&2
  exit 1
fi

extract_notes > "$NOTES"
echo "release notes preview:"
sed 's/^/  /' "$NOTES"

run() {
  if [[ "$DRY_RUN" -eq 1 ]]; then
    echo "dry-run: $*"
  else
    "$@"
  fi
}

echo "== build =="
run bash "$ROOT/scripts/build-image.sh" "${BUILD_ARGS[@]+"${BUILD_ARGS[@]}"}"

if [[ "$DRY_RUN" -eq 0 ]]; then
  docker tag "$LOCAL_IMAGE" "$VERSIONED_IMAGE"
  echo "tagged $VERSIONED_IMAGE"
else
  echo "dry-run: docker tag $LOCAL_IMAGE $VERSIONED_IMAGE"
fi

if [[ "$SKIP_NAS" -eq 0 ]]; then
  echo "== NAS registry =="
  run env TAGS="$VERSION latest" LOCAL_IMAGE="$LOCAL_IMAGE" \
    bash "$ROOT/scripts/publish-registry.sh"
else
  echo "skip NAS (--skip-nas)"
fi

if [[ "$SKIP_GHCR" -eq 0 ]]; then
  echo "== GHCR =="
  run env LOCAL_IMAGE="$LOCAL_IMAGE" bash "$ROOT/scripts/publish-ghcr.sh" "$VERSION"
else
  echo "skip GHCR (--skip-ghcr)"
fi

echo "== tarball =="
run env IMAGE="$VERSIONED_IMAGE" bash "$ROOT/scripts/save-image.sh" "$ROOT/$TAR"

echo "== git tag + GitHub Release =="
if [[ "$DRY_RUN" -eq 1 ]]; then
  echo "dry-run: git tag -a $TAG -m $TAG"
  echo "dry-run: git push origin $TAG"
  echo "dry-run: gh release create $TAG --title $TAG --notes-file … $TAR"
else
  if ! command -v gh >/dev/null 2>&1; then
    echo "error: gh CLI required for GitHub Release" >&2
    exit 1
  fi
  git tag -a "$TAG" -m "$TAG"
  git push origin "$TAG"
  gh release create "$TAG" \
    --title "$TAG" \
    --notes-file "$NOTES" \
    "$ROOT/$TAR"
fi

echo "OK — $TAG"
echo "  GHCR:  ghcr.io/cypoe/koru-orisha-media:${VERSION}"
echo "  asset: $TAR"
echo "  NAS:   recreate / nas-deploy when ready (tags pushed; stack not recreated)"

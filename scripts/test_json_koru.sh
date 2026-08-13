#!/usr/bin/env bash
# Run vendor/json Koru tests ported from W:\src\koru-libs\yyjson\tests
# (basic.kz + features.kz). Phantom Doc negatives are not applicable.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
export PATH="${HOME}/tools/zig-0.15.1:${HOME}/src/koru-build/zig-out/bin:${PATH}"

if ! command -v koruc >/dev/null 2>&1; then
  echo "skip json koru tests: koruc not on PATH" >&2
  exit 2
fi

KORUC="$(command -v koruc)"
STD="${HOME}/src/koru-build/koru_std"
if [[ ! -d "$STD" ]]; then
  STD="/usr/local/koru_std"
fi
JSON="$ROOT/vendor/json"
if [[ ! -d "$JSON" ]]; then
  echo "missing vendor/json" >&2
  exit 1
fi

OUTDIR=$(mktemp -d)
trap 'rm -rf "$OUTDIR"' EXIT

cat > "$OUTDIR/koru.json" <<EOF
{
  "name": "koru-json-tests",
  "version": "0.1.0",
  "paths": {
    "std": "$STD",
    "json": "$JSON"
  }
}
EOF
mkdir -p "$OUTDIR/tests"
cp "$JSON/tests/"*.kz "$OUTDIR/tests/"
cd "$OUTDIR"

run_one() {
  local name="$1"
  local expected="$JSON/tests/${name}.expected"
  "$KORUC" "tests/${name}.kz"
  local bin=""
  if [[ -f a.out ]]; then
    bin=a.out
  elif [[ -f "tests/a.out" ]]; then
    bin=tests/a.out
  else
    echo "json koru ${name}: expected a.out missing" >&2
    find . -name a.out >&2 || true
    exit 1
  fi
  local got
  got="$("./$bin")"
  local want
  want="$(cat "$expected")"
  if [[ "$got" != "$want" ]]; then
    echo "json koru ${name}: output mismatch" >&2
    echo "--- got ---" >&2
    printf '%s\n' "$got" >&2
    echo "--- want ---" >&2
    printf '%s\n' "$want" >&2
    exit 1
  fi
  echo "json koru ${name}: OK"
  rm -f a.out tests/a.out
}

run_one basic
run_one features
echo "vendor/json yyjson-port tests OK"

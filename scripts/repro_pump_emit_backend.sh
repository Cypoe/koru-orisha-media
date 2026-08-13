#!/usr/bin/env bash
# Split-stage INTREE/G pump emit: frontend then backend, as requested.
# koruc -o backend.zig  = frontend only (parse → backend.zig + program.ast.json)
# zig build             = compile ./backend
# ./backend output      = emit + compile output_emitted.zig  (Zig diagnostics live here)
set -u
KORUC="${KORUC:-$(command -v koruc)}"
STD="${STD:-/usr/local/koru_std}"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
OUT="${ARTIFACT_DIR:-$ROOT/pump-emit-artifacts}"
ORISHA_LIB="${ORISHA_LIB:-/src/orisha/lib}"
if [[ ! -d "$ORISHA_LIB" ]]; then ORISHA_LIB=/mnt/w/src/orisha/lib; fi

if [[ ! -x "$KORUC" ]]; then
  echo "no koruc" >&2
  exit 2
fi
if [[ ! -d "$ORISHA_LIB" ]]; then
  echo "no ORISHA_LIB at $ORISHA_LIB" >&2
  exit 2
fi

mkdir -p "${HOME}/lib/pkgconfig"
ln -sfn /usr/lib/x86_64-linux-gnu/libz.so.1 "${HOME}/lib/libz.so" 2>/dev/null || true
export LIBRARY_PATH="${HOME}/lib${LIBRARY_PATH:+:$LIBRARY_PATH}"
export LD_LIBRARY_PATH="${HOME}/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
cat >"${HOME}/lib/pkgconfig/zlib.pc" <<'PC'
prefix=/usr
exec_prefix=${prefix}
libdir=/usr/lib/x86_64-linux-gnu
includedir=/usr/include
Name: zlib
Description: zlib
Version: 1.2.11
Libs: -lz
Cflags:
PC
export PKG_CONFIG_PATH="${HOME}/lib/pkgconfig${PKG_CONFIG_PATH:+:$PKG_CONFIG_PATH}"

echo "=== pins ==="
echo "koruc=$KORUC"
"$KORUC" --version || true
sha256sum "$KORUC" 2>/dev/null || shasum -a 256 "$KORUC" 2>/dev/null || true
zig version
echo "ORISHA_LIB=$ORISHA_LIB"
ls -l "$ORISHA_LIB"
echo "STD=$STD"
echo

write_main_serve() {
  cat >"$1/main.k" <<'EOF'
import orisha
orisha:handler -> { status: 200, body: "ok", content_type: "text/plain" }
orisha:serve(port: 3090)
| shutdown _ |> _
| failed _ |> _
EOF
}

write_main_loop() {
  cat >"$1/main.k" <<'EOF'
import orisha
orisha:handler -> { status: 200, body: "ok", content_type: "text/plain" }
orisha:run-accept-loop(port: 3090)
EOF
}

run_split() {
  local name="$1"
  local dir="$2"
  local art="$OUT/$name"
  rm -rf "$art"
  mkdir -p "$art"
  echo "=== $name  dir=$dir ==="
  (
    cd "$dir" || exit 1
    echo "-- frontend: koruc -o backend.zig main.k --"
    "$KORUC" -o backend.zig main.k >"$art/frontend.log" 2>&1
    local fec=$?
    echo "frontend exit=$fec"
    tail -20 "$art/frontend.log"
    ls -l backend.zig program.ast.json build_backend.zig 2>/dev/null || true
    if [[ "$fec" -ne 0 ]]; then
      echo "frontend failed; skipping backend"
      echo "frontend_exit=$fec" >"$art/STATUS.txt"
      exit 0
    fi

    echo "-- zig build --build-file build_backend.zig --"
    zig build --build-file build_backend.zig >"$art/zig-build-backend.log" 2>&1
    local zec=$?
    echo "zig build backend exit=$zec"
    tail -30 "$art/zig-build-backend.log"
    if [[ "$zec" -ne 0 ]]; then
      echo "backend compile failed"
      echo "zig_build_backend_exit=$zec" >"$art/STATUS.txt"
      exit 0
    fi

    local backend_bin=""
    if [[ -x zig-out/bin/backend ]]; then
      backend_bin=zig-out/bin/backend
    elif [[ -x ./backend ]]; then
      backend_bin=./backend
    fi
    if [[ -z "$backend_bin" ]]; then
      echo "no backend binary"
      find zig-out -type f 2>/dev/null | head
      echo "no_backend_bin" >"$art/STATUS.txt"
      exit 0
    fi
    cp -f "$backend_bin" "$dir/backend"
    chmod +x "$dir/backend"

    echo "-- ./backend output --"
    ./backend output >"$art/backend.out" 2>"$art/backend.err"
    local bec=$?
    echo "backend output exit=$bec"
    echo "backend_output_exit=$bec" >"$art/STATUS.txt"
    echo "--- backend.err (head) ---"
    head -80 "$art/backend.err"
    echo "--- backend.out (head) ---"
    head -40 "$art/backend.out"
    if [[ -f output_emitted.zig ]]; then
      cp -f output_emitted.zig "$art/output_emitted.zig"
      echo "output_emitted.zig bytes=$(wc -c < output_emitted.zig)"
      echo "koru_pump mentions=$(grep -c 'pub const koru_pump' output_emitted.zig || true)"
      echo "duplicate lines=$(grep -c 'duplicate struct member' "$art/backend.err" || true)"
      echo "ambiguous lines=$(grep -c 'ambiguous reference' "$art/backend.err" || true)"
    else
      echo "no output_emitted.zig"
    fi
    # Keep a small excerpt of koru_pump from the emitted Zig if present.
    if [[ -f output_emitted.zig ]]; then
      grep -n "pub const koru_pump\|duplicate struct member\|ambiguous reference" \
        output_emitted.zig "$art/backend.err" 2>/dev/null | head -40 \
        >"$art/excerpt.txt" || true
    fi
  )
  echo
}

mkdir -p "$OUT"

# INTREE: original orisha/lib + serve
intree=$(mktemp -d /tmp/pump-split-INTREE.XXXXXX)
mkdir -p "$intree"
cp -a "$ORISHA_LIB" "$intree/lib"
cat >"$intree/koru.json" <<EOF
{
  "name": "orisha-intree",
  "version": "0.1.0",
  "paths": { "std": "$STD", "orisha": "lib" }
}
EOF
write_main_serve "$intree"
run_split INTREE "$intree"

# G: this vendor + unused sibling pump + run-accept-loop
if [[ -d "$ROOT/vendor/orisha" && -f "$ORISHA_LIB/pump.kz" ]]; then
  gdir=$(mktemp -d /tmp/pump-split-G.XXXXXX)
  mkdir -p "$gdir/vendor"
  cp -a "$ROOT/vendor/orisha" "$gdir/vendor/orisha"
  cp -a "$ORISHA_LIB/pump.k" "$gdir/vendor/orisha/pump.k"
  cp -a "$ORISHA_LIB/pump.kz" "$gdir/vendor/orisha/pump.kz"
  cat >"$gdir/koru.json" <<EOF
{
  "name": "pump-emit-G",
  "version": "0.0.1",
  "paths": { "std": "$STD", "orisha": "./vendor/orisha" }
}
EOF
  write_main_loop "$gdir"
  run_split G "$gdir"
fi

echo "=== artifacts in $OUT ==="
find "$OUT" -type f | sort
echo DONE

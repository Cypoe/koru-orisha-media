#!/usr/bin/env bash
# Isolated repros for pump/companion emit against current koruc.
# Not the media app. Exit 0 = all cases behaved as labeled.
set -u
export PATH="${HOME}/tools/zig-0.15.1:${HOME}/src/koru-build/zig-out/bin:${PATH}"
KORUC="${KORUC:-$(command -v koruc)}"
STD="${HOME}/src/koru-build/koru_std"
if [[ ! -d "$STD" ]]; then STD="/usr/local/koru_std"; fi
if [[ ! -x "$KORUC" ]]; then
  echo "no koruc" >&2
  exit 2
fi

echo "koruc=$KORUC"
"$KORUC" --version 2>/dev/null || true

# Frontend only, then the backend stage that emits/compiles output_emitted.zig.
# `koruc -o backend.zig` matches --help (emit .zig). Bare `koruc main.k` on 0.1.7
# also chains this pipeline; -o makes the split unambiguous.
compile_koru_program() {
  rm -f frontend.log backend.err backend.out
  "$KORUC" -o backend.zig main.k >frontend.log 2>&1
  local fec=$?
  if [[ "$fec" -ne 0 ]]; then
    return "$fec"
  fi
  zig build --build-file build_backend.zig >>frontend.log 2>&1
  local zec=$?
  if [[ "$zec" -ne 0 ]]; then
    return "$zec"
  fi
  local bin=zig-out/bin/backend
  if [[ ! -x "$bin" ]]; then bin=./backend; fi
  if [[ ! -x "$bin" ]]; then
    echo "no backend binary" >>frontend.log
    return 2
  fi
  cp -f "$bin" ./backend
  chmod +x ./backend
  ./backend output >backend.out 2>backend.err
}

run_case() {
  local name="$1" expect="$2" setup="$3"
  local tmp
  tmp=$(mktemp -d /tmp/pump-emit-"$name".XXXXXX)
  mkdir -p "$tmp/lib"
  cat >"$tmp/koru.json" <<EOF
{
  "name": "pump-emit-$name",
  "version": "0.0.1",
  "paths": { "std": "$STD", "lib": "./lib" }
}
EOF
  CASE_DIR="$tmp" eval "$setup"
  (cd "$tmp" && compile_koru_program)
  local ec=$?
  local dup amb ok
  dup=0
  amb=0
  if [[ -f "$tmp/backend.err" ]]; then
    dup=$(grep -c "duplicate struct member" "$tmp/backend.err" || true)
    amb=$(grep -c "ambiguous reference" "$tmp/backend.err" || true)
  fi
  ok=0
  if [[ "$ec" -eq 0 ]]; then ok=1; fi
  printf 'CASE %s expect=%s exit=%s duplicate=%s ambiguous=%s dir=%s\n' \
    "$name" "$expect" "$ec" "$dup" "$amb" "$tmp"
  if [[ -f "$tmp/backend.err" ]] && grep -E "duplicate struct member|ambiguous reference" "$tmp/backend.err" | head -20; then
    :
  elif [[ "$ok" -eq 1 ]]; then
    echo "  linked OK"
  else
    echo "  --- frontend.log tail ---"
    tail -20 "$tmp/frontend.log"
    if [[ -f "$tmp/backend.err" ]]; then
      echo "  --- backend.err tail ---"
      tail -20 "$tmp/backend.err"
    fi
  fi
  echo
}

write_tiny_index() {
  cat >"$CASE_DIR/lib/index.k" <<'EOF'
import std/io
pub tor ping {}
EOF
  cat >"$CASE_DIR/lib/index.kz" <<'EOF'
const std = @import("std");
~proc ping|zig {
    _ = std;
    return {};
}
EOF
}

write_tiny_pump() {
  cat >"$CASE_DIR/lib/pump.k" <<'EOF'
pub tor run {}
EOF
  cat >"$CASE_DIR/lib/pump.kz" <<'EOF'
const std = @import("std");
~proc run|zig {
    _ = std;
    return {};
}
EOF
}

write_orisha_shaped_pump() {
  cat >"$CASE_DIR/lib/pump.k" <<'EOF'
pub tor run {}
EOF
  cat >"$CASE_DIR/lib/pump.kz" <<'EOF'
const std = @import("std");
const posix = std.posix;
const c = std.c;
~proc run|zig {
    _ = posix;
    _ = c;
    return {};
}
EOF
}

write_main_ping() {
  cat >"$CASE_DIR/main.k" <<'EOF'
import lib
lib:ping()
EOF
}

write_main_pump() {
  cat >"$CASE_DIR/main.k" <<'EOF'
import lib
lib/pump:run()
EOF
}

if [[ "${SKIP_TINY:-}" != 1 ]]; then
echo "=== A2: sibling pump with posix/c aliases (orisha pump.kz shape), no import ==="
run_case A2 "if-bug-ambiguous" 'write_tiny_index; write_orisha_shaped_pump; write_main_ping'

echo "=== A4: parent AND sibling both declare std+posix+c (orisha index.kz ∩ pump.kz) ==="
run_case A4 "if-bug-ambiguous" '
cat >"$CASE_DIR/lib/index.k" <<EOF
pub tor ping {}
EOF
cat >"$CASE_DIR/lib/index.kz" <<EOF
const std = @import("std");
const posix = std.posix;
const c = std.c;
~proc ping|zig {
    _ = posix;
    _ = c;
    return {};
}
EOF
write_orisha_shaped_pump
write_main_ping
'

echo "=== B: index.k imports lib/pump, app calls ping only ==="
run_case B "if-bug-dup-koru_pump" 'write_tiny_index; write_tiny_pump; printf "import lib/pump\n" | cat - "$CASE_DIR/lib/index.k" >"$CASE_DIR/lib/index.k.tmp" && mv "$CASE_DIR/lib/index.k.tmp" "$CASE_DIR/lib/index.k"; write_main_ping'

echo "=== C: index.k imports lib/pump, app calls pump:run ==="
run_case C "if-bug-dup-koru_pump" 'write_tiny_index; write_tiny_pump; printf "import lib/pump\n" | cat - "$CASE_DIR/lib/index.k" >"$CASE_DIR/lib/index.k.tmp" && mv "$CASE_DIR/lib/index.k.tmp" "$CASE_DIR/lib/index.k"; write_main_pump'

echo "=== D: 110_030 shape (.kz only, index imports sibling) ==="
run_case D "should-link" '
cat >"$CASE_DIR/lib/index.kz" <<EOF
~import lib/helper
const std = @import("std");
~pub tor greet {}
~proc greet|zig { _ = std; return {}; }
EOF
cat >"$CASE_DIR/lib/helper.kz" <<EOF
const std = @import("std");
~pub tor helper-say {}
~proc helper-say|zig { _ = std; return {}; }
EOF
cat >"$CASE_DIR/main.k" <<EOF
import lib
lib:greet()
EOF
'

echo "=== E: companion split index.k+.kz, NO pump files ==="
run_case E "should-link" 'write_tiny_index; write_main_ping'
fi

# --- vendor / upstream orisha (needs zlib, like the media binary) ---
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
mkdir -p "${HOME}/lib" "${HOME}/lib/pkgconfig"
ln -sfn /usr/lib/x86_64-linux-gnu/libz.so.1 "${HOME}/lib/libz.so" 2>/dev/null || true
export LIBRARY_PATH="${HOME}/lib${LIBRARY_PATH:+:$LIBRARY_PATH}"
export LD_LIBRARY_PATH="${HOME}/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
if [[ ! -f "${HOME}/lib/pkgconfig/zlib.pc" ]]; then
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
fi
export PKG_CONFIG_PATH="${HOME}/lib/pkgconfig${PKG_CONFIG_PATH:+:$PKG_CONFIG_PATH}"

write_orisha_main_loop() {
  cat >"$CASE_DIR/main.k" <<'EOF'
import orisha
orisha:handler -> { status: 200, body: "ok", content_type: "text/plain" }
orisha:run-accept-loop(port: 3090)
EOF
}

write_orisha_main_serve() {
  cat >"$CASE_DIR/main.k" <<'EOF'
import orisha
orisha:handler -> { status: 200, body: "ok", content_type: "text/plain" }
orisha:serve(port: 3090)
| shutdown _ |> _
| failed _ |> _
EOF
}

run_orisha_case() {
  local name="$1" expect="$2" setup="$3"
  local tmp
  tmp=$(mktemp -d /tmp/pump-emit-"$name".XXXXXX)
  CASE_DIR="$tmp"
  eval "$setup"
  cat >"$tmp/koru.json" <<EOF
{
  "name": "pump-emit-$name",
  "version": "0.0.1",
  "paths": { "std": "$STD", "orisha": "./vendor/orisha" }
}
EOF
  (cd "$tmp" && compile_koru_program)
  local ec=$?
  local dup amb
  dup=0
  amb=0
  if [[ -f "$tmp/backend.err" ]]; then
    dup=$(grep -c "duplicate struct member" "$tmp/backend.err" || true)
    amb=$(grep -c "ambiguous reference" "$tmp/backend.err" || true)
  fi
  printf 'CASE %s expect=%s exit=%s duplicate=%s ambiguous=%s dir=%s\n' \
    "$name" "$expect" "$ec" "$dup" "$amb" "$tmp"
  if [[ -f "$tmp/backend.err" ]]; then
    grep -E "duplicate struct member|ambiguous reference" "$tmp/backend.err" | head -8 || true
  fi
  if [[ "$ec" -ne 0 && "$dup" -eq 0 && "$amb" -eq 0 ]]; then
    echo "  --- other failure ---"
    if [[ -f "$tmp/backend.err" ]]; then
      grep -E "error:|✗" "$tmp/backend.err" | head -15 || tail -15 "$tmp/backend.err"
    else
      grep -E "error:|✗" "$tmp/frontend.log" | head -15 || tail -15 "$tmp/frontend.log"
    fi
  fi
  if [[ -d /work ]]; then
    mkdir -p "/work/pump-emit-artifacts/$name"
    [[ -f "$tmp/frontend.log" ]] && cp -f "$tmp/frontend.log" "/work/pump-emit-artifacts/$name/"
    [[ -f "$tmp/backend.err" ]] && cp -f "$tmp/backend.err" "/work/pump-emit-artifacts/$name/"
    [[ -f "$tmp/output_emitted.zig" ]] && cp -f "$tmp/output_emitted.zig" "/work/pump-emit-artifacts/$name/"
  fi
  echo
}

if [[ "${SKIP_ORISHA:-}" != 1 ]]; then
echo "=== F: this vendor orisha (no pump files) + run-accept-loop — control ==="
run_orisha_case F "should-link" '
mkdir -p "$CASE_DIR/vendor"
cp -a "$ROOT/vendor/orisha" "$CASE_DIR/vendor/orisha"
write_orisha_main_loop
'

echo "=== G: vendor orisha + upstream pump as sibling, no import, run-accept-loop ==="
run_orisha_case G "ambiguous-std" '
mkdir -p "$CASE_DIR/vendor"
cp -a "$ROOT/vendor/orisha" "$CASE_DIR/vendor/orisha"
cp -a "$ROOT/vendor/upstream/orisha-pump/pump.k" "$CASE_DIR/vendor/orisha/pump.k"
cp -a "$ROOT/vendor/upstream/orisha-pump/pump.kz" "$CASE_DIR/vendor/orisha/pump.kz"
write_orisha_main_loop
'

setup_H() {
  mkdir -p "$CASE_DIR/vendor"
  cp -a "$ROOT/vendor/orisha" "$CASE_DIR/vendor/orisha"
  cp -a "$ROOT/vendor/upstream/orisha-pump/pump.k" "$CASE_DIR/vendor/orisha/pump.k"
  cp -a "$ROOT/vendor/upstream/orisha-pump/pump.kz" "$CASE_DIR/vendor/orisha/pump.kz"
  if ! grep -q 'import orisha/pump' "$CASE_DIR/vendor/orisha/index.k"; then
    awk '1; /^import std\/build$/ && !x {print "import orisha/pump"; x=1}' \
      "$CASE_DIR/vendor/orisha/index.k" >"$CASE_DIR/vendor/orisha/index.k.tmp"
    mv "$CASE_DIR/vendor/orisha/index.k.tmp" "$CASE_DIR/vendor/orisha/index.k"
  fi
  write_orisha_main_loop
}

echo "=== H: vendor orisha + pump sibling + import orisha/pump, run-accept-loop ==="
run_orisha_case H "dup-koru_pump" 'setup_H'

ORISHA_LIB="${ORISHA_LIB:-/mnt/w/src/orisha/lib}"
if [[ ! -d "$ORISHA_LIB" && -d /src/orisha/lib ]]; then
  ORISHA_LIB=/src/orisha/lib
fi

setup_I() {
  mkdir -p "$CASE_DIR/vendor"
  echo "ORISHA_LIB=$ORISHA_LIB"
  cp -a "$ORISHA_LIB" "$CASE_DIR/vendor/orisha"
  write_orisha_main_serve
}

echo "=== I: upstream orisha lib + serve ==="
run_orisha_case I "duplicate-koru_pump" 'setup_I'

ORISHA_ROOT="${ORISHA_ROOT:-}"
if [[ -z "$ORISHA_ROOT" && -d /src/orisha/lib ]]; then
  ORISHA_ROOT=/src/orisha
elif [[ -z "$ORISHA_ROOT" && -d /mnt/w/src/orisha/lib ]]; then
  ORISHA_ROOT=/mnt/w/src/orisha
fi
if [[ -n "$ORISHA_ROOT" && -d "$ORISHA_ROOT/lib" ]]; then
echo "=== INTREE: original orisha tree (orisha=lib) + serve ==="
  tmp=$(mktemp -d /tmp/pump-emit-INTREE.XXXXXX)
  CASE_DIR="$tmp"
  echo "ORISHA_ROOT=$ORISHA_ROOT"
  mkdir -p "$tmp"
  cp -a "$ORISHA_ROOT/lib" "$tmp/lib"
  cat >"$tmp/koru.json" <<EOF
{
  "name": "pump-emit-INTREE",
  "version": "0.0.1",
  "paths": { "std": "$STD", "orisha": "lib" }
}
EOF
  write_orisha_main_serve
  (cd "$tmp" && compile_koru_program)
  ec=$?
  dup=0
  amb=0
  if [[ -f "$tmp/backend.err" ]]; then
    dup=$(grep -c "duplicate struct member" "$tmp/backend.err" || true)
    amb=$(grep -c "ambiguous reference" "$tmp/backend.err" || true)
  fi
  printf 'CASE INTREE expect=duplicate-koru_pump exit=%s duplicate=%s ambiguous=%s dir=%s\n' \
    "$ec" "$dup" "$amb" "$tmp"
  if [[ -f "$tmp/backend.err" ]]; then
    grep -E "duplicate struct member|ambiguous reference" "$tmp/backend.err" | head -8 || true
  fi
  if [[ "$ec" -ne 0 && "$dup" -eq 0 && "$amb" -eq 0 ]]; then
    echo "  --- other failure ---"
    tail -15 "$tmp/frontend.log"
    [[ -f "$tmp/backend.err" ]] && tail -15 "$tmp/backend.err"
  fi
  if [[ -d /work ]]; then
    mkdir -p /work/pump-emit-artifacts/INTREE
    [[ -f "$tmp/backend.err" ]] && cp -f "$tmp/backend.err" /work/pump-emit-artifacts/INTREE/
    [[ -f "$tmp/output_emitted.zig" ]] && cp -f "$tmp/output_emitted.zig" /work/pump-emit-artifacts/INTREE/
  fi
  echo
fi
fi


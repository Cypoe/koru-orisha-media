#!/usr/bin/env bash
# Always-on Step 9 emit checks (no Chromium). Full keyed DOM ops: test_keyed_list.mjs
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
JS_HOST="$ROOT/public/enhance.js"
JS="$ROOT/public/koru-dom-enhance.js"
if [[ ! -f "$JS" || ! -f "$JS_HOST" ]]; then
  echo "missing emit — run bash scripts/build-frontend.sh" >&2
  exit 2
fi
sz=$(wc -c < "$JS")
szh=$(wc -c < "$JS_HOST")
[[ "$sz" -gt 5000 ]] || { echo "koru-dom-enhance.js too small ($sz)"; exit 1; }
[[ "$szh" -gt 500 ]] || { echo "enhance.js too small ($szh)"; exit 1; }
for needle in __koru_dom_track koruDomNode LibRow seed swap-rows data-action; do
  grep -q "$needle" "$JS" || { echo "missing symbol: $needle"; exit 1; }
done
for needle in isSafeSwapTarget playerIdentityOk localStorage; do
  grep -q "$needle" "$JS_HOST" || { echo "missing host symbol: $needle"; exit 1; }
done
grep -q 'main_module.flow0()' "$JS_HOST" || { echo "host emit missing startup flow0()"; exit 1; }
grep -q 'run_event.handler(' "$JS_HOST" || { echo "host emit missing koru/htmx run_event.handler call"; exit 1; }
grep -q 'enhance_player_event.handler(' "$JS_HOST" || { echo "host emit missing enhance_player_event.handler call"; exit 1; }
grep -q 'id="koru-list"' "$ROOT/public/enhance-demo.html"
grep -q 'koru-dom-enhance.js' "$ROOT/public/enhance-demo.html"
echo "koru/dom emit OK (host $szh bytes, keyed $sz bytes + demo html)"

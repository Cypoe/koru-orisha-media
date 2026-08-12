#!/usr/bin/env bash
# Always-on Step 9 emit checks (no browser). Full keyed DOM ops: test_keyed_list.mjs
set -euo pipefail
REPO=/mnt/c/Users/fabi0/repos/koru-orisha-media
JS="$REPO/public/koru-dom-enhance.js"
if [[ ! -f "$JS" ]]; then
  echo "missing $JS — run bash scripts/build-browser.sh" >&2
  exit 2
fi
sz=$(wc -c < "$JS")
[[ "$sz" -gt 5000 ]] || { echo "koru-dom-enhance.js too small ($sz)"; exit 1; }
for needle in __koru_dom_track koruDomNode LibRow seed swap-rows data-action; do
  grep -q "$needle" "$JS" || { echo "missing symbol: $needle"; exit 1; }
done
grep -q 'id="koru-list"' "$REPO/public/enhance-demo.html"
grep -q 'koru-dom-enhance.js' "$REPO/public/enhance-demo.html"
echo "koru/dom emit OK ($sz bytes + demo html)"

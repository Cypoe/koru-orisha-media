#!/usr/bin/env bash
set -euo pipefail
ID=m_994718
BASE=http://127.0.0.1:3090

echo '--- HEAD -I'
curl -sS -I "$BASE/media/$ID"

echo '--- Range 2-5'
curl -sS -D- -H 'Range: bytes=2-5' "$BASE/media/$ID" -o /tmp/r.bin | head -20
echo -n 'body='
xxd -p /tmp/r.bin
echo

echo '--- 416'
curl -sS -D- -H 'Range: bytes=99-100' "$BASE/media/$ID" -o /dev/null | head -15

echo '--- smoke'
curl -sS -o /dev/null -w '%{http_code}\n' "$BASE/smoke.html"

echo '--- missing'
curl -sS -o /dev/null -w '%{http_code}\n' "$BASE/item/nope"

echo '--- GET vs HEAD meta'
GET_META=$(curl -sS -D- -o /tmp/g.bin "$BASE/media/$ID" | tr -d '\r' | grep -E '^(Content-Type|Content-Length|Accept-Ranges|ETag):')
HEAD_META=$(curl -sS -I "$BASE/media/$ID" | tr -d '\r' | grep -E '^(Content-Type|Content-Length|Accept-Ranges|ETag):')
echo "GET:"
echo "$GET_META"
echo "HEAD:"
echo "$HEAD_META"
if [ "$GET_META" = "$HEAD_META" ]; then echo 'META_OK'; else echo 'META_MISMATCH'; exit 1; fi

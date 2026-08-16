#!/usr/bin/env bash
set -euo pipefail
ID=m_994718
echo '--- /item'
curl -sS "http://127.0.0.1:3090/item/$ID"
echo
echo '--- /play'
curl -sS "http://127.0.0.1:3090/play/$ID"
echo
echo '--- GET /media'
curl -sS -D- "http://127.0.0.1:3090/media/$ID" -o /tmp/media.bin | head -20
echo "body_bytes=$(wc -c </tmp/media.bin)"
xxd -p /tmp/media.bin || true
echo '--- HEAD /media'
curl -sS -D- -o /dev/null -X HEAD "http://127.0.0.1:3090/media/$ID" | head -20
echo '--- Range 2-5'
curl -sS -D- -H 'Range: bytes=2-5' "http://127.0.0.1:3090/media/$ID" -o /tmp/r.bin | head -20
xxd -p /tmp/r.bin || true
echo '--- Range bad'
curl -sS -D- -H 'Range: bytes=99-100' "http://127.0.0.1:3090/media/$ID" -o /dev/null | head -15
echo '--- smoke'
curl -sS -o /dev/null -w '%{http_code}\n' http://127.0.0.1:3090/smoke.html
echo '--- missing item'
curl -sS -o /dev/null -w '%{http_code}\n' http://127.0.0.1:3090/item/nope

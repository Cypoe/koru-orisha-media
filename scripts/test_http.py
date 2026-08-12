#!/usr/bin/env python3
"""HTTP integration tests — expects server already listening on BASE (default :3091).

Prefer: bash scripts/test_all.sh (starts Docker, runs this, tears down).
"""
from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).absolute().parent.parent
BASE = os.environ.get("KORU_TEST_BASE", "http://127.0.0.1:3091")


def http(method: str, path: str, headers: dict | None = None) -> tuple[int, dict[str, str], bytes]:
    req = urllib.request.Request(BASE + path, method=method, headers=headers or {})
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            hdrs = {k.lower(): v for k, v in resp.headers.items()}
            return resp.status, hdrs, resp.read()
    except urllib.error.HTTPError as e:
        hdrs = {k.lower(): v for k, v in e.headers.items()}
        return e.code, hdrs, e.read()


def main() -> int:
    mode = os.environ.get("KORU_TEST_MODE", "fixture")
    failures = 0

    def check(cond: bool, msg: str) -> None:
        nonlocal failures
        if not cond:
            print(f"FAIL: {msg}", file=sys.stderr)
            failures += 1
        else:
            print(f"ok: {msg}")

    if mode == "fixture":
        manifest = json.loads((ROOT / "data" / "manifest.json").read_text(encoding="utf-8"))
        demo = next(e for e in manifest["entries"] if e["title"] == "demo")
        demo_id = demo["id"]
        empty = next(e for e in manifest["entries"] if e["title"] == "empty")
        one = next(e for e in manifest["entries"] if e["title"] == "onebyte")

        st, hdrs, body = http("GET", "/library")
        check(st == 200, f"GET /library -> {st}")
        check(f"/item/{demo_id}".encode() in body, "library links to item")
        check(b"sort title" in body and b"fragment" in body, "sort/filter/fragment affordances")
        check(b'hx-get=' in body and b'hx-target="#library-list"' in body, "library hx-* attrs")
        check(b"<form" in body and b'name="q"' in body, "library search form")
        check("link" in hdrs and "self" in hdrs["link"], f"Link header on library: {hdrs.get('link')}")

        st, _, body = http("GET", f"/item/{demo_id}")
        check(st == 200 and b"/watch/" in body, "item page")
        check(b"container: mp4" in body, "item shows container")
        check(b"/art/" + demo_id.encode() in body, "item links poster art")
        check(b"/library/movie" in body, "item related kind collection")

        st, hdrs, art = http("GET", f"/art/{demo_id}")
        check(st == 200 and art.startswith(b"\xff\xd8"), "art jpeg body")
        check("image/" in hdrs.get("content-type", ""), f"art content-type: {hdrs.get('content-type')}")

        st, _, body = http("GET", "/library?limit=2")
        check(st == 200 and b"pagination" in body and b"next" in body, "pagination next link")

        st, _, prefer_body = http("GET", "/library?q=demo", headers={"Prefer": "return=minimal"})
        check(st == 200 and b'id="library-list"' in prefer_body, "Prefer return=minimal fragment")
        check(b"<h1>Library</h1>" not in prefer_body, "Prefer fragment is not full page")

        st, _, hx_body = http("GET", "/library?q=demo", headers={"HX-Request": "true"})
        check(st == 200 and b'id="library-list"' in hx_body, "HX-Request fragment")
        check(b"<h1>Library</h1>" not in hx_body, "HX-Request fragment is not full page")

        st, _, frag = http("GET", "/fragments/library")
        check(st == 200 and b'id="library-list"' in frag, "library fragment")
        check(b'id="player"' not in frag, "fragment has no player")

        st, hdrs, body = http("GET", f"/media/{demo_id}?download=1")
        check(st == 200 and body == b"hello world\n", "download body")
        check("attachment" in hdrs.get("content-disposition", ""), "Content-Disposition attachment")

        st, _, body = http("GET", f"/watch/{demo_id}")
        check(st == 200 and b'id="player"' in body, "watch page has player")
        check(b'class="capability"' not in body, "mp4 watch has no capability warning")

        st, hdrs, body = http("GET", f"/media/{demo_id}")
        check(st == 200 and body == b"hello world\n", "GET media body")
        check(hdrs.get("accept-ranges") == "bytes", "Accept-Ranges")
        check("last-modified" in hdrs, "Last-Modified present")
        check("etag" in hdrs, "ETag present")
        etag = hdrs["etag"].strip().strip('"')
        st304, _, body304 = http("GET", f"/media/{demo_id}", headers={"If-None-Match": f'"{etag}"'})
        check(st304 == 304 and body304 == b"", "If-None-Match 304")

        st_h, hdrs_h, body_h = http("HEAD", f"/media/{demo_id}")
        check(st_h == 200 and body_h == b"", "HEAD empty body")
        for k in ("content-type", "content-length", "accept-ranges", "etag"):
            check(hdrs.get(k) == hdrs_h.get(k), f"HEAD≡GET {k}")

        st, hdrs, body = http("GET", f"/media/{demo_id}", headers={"Range": "bytes=2-5"})
        check(st == 206 and body == b"llo ", "Range 206 body")
        check(hdrs.get("content-range", "").startswith("bytes 2-5/"), "Content-Range")

        st, _, _ = http("GET", f"/media/{demo_id}", headers={"Range": "bytes=99-100"})
        check(st == 416, "unsatisfiable range")

        st, _, _ = http("GET", "/item/nope")
        check(st == 404, "missing item")

        st, hdrs, _ = http("OPTIONS", f"/media/{demo_id}")
        check(st in (200, 204) and "GET" in hdrs.get("allow", ""), f"OPTIONS Allow={hdrs.get('allow')}")

        st, hdrs, body = http("GET", f"/media/{empty['id']}")
        check(st == 200 and body == b"" and hdrs.get("content-length") == "0", "empty file")

        st, _, body = http("GET", f"/media/{one['id']}")
        check(st == 200 and body == b"y", "one-byte file")

        st, _, body = http("GET", "/library?q=demo")
        check(st == 200 and demo_id.encode() in body, "filter q=demo")

        st, _, body = http("GET", "/library?sort=id")
        check(st == 200, "sort=id")

        odd = next((e for e in manifest["entries"] if e["title"] == "odd"), None)
        if odd:
            st, _, body = http("GET", f"/watch/{odd['id']}")
            check(st == 200 and b'class="capability"' in body, "mkv watch capability warning")
        else:
            check(False, "odd.mkv fixture present in manifest")

        arrival = next((e for e in manifest["entries"] if "2016" in e.get("title", "")), None)
        if arrival and arrival.get("year") == 2016:
            st, _, body = http("GET", f"/item/{arrival['id']}")
            check(st == 200 and b"year: 2016" in body, "item shows year")
        else:
            check(False, "Arrival (2016) fixture with year in manifest")

        st, hdrs, body = http("GET", "/enhance.js")
        check(st == 200 and b"localStorage" in body, "enhance.js served")
        check(b"application/javascript" in hdrs.get("content-type", "").encode() or "javascript" in hdrs.get("content-type", ""), "enhance content-type")

        st, _, body = http("GET", "/koru-dom-enhance.js")
        check(st == 200 and b"__koru_dom_track" in body, "koru-dom-enhance.js served")

        st, _, body = http("GET", "/enhance-demo.html")
        check(st == 200 and b'id="koru-list"' in body and b"/koru-dom-enhance.js" in body, "enhance-demo.html served")

        st, _, body = http("GET", "/library")
        check(b"/enhance.js" in body and b"hx-get=" in body, "library progressive enhance hooks")

        st, _, body = http("GET", f"/watch/{demo_id}")
        check(b'data-media-id="' + demo_id.encode() in body and b"/enhance.js" in body, "watch resume hooks")

    elif mode == "security":
        st, _, body = http("GET", "/library")
        check(st == 200, "security library")
        check(b"<script>" not in body, "raw script tag absent")
        check(b"&lt;script&gt;" in body, "escaped script title")
        st, _, _ = http("GET", "/media/m_trav")
        check(st == 403, "traversal path forbidden")

    else:
        print(f"unknown mode {mode}", file=sys.stderr)
        return 2

    if failures:
        print(f"{failures} failure(s)", file=sys.stderr)
        return 1
    print("ALL OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

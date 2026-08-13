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
        manifest = json.loads((ROOT / "fixtures" / "manifest.json").read_text(encoding="utf-8"))
        demo = next(e for e in manifest["entries"] if e["title"] == "demo")
        demo_id = demo["id"]
        empty = next(e for e in manifest["entries"] if e["title"] == "empty")
        one = next(e for e in manifest["entries"] if e["title"] == "onebyte")
        beep = next((e for e in manifest["entries"] if e.get("kind") == "audio"), None)

        st, hdrs, body = http("GET", "/library")
        check(st == 200, f"GET /library -> {st}")
        check(f"/item/{demo_id}".encode() in body, "library links to item")
        check(b"sort title" in body and b"fragment" in body, "sort/filter/fragment affordances")
        check(b'hx-get=' in body and b'hx-target="#library-region"' in body, "library hx-* attrs")
        check(b'id="library-region"' in body and b'id="library-list"' in body, "library-region wraps list")
        check(f"/watch/{demo_id}".encode() in body, "library row watch affordance")
        check(b"<form" in body and b'name="q"' in body, "library search form")
        check("link" in hdrs and "self" in hdrs["link"], f"Link header on library: {hdrs.get('link')}")
        check(b"class=\"archive-note\"" in body and b"projection index" in body, "library names catalogue overlay when index exists")

        st, hdrs, body = http("GET", "/library/movie")
        check(st == 200 and "Library — movie".encode() in body, "kind collection title")
        check("link" in hdrs and "/library/movie" in hdrs["link"] and "self" in hdrs["link"], f"kind Link self: {hdrs.get('link')}")
        check(b"<strong>movies</strong>" in body and b'href="/library/audio"' in body, "kind nav marks movies + audio")
        check(b'href="/library"' in body and b"class=\"kinds\"" in body, "kind up/all affordances")

        st, _, body = http("GET", "/library/audio")
        check(st == 200 and b"<strong>audio</strong>" in body, "audio kind marked active")
        if beep:
            check(beep["id"].encode() in body and b'id="library-list"' in body, "audio collection lists fixture")
            check(b'class="empty"' not in body, "audio collection not empty-only")
        else:
            check(False, "audio fixture present in manifest")

        st, _, body = http("GET", "/library/tv")
        check(st == 200 and b'class="empty"' in body and b"No items in this collection" in body, "empty kind collection state")

        st, _, body = http("GET", "/library?q=zzznomatch")
        check(st == 200 and b'class="empty"' in body and b"No titles match" in body, "search zero state")
        check(b"Clear search" in body or b"clear search" in body, "search zero clear link")
        check(b'value="zzznomatch"' in body, "search form preserves q")

        st, _, body = http("GET", f"/item/{demo_id}")
        check(st == 200 and b"/watch/" in body, "item page")
        check(b"container" in body and b"<code>mp4</code>" in body, "item shows container")
        check(b'class="probe"' in body and b"brand <code>isom</code>" in body, "item shows probe brand")
        check(b"video codec not probed" in body, "item shows honest unknown codec")
        check(b"/art/" + demo_id.encode() in body, "item links poster art")
        check(b"/library/movie" in body, "item related kind collection")
        check(f"/subtitles/{demo_id}".encode() in body and b">subtitles</a>" in body, "item links subtitles")

        st, hdrs, art = http("GET", f"/art/{demo_id}")
        check(st == 200 and art.startswith(b"\xff\xd8"), "art jpeg body")
        check("image/" in hdrs.get("content-type", ""), f"art content-type: {hdrs.get('content-type')}")

        st, _, body = http("GET", "/library?limit=2")
        check(st == 200 and b"pagination" in body and b"next" in body, "pagination next link")
        check(b"sort=title" in body and b"offset=2" in body, "pagination preserves sort")

        st, _, body = http("GET", "/library?sort=id&q=demo&limit=2")
        check(st == 200, "paginated filtered library")
        if b"pagination" in body:
            check(b"sort=id" in body and b"q=demo" in body, "pagination preserves sort+q")

        st, _, prefer_body = http("GET", "/library?q=demo", headers={"Prefer": "return=minimal"})
        check(st == 200 and b'id="library-region"' in prefer_body, "Prefer return=minimal fragment")
        check(b"<h1>Library</h1>" not in prefer_body, "Prefer fragment is not full page")

        st, _, hx_body = http("GET", "/library?q=demo", headers={"HX-Request": "true"})
        check(st == 200 and b'id="library-region"' in hx_body, "HX-Request fragment")
        check(b"<h1>Library</h1>" not in hx_body, "HX-Request fragment is not full page")

        st, _, frag = http("GET", "/fragments/library")
        check(st == 200 and b'id="library-region"' in frag and b'id="library-list"' in frag, "library fragment")
        check(b'id="player"' not in frag, "fragment has no player")

        st, hdrs, body = http("GET", f"/media/{demo_id}?download=1")
        check(st == 200 and body == b"hello world\n", "download body")
        check("attachment" in hdrs.get("content-disposition", ""), "Content-Disposition attachment")

        st, _, body = http("GET", f"/watch/{demo_id}")
        check(st == 200 and b'id="player"' in body, "watch page has player")
        check(b'class="capability"' not in body, "mp4 watch has no capability warning")
        check(b'class="probe"' in body and b"brand <code>isom</code>" in body, "mp4 watch shows probe brand")
        check(b'id="library-region"' in body and b"More in collection" in body, "watch related shelf")
        check(b'hx-target="#library-region"' in body, "watch shelf hx target")
        player_at = body.find(b'id="player"')
        region_at = body.find(b'id="library-region"')
        check(player_at != -1 and region_at != -1 and player_at < region_at, "player precedes library-region")
        check(b'<track kind="subtitles"' in body and f'/subtitles/{demo_id}'.encode() in body, "watch video has subtitle track")
        check(f'/subtitles/{demo_id}'.encode() in body and b">subtitles</a>" in body, "watch links subtitles")

        st, hdrs, vtt = http("GET", f"/subtitles/{demo_id}")
        check(st == 200 and vtt.startswith(b"WEBVTT"), "subtitles VTT body")
        check("text/vtt" in hdrs.get("content-type", ""), f"subtitles content-type: {hdrs.get('content-type')}")

        st, _, _ = http("GET", f"/subtitles/{one['id']}")
        check(st == 404, "missing subtitles 404")

        if beep:
            st, _, body = http("GET", f"/watch/{beep['id']}")
            check(st == 200 and b"<audio id=\"player\"" in body, "audio watch uses audio element")
            check(b"<track " not in body, "audio watch has no subtitle track")
            st, hdrs, abody = http("GET", f"/media/{beep['id']}")
            check(st == 200 and len(abody) > 0 and "audio/" in hdrs.get("content-type", ""), "GET audio media")


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
            st, hdrs, body = http("GET", f"/item/{arrival['id']}")
            check(st == 200 and b"year 2016" in body, "item shows year")
            check(b"video <code>hevc</code>" in body and b"audio <code>aac</code>" in body, "item shows nested codecs")
            check(b">Arrival<" in body and b"Arrival (2016)" in body, "item semantic title vs filename")
            check(b"themoviedb.org/movie/329865" in body and b">TMDB<" in body, "item TMDB link")
            check(b"imdb.com/title/tt2543164" in body and b">IMDb<" in body, "item IMDb link")
            check(b'class="catalogue"' in body and b">Catalogue<" in body, "item catalogue pane")
            check(b'class="overview"' in body and b"hand-linked provider" in body, "item catalogue overview")
            check(b'class="archive"' in body and b">Local archive<" in body, "item local archive pane")
            check(b"movies/Arrival (2016).mp4" in body, "item archive path")
            check(b"size " in body and b" bytes" in body, "item archive byte size")
            check(b"container" in body and b"<code>mp4</code>" in body, "item archive container")
            link = hdrs.get("link", "")
            check("themoviedb.org" in link and "imdb.com" in link, "item Link related providers")
            check("format=jsonld" in link and "application/ld+json" in link, "item JSON-LD alternate Link")
            st, jhdrs, jbody = http("GET", f"/item/{arrival['id']}?format=jsonld")
            check(st == 200 and "ld+json" in jhdrs.get("content-type", ""), "jsonld content-type")
            check(b'"@type":"Movie"' in jbody and b"imdb.com" in jbody and b"themoviedb.org" in jbody, "jsonld movie sameAs")
            st, _, abody = http("GET", f"/item/{arrival['id']}", headers={"Accept": "application/json"})
            check(st == 200 and b'"@type":"Movie"' in abody, "Accept application/json jsonld")
            st, _, wbody = http("GET", f"/watch/{arrival['id']}")
            check(st == 200 and b'class="probe"' in wbody and b"video <code>hevc</code>" in wbody, "watch shows nested codecs")
            check(b">TMDB<" in wbody and b">IMDb<" in wbody, "watch provider line")
            check(b'class="catalogue"' in wbody and b'class="archive"' in wbody, "watch catalogue vs archive")
            check(b"Arrival (2016)" in wbody and b"size " in wbody and b" bytes" in wbody, "watch archive filename+bytes")
            check(b'id="player"' in wbody, "watch player intact with semantic line")
        else:
            check(False, "Arrival (2016) fixture with year in manifest")

        st, hdrs, body = http("GET", "/enhance.js")
        check(st == 200 and b"localStorage" in body, "enhance.js served")
        check(b"isSafeSwapTarget" in body and b"playerIdentityOk" in body, "enhance player identity guards")
        check(b"#library-region" in body and b"performance.mark" in body, "enhance region + measure marks")
        check(b"application/javascript" in hdrs.get("content-type", "").encode() or "javascript" in hdrs.get("content-type", ""), "enhance content-type")

        st, hdrs, body = http("GET", "/app.css")
        check(st == 200 and b"--ink" in body, "app.css served")
        check("text/css" in hdrs.get("content-type", ""), "app.css content-type")

        st, _, body = http("GET", "/")
        check(st == 200 and b"Koru Media" in body and b"/app.css" in body and b"Open library" in body, "home brand surface")
        check(b"Local movies" in body and b"Arrival (2016)" in body and demo_id.encode() in body, "home lists local movies")
        check(f"/watch/{demo_id}".encode() in body, "home local movies are playable")
        check(b"class=\"archive-note\"" in body and b"projection index" in body, "home names catalogue overlay when index exists")
        check(b">TMDB<" not in body, "home is not a TMDB grid")

        st, _, body = http("GET", "/koru-dom-enhance.js")
        check(st == 200 and b"__koru_dom_track" in body, "koru-dom-enhance.js served")

        st, _, body = http("GET", "/enhance-demo.html")
        check(st == 200 and b'id="koru-list"' in body and b"/koru-dom-enhance.js" in body, "enhance-demo.html served")

        st, _, body = http("GET", "/library")
        check(b"/enhance.js" in body and b"/app.css" in body and b"hx-get=" in body, "library progressive enhance hooks")

        st, _, body = http("GET", f"/item/{demo_id}")
        check(b"/enhance.js" in body and b"/app.css" in body and b"item-actions" in body, "item page enhance + css")
        check(b">TMDB<" not in body and b">IMDb<" not in body and b"themoviedb.org" not in body, "demo item has no provider links")
        check(b'class="catalogue"' not in body and b'class="archive"' not in body, "demo item has no catalogue/archive split")
        check(b">Local archive<" not in body, "demo item has no archive heading")
        st, _, jdemo = http("GET", f"/item/{demo_id}?format=jsonld")
        check(st == 404, "demo jsonld absent")

        st, _, body = http("GET", f"/watch/{demo_id}")
        check(b'data-media-id="' + demo_id.encode() in body and b"/enhance.js" in body and b"/app.css" in body, "watch resume hooks")
        check(b'id="resume-ui"' in body and b'id="player"' in body, "watch resume-ui beside player")
        check(b'class="catalogue"' not in body and b">TMDB<" not in body, "demo watch has no catalogue overlay")
        player_at = body.find(b'id="player"')
        resume_at = body.find(b'id="resume-ui"')
        check(player_at != -1 and resume_at != -1 and player_at < resume_at, "player precedes resume-ui")

        st, _, body = http("GET", "/enhance.js")
        check(b"showResumeUi" in body and b"resume-ui" in body, "enhance resume UI helper")

        arrival = next((e for e in manifest["entries"] if e.get("year") == 2016), None)
        if arrival:
            st, _, body = http("GET", "/library")
            check(" · 2016".encode() in body, "library row shows year")
        else:
            check(False, "year fixture for library row")

    elif mode == "security":
        st, _, body = http("GET", "/library")
        check(st == 200, "security library")
        check(b"<script>" not in body, "raw script tag absent")
        check(b"&lt;script&gt;" in body, "escaped script title")
        st, _, _ = http("GET", "/media/m_trav")
        check(st == 403, "traversal path forbidden")
        st, _, body = http("GET", "/item/m_xss")
        check(b">TMDB<" not in body and b"themoviedb.org" not in body, "missing semantic snapshot: no provider links")
        check(b'class="catalogue"' not in body and b'class="archive"' not in body, "missing semantic snapshot: no catalogue split")

    elif mode == "nonsemantic":
        manifest = json.loads((ROOT / "fixtures" / "manifest.json").read_text(encoding="utf-8"))
        arrival = next((e for e in manifest["entries"] if e.get("year") == 2016), None)
        demo = next(e for e in manifest["entries"] if e["title"] == "demo")
        if not arrival:
            check(False, "Arrival fixture in manifest")
        else:
            st, _, body = http("GET", f"/item/{arrival['id']}")
            check(st == 200 and b"Arrival (2016)" in body, "missing semantic: physical title")
            check(b">TMDB<" not in body and b">IMDb<" not in body and b"themoviedb.org" not in body, "missing semantic: no provider links")
            check(b'class="catalogue"' not in body and b'class="archive"' not in body, "missing semantic: physical HTML only")
            check(b"container" in body and b"<code>mp4</code>" in body, "missing semantic: container still shown")
            st, _, jbody = http("GET", f"/item/{arrival['id']}?format=jsonld")
            check(st == 404, "missing semantic: jsonld absent")
            st, _, wbody = http("GET", f"/watch/{arrival['id']}")
            check(st == 200 and b'id="player"' in wbody, "missing semantic: watch still plays")
            check(b">TMDB<" not in wbody, "missing semantic: watch has no providers")
        st, _, body = http("GET", f"/media/{demo['id']}")
        check(st == 200 and body == b"hello world\n", "missing semantic: physical playback")
        st, _, home = http("GET", "/")
        check(st == 200 and b"Open library" in home, "missing semantic: home still serves")
        check(b"Arrival (2016)" in home and demo["id"].encode() in home, "missing semantic: home lists local movies")
        check(f"/watch/{demo['id']}".encode() in home, "missing semantic: home movies are playable")
        check(b">TMDB<" not in home and b">IMDb<" not in home and b"themoviedb.org" not in home, "missing semantic: home has no catalogue chips")
        check(b"class=\"archive-note\"" in home and b"without a catalogue fetch" in home, "missing semantic: home is local archive")
        st, _, lib = http("GET", "/library")
        check(st == 200 and b"Arrival (2016)" in lib and demo["id"].encode() in lib, "missing semantic: library lists local files")
        check(f"/watch/{demo['id']}".encode() in lib, "missing semantic: library watch affordance")
        check(b">TMDB<" not in lib and b'class="catalogue"' not in lib, "missing semantic: library has no catalogue chips")
        check(b"without a catalogue fetch" in lib, "missing semantic: library is local archive")
        st, _, movies = http("GET", "/library/movie")
        check(st == 200 and b"Arrival (2016)" in movies and demo["id"].encode() in movies, "missing semantic: movie collection lists local files")
        check(b">TMDB<" not in movies, "missing semantic: movie collection has no catalogue chips")

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

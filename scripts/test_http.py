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


def http(method: str, path: str, headers: dict | None = None, data: bytes | None = None) -> tuple[int, dict[str, str], bytes]:
    hdrs = dict(headers or {})
    if data is not None and not any(k.lower() == "content-type" for k in hdrs):
        hdrs["Content-Type"] = "application/x-www-form-urlencoded"
    req = urllib.request.Request(BASE + path, data=data, method=method, headers=hdrs)
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
        beep = next((e for e in manifest["entries"] if e["title"] == "beep"), None)
        andor_ep = next(e for e in manifest["entries"] if e["id"] == "m_and1e1")
        ost = next(e for e in manifest["entries"] if e["id"] == "m_andost")

        page_open = (ROOT / "public" / "fragments" / "layout" / "page-open.html").read_text(encoding="utf-8")
        check("{{title}}" in page_open and "favicon.svg" in page_open, "page-open fragment has title + favicon")
        chrome_end = (ROOT / "public" / "fragments" / "layout" / "chrome-end.html").read_text(encoding="utf-8")
        check("persist-now" not in chrome_end and "persist-inner" in chrome_end, "chrome-end persist dock has no play-page button")
        check(chrome_end.lstrip().startswith("</div>"), "chrome-end closes the library region before persist")
        check('<button type="button" class="icon-btn persist-max"' in chrome_end, "persist maximize is a button")
        check('<button type="button" class="icon-btn persist-close"' in chrome_end, "persist close is a button")
        check('id="persist-max" href' not in chrome_end, "persist maximize is not a link")
        hero_slide = (ROOT / "public" / "fragments" / "components" / "hero-slide.html").read_text(encoding="utf-8")
        check("hero-info" in hero_slide and "{{id}}" in hero_slide, "hero-slide fragment is slotted")
        check("hero-info" in hero_slide and "{{heart}}" in hero_slide, "hero-slide has Info + heart")
        poster_card = (ROOT / "public" / "fragments" / "components" / "poster-card.html").read_text(encoding="utf-8")
        check("poster-tags" in poster_card and "{{tags}}" in poster_card, "poster-card landmark has quality tags")
        check("poster-caption" in poster_card and "poster-year" in poster_card, "poster-card shows title and year")
        check("kind-toolbar" in (ROOT / "public" / "fragments" / "components" / "kind-toolbar.html").read_text(encoding="utf-8"), "kind toolbar fragment exists")
        check("music-row" in (ROOT / "public" / "fragments" / "components" / "music-row.html").read_text(encoding="utf-8"), "music list row fragment exists")
        check("search-page" in (ROOT / "public" / "fragments" / "pages" / "search-open.html").read_text(encoding="utf-8"), "search page fragment exists")
        check("search-idle" in (ROOT / "public" / "fragments" / "pages" / "search-idle.html").read_text(encoding="utf-8"), "search idle fragment exists")
        check("my-media" in (ROOT / "public" / "fragments" / "components" / "my-media-open.html").read_text(encoding="utf-8"), "my-media fragment exists")
        play_heading = (ROOT / "public" / "fragments" / "components" / "play-heading.html").read_text(encoding="utf-8")
        check("play-title" in play_heading and "Back to {{label}}" in play_heading, "play-heading landmark is title + back")
        check("More {{label}}" not in play_heading, "play-heading has no duplicate library button")
        item_heading = (ROOT / "public" / "fragments" / "components" / "item-heading.html").read_text(encoding="utf-8")
        check("Back to {{label}}" in item_heading and "{{title}}" in item_heading, "item-heading landmark is title + collection back")
        episode_item = (ROOT / "public" / "fragments" / "components" / "episode-item.html").read_text(encoding="utf-8")
        check("{{current}}" in episode_item and "{{aria}}" in episode_item, "episode-item landmark can mark the current row")

        st, hdrs, body = http("GET", "/library")
        check(st == 200, f"GET /library -> {st}")
        check(f"/item/{demo_id}".encode() in body, "library links to item")
        check(b'hx-get=' in body and b'hx-target="#library-region"' in body, "library hx-* attrs")
        check(b"sidebar-nav" in body and b'href="/library/movie"' in body, "kind nav present")
        check(b'data-nav="home"' in body and b'data-nav="settings"' in body, "nav items carry icon keys")
        check(b'href="/settings"' in body and b">Settings<" in body, "sidebar includes Settings")
        check(b'<span class="kinds">' not in body, "topbar has no duplicate kind row")
        check(b">Home<" in body and b'href="/library"' in body, "sidebar includes Home")
        check(b">Library<" in body or b"<strong>Library</strong>" in body, "sidebar includes Library")
        check(b">Discover<" not in body, "sidebar Home is not labeled Discover")
        check(b"sort title" not in body and b"filter demo" not in body and b"page size 2" not in body, "demo sort/filter affordances absent")
        check(b'id="library-region"' in body and b'id="library-list"' in body, "library-region wraps list")
        check(b'class="poster-link" href="/play/' not in body, "library cards have no under-card play link")
        check(b'class="topbar-search"' in body and b'name="q"' in body, "topbar has a typeable search field")
        check(b'id="topbar-back"' in body, "topbar has a back slot")
        check(b"topbar-tools" in body, "topbar clusters floating controls")
        check(b'id="nav-toggle"' in body, "chrome has hamburger")
        check(b"sidebar-head" in body, "hamburger lives in the sidebar head")
        check(b"top-pills" not in body, "topbar has no Home/Favourites pills")
        check(b'data-nav="favourites"' not in body, "sidebar has no Favourites destination")
        check(b"kind-toolbar" in body and b">Shuffle<" in body and b">Sort<" in body and b">Filter<" in body, "library hub has Shuffle/Sort/Filter")
        check(b">All<" in body and b'data-filter-fav' in body, "library hub has All and Favourites chips")
        check("link" in hdrs and "self" in hdrs["link"], f"Link header on library: {hdrs.get('link')}")
        check(b"class=\"archive-note\"" not in body, "library has no archive status prose")

        st, hdrs, body = http("GET", "/library/movie")
        check(st == 200 and b"<h1>Movies</h1>" in body, "kind collection title")
        check("link" in hdrs and "/library/movie" in hdrs["link"] and "self" in hdrs["link"], f"kind Link self: {hdrs.get('link')}")
        check(b"<strong>Movies</strong>" in body and b'href="/library/audio"' in body, "kind nav marks movies + audio")
        check(b"sidebar-nav" in body and b">Home<" in body and b">Library<" in body, "sidebar Home + Library + kinds")
        check(b"kind-toolbar" in body and b"kind-count" in body, "movie kind page has toolbar + count")
        check(b">Shuffle<" in body and b">Sort<" in body and b">Filter<" in body, "movie toolbar has shuffle/sort/filter")
        check(b'data-filter-fav' in body and b">Favourites<" in body, "movie toolbar has a Favourites chip")
        check(b'class="badge kind-movie"' in body and b">watch</a>" not in body, "movie cards are poster+badge only")
        check(b"poster-tags" in body and b'class="badge tag tag-3d"' in body and b">3D<" in body, "movie posters show 3D quality pills from the filename")
        check(b"poster-caption" in body and b"poster-title" in body, "movie posters show title under the card")

        st, _, body = http("GET", "/library/audio")
        check(st == 200 and b"<strong>Music</strong>" in body, "audio kind marked active")
        check(b"kind-toolbar" in body, "music collection has the kind toolbar")
        if beep:
            check(beep["id"].encode() in body and b'id="library-list"' in body, "audio collection lists fixture")
            check(b'class="empty"' not in body, "audio collection not empty-only")
            check(b'aria-label="Discovery"' in body, "music groups album-level work")
            check(body.count(b'class="music-row"') == 2, "music shows beep + one album row")
            check(b"music-title" in body and b"music-artist" in body, "music rows have title and artist")
            check(b">One More Time<" not in body and b">Aerodynamic<" not in body, "music does not list tracks as works")
        else:
            check(False, "audio fixture present in manifest")

        st, _, body = http("GET", "/library/tv")
        check(st == 200 and b"<h1>Series</h1>" in body, "series collection title")
        check(b"kind-toolbar" in body, "series collection has the kind toolbar")
        check(b'class="empty"' not in body, "series collection is not empty")
        check(body.count(b'class="poster-card"') == 1, "series shows one poster per work")
        check(b'aria-label="Andor"' in body and b'class="badge kind-tv"' in body, "series card is Andor with SERIES badge")
        check(b"poster-title" in body, "series cards show title under the poster")
        check(andor_ep["id"].encode() in body, "series card links a work file")
        check(ost["id"].encode() not in body, "soundtrack extra is not a series card")
        check(b">Kassa<" not in body and b">One Way Out<" not in body, "series does not list episodes as works")
        check(b"(tv)" not in body and b">watch</a>" not in body, "series cards drop raw kind and watch link")

        st, _, body = http("GET", "/library/book")
        check(st == 200 and b'class="empty"' in body and b"No items in this collection" in body, "empty kind collection state")

        st, _, body = http("GET", "/library?q=zzznomatch")
        check(st == 200 and b'class="empty"' in body and b"No titles match" in body, "search zero state")
        check(b"Clear search" in body or b"clear search" in body, "search zero clear link")
        check(b"zzznomatch" in body, "kind search empty state echoes q")

        st, _, body = http("GET", f"/item/{demo_id}")
        check(st == 200 and b"/play/" in body, "item page")
        check(b"container" in body and b"<code>mp4</code>" in body, "item shows container")
        check(b'class="probe"' in body and b"brand <code>isom</code>" in body, "item shows probe brand")
        check(b"video codec not probed" in body, "item shows honest unknown codec")
        check(b"/art/" + demo_id.encode() in body, "item links poster art")
        check(b"/library/movie" in body, "item related kind collection")
        check(f"/subtitles/{demo_id}".encode() in body and b">subtitles</a>" in body, "item links subtitles")
        check(b">Play</a>" in body and b"play-now" in body, "item CTA is Play")
        check(b"Back to Movies" in body and b"More Movies" not in body, "item has collection back, not More Movies")
        check(b'id="topbar-back"' in body and b"topbar-back-link" in body, "item back lives in the topbar")
        check(b">Library</a>" not in body, "item page has no Library button")
        check(b'id="persist"' in body, "item chrome has persist player")
        check(b"item-hero" in body, "item uses the backdrop hero skin")

        st, _, body = http("GET", f"/item/{andor_ep['id']}")
        check(st == 200 and b">Andor</h1>" in body, "series item uses work title")
        check(b"Back to Series" in body, "series item backs to the series collection")
        check(b"<h2>Season 1</h2>" in body and b"<h2>Season 2</h2>" in body, "series item lists seasons")
        check(b'class="episode-list"' in body, "series item has episode list")
        check(f"/play/{andor_ep['id']}".encode() in body, "episode click goes to watch")
        check(b"/play/m_and1e2" in body and b"/play/m_and2e1" in body, "all parsed episodes link to watch")
        check("E01 · Kassa".encode() in body and "E02 · That Would Be Me".encode() in body, "episode labels from SxxEyy")
        check(b"<h2>Soundtracks</h2>" in body and ost["id"].encode() in body, "soundtrack lives under Soundtracks")
        check(b"Andor (Main Title Theme)" in body, "extras section names the soundtrack")
        check(b"<h2>Episodes</h2>" not in body, "soundtrack is not dumped as uncategorized episodes")

        st, _, play_ep = http("GET", f"/play/{andor_ep['id']}")
        check(st == 200 and b'data-rel="next"' in play_ep, "andor E01 play has relate(next)")
        check(b"play-title" in play_ep and b"Back to Series" in play_ep, "play heading is item + series back")
        check(b"More Series" not in play_ep, "play heading has a single back control")
        check(b'class="player-skip"' in play_ep, "episode skip controls sit on the right of the player bar")
        check(b"/play/m_and1e2" in play_ep and b"Next episode" in play_ep, "andor E01 next is E02")
        check(b"<h2>Season 1</h2>" in play_ep, "episode play lists the current season")
        check(b'<details class="season-block" open>' in play_ep, "current season is expanded")
        check(b'aria-current="page"' in play_ep and b"is-current" in play_ep, "current episode is highlighted")
        check(b'<details class="extra-block">' in play_ep, "non-current extras stay collapsed")
        check(b'class="season-block"' in play_ep, "play season headings are collapsible")
        check(b"/watch/" not in play_ep, "andor play has no /watch/")
        st, _, play_e2 = http("GET", "/play/m_and1e2")
        check(st == 200 and b'data-rel="previous"' in play_e2, "andor E02 play has relate(previous)")
        check(b"/play/m_and1e1" in play_e2 and b"Previous episode" in play_e2, "andor E02 previous is E01")
        check(b"/play/m_and2e1" in play_e2 and b"Next episode" in play_e2, "andor E02 next is S02E01")
        st, _, play_ost = http("GET", f"/play/{ost['id']}")
        check(st == 200 and b'<details class="extra-block" open>' in play_ost, "playing a soundtrack expands that extra list")
        check(b'aria-current="page"' in play_ost, "playing a soundtrack highlights that extra row")
        check(b"extra-list" in body, "extras use a named list not poster dump")
        check(b"<h2>Trailers</h2>" in body and b"m_andtrl" in body, "trailer extras are their own list")

        st, _, av_body = http("GET", "/item/m_avflat")
        check(st == 200 and b'class="edition-select"' in av_body, "movie item lists editions")
        check(b">Flat<" in av_body and b">3D HSBS<" in av_body, "3D and flat editions are named")
        check(b"/play/m_av3d" in av_body, "3D edition links to its watch page")
        check(b"?download=1" not in av_body.split(b"edition-select")[-1].split(b"</select>")[0] if b"edition-select" in av_body else True, "edition dropdown has no download links")
        check(b"<h2>Featurettes</h2>" in av_body and b"m_avfeat" in av_body, "featurette extras grouped")
        check(b"<h2>Documents</h2>" in av_body and b"m_avpdf" in av_body, "PDF extras grouped")
        check(b'<script type="application/ld+json">' in body, "series item embeds JSON-LD")
        check(b'"@type":"TVSeries"' in body and b'"name":"Andor"' in body, "series item JSON-LD is TVSeries")
        check(b"work.movie" not in body and b"/item/work." not in body, "series item does not leak work ids")
        check(b"A spy thriller set in the Star Wars universe." in body, "series item shows nfo work plot")
        check(b'class="overview"' in body, "series item plot uses overview")
        check(b"nfo-aired" in body and b"2022-09-21" in body, "series item shows nfo aired")
        check(b"nfo-rating" in body and b"8.4" in body, "series item shows nfo rating")
        check(b'class="btn trailer"' in body and b"/play/m_andtrl" in body, "series item trailer chip direct-plays")
        check(b"Cassian Andor's journey begins" not in body, "series item uses work plot not episode plot")

        st, jhdrs, jseries = http("GET", f"/item/{andor_ep['id']}?format=jsonld")
        check(st == 200 and "ld+json" in jhdrs.get("content-type", ""), "andor series jsonld content-type")
        check(b'"@type":"TVSeries"' in jseries and b'"name":"Andor"' in jseries, "andor series jsonld type+name")
        check(f'/media/{andor_ep["id"]}'.encode() in jseries, "andor series contentUrl is /media/{id}")
        check(b"tt9253284" in jseries, "andor series local imdb assertion")
        check(b"work.movie" not in jseries and b"work.tv" not in jseries and b"/item/work." not in jseries, "series jsonld keeps opaque m_* ids")
        check(b"themoviedb.org" not in jseries, "series jsonld does not invent TMDB")
        check(b'"description":"A spy thriller set in the Star Wars universe."' in jseries, "series jsonld description from nfo")
        check(b'"trailer"' in jseries and b"/media/m_andtrl" in jseries, "series jsonld trailer is local media")

        st, _, jep = http("GET", "/item/m_and1e2?format=jsonld")
        check(st == 200 and b'"@type":"TVEpisode"' in jep, "episode jsonld type")
        check(b'"name":"That Would Be Me"' in jep, "episode jsonld name")
        check(b'"episodeNumber":2' in jep and b'"seasonNumber":1' in jep, "episode season/episode numbers")
        check(b'"@type":"TVSeries"' in jep and b'"name":"Andor"' in jep, "episode partOfSeries")
        check(b"/media/m_and1e2" in jep, "episode contentUrl is the file")
        check(b"/item/m_and1e1" in jep, "episode partOfSeries url is the work item")
        check(b"work.movie" not in jep and b"/item/work." not in jep, "episode jsonld keeps opaque m_* ids")

        st, _, jacc = http("GET", f"/item/{andor_ep['id']}", headers={"Accept": "application/ld+json"})
        check(st == 200 and b'"@type":"TVSeries"' in jacc, "Accept ld+json expands to series work")

        st, _, jmusic = http("GET", "/item/m_dpot?format=jsonld")
        check(st == 200 and b'"@type":"MusicRecording"' in jmusic, "music track jsonld")
        check(b"/media/m_dpot" in jmusic, "music contentUrl is /media/{id}")

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
        check(b"<!doctype" not in prefer_body and b"sidebar-nav" not in prefer_body, "Prefer fragment is not full page")
        check(b"<h1>Library</h1>" in prefer_body, "Prefer fragment includes library heading")

        st, _, hx_body = http("GET", "/library?q=demo", headers={"HX-Request": "true"})
        check(st == 200 and b'id="library-region"' in hx_body, "HX-Request fragment")
        check(b"<!doctype" not in hx_body and b"sidebar-nav" not in hx_body, "HX-Request fragment is not full page")

        st, _, frag = http("GET", "/fragments/library")
        check(st == 200 and b'id="library-region"' in frag and b'id="library-list"' in frag, "library fragment")
        check(b'id="player"' not in frag, "fragment has no player")

        st, hdrs, body = http("GET", f"/media/{demo_id}?download=1")
        check(st == 200 and body == b"hello world\n", "download body")
        check("attachment" in hdrs.get("content-disposition", ""), "Content-Disposition attachment")

        st, _, body = http("GET", f"/play/{demo_id}")
        check(st == 200 and b'id="player"' in body, "play page has player")
        check(b'class="capability"' not in body, "mp4 play has no capability warning")
        check(b'class="probe"' in body and b"brand <code>isom</code>" in body, "mp4 play shows probe brand")
        check(b'id="library-region"' in body and b"More in collection" in body, "play related shelf")
        check(b'id="player"' in body and b'id="persist"' in body, "play has stage player and persist dock")
        check(body.find(b'id="library-region"') < body.find(b'id="persist"'), "persist dock is outside the swap region")
        check(b'id="persist"' in body, "persist dock is present")
        check(b'id="persist-now"' not in body and b">Play page</a>" not in body, "persist dock has no play-page button")
        check(b'id="persist-close"' in body and b'id="persist-max"' in body, "persist dock has close and maximize")
        check(b'<track kind="subtitles"' in body and f'/subtitles/{demo_id}'.encode() in body, "play video has subtitle track")
        check(f'/subtitles/{demo_id}'.encode() in body and b">Subtitles</a>" in body, "play links subtitles")
        check(b'class="play kino"' in body or b"play kino" in body, "video play page is kino")
        check(b'id="kino-toggle"' in body and b'aria-label="Cinema mode"' in body, "video play has kino toggle")
        check(b">Cinema mode<" not in body, "kino toggle is an icon")
        check(b'class="player-bar"' in body, "play controls sit under the player")
        check(b"Back to Movies" in body and b"More Movies" not in body, "movie play has a single back control")
        check(b"topbar-logo" in body, "topbar has a compact logo for narrow chrome")
        check(b'id="persist"' in body, "play chrome has persist player")
        check(b"/watch/" not in body, "play page has no /watch/")
        check(b"stream URL" not in body, "play has no duplicate stream URL download")
        check(body.count(b"?download=1") == 1, "play has a single download control")

        st, hdrs, vtt = http("GET", f"/subtitles/{demo_id}")
        check(st == 200 and vtt.startswith(b"WEBVTT"), "subtitles VTT body")
        check("text/vtt" in hdrs.get("content-type", ""), f"subtitles content-type: {hdrs.get('content-type')}")

        st, _, _ = http("GET", f"/subtitles/{one['id']}")
        check(st == 404, "missing subtitles 404")

        if beep:
            st, _, body = http("GET", f"/play/{beep['id']}")
            check(st == 200 and b"<audio id=\"player\"" in body, "audio play uses audio element")
            check(b"<track " not in body, "audio play has no subtitle track")
            check(b"play kino" not in body, "audio play page does not force kino")
            check(b'id="kino-toggle"' in body, "audio play has cinema toggle")
            check(b'id="persist"' in body, "audio play chrome has persist player")
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
            st, _, body = http("GET", f"/play/{odd['id']}")
            check(st == 200 and b"may not play in the browser" in body, "mkv play capability warning")
            check(b"play-external" in body and b".m3u" in body and b'rel="dlna"' in body, "mkv offers host/DLNA play")
            check(b"stream URL" not in body, "mkv play has no duplicate stream URL")
            st, _, m3u = http("GET", f"/play/{odd['id']}.m3u")
            check(st == 200 and b"#EXTM3U" in m3u and f"/media/{odd['id']}".encode() in m3u, "play m3u playlist")
        else:
            check(False, "odd.mkv fixture present in manifest")

        arrival = next((e for e in manifest["entries"] if "2016" in e.get("title", "")), None)
        if arrival and arrival.get("year") == 2016:
            st, hdrs, body = http("GET", f"/item/{arrival['id']}")
            check(st == 200 and b"item-hero-meta" in body and b"2016" in body, "item shows year")
            check(b"video <code>hevc</code>" in body and b"audio <code>aac</code>" in body, "item shows nested codecs")
            check(b">Arrival<" in body and b"Arrival (2016)" in body, "item semantic title vs filename")
            check(b"themoviedb.org/movie/329865" in body and b">TMDB<" in body, "item TMDB link")
            check(b"imdb.com/title/tt2543164" in body and b">IMDb<" in body, "item IMDb link")
            check(b'class="catalogue"' in body and b">Catalogue<" in body, "item catalogue pane")
            check(b'class="overview"' in body and b"hand-linked provider" in body, "item catalogue overview")
            check(b">Local archive<" not in body and b'class="archive"' not in body, "item has no local archive pane")
            check(b"item-hero-stage" in body, "item banner copy sits on the backdrop")
            link = hdrs.get("link", "")
            check("themoviedb.org" in link and "imdb.com" in link, "item Link related providers")
            check("format=jsonld" in link and "application/ld+json" in link, "item JSON-LD alternate Link")
            check(b'<script type="application/ld+json">' in body and b'"@type":"Movie"' in body, "item HTML embeds Movie JSON-LD")
            st, jhdrs, jbody = http("GET", f"/item/{arrival['id']}?format=jsonld")
            check(st == 200 and "ld+json" in jhdrs.get("content-type", ""), "jsonld content-type")
            check(b'"@type":"Movie"' in jbody and b"imdb.com" in jbody and b"themoviedb.org" in jbody, "jsonld movie sameAs")
            st, _, abody = http("GET", f"/item/{arrival['id']}", headers={"Accept": "application/json"})
            check(st == 200 and b'"@type":"Movie"' in abody, "Accept application/json jsonld")
            st, _, wbody = http("GET", f"/play/{arrival['id']}")
            check(st == 200 and b'class="probe"' in wbody and b"video <code>hevc</code>" in wbody, "play shows nested codecs")
            check(b">TMDB<" in wbody and b">IMDb<" in wbody, "play provider line")
            check(b'class="catalogue"' in wbody and b'class="archive"' in wbody, "play catalogue vs archive")
            check(b"Arrival (2016)" in wbody and b"size " in wbody and b" bytes" in wbody, "play archive filename+bytes")
            check(b'id="player"' in wbody, "play player intact with semantic line")
        else:
            check(False, "Arrival (2016) fixture with year in manifest")

        st, hdrs, body = http("GET", "/enhance.js")
        check(st == 200 and b"localStorage" in body, "enhance.js served")
        check(b"modestbranding=1" in body and b"iv_load_policy=3" in body, "home youtube teaser hides player chrome")
        check(b"isSafeSwapTarget" in body and b"playerIdentityOk" in body, "enhance player identity guards")
        check(b"#persist" in body, "enhance persist player")
        check(b"popOutToPersist" in body and b"kino-toggle" in body, "enhance pops persist and binds kino")
        check(b"reclaimPlayer" in body and b"dismissPersist" in body, "enhance restores play without reload and dismisses the dock")
        check(b"openFullPlayer" in body and b"data-play" in body, "enhance maximize is a button that swaps play")
        check(b"data-dismissed" in body, "enhance does not resurrect a closed persist dock")
        check(b"clearPlayingHighlight" in body, "enhance drops the current-row highlight when playback ends")
        check(b"persist.contains" in body, "enhance persist identity")
        check(b"7000" in body and b"medushu-continue" in body, "enhance auto-advances the hero and fills Continue Watching")
        check(b"hero-prev" not in body, "enhance has no carousel prev/next")
        check(b"placeTopbarBack" in body, "enhance moves collection back into the topbar")
        check(b"bindMusicPlay" in body and b"popPersist" in body, "enhance plays music in the persist dock")
        check(b"setFavOnly" in body and b"kind-chip" in body, "enhance highlights All or Favourites, not both")
        check(b"bindKindMenus" in body, "enhance closes Sort when Filter opens")
        check(b"nav-collapsed" in body, "enhance can collapse the desktop sidebar")
        check(b"placeNavToggle" in body, "enhance lines the menu button up with the topbar logo")
        check(b"syncTopbarSearch" in body, "enhance keeps the topbar search in sync")
        check(b"syncNav" in body, "enhance syncs sidebar active after swap")
        check(b"content-home" in body, "enhance toggles home content padding after swap")
        check(b"medushu-hearts" in body and b"nav-toggle" in body, "enhance binds hearts and hamburger")
        check(b"appBase" in body and b"withAppBase" in body, "enhance reads html data-base")
        check(b"#library-region" in body and b"performance.mark" in body, "enhance region + measure marks")
        check(b"application/javascript" in hdrs.get("content-type", "").encode() or "javascript" in hdrs.get("content-type", ""), "enhance content-type")

        st, hdrs, body = http("GET", "/app.css")
        check(st == 200 and b"--ink" in body, "app.css served")
        check("text/css" in hdrs.get("content-type", ""), "app.css content-type")
        check(b"overflow-wrap: anywhere" in body and b"play-overlay" in body, "app.css wraps meta + hover play")
        check(b"::-webkit-scrollbar" in body and b"scrollbar-width" in body, "app.css styles dark scrollbars")
        check(b"hero-carousel" in body and b"kino-toggle" in body, "app.css has hero carousel + kino toggle")
        check(b"aspect-ratio: 16 / 9" in body and b"my-media" in body, "app.css uses a landscape hero with My Media tiles")
        check(b"video::-webkit-media-controls" not in body, "app.css does not paint WebKit media controls over the picture")
        check(b"max-width: 9.5rem" in body and b".poster-row .poster-card" in body, "home poster row keeps a uniform card width")
        check(b"item-hero-stage" in body and b"topbar-search" in body, "app.css overlays poster on the item banner")
        check(b"topbar-tools" in body, "app.css floats a compact topbar control cluster")
        check(b"topbar-search:focus-within" in body, "app.css expands collapsed mobile search on focus")
        check(b"container-name: chrome" in body, "app.css sizes topbar chrome from the main column")
        check(b"kind-toolbar" in body and b"music-row" in body, "app.css has kind toolbar + music rows")
        check(b"search-page" in body and b"hamburger" in body, "app.css has search page + hamburger chrome")
        check(b"sidebar-head" in body, "app.css places the hamburger in the sidebar head")
        check(b"nav-collapsed" in body and b"fav-only" in body, "app.css can collapse the desktop sidebar and filter Favourites")
        check(b"heart-btn[aria-pressed" in body and b"fill: currentColor" in body, "app.css fills the heart when favourited")
        check(b"player-bar" in body and b"icon-btn" in body, "app.css has player bar + kino icon")
        check(b"persist-close" in body and b"nav-icon" in body, "app.css has persist close + nav icons")
        check(b"--page-pad-x" in body, "app.css shares page gutters across layouts")
        check(b"layout.kino::before" in body, "kino dims sidebar and page body")
        check(b"layout.kino .main::before" not in body, "kino overlay is not limited to main")
        check(b"layout.kino .player-frame" in body, "kino keeps the video stage bright")
        check(b".layout.kino .content::after" not in body, "kino overlay does not cover the player bar")
        check(b".layout.kino form.search" in body, "kino dims the search field")
        check(b".player-skip" in body and b".play-title" in body, "app.css has play skip + title link")
        check(b".is-current" in body, "app.css highlights the current episode row")
        check(b".topbar-logo" in body, "app.css places a compact logo in the topbar")
        check(b".mount-name" in body and b".settings-section h2" in body, "app.css lays out settings fields")
        check(b".hint" in body and b"background-image" in body, "app.css styles hints and select chevrons")
        check(b"min(52rem" in body, "app.css persist player is large")
        check(b"hydrate-section" in body, "app.css pads the hydrate section")
        check(b"settings-page" in body and b"mount-card" in body, "app.css has settings chrome")
        check(b".poster-tags" in body and b".badge.tag" in body, "app.css stacks quality pills on posters")

        st, hdrs, body = http("GET", "/favicon.svg")
        check(st == 200 and b"<svg" in body, "favicon svg served")

        st, _, body = http("GET", "/")
        check(st == 200 and b"Medushu" in body and b"/app.css" in body and b"Recently added" in body, "home brand surface")
        check(b'id="kino-toggle"' in body, "home has cinema toggle")
        check(b"Recently added" in body and b'aria-label="Arrival (2016)"' in body and demo_id.encode() in body, "home lists local movies")
        check(f"/item/{demo_id}".encode() in body, "home local movies link to item")
        check(b"my-media" in body and b"my-media-tile" in body, "home hero has My Media tiles")
        check(b"data-continue" in body and b"Continue Watching" in body, "home has Continue Watching slot")
        check(b"hero-prev" not in body and b">Previous<" not in body, "home carousel has no Previous/Next buttons")
        check(b'class="topbar-search"' in body, "home topbar search is typeable")
        check(b"<h2>Movies</h2>" not in body and b"<h2>Series</h2>" not in body, "home has no per-mount poster shelves")
        check(b'class="poster-link" href="/play/' not in body, "home cards have no under-card play link")
        check(b'id="persist"' in body, "home chrome has persist player")
        check(b'data-hero="orisha.hero"' in body and b"hero-carousel" in body, "home has orisha.hero carousel")
        check(b"hero-info" in body and b"data-heart" in body, "home hero has Play/Info/heart")
        check(b"role=backdrop" in body or b"hero-poster" in body, "home hero prefers backdrop art")
        check(b"hero-teaser" in body or b"m_andtrl" in body, "home carousel can fade to a local trailer")
        check(b'id="persist"' in body, "home chrome has persist player")
        check(b'id="persist-now"' not in body, "home chrome has no persist play-page button")
        check(b"logo-mark" in body and b"/favicon.svg" in body, "home has logo mark + favicon")
        check(b"topbar-logo" in body, "home topbar has a compact logo")
        check(b">Home<" in body and b">Library<" in body, "home sidebar has Home and Library")
        check(b'data-home-view="home"' in body and b'data-home-view="favourites"' in body, "home has Home/Favourites view chips")
        check(b'href="/library?fav=1"' in body, "home Favourites opens the library with Favourites on")
        check(b'data-nav="favourites"' not in body, "home sidebar has no Favourites destination")
        check(b'aria-label="Andor"' in body, "home recently-added still groups Andor")
        check(b"Open library" not in body and b"direct-play library" not in body, "home has no marketing lede or library CTA")
        check(b"class=\"archive-note\"" not in body, "home has no archive status prose")
        check(b">TMDB<" not in body, "home is not a TMDB grid")

        st, _, body = http("GET", "/search")
        check(st == 200 and b"search-page" in body, "dedicated search page")
        check(b"search-pill" not in body and b"<h1>Search</h1>" not in body, "search page has no second field or heading")
        check(b'class="topbar-search"' in body and b'name="q"' in body, "topbar is the only search field")
        check(b"search-idle" in body and b"search-body" in body, "empty search prompts from the topbar")

        st, _, body = http("GET", "/search?q=zzznomatch")
        check(st == 200 and b'class="empty"' in body and b"No titles match" in body, "search page zero state")
        check(b'value="zzznomatch"' in body, "search form preserves q")
        check(body.count(b'name="q"') == 1, "search has a single q field")

        st, _, body = http("GET", "/search?q=Andor")
        check(st == 200 and b"search-group" in body, "search groups results by kind")
        check(b"<h2>Series</h2>" in body, "search has a Series group for Andor")

        st, _, body = http("GET", "/favourites")
        check(st == 200 and b"kind-toolbar" in body and b">Shuffle<" in body, "favourites URL is the library with toolbar")
        check(b">All<" in body and b'data-filter-fav' in body, "favourites URL has All and Favourites chips")
        check(b"hero-carousel" not in body and b"favourites-page" not in body, "favourites is not a dedicated page")

        st, _, body = http("GET", "/koru-dom-enhance.js")
        check(st == 200 and b"__koru_dom_track" in body, "koru-dom-enhance.js served")

        st, _, body = http("GET", "/enhance-demo.html")
        check(st == 200 and b'id="koru-list"' in body and b"/koru-dom-enhance.js" in body, "enhance-demo.html served")

        st, hdrs, body = http("GET", "/settings")
        check(st == 200 and b'id="settings-page"' in body, "GET /settings -> 200")
        check(b"<form" in body and b'method="post"' in body, "settings has POST form")
        check(b'name="path_0"' in body and b'value="movies"' in body, "settings default movies mount")
        check(b'value="shows"' in body and b'value="music"' in body, "settings default shows+music")
        check(b'value="books"' in body and b'value="musicVideos"' in body, "settings default books+musicVideos")
        check(b'name="cap_0"' in body and b'name="base_path"' in body, "settings has capability + base path")
        check(b'name="catalog_driver"' in body and b'name="catalog_dsn"' in body, "settings has catalog store fields")
        check(b"SQLite (linked)" in body and b"PostgreSQL (not linked)" in body, "settings is honest about unlinked SQL drivers")
        check(b">Hydrate now<" in body, "settings has Hydrate now")
        check(b"<h2>Hydrate</h2>" in body and b"hydrate-section" in body, "settings hydrate section is padded")
        check(b"name=\"tmdb_token\"" in body and b"name=\"login_password\"" in body, "settings has catalogue keys + password")
        check(b"data-host-register" in body and b"play.video" in body, "host capability register is declared")
        check(b"index_media.py" not in body and b"hydrate_catalog.py" not in body, "settings does not name Python as indexer")
        check(b"KORU_BASE_PATH" in body, "settings shows web alias")
        check(b"strong>Settings</strong>" in body, "settings nav is active")
        check(b"mount-add" in body, "settings has an add-library slot")
        check(b'class="mount-name"' in body and b'class="mount-cap"' in body, "settings mount fields are labeled for layout")
        check("link" in hdrs and "/settings" in hdrs.get("link", "") and "self" in hdrs.get("link", ""), f"Link header on settings: {hdrs.get('link')}")

        mounts = (
            b"action=save&on_0=1&name_0=Films&path_0=movies&cap_0=movies&aff_ex_0=1&aff_ae_0=1"
            b"&on_1=1&name_1=Series&path_1=shows&cap_1=series&aff_ep_1=1&aff_ex_1=1&aff_ae_1=1"
            b"&on_2=1&name_2=Music&path_2=music&cap_2=music"
            b"&on_3=1&name_3=Books&path_3=books&cap_3=books"
            b"&on_4=1&name_4=Music+videos&path_4=musicVideos&cap_4=music_videos"
            b"&catalog_driver=sqlite&catalog_dsn=data/catalog.sqlite&walk_on_empty=1"
        )
        st, _, body = http("POST", "/settings", data=mounts)
        check(st == 200 and b'id="settings-page"' in body, "POST /settings save -> 200")
        if b"Saved library mounts" in body:
            check(b'value="Films"' in body, "POST save persists display name")
            check(b'value="series"' in body, "POST save persists series capability")
        check(b"index_media.py" not in body, "POST save does not name Python indexer")

        st, _, body = http("POST", "/settings", data=b"action=save&on_0=1&name_0=Hack&path_0=../etc")
        check(st == 200, "POST traversal -> 200")
        check(b'value="../etc"' not in body, "POST traversal path is not stored")
        check(b"Not saved" in body and b"must stay under" in body, "POST traversal rejected")

        st, _, body = http("POST", "/settings", data=b"action=save&on_0=1&name_0=Hack&path_0=%2Fetc%2Fpasswd")
        check(st == 200 and b'value="/etc/passwd"' not in body, "POST absolute escape is not stored")
        check(b"Not saved" in body, "POST absolute escape rejected")

        st, _, body = http(
            "POST",
            "/settings",
            data=b"action=save&on_0=1&name_0=Movies&path_0=movies&base_path=%2Fmedia",
        )
        check(st == 200 and b"Not saved" in body and b"/media" in body, "POST rejects /media base path")

        st, _, body = http(
            "POST",
            "/settings",
            data=(
                b"action=save&on_0=1&name_0=Movies&path_0=movies&cap_0=movies"
                b"&catalog_driver=postgres&catalog_dsn=postgres://db.example/koru"
            ),
        )
        check(st == 200 and b"The selected SQL driver is not linked" in body, "POST postgres driver is stored but not pretended")

        st, _, body = http("GET", "/library")
        check(b"/enhance.js" in body and b"/app.css" in body and b"hx-get=" in body, "library progressive enhance hooks")

        st, _, body = http("GET", f"/item/{demo_id}")
        check(b"/enhance.js" in body and b"/app.css" in body and b"item-actions" in body, "item page enhance + css")
        check(b">TMDB<" not in body and b">IMDb<" not in body and b"themoviedb.org" not in body, "demo item has no provider links")
        check(b'class="catalogue"' not in body and b'class="archive"' not in body, "demo item has no catalogue/archive split")
        check(b">Local archive<" not in body, "demo item has no archive heading")
        st, _, jdemo = http("GET", f"/item/{demo_id}?format=jsonld")
        check(st == 200 and b'"@type":"Movie"' in jdemo, "demo catalog jsonld movie")
        check(b"imdb.com" not in jdemo and b"themoviedb.org" not in jdemo, "demo jsonld has no provider sameAs")
        check(f"/media/{demo_id}".encode() in jdemo, "demo contentUrl is /media/{id}")
        check(b"work.movie" not in jdemo and b"/item/work." not in jdemo, "demo jsonld keeps opaque m_* ids")

        st, _, body = http("GET", f"/play/{demo_id}")
        check(b'data-media-id="' + demo_id.encode() in body and b"/enhance.js" in body and b"/app.css" in body, "play resume hooks")
        check(b'id="resume-ui"' in body and b'id="player"' in body, "play resume-ui beside player")
        check(b'class="catalogue"' not in body and b">TMDB<" not in body, "demo play has no catalogue overlay")
        player_at = body.find(b'id="player"')
        resume_at = body.find(b'id="resume-ui"')
        check(player_at != -1 and resume_at != -1 and player_at < resume_at, "player precedes resume-ui")

        st, _, body = http("GET", "/enhance.js")
        check(b"showResumeUi" in body and b"resume-ui" in body, "enhance resume UI helper")

        arrival = next((e for e in manifest["entries"] if e.get("year") == 2016), None)
        if arrival:
            st, _, body = http("GET", "/library")
            check(b'aria-label="Arrival (2016)"' in body, "library card names movie via aria-label")
        else:
            check(False, "year fixture for library row")

        reindex = (
            b"action=reindex&on_0=1&name_0=Movies&path_0=movies&cap_0=movies"
            b"&on_1=1&name_1=Series&path_1=shows&cap_1=series&aff_ep_1=1&aff_ex_1=1&aff_ae_1=1"
            b"&on_2=1&name_2=Music&path_2=music&cap_2=music"
            b"&on_3=1&name_3=Books&path_3=books&cap_3=books"
            b"&on_4=1&name_4=Music+videos&path_4=musicVideos&cap_4=music_videos"
            b"&catalog_driver=sqlite&walk_on_empty=1"
        )
        st, _, body = http("POST", "/settings", data=reindex)
        check(st == 200 and b'id="settings-page"' in body, "POST reindex -> 200")
        check(b"index_media.py" not in body and b"hydrate_catalog.py" not in body, "POST reindex does not name Python indexer")
        if b"Saved." in body or b"flagged" in body:
            check(b"idle" not in body, "reindex does not wait for an idle stream")
            check(b"accept tick" in body, "reindex is flagged for the next accept tick")

        hydrate = reindex.replace(b"action=reindex", b"action=hydrate")
        st, _, body = http("POST", "/settings", data=hydrate)
        check(st == 200 and b'id="settings-page"' in body, "POST hydrate now -> 200")
        check(b"Hydrate is flagged" in body or b"flagged" in body, "hydrate is flagged for the next accept tick")
        check(b"idle" not in body, "hydrate does not wait for an idle stream")

        st, _, body = http("GET", "/login")
        check(st == 200 and b"Sign in" in body, "GET /login is open before a password is set")

        st, _, body = http("POST", "/settings", data=reindex + b"&login_password=secret")
        check(st == 200, "POST set household password")

        st, _, body = http("GET", "/library")
        check(st == 401 and b"Sign in" in body, "library requires login after password")
        st, _, body = http("GET", f"/play/{demo_id}")
        check(st == 401, "play requires login after password")
        st, _, body = http("GET", "/enhance.js")
        check(st == 200 and b"playerIdentityOk" in body, "static js stays open after password")

        st, _, body = http("POST", "/login", data=b"password=wrong")
        check(st == 401, "bad password stays 401")

        st, hdrs, body = http("POST", "/login", data=b"password=secret")
        check(st == 200, "good password signs in")
        cookie = hdrs.get("set-cookie", "")
        check("koru_sid=" in cookie, "login sets session cookie")
        sid = cookie.split(";")[0]

        st, _, body = http("GET", "/library", headers={"Cookie": sid})
        check(st == 200 and b'id="library-list"' in body, "cookie unlocks library")

        st, _, body = http("POST", "/settings", data=reindex)
        check(st == 401, "settings POST without session fails")

        st, _, body = http("GET", "/library", headers={"X-Forwarded-User": "alice"})
        check(st == 200 and b'id="library-list"' in body, "proxy user header establishes session")

    elif mode == "security":
        st, _, body = http("GET", "/library")
        check(st == 200, "security library")
        check(b"<script>" not in body, "raw script tag absent")
        check(b"&lt;script&gt;" in body, "escaped script title")
        st, _, _ = http("GET", "/media/m_trav")
        check(st == 403, "traversal path forbidden")
        st, _, body = http("GET", "/settings")
        check(st == 200 and b'id="settings-page"' in body, "security settings page")
        st, _, body = http("POST", "/settings", data=b"action=save&on_0=1&name_0=Hack&path_0=../etc")
        check(st == 200 and b'value="../etc"' not in body, "security settings rejects traversal mount")
        check(b"Not saved" in body, "security settings traversal notice")
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
            check(st == 200 and b">Arrival</h1>" in body, "missing semantic: physical title")
            check(b">TMDB<" not in body and b">IMDb<" not in body and b"themoviedb.org" not in body, "missing semantic: no provider links")
            check(b'class="catalogue"' not in body and b'class="archive"' not in body, "missing semantic: physical HTML only")
            check(b"container" in body and b"<code>mp4</code>" in body, "missing semantic: container still shown")
            st, _, jbody = http("GET", f"/item/{arrival['id']}?format=jsonld")
            check(st == 200 and b'"@type":"Movie"' in jbody, "missing semantic: catalog jsonld movie")
            check(b"themoviedb.org" not in jbody and b"imdb.com" not in jbody, "missing semantic: jsonld has no provider sameAs")
            check(f"/media/{arrival['id']}".encode() in jbody, "missing semantic: contentUrl is /media/{id}")
            st, _, wbody = http("GET", f"/play/{arrival['id']}")
            check(st == 200 and b'id="player"' in wbody, "missing semantic: play still plays")
            check(b">TMDB<" not in wbody, "missing semantic: play has no providers")
        st, _, body = http("GET", f"/media/{demo['id']}")
        check(st == 200 and body == b"hello world\n", "missing semantic: physical playback")
        st, _, home = http("GET", "/")
        check(st == 200 and b"Recently added" in home, "missing semantic: home still serves")
        check(b"Recently added" in home and demo["id"].encode() in home, "missing semantic: home lists local movies")
        check(f"/item/{demo['id']}".encode() in home, "missing semantic: home movies link to item")
        check(b">TMDB<" not in home and b">IMDb<" not in home and b"themoviedb.org" not in home, "missing semantic: home has no catalogue chips")
        st, _, lib = http("GET", "/library")
        check(st == 200 and b'aria-label="Arrival (2016)"' in lib and demo["id"].encode() in lib, "missing semantic: library lists local files")
        check(f"/item/{demo['id']}".encode() in lib, "missing semantic: library cards link to item")
        check(f"/play/{demo['id']}".encode() not in lib or b'class="poster-link" href="/play/' not in lib, "missing semantic: library has no under-card play")
        check(b">TMDB<" not in lib and b'class="catalogue"' not in lib, "missing semantic: library has no catalogue chips")
        check(b"without a catalogue fetch" in lib, "missing semantic: library is local archive")
        st, _, movies = http("GET", "/library/movie")
        check(st == 200 and b'aria-label="Arrival (2016)"' in movies and demo["id"].encode() in movies, "missing semantic: movie collection lists local files")
        check(b">TMDB<" not in movies, "missing semantic: movie collection has no catalogue chips")

    elif mode == "prefix":
        prefix = os.environ.get("KORU_TEST_PREFIX", "/korisha")
        manifest = json.loads((ROOT / "fixtures" / "manifest.json").read_text(encoding="utf-8"))
        demo = next(e for e in manifest["entries"] if e["title"] == "demo")
        demo_id = demo["id"]

        st, _, body = http("GET", prefix + "/")
        check(st == 200, f"GET {prefix}/ -> {st}")
        check(f'href="{prefix}/library"'.encode() in body, f"home href={prefix}/library")
        check(f'data-base="{prefix}"'.encode() in body, f"html data-base={prefix}")
        check(f'href="{prefix}/app.css"'.encode() in body, f"home stylesheet href={prefix}/app.css")

        st, _, body = http("GET", prefix + "/library")
        check(st == 200, f"GET {prefix}/library -> {st}")
        check(f'href="{prefix}/library/movie"'.encode() in body, "library hrefs stay under alias")
        check(f'href="{prefix}/item/{demo_id}"'.encode() in body, "library item href prefixed")
        check(f'href="{prefix}/settings"'.encode() in body, "library settings href prefixed")

        st, _, body = http("GET", prefix + "/settings")
        check(st == 200 and b'id="settings-page"' in body, f"GET {prefix}/settings -> 200")
        check(f'action="{prefix}/settings"'.encode() in body, "settings form action stays under alias")
        check(f'href="{prefix}/settings"'.encode() in body, "settings self href prefixed")
        check(b'value="movies"' in body and b">Reindex<" in body, "prefixed settings has mounts + Reindex")
        check(b"index_media.py" not in body, "prefixed settings does not name Python indexer")
        check(prefix.encode() in body and b"KORU_BASE_PATH" in body, "prefixed settings shows web alias")
        check(b'name="base_path"' in body and b'name="catalog_driver"' in body, "prefixed settings has base path + catalog store")

        st, _, body = http("GET", f"{prefix}/play/{demo_id}")
        check(st == 200 and b'id="player"' in body, "prefixed play page")
        check(f'src="{prefix}/media/{demo_id}"'.encode() in body, f"player src={prefix}/media/…")

        st, _, body = http("GET", f"{prefix}/media/{demo_id}")
        check(st == 200 and body == b"hello world\n", "prefixed /media/{id} streams")

        st, _, body = http("GET", f"/media/{demo_id}")
        check(st == 200 and body == b"hello world\n", "unprefixed /media/{id} still streams when alias is not /media")

        st, hdrs, css = http("GET", prefix + "/app.css")
        check(st == 200 and b"--ink" in css, "prefixed app.css")
        check("text/css" in hdrs.get("content-type", ""), "prefixed app.css content-type")

        st, _, js = http("GET", prefix + "/enhance.js")
        check(st == 200 and b"appBase" in js and b"withAppBase" in js, "prefixed enhance.js reads data-base")
        check(b"match(/^\\/play\\/" not in js, "mediaIdFromPath is not ^/play/ anchored")
        check(b"match(/\\/play\\/" in js, "mediaIdFromPath matches /play/ anywhere")

        st, _, body = http("GET", "/library", headers={"X-Forwarded-Prefix": prefix})
        check(st == 200 and f'href="{prefix}/library/movie"'.encode() in body, "X-Forwarded-Prefix on stripped /library")
        check(f'data-base="{prefix}"'.encode() in body, "forwarded prefix sets data-base")

        st, _, body = http("GET", prefix + "/library", headers={"X-Forwarded-Prefix": prefix})
        check(st == 200 and f'href="{prefix}/library/movie"'.encode() in body, "X-Forwarded-Prefix + full /korisha/library")

        st, _, body = http("GET", f"{prefix}/play/{demo_id}", headers={"X-Forwarded-Prefix": prefix})
        check(f'src="{prefix}/media/{demo_id}"'.encode() in body, "forwarded prefix player src")

        st, _, jbody = http("GET", f"{prefix}/item/m_and1e2?format=jsonld")
        check(st == 200 and b'"@type":"TVEpisode"' in jbody, "prefixed episode jsonld")
        check(f"{prefix}/media/m_and1e2".encode() in jbody, "prefixed episode contentUrl")
        check(b"/item/work." not in jbody, "prefixed jsonld keeps opaque ids")

    elif mode == "overlap":
        import socket
        import threading
        from urllib.parse import urlparse

        big_id = os.environ["KORU_TEST_BIG_ID"]
        parsed = urlparse(BASE)
        host = parsed.hostname or "127.0.0.1"
        port = parsed.port or 80
        home_st: list[int | None] = [None]
        home_done = threading.Event()

        def fetch_home() -> None:
            st, _, _ = http("GET", "/")
            home_st[0] = st
            home_done.set()

        sock = socket.create_connection((host, port), timeout=5)
        try:
            sock.sendall(f"GET /media/{big_id} HTTP/1.1\r\nHost: test\r\n\r\n".encode())
            hdr = b""
            while b"\r\n\r\n" not in hdr:
                chunk = sock.recv(1)
                if not chunk:
                    break
                hdr += chunk
            check(hdr.startswith(b"HTTP/1.1 200") or hdr.startswith(b"HTTP/1.1 206"), "slow STREAM headers")
            t = threading.Thread(target=fetch_home, daemon=True)
            t.start()
            ok = home_done.wait(3.0)
            check(ok and home_st[0] == 200, "GET / returns while a STREAM body is still open")
        finally:
            sock.close()

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

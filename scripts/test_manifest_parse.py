#!/usr/bin/env python3
"""Spec twin of the vendor schema-specific manifest loader (entries array + unescape).

Mirrors `loadManifest` / `entriesArraySlice` / JSON string unescape in
`vendor/orisha-lib/index.kz` (APP:media-handler / SPLIT→ manifest-load.kz).
Not a full JSON parser — only what the media server promises to accept.
"""
from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def entries_array_slice(text: str) -> str | None:
    key = '"entries"'
    at = text.find(key)
    if at < 0:
        return None
    p = at + len(key)
    while p < len(text) and text[p] in " \t\r\n:":
        p += 1
    if p >= len(text) or text[p] != "[":
        return None
    depth = 0
    in_string = False
    escape = False
    k = p
    while k < len(text):
        ch = text[k]
        if in_string:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == '"':
                in_string = False
            k += 1
            continue
        if ch == '"':
            in_string = True
            k += 1
            continue
        if ch == "[":
            depth += 1
        elif ch == "]":
            depth -= 1
            if depth == 0:
                return text[p : k + 1]
        k += 1
    return None


def entry_object_slice(text: str, id_at: int) -> str:
    """Slice the entry object containing `"id"` at id_at.

    Walks backward with brace depth so nested `audio`/`video` objects that
    appear before `"id"` are not mistaken for the entry start.
    """
    start = 0
    depth = 0
    in_string = False
    i = id_at
    while i > 0:
        i -= 1
        ch = text[i]
        if in_string:
            if ch == '"':
                bs = 0
                j = i
                while j > 0 and text[j - 1] == "\\":
                    bs += 1
                    j -= 1
                if bs % 2 == 1:
                    continue
                in_string = False
            continue
        if ch == '"':
            in_string = True
            continue
        if ch == "}":
            depth += 1
        elif ch == "{":
            if depth == 0:
                start = i
                break
            depth -= 1

    depth = 0
    seen_open = False
    in_string = False
    escape = False
    k = start
    while k < len(text):
        ch = text[k]
        if in_string:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == '"':
                in_string = False
            k += 1
            continue
        if ch == '"':
            in_string = True
            k += 1
            continue
        if ch == "{":
            depth += 1
            seen_open = True
        elif ch == "}":
            depth -= 1
            if seen_open and depth == 0:
                return text[start : k + 1]
        k += 1
    return text[start:]


def extract_raw_string(slice_: str) -> str | None:
    colon = slice_.find(":")
    if colon < 0:
        return None
    q1 = slice_.find('"', colon)
    if q1 < 0:
        return None
    start = q1 + 1
    i = start
    escape = False
    while i < len(slice_):
        if escape:
            escape = False
            i += 1
            continue
        if slice_[i] == "\\":
            escape = True
            i += 1
            continue
        if slice_[i] == '"':
            return slice_[start:i]
        i += 1
    return None


def unescape_json(raw: str) -> str:
    if "\\" not in raw:
        return raw
    out: list[str] = []
    i = 0
    while i < len(raw):
        if raw[i] == "\\" and i + 1 < len(raw):
            i += 1
            esc = raw[i]
            out.append(
                {
                    '"': '"',
                    "\\": "\\",
                    "/": "/",
                    "n": "\n",
                    "t": "\t",
                    "r": "\r",
                }.get(esc, esc)
            )
        else:
            out.append(raw[i])
        i += 1
    return "".join(out)


def extract_after_unescaped(slice_: str, key: str) -> str | None:
    at = slice_.find(key)
    if at < 0:
        return None
    raw = extract_raw_string(slice_[at:])
    if raw is None:
        return None
    return unescape_json(raw)


def extract_number_after(slice_: str, key: str) -> int | None:
    at = slice_.find(key)
    if at < 0:
        return None
    colon = slice_.find(":", at)
    if colon < 0:
        return None
    p = colon + 1
    while p < len(slice_) and slice_[p] in " \t":
        p += 1
    end = p
    while end < len(slice_) and slice_[end].isdigit():
        end += 1
    if end == p:
        return None
    return int(slice_[p:end])


def first_array_object_slice(entry_obj: str, key: str) -> str | None:
    """First object inside an entry array field (e.g. `"video":[{...}]`)."""
    at = entry_obj.find(key)
    if at < 0:
        return None
    p = at + len(key)
    while p < len(entry_obj) and entry_obj[p] in " \t\r\n:":
        p += 1
    if p >= len(entry_obj) or entry_obj[p] != "[":
        return None
    depth = 0
    in_string = False
    escape = False
    k = p
    while k < len(entry_obj):
        ch = entry_obj[k]
        if in_string:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == '"':
                in_string = False
            k += 1
            continue
        if ch == '"':
            in_string = True
            k += 1
            continue
        if ch == "[":
            depth += 1
            k += 1
            continue
        if ch == "]":
            depth -= 1
            if depth == 0:
                return None
            k += 1
            continue
        if ch == "{" and depth == 1:
            obj_depth = 0
            j = k
            obj_in_string = False
            obj_escape = False
            while j < len(entry_obj):
                oj = entry_obj[j]
                if obj_in_string:
                    if obj_escape:
                        obj_escape = False
                    elif oj == "\\":
                        obj_escape = True
                    elif oj == '"':
                        obj_in_string = False
                    j += 1
                    continue
                if oj == '"':
                    obj_in_string = True
                    j += 1
                    continue
                if oj == "{":
                    obj_depth += 1
                elif oj == "}":
                    obj_depth -= 1
                    if obj_depth == 0:
                        return entry_obj[k : j + 1]
                j += 1
            return None
        k += 1
    return None


def load_manifest_entries(text: str) -> list[dict]:
    entries = entries_array_slice(text)
    if entries is None:
        return []
    out: list[dict] = []
    seen: set[str] = set()
    i = 0
    while i < len(entries):
        if entries.startswith('"id"', i):
            obj = entry_object_slice(entries, i)
            id_ = extract_after_unescaped(obj, '"id"')
            path = extract_after_unescaped(obj, '"path"')
            if not id_ or not path:
                i += 1
                continue
            if id_ in seen:
                i += 1
                continue
            seen.add(id_)
            title = extract_after_unescaped(obj, '"title"') or id_
            video_track = first_array_object_slice(obj, '"video"') or ""
            audio_track = first_array_object_slice(obj, '"audio"') or ""
            out.append(
                {
                    "id": id_,
                    "title": title,
                    "path": path,
                    "mime": extract_after_unescaped(obj, '"mime"') or "application/octet-stream",
                    "kind": extract_after_unescaped(obj, '"kind"') or "file",
                    "container": extract_after_unescaped(obj, '"container"') or "",
                    "poster": extract_after_unescaped(obj, '"poster"') or "",
                    "bytes": extract_number_after(obj, '"bytes"') or 0,
                    "modified_ns": extract_number_after(obj, '"modified_ns"') or 0,
                    "year": extract_number_after(obj, '"year"') or 0,
                    "video_codec": (extract_after_unescaped(video_track, '"codec"') or "") if video_track else "",
                    "video_brand": (extract_after_unescaped(video_track, '"brand"') or "") if video_track else "",
                    "audio_codec": (extract_after_unescaped(audio_track, '"codec"') or "") if audio_track else "",
                }
            )
        i += 1
    return out


class ManifestParseTests(unittest.TestCase):
    def test_fixture_manifest_matches_json(self) -> None:
        text = (ROOT / "data" / "manifest.json").read_text(encoding="utf-8")
        scraped = load_manifest_entries(text)
        real = json.loads(text)["entries"]
        self.assertEqual(len(scraped), len(real))
        by_id = {e["id"]: e for e in scraped}
        for e in real:
            got = by_id[e["id"]]
            self.assertEqual(got["title"], e["title"])
            self.assertEqual(got["path"], e["path"])
            self.assertEqual(got["bytes"], e["bytes"])
            self.assertEqual(got.get("year", 0) or 0, e.get("year", 0) or 0)
            video = (e.get("video") or [{}])[0] if e.get("video") else {}
            audio = (e.get("audio") or [{}])[0] if e.get("audio") else {}
            self.assertEqual(got["video_codec"], video.get("codec", "") or "")
            self.assertEqual(got["video_brand"], video.get("brand", "") or "")
            self.assertEqual(got["audio_codec"], audio.get("codec", "") or "")

    def test_ignores_id_outside_entries(self) -> None:
        text = '{"meta":{"id":"noise"},"entries":[{"id":"m_ok","path":"a.mp4","title":"ok","bytes":1}]}'
        scraped = load_manifest_entries(text)
        self.assertEqual([e["id"] for e in scraped], ["m_ok"])

    def test_unescape_title(self) -> None:
        text = r'{"entries":[{"id":"m_1","path":"a.mp4","title":"Say \"hi\"\nthere","bytes":1}]}'
        scraped = load_manifest_entries(text)
        self.assertEqual(len(scraped), 1)
        self.assertEqual(scraped[0]["title"], 'Say "hi"\nthere')

    def test_braces_inside_string_do_not_break_object(self) -> None:
        text = r'{"entries":[{"id":"m_1","path":"a.mp4","title":"has { brace","bytes":1,"kind":"movie"}]}'
        scraped = load_manifest_entries(text)
        self.assertEqual(len(scraped), 1)
        self.assertEqual(scraped[0]["kind"], "movie")
        self.assertEqual(scraped[0]["title"], "has { brace")

    def test_duplicate_id_rejected(self) -> None:
        text = (
            '{"entries":['
            '{"id":"m_1","path":"a.mp4","title":"a","bytes":1},'
            '{"id":"m_1","path":"b.mp4","title":"b","bytes":2}'
            "]}"
        )
        scraped = load_manifest_entries(text)
        self.assertEqual(len(scraped), 1)
        self.assertEqual(scraped[0]["path"], "a.mp4")

    def test_missing_entries_yields_empty(self) -> None:
        self.assertEqual(load_manifest_entries('{"items":[{"id":"x","path":"a"}]}'), [])

    def test_nested_video_audio_first_track(self) -> None:
        text = (
            '{"entries":[{'
            '"id":"m_1","path":"a.mp4","title":"a","bytes":1,'
            '"video":[{"codec":"hevc","brand":"isom"},{"codec":"ignored"}],'
            '"audio":[{"codec":"aac"},{"codec":"ignored"}]'
            "}]}"
        )
        scraped = load_manifest_entries(text)
        self.assertEqual(len(scraped), 1)
        self.assertEqual(scraped[0]["video_codec"], "hevc")
        self.assertEqual(scraped[0]["video_brand"], "isom")
        self.assertEqual(scraped[0]["audio_codec"], "aac")

    def test_nested_object_before_id_still_loads(self) -> None:
        text = (
            '{"entries":[{'
            '"audio":[{"codec":"aac"}],'
            '"id":"m_1","path":"a.mp4","title":"a","bytes":1,'
            '"video":[{"codec":"hevc","brand":"isom"}]'
            "}]}"
        )
        scraped = load_manifest_entries(text)
        self.assertEqual(len(scraped), 1)
        self.assertEqual(scraped[0]["id"], "m_1")
        self.assertEqual(scraped[0]["video_codec"], "hevc")
        self.assertEqual(scraped[0]["audio_codec"], "aac")

    def test_empty_video_array_yields_empty_probe(self) -> None:
        text = '{"entries":[{"id":"m_1","path":"a.mp4","title":"a","bytes":1,"video":[]}]}'
        scraped = load_manifest_entries(text)
        self.assertEqual(scraped[0]["video_codec"], "")
        self.assertEqual(scraped[0]["video_brand"], "")


if __name__ == "__main__":
    unittest.main()

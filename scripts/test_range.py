#!/usr/bin/env python3
"""Pure-Python mirrors of media path / range rules used by the Orisha handler."""
from __future__ import annotations

import unittest


def parse_bytes_range(range_hdr: str, size: int):
    if not range_hdr.startswith("bytes="):
        return None
    spec = range_hdr[len("bytes=") :]
    if "-" not in spec or spec.startswith("-"):
        return None
    start_s, end_s = spec.split("-", 1)
    try:
        start = int(start_s)
    except ValueError:
        return None
    if end_s == "":
        end = size - 1
    else:
        try:
            end = int(end_s)
        except ValueError:
            return None
    if size <= 0 or start >= size or end < start:
        return None
    end = min(end, size - 1)
    return start, end


def path_ok(rel: str) -> bool:
    if not rel or rel.startswith("/") or ".." in rel:
        return False
    return True


def html_escape(s: str) -> str:
    return (
        s.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


class RangeTests(unittest.TestCase):
    def test_full_open_end(self):
        self.assertEqual(parse_bytes_range("bytes=0-", 12), (0, 11))

    def test_partial(self):
        self.assertEqual(parse_bytes_range("bytes=2-5", 12), (2, 5))

    def test_unsatisfiable(self):
        self.assertIsNone(parse_bytes_range("bytes=12-20", 12))

    def test_path_traversal_rejected(self):
        self.assertFalse(path_ok("../etc/passwd"))
        self.assertFalse(path_ok("/etc/passwd"))
        self.assertFalse(path_ok(""))
        self.assertTrue(path_ok("movies/demo.mp4"))

    def test_html_escape(self):
        self.assertEqual(html_escape('a<b&c>"'), "a&lt;b&amp;c&gt;&quot;")


if __name__ == "__main__":
    unittest.main()

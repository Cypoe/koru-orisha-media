#!/usr/bin/env python3
"""Fixture tests for indexer + path safety (no Koru runtime required)."""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INDEXER = ROOT / "scripts" / "index_media.py"


class IndexerTests(unittest.TestCase):
    def test_indexes_fixture_media(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "manifest.json"
            media = ROOT / "fixtures" / "media"
            subprocess.check_call(
                [sys.executable, str(INDEXER), "--root", str(media), "--out", str(out)]
            )
            data = json.loads(out.read_text(encoding="utf-8"))
            self.assertIn("entries", data)
            self.assertGreaterEqual(len(data["entries"]), 1)
            paths = {e["path"] for e in data["entries"]}
            self.assertIn("clips/demo.mp4", paths)
            for e in data["entries"]:
                self.assertTrue(e["id"].startswith("m_"))
                self.assertNotIn("..", e["path"])
                self.assertFalse(e["path"].startswith("/"))
                self.assertIn("container", e)
                self.assertEqual(e["container"], Path(e["path"]).suffix.lstrip(".").lower())

    def test_poster_sidecar(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "media"
            clips = root / "clips"
            clips.mkdir(parents=True)
            (clips / "show.mp4").write_bytes(b"vid")
            (clips / "show.jpg").write_bytes(b"\xff\xd8fake")
            out = Path(td) / "manifest.json"
            subprocess.check_call(
                [sys.executable, str(INDEXER), "--root", str(root), "--out", str(out)]
            )
            data = json.loads(out.read_text(encoding="utf-8"))
            self.assertEqual(len(data["entries"]), 1)
            self.assertEqual(data["entries"][0]["poster"], "clips/show.jpg")
            self.assertEqual(data["entries"][0]["container"], "mp4")

    def test_ids_stable_for_same_file(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            out1 = Path(td) / "a.json"
            out2 = Path(td) / "b.json"
            media = ROOT / "fixtures" / "media"
            subprocess.check_call(
                [sys.executable, str(INDEXER), "--root", str(media), "--out", str(out1)]
            )
            subprocess.check_call(
                [sys.executable, str(INDEXER), "--root", str(media), "--out", str(out2)]
            )
            a = json.loads(out1.read_text(encoding="utf-8"))
            b = json.loads(out2.read_text(encoding="utf-8"))
            self.assertEqual(
                {e["path"]: e["id"] for e in a["entries"]},
                {e["path"]: e["id"] for e in b["entries"]},
            )

    def test_atomic_publish(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "manifest.json"
            media = ROOT / "fixtures" / "media"
            subprocess.check_call(
                [sys.executable, str(INDEXER), "--root", str(media), "--out", str(out)]
            )
            self.assertTrue(out.is_file())
            # No leftover tmp files from NamedTemporaryFile
            leftovers = [p for p in Path(td).iterdir() if p.name != "manifest.json"]
            self.assertEqual(leftovers, [])
            data = json.loads(out.read_text(encoding="utf-8"))
            self.assertIn("entries", data)

    def test_duplicate_id_rejected(self) -> None:
        # Force duplicate by patching opaque_id via two files with same content+mtime is hard;
        # call index_root after monkeypatching opaque_id.
        import importlib.util

        spec = importlib.util.spec_from_file_location("index_media", INDEXER)
        mod = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(mod)

        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "a.mp4").write_bytes(b"1")
            (root / "b.mp4").write_bytes(b"2")
            orig = mod.opaque_id
            mod.opaque_id = lambda rel, size, mtime_ns: "m_dup"  # type: ignore
            try:
                with self.assertRaises(SystemExit):
                    mod.index_root(root)
            finally:
                mod.opaque_id = orig


if __name__ == "__main__":
    unittest.main()

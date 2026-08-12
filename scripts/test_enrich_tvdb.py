#!/usr/bin/env python3
"""TVDB offline enricher tests (fixture path; no network)."""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class EnrichTvdbTests(unittest.TestCase):
    def test_fixture_enrich(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "semantic.json"
            r = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts" / "enrich_tvdb.py"),
                    "--in",
                    str(ROOT / "fixtures" / "semantic.json"),
                    "--out",
                    str(out),
                    "--fixture",
                    str(ROOT / "fixtures" / "tvdb" / "series_121361.json"),
                    "--entity",
                    "series.fixture-demo",
                    "--series-id",
                    "121361",
                ],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(r.returncode, 0, r.stderr)
            data = json.loads(out.read_text(encoding="utf-8"))
            ent = next(e for e in data["entities"] if e["id"] == "series.fixture-demo")
            self.assertEqual(ent["title"], "Game of Thrones")
            self.assertEqual(ent["year"], 2011)
            tvdb = next(p for p in ent["provider_ids"] if p["provider"] == "tvdb")
            self.assertEqual(tvdb["value"], "121361")
            self.assertEqual(tvdb["source"], "provider")
            self.assertTrue(any(a["property"] == "name" for a in ent["assertions"]))


if __name__ == "__main__":
    unittest.main()

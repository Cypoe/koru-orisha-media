#!/usr/bin/env python3
"""TMDB offline enricher tests (fixture path; no network)."""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class EnrichTmdbTests(unittest.TestCase):
    def test_fixture_enrich(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "semantic.json"
            r = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts" / "enrich_tmdb.py"),
                    "--in",
                    str(ROOT / "fixtures" / "semantic.json"),
                    "--out",
                    str(out),
                    "--fixture",
                    str(ROOT / "fixtures" / "tmdb" / "movie_329865.json"),
                    "--entity",
                    "work.movie.arrival-2016",
                    "--kind",
                    "movie",
                    "--tmdb-id",
                    "329865",
                ],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(r.returncode, 0, r.stderr)
            data = json.loads(out.read_text(encoding="utf-8"))
            ent = next(e for e in data["entities"] if e["id"] == "work.movie.arrival-2016")
            self.assertEqual(ent["title"], "Arrival")
            self.assertEqual(ent["year"], 2016)
            tmdb = next(p for p in ent["provider_ids"] if p["provider"] == "tmdb")
            self.assertEqual(tmdb["value"], "329865")
            self.assertEqual(tmdb["source"], "provider")
            imdb = next(p for p in ent["provider_ids"] if p["provider"] == "imdb")
            self.assertEqual(imdb["value"], "tt2543164")
            self.assertEqual(imdb["source"], "provider")
            self.assertTrue(any(a["property"] == "name" for a in ent["assertions"]))


if __name__ == "__main__":
    unittest.main()

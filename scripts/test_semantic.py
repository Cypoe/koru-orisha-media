#!/usr/bin/env python3
"""Tests for semantic stages 1–4 (no network)."""
from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from semantic_schema import (  # noqa: E402
    SemanticSnapshot,
    project_jsonld,
    resolve_asset,
)


class SemanticSchemaTests(unittest.TestCase):
    def setUp(self) -> None:
        raw = json.loads((ROOT / "fixtures" / "semantic.json").read_text(encoding="utf-8"))
        self.snap = SemanticSnapshot.from_dict(raw)

    def test_load_fixture(self) -> None:
        self.assertGreaterEqual(len(self.snap.entities), 2)
        self.assertTrue(any(e.id == "work.movie.arrival-2016" for e in self.snap.entities))

    def test_jsonld_movie(self) -> None:
        ent = next(e for e in self.snap.entities if e.id == "work.movie.arrival-2016")
        doc = project_jsonld(ent)
        self.assertEqual(doc["@type"], "Movie")
        self.assertEqual(doc["name"], "Arrival")
        self.assertEqual(doc["datePublished"], "2016")
        self.assertIn("sameAs", doc)
        self.assertIn("imdb.com", str(doc["sameAs"]))

    def test_jsonld_recording(self) -> None:
        ent = next(e for e in self.snap.entities if e.id == "music.recording.beep")
        doc = project_jsonld(ent)
        self.assertEqual(doc["@type"], "MusicRecording")
        self.assertEqual(doc["name"], "beep")

    def test_resolve_by_asset_id(self) -> None:
        r = resolve_asset(self.snap, asset_id="m_6d5d84")
        self.assertEqual(r.status, "accepted")
        self.assertEqual(r.entity_id, "work.movie.arrival-2016")

    def test_resolve_by_title_year(self) -> None:
        r = resolve_asset(self.snap, title="Arrival", year=2016)
        self.assertEqual(r.status, "accepted")
        self.assertEqual(r.entity_id, "work.movie.arrival-2016")

    def test_resolve_unlinked_asset(self) -> None:
        r = resolve_asset(self.snap, asset_id="m_ca931e")
        self.assertEqual(r.status, "no_match")

    def test_provider_ids_without_network(self) -> None:
        ent = next(e for e in self.snap.entities if e.id == "work.movie.arrival-2016")
        providers = {p.provider for p in ent.provider_ids}
        self.assertIn("imdb", providers)
        self.assertIn("tvdb", providers)


if __name__ == "__main__":
    unittest.main()

#!/usr/bin/env python3
"""Tests for semantic stages 1–8 (no network)."""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from project_semantic import project_snapshot  # noqa: E402
from semantic_schema import (  # noqa: E402
    ASSERTION_PROPERTIES,
    CONSTRUCTION_ORISHA_ITEM,
    CONSTRUCTION_ORISHA_LINKS,
    CONSTRUCTION_SCHEMA_ORG_JSONLD,
    ENTITY_TYPES,
    Assertion,
    Asset,
    Entity,
    SemanticSnapshot,
    display_title,
    join_asset,
    load_snapshot,
    project_all,
    project_jsonld,
    project_orisha_item,
    project_orisha_links,
    project_schema_org_jsonld,
    register_entity_type,
    resolve_asset,
    resolve_name_conflict,
    validate_entity,
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
        self.assertIn("themoviedb.org", str(doc["sameAs"]))

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
        self.assertIn("tmdb", providers)
        self.assertIn("tvdb", providers)

    def test_missing_snapshot(self) -> None:
        self.assertIsNone(load_snapshot(ROOT / "fixtures" / "no-such-semantic.json"))
        self.assertIsNone(join_asset(None, asset_id="m_6d5d84", physical_title="Arrival (2016)"))

    def test_join_unlinked_asset(self) -> None:
        self.assertIsNone(join_asset(self.snap, asset_id="m_ca931e", physical_title="demo"))

    def test_join_arrival(self) -> None:
        j = join_asset(self.snap, asset_id="m_6d5d84", physical_title="Arrival (2016)")
        self.assertIsNotNone(j)
        self.assertEqual(j["title"], "Arrival")
        self.assertEqual(j["entity_id"], "work.movie.arrival-2016")

    def test_display_title_falls_back_to_physical(self) -> None:
        self.assertEqual(display_title(None, "demo"), "demo")

    def test_name_conflict_keeps_both(self) -> None:
        ent = Entity(
            id="work.movie.conflict",
            type="Movie",
            title="File Name",
            assertions=[
                Assertion(
                    entity="work.movie.conflict",
                    property="name",
                    value="File Name",
                    source={"kind": "user", "provider": "fixture"},
                    status="accepted",
                ),
                Assertion(
                    entity="work.movie.conflict",
                    property="name",
                    value="Provider Title",
                    source={"kind": "provider", "provider": "tmdb"},
                    status="accepted",
                ),
            ],
        )
        resolve_name_conflict(ent, prefer="user")
        statuses = {a.value: a.status for a in ent.assertions if a.property == "name"}
        self.assertEqual(statuses["File Name"], "accepted")
        self.assertEqual(statuses["Provider Title"], "superseded")
        self.assertEqual(len([a for a in ent.assertions if a.property == "name"]), 2)
        self.assertEqual(ent.title, "File Name")

    def test_entity_roundtrip_omits_representation_fields(self) -> None:
        ent = Entity(id="work.movie.x", type="Movie", title="X")
        d = ent.to_dict()
        self.assertNotIn("display_title", d)
        self.assertNotIn("display_description", d)
        self.assertNotIn("jsonld", d)
        snap = SemanticSnapshot(entities=[ent])
        dumped = snap.to_dict()["entities"][0]
        self.assertNotIn("display_title", dumped)
        self.assertNotIn("jsonld", dumped)

    def test_from_dict_ignores_legacy_entity_display_fields(self) -> None:
        snap = SemanticSnapshot.from_dict(
            {
                "version": 1,
                "assets": [],
                "entities": [
                    {
                        "id": "work.movie.x",
                        "type": "Movie",
                        "title": "X",
                        "display_title": "LEAK",
                        "display_description": "nope",
                        "jsonld": "{}",
                    }
                ],
            }
        )
        ent = snap.entities[0]
        self.assertFalse(hasattr(ent, "display_title"))
        self.assertFalse(hasattr(ent, "jsonld"))
        dumped = ent.to_dict()
        self.assertNotIn("display_title", dumped)
        self.assertNotIn("jsonld", dumped)
        self.assertNotIn("projections", snap.to_dict())

    def test_from_dict_skips_legacy_mixed_projection_blob(self) -> None:
        snap = SemanticSnapshot.from_dict(
            {
                "version": 1,
                "assets": [],
                "entities": [],
                "projections": [
                    {
                        "asset_id": "m_6d5d84",
                        "entity_id": "work.movie.arrival-2016",
                        "display_title": "Arrival",
                        "jsonld": "{}",
                        "tmdb_url": "https://www.themoviedb.org/movie/329865",
                    }
                ],
            }
        )
        self.assertEqual(snap.projections, [])

    def test_movie_name_assertion_valid(self) -> None:
        ent = Entity(
            id="work.movie.x",
            type="Movie",
            title="X",
            assertions=[
                Assertion(
                    entity="work.movie.x",
                    property="name",
                    value="X",
                    source={"kind": "user"},
                )
            ],
        )
        self.assertEqual(validate_entity(ent), [])

    def test_unknown_property_on_movie_flagged(self) -> None:
        ent = Entity(
            id="work.movie.x",
            type="Movie",
            title="X",
            assertions=[
                Assertion(
                    entity="work.movie.x",
                    property="runtime",
                    value=118,
                    source={"kind": "user"},
                )
            ],
        )
        issues = validate_entity(ent)
        self.assertTrue(any("runtime" in i for i in issues), issues)

    def test_register_type_without_entity_fields(self) -> None:
        previous = ENTITY_TYPES.get("PodcastEpisode")
        try:
            spec = register_entity_type(
                "PodcastEpisode",
                admitted_properties=("name", "description"),
                constructions=(CONSTRUCTION_ORISHA_ITEM,),
            )
            self.assertEqual(spec.id, "PodcastEpisode")
            self.assertIn("name", spec.admitted_properties)
            ent = Entity(id="ep.1", type="PodcastEpisode", title="Hello")
            self.assertEqual(validate_entity(ent), [])
            self.assertFalse(hasattr(ent, "display_title"))
            self.assertFalse(hasattr(Entity, "podcast_field"))
            self.assertNotIn("display_title", ent.to_dict())
            row = project_orisha_item(ent, asset_id="m_ep")
            self.assertIsNotNone(row)
            self.assertEqual(row.construction, CONSTRUCTION_ORISHA_ITEM)
            self.assertIsNone(project_orisha_links(ent, asset_id="m_ep"))
            self.assertIsNone(project_schema_org_jsonld(ent, asset_id="m_ep"))
        finally:
            if previous is None:
                ENTITY_TYPES.pop("PodcastEpisode", None)
            else:
                ENTITY_TYPES["PodcastEpisode"] = previous

    def test_unknown_type_kept_not_projected(self) -> None:
        snap = SemanticSnapshot(
            assets=[
                Asset(id="m_x", path="x.mp4", kind="movie", entity_ids=["work.other.x"])
            ],
            entities=[Entity(id="work.other.x", type="Sculpture", title="X", asset_ids=["m_x"])],
        )
        self.assertTrue(any("unknown type" in i for i in validate_entity(snap.entities[0])))
        self.assertEqual(project_all(snap), [])
        dumped = snap.to_dict()
        self.assertEqual(dumped["entities"][0]["type"], "Sculpture")

    def test_constructions_are_named_not_mixed(self) -> None:
        ent = next(e for e in self.snap.entities if e.id == "work.movie.arrival-2016")
        item = project_orisha_item(ent, asset_id="m_6d5d84")
        links = project_orisha_links(ent, asset_id="m_6d5d84")
        jsonld = project_schema_org_jsonld(ent, asset_id="m_6d5d84")
        self.assertIsNotNone(item)
        self.assertEqual(item.construction, CONSTRUCTION_ORISHA_ITEM)
        self.assertEqual(item.display_title, "Arrival")
        self.assertIn("Fixture movie", item.display_description)
        self.assertNotIn("jsonld", item.to_dict())
        self.assertNotIn("tmdb_url", item.to_dict())
        self.assertIsNotNone(links)
        self.assertEqual(links.construction, CONSTRUCTION_ORISHA_LINKS)
        self.assertEqual(links.tmdb_url, "https://www.themoviedb.org/movie/329865")
        self.assertEqual(links.imdb_url, "https://www.imdb.com/title/tt2543164/")
        self.assertNotIn("display_title", links.to_dict())
        self.assertNotIn("jsonld", links.to_dict())
        self.assertIsNotNone(jsonld)
        self.assertEqual(jsonld.construction, CONSTRUCTION_SCHEMA_ORG_JSONLD)
        self.assertIn('"@type":"Movie"', jsonld.jsonld)
        self.assertIn("themoviedb.org", jsonld.jsonld)
        self.assertNotIn("display_title", jsonld.to_dict())
        self.assertNotIn("tmdb_url", jsonld.to_dict())
        self.assertNotIn("display_title", ent.to_dict())
        self.assertNotIn("jsonld", ent.to_dict())

    def test_project_snapshot_skips_unlinked_and_tvseries(self) -> None:
        rows = project_snapshot(self.snap)
        ids = {p.asset_id for p in rows}
        self.assertIn("m_6d5d84", ids)
        self.assertIn("m_31afda", ids)
        self.assertNotIn("m_ca931e", ids)
        self.assertFalse(any(p.entity_id == "series.fixture-demo" for p in rows))
        constructions = {(p.asset_id, p.construction) for p in rows}
        self.assertIn(("m_6d5d84", CONSTRUCTION_ORISHA_ITEM), constructions)
        self.assertIn(("m_6d5d84", CONSTRUCTION_ORISHA_LINKS), constructions)
        self.assertIn(("m_6d5d84", CONSTRUCTION_SCHEMA_ORG_JSONLD), constructions)
        self.assertIn(("m_31afda", CONSTRUCTION_ORISHA_ITEM), constructions)
        self.assertIn(("m_31afda", CONSTRUCTION_SCHEMA_ORG_JSONLD), constructions)
        self.assertNotIn(("m_31afda", CONSTRUCTION_ORISHA_LINKS), constructions)
        self.assertIn("TVSeries", ENTITY_TYPES)
        self.assertIn(CONSTRUCTION_ORISHA_ITEM, ENTITY_TYPES["TVSeries"].constructions)
        self.assertIn("name", ASSERTION_PROPERTIES)

    def test_andor_relations_next_and_part_of(self) -> None:
        from semantic_schema import relate

        nxt = relate(self.snap, "episode.andor.s1e1", "next")
        self.assertEqual(len(nxt), 1)
        self.assertEqual(nxt[0].object, "episode.andor.s1e2")
        s1_to_s2 = relate(self.snap, "episode.andor.s1e2", "next")
        self.assertEqual(len(s1_to_s2), 1)
        self.assertEqual(s1_to_s2[0].object, "episode.andor.s2e1")
        parts = relate(self.snap, "episode.andor.s1e1", "part_of")
        self.assertEqual(parts[0].object, "season.andor.s1")

    def test_project_cli_writes_projections(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "semantic.json"
            r = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts" / "project_semantic.py"),
                    "--in",
                    str(ROOT / "fixtures" / "semantic.json"),
                    "--out",
                    str(out),
                ],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(r.returncode, 0, r.stderr)
            data = json.loads(out.read_text(encoding="utf-8"))
            ent = next(e for e in data["entities"] if e["id"] == "work.movie.arrival-2016")
            self.assertNotIn("display_title", ent)
            self.assertNotIn("display_description", ent)
            self.assertNotIn("jsonld", ent)
            item = next(
                p
                for p in data["projections"]
                if p["asset_id"] == "m_6d5d84" and p["construction"] == CONSTRUCTION_ORISHA_ITEM
            )
            self.assertEqual(item["display_title"], "Arrival")
            self.assertIn("hand-linked", item["display_description"])
            links = next(
                p
                for p in data["projections"]
                if p["asset_id"] == "m_6d5d84" and p["construction"] == CONSTRUCTION_ORISHA_LINKS
            )
            self.assertEqual(links["tmdb_url"], "https://www.themoviedb.org/movie/329865")
            self.assertEqual(links["imdb_url"], "https://www.imdb.com/title/tt2543164/")
            jsonld = next(
                p
                for p in data["projections"]
                if p["asset_id"] == "m_6d5d84" and p["construction"] == CONSTRUCTION_SCHEMA_ORG_JSONLD
            )
            self.assertIn('"@type":"Movie"', jsonld["jsonld"])
            self.assertIn("themoviedb.org", jsonld["jsonld"])
            self.assertIn("imdb.com", jsonld["jsonld"])
            self.assertFalse(any(p["asset_id"] == "m_ca931e" for p in data["projections"]))
            asset = next(a for a in data["assets"] if a["id"] == "m_6d5d84")
            self.assertIn("work.movie.arrival-2016", asset["entity_ids"])

    def test_prefetch_enrich_then_project(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            enriched = Path(td) / "enriched.json"
            projected = Path(td) / "projected.json"
            r = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts" / "enrich_tmdb.py"),
                    "--in",
                    str(ROOT / "fixtures" / "semantic.json"),
                    "--out",
                    str(enriched),
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
            r = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts" / "project_semantic.py"),
                    "--in",
                    str(enriched),
                    "--out",
                    str(projected),
                ],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(r.returncode, 0, r.stderr)
            data = json.loads(projected.read_text(encoding="utf-8"))
            ent = next(e for e in data["entities"] if e["id"] == "work.movie.arrival-2016")
            self.assertNotIn("jsonld", ent)
            self.assertNotIn("display_title", ent)
            item = next(
                p
                for p in data["projections"]
                if p["asset_id"] == "m_6d5d84" and p["construction"] == CONSTRUCTION_ORISHA_ITEM
            )
            self.assertEqual(item["display_title"], "Arrival")
            self.assertIn("Recorded TMDB movie payload", item["display_description"])
            jsonld = next(
                p
                for p in data["projections"]
                if p["asset_id"] == "m_6d5d84" and p["construction"] == CONSTRUCTION_SCHEMA_ORG_JSONLD
            )
            self.assertIn("themoviedb.org/movie/329865", jsonld["jsonld"])
            self.assertIn("tt2543164", jsonld["jsonld"])


if __name__ == "__main__":
    unittest.main()

#!/usr/bin/env python3
"""Offline catalog hydrate tests (fixture path; no network)."""
from __future__ import annotations

import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HYDRATE = ROOT / "scripts" / "hydrate_catalog.py"
HANDLER_STEMS = (
    ROOT / "src" / "consumers.kz",
    ROOT / "src" / "consumers.k",
    ROOT / "src" / "index.kz",
    ROOT / "src" / "index.k",
    ROOT / "src" / "graph.kz",
    ROOT / "src" / "graph.k",
    ROOT / "src" / "catalog.kz",
    ROOT / "src" / "catalog.k",
    ROOT / "main.k",
)
FORBIDDEN = (
    "api.themoviedb.org",
    "api4.thetvdb.com",
    "urllib.request",
    "urllib.error",
    "std.http",
    "ffmpeg",
    "ffprobe",
)

ENTRIES_DDL = """
CREATE TABLE IF NOT EXISTS entries (
  id TEXT PRIMARY KEY,
  kind TEXT NOT NULL,
  title TEXT NOT NULL,
  path TEXT NOT NULL UNIQUE,
  bytes INTEGER NOT NULL DEFAULT 0,
  modified_ns INTEGER NOT NULL DEFAULT 0,
  mime TEXT NOT NULL DEFAULT '',
  container TEXT NOT NULL DEFAULT '',
  poster TEXT NOT NULL DEFAULT '',
  subtitle TEXT NOT NULL DEFAULT '',
  year INTEGER NOT NULL DEFAULT 0,
  video_codec TEXT NOT NULL DEFAULT '',
  video_brand TEXT NOT NULL DEFAULT '',
  audio_codec TEXT NOT NULL DEFAULT '',
  work_key TEXT NOT NULL DEFAULT '',
  season INTEGER NOT NULL DEFAULT 0,
  episode INTEGER NOT NULL DEFAULT 0,
  imdb_id TEXT NOT NULL DEFAULT '',
  work_title TEXT NOT NULL DEFAULT ''
);
"""


def _run(args: list[str], *, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(HYDRATE), *args],
        check=False,
        capture_output=True,
        text=True,
        env=env,
    )


def _seed(catalog: Path, imdb: str = "tt2543164") -> None:
    conn = sqlite3.connect(str(catalog))
    conn.executescript(ENTRIES_DDL)
    conn.execute(
        "INSERT INTO entries(id,kind,title,path,work_key,imdb_id,work_title) VALUES(?,?,?,?,?,?,?)",
        (
            "m_arrival",
            "movie",
            "Arrival",
            "movies/Arrival (2016)/Arrival.mkv",
            "movies/Arrival (2016)",
            imdb,
            "Arrival",
        ),
    )
    conn.commit()
    conn.close()


class HydrateCatalogTests(unittest.TestCase):
    def test_offline_noop(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            catalog = Path(td) / "catalog.sqlite"
            _seed(catalog)
            r = _run(["--catalog", str(catalog), "--offline", "--no-dotenv"])
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn("skip", r.stdout.lower())
            conn = sqlite3.connect(str(catalog))
            n = conn.execute("SELECT COUNT(*) FROM hydrate_works").fetchone()[0]
            conn.close()
            self.assertEqual(n, 0)

    def test_no_keys_noop(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            catalog = Path(td) / "catalog.sqlite"
            _seed(catalog)
            env = {k: v for k, v in __import__("os").environ.items() if k not in (
                "TMDB_API_KEY",
                "TMDB_API_TOKEN",
                "TMDB_READ_ACCESS_TOKEN",
                "TVDB_API_KEY",
                "TVDB_KEY",
            )}
            env.update(
                {
                    "TMDB_API_KEY": "",
                    "TMDB_API_TOKEN": "",
                    "TVDB_API_KEY": "",
                }
            )
            r = _run(["--catalog", str(catalog), "--no-dotenv"], env=env)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn("skip", r.stdout.lower())
            conn = sqlite3.connect(str(catalog))
            n = conn.execute("SELECT COUNT(*) FROM hydrate_works").fetchone()[0]
            conn.close()
            self.assertEqual(n, 0)

    def test_tmdb_fixture_writes_overlay(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            catalog = Path(td) / "catalog.sqlite"
            _seed(catalog)
            r = _run(
                [
                    "--catalog",
                    str(catalog),
                    "--fixture",
                    str(ROOT / "fixtures" / "tmdb" / "movie_329865.json"),
                    "--imdb",
                    "tt2543164",
                    "--kind",
                    "movie",
                    "--work-key",
                    "movies/Arrival (2016)",
                    "--no-dotenv",
                ]
            )
            self.assertEqual(r.returncode, 0, r.stderr + r.stdout)
            conn = sqlite3.connect(str(catalog))
            row = conn.execute(
                "SELECT imdb_id, source, tmdb_id, title, poster_url, actors, plot FROM hydrate_works WHERE imdb_id=?",
                ("tt2543164",),
            ).fetchone()
            self.assertIsNotNone(row)
            self.assertEqual(row[0], "tt2543164")
            self.assertEqual(row[1], "tmdb")
            self.assertEqual(row[2], "329865")
            self.assertEqual(row[3], "Arrival")
            self.assertIn("image.tmdb.org", row[4])
            self.assertIn("Amy Adams", row[5])
            self.assertIn("Jeremy Renner", row[5])
            self.assertTrue(row[6])
            ent = conn.execute("SELECT id, type FROM sem_entities").fetchone()
            self.assertIsNotNone(ent)
            self.assertEqual(ent[1], "Movie")
            name = conn.execute(
                "SELECT value FROM sem_assertions WHERE property='name' LIMIT 1"
            ).fetchone()
            self.assertEqual(name[0], "Arrival")
            same = conn.execute(
                "SELECT object FROM sem_relations WHERE kind='same_as' AND object='tt2543164'"
            ).fetchone()
            self.assertIsNotNone(same)
            conn.close()

    def test_tvdb_fixture_writes_overlay(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            catalog = Path(td) / "catalog.sqlite"
            _seed(catalog, imdb="tt0944947")
            r = _run(
                [
                    "--catalog",
                    str(catalog),
                    "--tvdb-fixture",
                    str(ROOT / "fixtures" / "tvdb" / "series_121361.json"),
                    "--imdb",
                    "tt0944947",
                    "--kind",
                    "tv",
                    "--no-dotenv",
                ]
            )
            self.assertEqual(r.returncode, 0, r.stderr + r.stdout)
            conn = sqlite3.connect(str(catalog))
            row = conn.execute(
                "SELECT source, tvdb_id, poster_url, actors FROM hydrate_works WHERE imdb_id=?",
                ("tt0944947",),
            ).fetchone()
            self.assertIsNotNone(row)
            self.assertEqual(row[0], "tvdb")
            self.assertEqual(row[1], "121361")
            self.assertIn("artworks.thetvdb.com", row[2])
            self.assertIn("Peter Dinklage", row[3])
            ent = conn.execute("SELECT id FROM sem_entities LIMIT 1").fetchone()
            self.assertIsNotNone(ent)
            conn.close()

    def test_handlers_never_call_providers(self) -> None:
        hits: list[str] = []
        for path in HANDLER_STEMS:
            text = path.read_text(encoding="utf-8")
            for i, line in enumerate(text.splitlines(), 1):
                stripped = line.strip()
                if stripped.startswith("//") or stripped.startswith("#"):
                    continue
                if "never call" in stripped.lower() or "does not call" in stripped.lower():
                    continue
                lower = stripped.lower()
                for needle in FORBIDDEN:
                    if needle in lower:
                        hits.append(f"{path.name}:{i}: {stripped}")
        self.assertEqual(hits, [], "handlers must not call TMDB/TVDB/ffmpeg:\n" + "\n".join(hits))


if __name__ == "__main__":
    unittest.main()

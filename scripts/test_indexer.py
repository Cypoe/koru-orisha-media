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
            self.assertIn("movies/demo.mp4", paths)
            self.assertIn("music/beep.wav", paths)
            kinds = {e["path"]: e["kind"] for e in data["entries"]}
            self.assertEqual(kinds["movies/demo.mp4"], "movie")
            self.assertEqual(kinds["music/beep.wav"], "audio")
            for e in data["entries"]:
                self.assertTrue(e["id"].startswith("m_"))
                self.assertNotIn("..", e["path"])
                self.assertFalse(e["path"].startswith("/"))
                self.assertIn("container", e)
                self.assertEqual(e["container"], Path(e["path"]).suffix.lstrip(".").lower())

    def test_year_from_stem(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "media"
            movies = root / "movies"
            movies.mkdir(parents=True)
            (movies / "Arrival (2016).mp4").write_bytes(b"x")
            out = Path(td) / "manifest.json"
            subprocess.check_call(
                [sys.executable, str(INDEXER), "--root", str(root), "--out", str(out)]
            )
            data = json.loads(out.read_text(encoding="utf-8"))
            self.assertEqual(data["entries"][0]["year"], 2016)

    def test_poster_sidecar(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "media"
            movies = root / "movies"
            movies.mkdir(parents=True)
            (movies / "show.mp4").write_bytes(b"vid")
            (movies / "show.jpg").write_bytes(b"\xff\xd8fake")
            out = Path(td) / "manifest.json"
            subprocess.check_call(
                [sys.executable, str(INDEXER), "--root", str(root), "--out", str(out)]
            )
            data = json.loads(out.read_text(encoding="utf-8"))
            self.assertEqual(len(data["entries"]), 1)
            self.assertEqual(data["entries"][0]["poster"], "movies/show.jpg")
            self.assertEqual(data["entries"][0]["container"], "mp4")

    def test_subtitle_sidecar(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "media"
            movies = root / "movies"
            movies.mkdir(parents=True)
            (movies / "show.mp4").write_bytes(b"vid")
            (movies / "show.vtt").write_text("WEBVTT\n\n00:00:00.000 --> 00:00:01.000\nHi\n", encoding="utf-8")
            out = Path(td) / "manifest.json"
            subprocess.check_call(
                [sys.executable, str(INDEXER), "--root", str(root), "--out", str(out)]
            )
            data = json.loads(out.read_text(encoding="utf-8"))
            self.assertEqual(len(data["entries"]), 1)
            self.assertEqual(data["entries"][0]["subtitle"], "movies/show.vtt")
            # .vtt is not indexed as its own media entry
            paths = {e["path"] for e in data["entries"]}
            self.assertNotIn("movies/show.vtt", paths)

    def test_audio_kind_indexed(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "media"
            music = root / "music"
            music.mkdir(parents=True)
            (music / "tone.wav").write_bytes(b"RIFF")
            out = Path(td) / "manifest.json"
            subprocess.check_call(
                [sys.executable, str(INDEXER), "--root", str(root), "--out", str(out)]
            )
            data = json.loads(out.read_text(encoding="utf-8"))
            self.assertEqual(len(data["entries"]), 1)
            self.assertEqual(data["entries"][0]["kind"], "audio")
            self.assertEqual(data["entries"][0]["path"], "music/tone.wav")
            self.assertEqual(data["entries"][0]["container"], "wav")

    def test_kind_from_library_root(self) -> None:
        """Library root names the work; audio under movies/shows is extra."""
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "media"
            (root / "movies").mkdir(parents=True)
            (root / "shows" / "Demo").mkdir(parents=True)
            (root / "music").mkdir(parents=True)
            (root / "movies" / "film.mp4").write_bytes(b"v")
            (root / "movies" / "bonus.wav").write_bytes(b"RIFF")
            (root / "shows" / "Demo" / "S01E01.mkv").write_bytes(b"e")
            (root / "music" / "track.mp4").write_bytes(b"a")
            (root / "loose.mp4").write_bytes(b"x")
            out = Path(td) / "manifest.json"
            subprocess.check_call(
                [sys.executable, str(INDEXER), "--root", str(root), "--out", str(out)]
            )
            data = json.loads(out.read_text(encoding="utf-8"))
            kinds = {e["path"]: e["kind"] for e in data["entries"]}
            self.assertEqual(kinds["movies/film.mp4"], "movie")
            self.assertEqual(kinds["movies/bonus.wav"], "extra")
            self.assertEqual(kinds["shows/Demo/S01E01.mkv"], "tv")
            self.assertEqual(kinds["music/track.mp4"], "audio")
            self.assertEqual(kinds["loose.mp4"], "movie")

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

    def _load_indexer(self):
        import importlib.util

        spec = importlib.util.spec_from_file_location("index_media", INDEXER)
        mod = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(mod)
        return mod

    def test_id_sidecar_survives_rename(self) -> None:
        """Same-dir rename: orphan sidecar is auto-moved onto the new media path."""
        mod = self._load_indexer()

        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "media"
            movies = root / "movies"
            movies.mkdir(parents=True)
            media = movies / "show.mp4"
            media.write_bytes(b"vid-bytes")
            before = mod.index_root(root, write_id_sidecars=True)
            self.assertEqual(len(before), 1)
            eid = before[0]["id"]
            self.assertTrue((movies / "show.mp4.id").is_file())
            renamed = movies / "renamed.mp4"
            media.rename(renamed)
            # Leave show.mp4.id in place — indexer must reclaim it.
            self.assertFalse((movies / "renamed.mp4.id").exists())
            after = mod.index_root(root)
            self.assertEqual(after[0]["path"], "movies/renamed.mp4")
            self.assertEqual(after[0]["id"], eid)
            self.assertTrue((movies / "renamed.mp4.id").is_file())
            self.assertFalse((movies / "show.mp4.id").exists())

    def test_id_sidecar_survives_cross_dir_move(self) -> None:
        """Cross-directory move: fingerprint in sidecar uniquely reclaim identity."""
        mod = self._load_indexer()

        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "media"
            movies = root / "movies"
            other = root / "other"
            movies.mkdir(parents=True)
            other.mkdir(parents=True)
            media = movies / "show.mp4"
            media.write_bytes(b"move-bytes")
            before = mod.index_root(root, write_id_sidecars=True)
            eid = before[0]["id"]
            side_meta = json.loads((movies / "show.mp4.id").read_text(encoding="utf-8"))
            self.assertEqual(side_meta["id"], eid)
            self.assertIn("bytes", side_meta)
            self.assertIn("modified_ns", side_meta)

            dest = other / "moved.mp4"
            media.rename(dest)
            # Orphan remains under movies/; media is under other/.
            self.assertTrue((movies / "show.mp4.id").is_file())
            after = mod.index_root(root, write_id_sidecars=True)
            self.assertEqual(after[0]["path"], "other/moved.mp4")
            self.assertEqual(after[0]["id"], eid)
            self.assertTrue((other / "moved.mp4.id").is_file())
            self.assertFalse((movies / "show.mp4.id").exists())

    def test_id_sidecar_ambiguous_same_dir_not_moved(self) -> None:
        """Two orphans + two unmatched in one dir: do not guess."""
        mod = self._load_indexer()

        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "media"
            movies = root / "movies"
            movies.mkdir(parents=True)
            a = movies / "a.mp4"
            b = movies / "b.mp4"
            a.write_bytes(b"aaa")
            b.write_bytes(b"bbb")
            # Legacy id-only sidecars (no fingerprint) for both.
            (movies / "a.mp4.id").write_text('{"id": "m_aaaaaa"}\n', encoding="utf-8")
            (movies / "b.mp4.id").write_text('{"id": "m_bbbbbb"}\n', encoding="utf-8")
            a.rename(movies / "x.mp4")
            b.rename(movies / "y.mp4")
            moved = mod.reclaim_orphaned_id_sidecars(root)
            self.assertEqual(moved, 0)
            self.assertTrue((movies / "a.mp4.id").is_file())
            self.assertTrue((movies / "b.mp4.id").is_file())
            self.assertFalse((movies / "x.mp4.id").exists())
            self.assertFalse((movies / "y.mp4.id").exists())

    def test_injectable_probe_merges_fields(self) -> None:
        import importlib.util

        spec = importlib.util.spec_from_file_location("index_media", INDEXER)
        mod = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(mod)

        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "a.mp4").write_bytes(b"x")

            def probe(_p: Path) -> dict:
                return {"video": [{"codec": "probe-test", "width": 1280, "height": 720}]}

            entries = mod.index_root(root, probe=probe)
            self.assertEqual(entries[0]["video"][0]["codec"], "probe-test")

    def test_ftyp_probe_reads_brand(self) -> None:
        import importlib.util

        spec = importlib.util.spec_from_file_location("index_media", INDEXER)
        mod = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(mod)

        # Minimal ISO BMFF: size(16) + 'ftyp' + major('isom') + minor(0)
        ftyp = (
            b"\x00\x00\x00\x10"
            + b"ftyp"
            + b"isom"
            + b"\x00\x00\x00\x00"
        )
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "clip.mp4").write_bytes(ftyp + b"\x00" * 8)
            entries = mod.index_root(root, probe=mod.probe_ftyp)
            self.assertEqual(entries[0]["video"][0]["brand"], "isom")
            self.assertEqual(entries[0]["video"][0]["codec"], "unknown")

    def test_extras_and_books_kinds(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "media"
            movie_dir = root / "movies" / "Arrival (2016)"
            extras = movie_dir / "extras"
            extras.mkdir(parents=True)
            (movie_dir / "Arrival (2016).mkv").write_bytes(b"m")
            (extras / "featurette.mkv").write_bytes(b"x")
            books = root / "books"
            books.mkdir(parents=True)
            (books / "note.epub").write_bytes(b"e")
            (root / "musicVidoes").mkdir(parents=True)
            (root / "musicVidoes" / "clip.mp4").write_bytes(b"v")
            out = Path(td) / "manifest.json"
            subprocess.check_call(
                [sys.executable, str(INDEXER), "--root", str(root), "--out", str(out)]
            )
            data = json.loads(out.read_text(encoding="utf-8"))
            kinds = {e["path"]: e["kind"] for e in data["entries"]}
            self.assertEqual(kinds["movies/Arrival (2016)/Arrival (2016).mkv"], "movie")
            self.assertEqual(kinds["movies/Arrival (2016)/extras/featurette.mkv"], "extra")
            self.assertEqual(kinds["books/note.epub"], "book")
            self.assertEqual(kinds["musicVidoes/clip.mp4"], "musicVideo")

    def test_bind_maps_share_name(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            movies = Path(td) / "movies"
            movies.mkdir()
            (movies / "film.mp4").write_bytes(b"v")
            out = Path(td) / "manifest.json"
            subprocess.check_call(
                [
                    sys.executable,
                    str(INDEXER),
                    "--bind",
                    f"movies={movies}",
                    "--out",
                    str(out),
                ]
            )
            data = json.loads(out.read_text(encoding="utf-8"))
            self.assertEqual(data["entries"][0]["path"], "movies/film.mp4")
            self.assertEqual(data["entries"][0]["kind"], "movie")

    def test_work_key_and_display_title(self) -> None:
        mod = self._load_indexer()
        ep = "shows/Andor [tt9253284]/Andor (2022) Season - 1 [tt9253284]/Andor - S01E01 - Kassa.mkv"
        ost = "shows/Andor [tt9253284]/soundtrack/01 - Andor (Main Title Theme) - Episode 5.mp3"
        self.assertEqual(mod.work_key(ep), "shows/Andor [tt9253284]")
        self.assertEqual(mod.work_key(ost), "shows/Andor [tt9253284]")
        self.assertEqual(
            mod.work_key("shows/Andor [tt9253284]/clips/deleted.mkv"),
            "shows/Andor [tt9253284]",
        )
        self.assertEqual(mod.work_display_title("shows/Andor [tt9253284]"), "Andor")
        self.assertEqual(
            mod.work_display_title("movies/Movie (2021) [imdbid-tt12801262]"),
            "Movie",
        )
        self.assertEqual(mod.parse_imdb_id(ep), "tt9253284")
        self.assertEqual(mod.parse_imdb_id("movies/Film [imdbid-tt12801262]/Film.mkv"), "tt12801262")
        self.assertEqual(mod.parse_season_episode(ep), (1, 1))
        self.assertEqual(
            mod.parse_season_episode("shows/X/Season 02/untitled.mkv"),
            (2, 0),
        )

    def test_andor_layout_kinds_posters_nfo(self) -> None:
        """Jellyfin/Sonarr Andor tree: one series work, soundtrack extra, series poster, nfo title."""
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "media"
            series = root / "shows" / "Andor [tt9253284]"
            season = series / "Andor (2022) Season - 1 [tt9253284]"
            ost = series / "soundtrack"
            season.mkdir(parents=True)
            ost.mkdir(parents=True)
            (series / "poster.jpg").write_bytes(b"\xff\xd8fake")
            ep = season / "Andor - S01E01 - Kassa.mkv"
            ep.write_bytes(b"vid")
            (season / "Andor - S01E01 - Kassa.nfo").write_text(
                '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
                "<episodedetails>\n"
                "  <title>Kassa</title>\n"
                "  <showtitle>Andor</showtitle>\n"
                "  <plot>Cassian Andor&apos;s journey begins on Ferrix.</plot>\n"
                "  <aired>2022-09-21</aired>\n"
                "  <rating>8.4</rating>\n"
                "</episodedetails>\n",
                encoding="utf-8",
            )
            (series / "tvshow.nfo").write_text(
                "<tvshow>\n"
                "  <title>Andor</title>\n"
                "  <plot>A spy thriller set in the Star Wars universe.</plot>\n"
                "  <premiered>2022-09-21</premiered>\n"
                "  <ratings><rating name=\"imdb\" max=\"10\"><value>8.4</value></rating></ratings>\n"
                "</tvshow>\n",
                encoding="utf-8",
            )
            trailers = series / "trailers"
            trailers.mkdir()
            (trailers / "Andor - Official Trailer.mp4").write_bytes(b"vid")
            (ost / "01 - Andor (Main Title Theme) - Episode 5.mp3").write_bytes(b"ID3")
            (series / "01 - Andor (Main Title Theme) - Episode 5.flac").write_bytes(b"fLaC")
            out = Path(td) / "manifest.json"
            subprocess.check_call(
                [sys.executable, str(INDEXER), "--root", str(root), "--out", str(out)]
            )
            data = json.loads(out.read_text(encoding="utf-8"))
            by_path = {e["path"]: e for e in data["entries"]}
            video = by_path[
                "shows/Andor [tt9253284]/Andor (2022) Season - 1 [tt9253284]/Andor - S01E01 - Kassa.mkv"
            ]
            theme = by_path[
                "shows/Andor [tt9253284]/soundtrack/01 - Andor (Main Title Theme) - Episode 5.mp3"
            ]
            loose_audio = by_path[
                "shows/Andor [tt9253284]/01 - Andor (Main Title Theme) - Episode 5.flac"
            ]
            self.assertEqual(video["kind"], "tv")
            self.assertEqual(theme["kind"], "extra")
            self.assertEqual(loose_audio["kind"], "extra")
            self.assertEqual(video["title"], "Kassa")
            self.assertEqual(video["work_title"], "Andor")
            self.assertEqual(video["work_key"], "shows/Andor [tt9253284]")
            self.assertEqual(theme["work_key"], video["work_key"])
            self.assertEqual(video["season"], 1)
            self.assertEqual(video["episode"], 1)
            self.assertEqual(video["imdb_id"], "tt9253284")
            self.assertEqual(video["poster"], "shows/Andor [tt9253284]/poster.jpg")
            self.assertEqual(theme["poster"], "shows/Andor [tt9253284]/poster.jpg")
            self.assertEqual(video["plot"], "Cassian Andor's journey begins on Ferrix.")
            self.assertEqual(video["aired"], "2022-09-21")
            self.assertEqual(video["rating"], "8.4")
            self.assertEqual(video["work_plot"], "A spy thriller set in the Star Wars universe.")
            self.assertEqual(video["work_aired"], "2022-09-21")
            self.assertEqual(video["work_rating"], "8.4")
            trailer = by_path[
                "shows/Andor [tt9253284]/trailers/Andor - Official Trailer.mp4"
            ]
            self.assertEqual(trailer["kind"], "extra")
            self.assertEqual(trailer["work_key"], video["work_key"])

    def test_embedded_audio_cover_last_resort(self) -> None:
        jpeg = bytes.fromhex("ffd8ffe000104a46494600010100000100010000ffd9")
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "media"
            album = root / "music" / "Artist" / "Album"
            album.mkdir(parents=True)
            (album / "01 - Track.mp3").write_bytes(b"ID3" + jpeg + b"\xff\xfb")
            out = Path(td) / "manifest.json"
            subprocess.check_call(
                [sys.executable, str(INDEXER), "--root", str(root), "--out", str(out)]
            )
            data = json.loads(out.read_text(encoding="utf-8"))
            self.assertEqual(len(data["entries"]), 1)
            self.assertEqual(data["entries"][0]["poster"], "music/Artist/Album/cover.jpg")
            cover = album / "cover.jpg"
            self.assertTrue(cover.is_file())
            self.assertTrue(cover.read_bytes().startswith(b"\xff\xd8"))

    def test_embedded_cover_skipped_when_sidecar_exists(self) -> None:
        jpeg = bytes.fromhex("ffd8ffe000104a46494600010100000100010000ffd9")
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "media"
            album = root / "music" / "Artist" / "Album"
            album.mkdir(parents=True)
            (album / "folder.png").write_bytes(b"png")
            (album / "01 - Track.mp3").write_bytes(b"ID3" + jpeg)
            out = Path(td) / "manifest.json"
            subprocess.check_call(
                [sys.executable, str(INDEXER), "--root", str(root), "--out", str(out)]
            )
            data = json.loads(out.read_text(encoding="utf-8"))
            self.assertEqual(data["entries"][0]["poster"], "music/Artist/Album/folder.png")
            self.assertFalse((album / "cover.jpg").exists())

    def test_poster_walks_to_work_not_library_root(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "media"
            shows = root / "shows"
            series = shows / "Andor [tt9253284]"
            season = series / "Season 01"
            season.mkdir(parents=True)
            (shows / "poster.jpg").write_bytes(b"lib")
            (series / "folder.png").write_bytes(b"ser")
            (season / "Andor - S01E02 - That Would Be Me.mkv").write_bytes(b"v")
            out = Path(td) / "manifest.json"
            subprocess.check_call(
                [sys.executable, str(INDEXER), "--root", str(root), "--out", str(out)]
            )
            data = json.loads(out.read_text(encoding="utf-8"))
            self.assertEqual(len(data["entries"]), 1)
            self.assertEqual(data["entries"][0]["poster"], "shows/Andor [tt9253284]/folder.png")
            self.assertEqual(data["entries"][0]["season"], 1)
            self.assertEqual(data["entries"][0]["episode"], 2)

    def test_nfo_skipped_when_huge(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "media"
            movies = root / "movies"
            movies.mkdir(parents=True)
            (movies / "show.mp4").write_bytes(b"vid")
            nfo = movies / "show.nfo"
            nfo.write_text("<title>" + ("x" * (65 * 1024)) + "</title>\n", encoding="utf-8")
            out = Path(td) / "manifest.json"
            subprocess.check_call(
                [sys.executable, str(INDEXER), "--root", str(root), "--out", str(out)]
            )
            data = json.loads(out.read_text(encoding="utf-8"))
            self.assertEqual(data["entries"][0]["title"], "show")


if __name__ == "__main__":
    unittest.main()

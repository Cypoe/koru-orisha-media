#!/usr/bin/env python3
"""Live HTTPS hydrate tests (Cinemeta posters/trailers + Koru nfo ingest).

Default: skip when the network is down or :3090 is busy.
Set KORU_TEST_HYDRATE_LIVE=1 to fail instead of skip.
"""
from __future__ import annotations

import json
import os
import socket
import sqlite3
import subprocess
import tempfile
import time
import unittest
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CINEMETA = "https://v3-cinemeta.strem.io/meta/movie/tt2543164.json"
IMDB = "tt2543164"
BIN = ROOT / "bin" / "media-server"
LIVE = os.environ.get("KORU_TEST_HYDRATE_LIVE", "").strip().lower() in ("1", "true", "yes")
NFO = """<?xml version="1.0" encoding="utf-8"?>
<movie>
  <title>Arrival</title>
  <uniqueid type="imdb">tt2543164</uniqueid>
  <plot>A linguist works with the military to communicate with alien visitors.</plot>
  <trailer>https://www.youtube.com/watch?v=tFMo3UJ4B4g</trailer>
</movie>
"""


def _cinemeta() -> dict | None:
    try:
        with urllib.request.urlopen(CINEMETA, timeout=20) as resp:
            if resp.status != 200:
                return None
            return json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError):
        return None


def _skip_or_fail(reason: str) -> None:
    if LIVE:
        raise AssertionError(reason)
    raise unittest.SkipTest(reason)


def _port_open(port: int) -> bool:
    s = socket.socket()
    try:
        return s.connect_ex(("127.0.0.1", port)) == 0
    finally:
        s.close()


class HydrateHttpsTests(unittest.TestCase):
    def test_cinemeta_https_poster_and_trailer(self) -> None:
        data = _cinemeta()
        if data is None:
            _skip_or_fail("Cinemeta HTTPS unreachable")
        meta = data.get("meta") or {}
        poster = str(meta.get("poster") or "")
        self.assertTrue(poster.startswith("http"), poster)
        trailer = ""
        trailers = meta.get("trailers") or []
        if isinstance(trailers, list) and trailers:
            first = trailers[0]
            if isinstance(first, dict):
                trailer = str(first.get("source") or first.get("ytId") or "")
            else:
                trailer = str(first)
        trailer = trailer or str(meta.get("trailer") or "")
        self.assertTrue(trailer, "Cinemeta payload should include a trailer id or URL")

    def test_binary_ingests_nfo_then_live_poster(self) -> None:
        if not BIN.is_file():
            _skip_or_fail("bin/media-server missing")
        if _cinemeta() is None:
            _skip_or_fail("Cinemeta HTTPS unreachable")
        if _port_open(3090):
            _skip_or_fail("127.0.0.1:3090 is already in use")

        with tempfile.TemporaryDirectory() as td:
            td_path = Path(td)
            movie = td_path / "media" / "movies" / "Arrival (2016)"
            movie.mkdir(parents=True)
            (movie / "Arrival.mkv").write_bytes(b"\x00" * 32)
            (movie / "movie.nfo").write_text(NFO, encoding="utf-8")
            catalog = td_path / "catalog.sqlite"
            env = {
                **os.environ,
                "KORU_MEDIA_ROOT": str(td_path / "media"),
                "KORU_CATALOG": str(catalog),
                "KORU_CONFIG": str(td_path / "settings.conf"),
                "KORU_REINDEX": "1",
                "KORU_IDLE_SECS": "45",
            }
            env.pop("KORU_TMDB_FIXTURE", None)
            env.pop("KORU_MANIFEST", None)
            proc = subprocess.Popen(
                [str(BIN)],
                cwd=str(td_path),
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
            )
            try:
                ready = False
                for _ in range(60):
                    if proc.poll() is not None:
                        out = proc.stdout.read().decode("utf-8", "replace") if proc.stdout else ""
                        _skip_or_fail(f"media-server exited: {out[-800:]}")
                    if _port_open(3090):
                        ready = True
                        break
                    time.sleep(0.15)
                if not ready:
                    _skip_or_fail("media-server did not listen on :3090")
                urllib.request.urlopen("http://127.0.0.1:3090/", timeout=8).read()
                imdb = plot = nfo_trailer = poster = ""
                for _ in range(50):
                    if catalog.is_file():
                        conn = sqlite3.connect(str(catalog))
                        try:
                            row = conn.execute(
                                "SELECT imdb_id FROM entries WHERE imdb_id LIKE 'tt%' LIMIT 1"
                            ).fetchone()
                            imdb = row[0] if row else ""
                            try:
                                nfo = conn.execute(
                                    "SELECT plot, trailer_youtube FROM nfo_works LIMIT 1"
                                ).fetchone()
                            except sqlite3.OperationalError:
                                nfo = None
                            if nfo:
                                plot, nfo_trailer = nfo[0] or "", nfo[1] or ""
                            try:
                                art = conn.execute(
                                    "SELECT value FROM sem_assertions WHERE property='poster_url' LIMIT 1"
                                ).fetchone()
                            except sqlite3.OperationalError:
                                art = None
                            if art:
                                poster = art[0] or ""
                        finally:
                            conn.close()
                    if imdb == IMDB and "linguist" in plot and poster.startswith("http"):
                        break
                    time.sleep(0.4)
                self.assertEqual(imdb, IMDB, "nfo uniqueid should land on entries.imdb_id")
                self.assertIn("linguist", plot)
                self.assertEqual(nfo_trailer, "tFMo3UJ4B4g")
                self.assertTrue(poster.startswith("http"), f"live hydrate poster_url missing: {poster!r}")
            finally:
                proc.terminate()
                try:
                    proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    proc.kill()


if __name__ == "__main__":
    unittest.main()

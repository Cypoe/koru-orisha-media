#!/usr/bin/env python3
"""Round-trip the vendor/json fixture via src/json usage (Koru one-shot or Python fallback).

Always asserts the Python-equivalent object. If bin/json-publish exists
(koruc linked, no libyyjson), also asserts that binary's stdout parses to the
same entries object. Missing koruc is not a failure.
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from json_publish import (  # noqa: E402
    FIXTURE,
    PROJECTIONS,
    emit_fixture_text,
    python_dumps,
)

KORU_BIN = ROOT / "bin" / "json-publish"


class JsonPublishTests(unittest.TestCase):
    def test_python_roundtrip(self) -> None:
        loaded = json.loads(python_dumps(FIXTURE))
        self.assertEqual(loaded, FIXTURE)
        self.assertEqual(loaded["entries"][0]["id"], "m_fixture")
        self.assertEqual(loaded["entries"][0]["title"], "demo")

    def test_projections_python_roundtrip(self) -> None:
        loaded = json.loads(python_dumps(PROJECTIONS))
        self.assertEqual(loaded, PROJECTIONS)
        self.assertEqual(loaded["projections"][0]["construction"], "orisha.item")

    def test_wrapper_writes_same_object(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "fixture.json"
            subprocess.check_call(
                [
                    sys.executable,
                    str(ROOT / "scripts" / "json_publish.py"),
                    "--python-only",
                    "--out",
                    str(out),
                ]
            )
            self.assertEqual(json.loads(out.read_text(encoding="utf-8")), FIXTURE)

    def test_src_json_or_python_fallback(self) -> None:
        text, engine = emit_fixture_text(prefer_koru=True)
        loaded = json.loads(text)
        self.assertEqual(loaded, FIXTURE)
        if KORU_BIN.is_file():
            self.assertEqual(engine, "src/json")
            raw = subprocess.check_output([str(KORU_BIN)], text=True)
            self.assertEqual(json.loads(raw), FIXTURE)
        else:
            self.assertEqual(engine, "python")
            print(
                "skip src/json path: bin/json-publish missing (no koruc)",
                file=sys.stderr,
            )


if __name__ == "__main__":
    unittest.main()

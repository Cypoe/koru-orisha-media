#!/usr/bin/env python3
"""Full parse + emit tests for vendor/json via src/json usage (bin/json-publish).

Requires bin/json-publish (scripts/build-json-publish.sh). Python json is the
oracle: our emit must json.loads to the same value; our parse must reject
invalid JSON and round-trip valid documents (including fixtures).
"""
from __future__ import annotations

import json
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BIN = ROOT / "bin" / "json-publish"


def native_parse(text: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [str(BIN), "parse"],
        input=text,
        capture_output=True,
        text=True,
        timeout=10,
    )


def native_emit(cmd: str = "emit-entries") -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [str(BIN), cmd],
        capture_output=True,
        text=True,
        timeout=10,
    )


@unittest.skipUnless(BIN.is_file(), "bin/json-publish missing — run bash scripts/build-json-publish.sh")
class JsonCodecTests(unittest.TestCase):
    def assertParsesTo(self, src: str, expected) -> None:
        r = native_parse(src)
        self.assertEqual(r.returncode, 0, msg=r.stderr)
        self.assertEqual(json.loads(r.stdout), expected)

    def assertRejects(self, src: str) -> None:
        r = native_parse(src)
        self.assertNotEqual(r.returncode, 0, msg=f"accepted invalid JSON: {src!r} -> {r.stdout!r}")

    def test_emit_entries_fixture(self) -> None:
        r = native_emit("emit-entries")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(
            json.loads(r.stdout),
            {"entries": [{"id": "m_fixture", "kind": "movie", "title": "demo"}]},
        )

    def test_emit_projections_fixture(self) -> None:
        r = native_emit("emit-projections")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(
            json.loads(r.stdout),
            {
                "projections": [
                    {
                        "asset_id": "m_fixture",
                        "construction": "orisha.item",
                        "display_title": "Demo",
                    }
                ]
            },
        )

    def test_literals(self) -> None:
        self.assertParsesTo("null", None)
        self.assertParsesTo("true", True)
        self.assertParsesTo("false", False)
        self.assertParsesTo("0", 0)
        self.assertParsesTo("-1", -1)
        self.assertParsesTo("1.5", 1.5)
        self.assertParsesTo("1e2", 100)
        self.assertParsesTo("[]", [])
        self.assertParsesTo("{}", {})

    def test_string_escapes(self) -> None:
        self.assertParsesTo(r'"quote \" here"', 'quote " here')
        self.assertParsesTo(r'"back\\slash"', "back\\slash")
        self.assertParsesTo(r'"line\nfeed"', "line\nfeed")
        self.assertParsesTo(r'"tab\there"', "tab\there")
        self.assertParsesTo(r'"slash\/ok"', "slash/ok")
        self.assertParsesTo(r'"A\u0041"', "AA")
        self.assertParsesTo('"café"', "café")

    def test_emit_escapes_control_and_quote(self) -> None:
        src = json.dumps({"t": 'a"b\\c\n\t'})
        r = native_parse(src)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(json.loads(r.stdout), {"t": 'a"b\\c\n\t'})
        self.assertIn("\\n", r.stdout)
        self.assertIn('\\"', r.stdout)

    def test_nested_object_array(self) -> None:
        doc = {"entries": [{"id": "m_1", "year": 2016, "tags": ["a", "b"], "ok": True, "n": None}]}
        src = json.dumps(doc)
        r = native_parse(src)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(json.loads(r.stdout), doc)

    def test_whitespace(self) -> None:
        self.assertParsesTo("  { \"a\" : 1 }  ", {"a": 1})

    def test_roundtrip_compact(self) -> None:
        src = '{"a":[1,2,{"b":false}]}'
        r = native_parse(src)
        self.assertEqual(r.returncode, 0, r.stderr)
        again = native_parse(r.stdout)
        self.assertEqual(again.returncode, 0, again.stderr)
        self.assertEqual(json.loads(r.stdout), json.loads(again.stdout))

    def test_fixture_manifest(self) -> None:
        raw = (ROOT / "fixtures" / "manifest.json").read_text(encoding="utf-8")
        expected = json.loads(raw)
        r = native_parse(raw)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(json.loads(r.stdout), expected)

    def test_fixture_semantic(self) -> None:
        raw = (ROOT / "fixtures" / "semantic.json").read_text(encoding="utf-8")
        expected = json.loads(raw)
        r = native_parse(raw)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(json.loads(r.stdout), expected)

    def test_kopium_body_escape_parity(self) -> None:
        """Same body as koru-libs/yyjson/tests/kopium_body_parity.kz (emit, not Builder)."""
        body = (
            '{"model":"anthropic/claude-haiku-4.5","stream":true,'
            '"messages":[{"role":"user","content":"she said \\"go\\\\stop\\"\\n\\tnål ✓"}]}'
        )
        r = native_parse(body)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(r.stdout.strip(), body)
        self.assertEqual(json.loads(r.stdout), json.loads(body))

    def test_rejects_invalid(self) -> None:
        for src in (
            "",
            "{",
            "[",
            "]",
            "{]",
            "[}",
            '{"a":}',
            "[1,]",
            '{"a":1,}',
            "01",
            "-01",
            "truee",
            "nul",
            '{"a" 1}',
            '"unterminated',
            "{}\n{}",
            "['a']",
            "{a:1}",
            "[1 2]",
            "1.",
            "1e",
            '"\x01"',
            '"\\u12"',
            '"\\q"',
        ):
            with self.subTest(src=src):
                self.assertRejects(src)


if __name__ == "__main__":
    unittest.main()

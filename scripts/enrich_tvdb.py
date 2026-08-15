#!/usr/bin/env python3
"""Offline TVDB enrichment for the semantic snapshot (stage 5).

Reads TVDB_API_KEY from the environment. Never called from Orisha handlers.

Usage:
  # Apply recorded fixture response (no network) — default for CI:
  python3 scripts/enrich_tvdb.py --fixture fixtures/tvdb/series_121361.json \\
      --in fixtures/semantic.json --out /tmp/semantic.out.json

  # Live enrich (requires TVDB_API_KEY):
  TVDB_API_KEY=... python3 scripts/enrich_tvdb.py --live --series-id 121361 \\
      --entity series.fixture-demo --in data/semantic.json --out data/semantic.json
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from semantic_schema import (  # noqa: E402
    Assertion,
    ProviderIdentity,
    SemanticSnapshot,
)

TVDB_API = "https://api4.thetvdb.com/v4"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _env_value(*names: str) -> str:
    """Read from process env, then gitignored .env. Never logs secrets."""
    for name in names:
        v = os.environ.get(name, "").strip()
        if v:
            return v
    env_path = ROOT / ".env"
    if env_path.is_file():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, _, val = line.partition("=")
            k, val = k.strip(), val.strip().strip('"').strip("'")
            if k in names and val:
                return val
    return ""


def _api_key() -> str:
    return _env_value("TVDB_API_KEY", "TVDB_KEY")


def _pin() -> str:
    return _env_value("TVDB_PIN", "TVDB_SUBSCRIBER_PIN")


def login(api_key: str, pin: str = "") -> str:
    body: dict = {"apikey": api_key}
    if pin:
        body["pin"] = pin
    req = urllib.request.Request(
        f"{TVDB_API}/login",
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json", "Accept": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        payload = json.loads(resp.read().decode())
    token = payload.get("data", {}).get("token")
    if not token:
        raise RuntimeError("TVDB login did not return a token")
    return token


def fetch_series(token: str, series_id: str) -> dict:
    req = urllib.request.Request(
        f"{TVDB_API}/series/{series_id}",
        headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode())


def fetch_remote_id(token: str, remote_id: str) -> dict:
    req = urllib.request.Request(
        f"{TVDB_API}/search/remoteid/{urllib.parse.quote(remote_id, safe='')}",
        headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode())


def series_id_from_remote(payload: dict) -> str:
    data = payload.get("data")
    rows: list = []
    if isinstance(data, list):
        rows = data
    elif isinstance(data, dict):
        for key in ("series", "movies", "episodes"):
            v = data.get(key)
            if isinstance(v, list):
                rows.extend(v)
            elif isinstance(v, dict):
                rows.append(v)
        if not rows:
            rows = [data]
    for row in rows:
        if not isinstance(row, dict):
            continue
        series = row.get("series") if isinstance(row.get("series"), dict) else row
        if not isinstance(series, dict):
            continue
        sid = series.get("id") or series.get("tvdb_id")
        if sid:
            return str(sid)
    return ""


def overlay_from_tvdb(
    payload: dict,
    *,
    imdb_id: str,
    work_key: str = "",
    series_id: str = "",
) -> dict:
    """SQLite hydrate_works row fields from a TVDB series payload. No network."""
    data = payload.get("data") or payload
    name = data.get("name") or data.get("Name") or ""
    overview = data.get("overview") or data.get("Overview") or ""
    year = 0
    yraw = data.get("year") or data.get("firstAired") or data.get("first_air_time")
    if isinstance(yraw, str) and len(yraw) >= 4 and yraw[:4].isdigit():
        year = int(yraw[:4])
    elif isinstance(yraw, int):
        year = yraw
    image = data.get("image") or data.get("imageUrl") or ""
    if isinstance(image, str) and image.startswith("/"):
        image = f"https://artworks.thetvdb.com{image}"
    elif not isinstance(image, str):
        image = ""
    names: list[str] = []
    chars = data.get("characters") or data.get("actors") or []
    if isinstance(chars, list):
        for c in chars:
            if not isinstance(c, dict):
                continue
            n = c.get("personName") or c.get("name") or c.get("Name")
            if isinstance(n, str) and n.strip() and n.strip() not in names:
                names.append(n.strip())
            if len(names) >= 12:
                break
    sid = str(data.get("id") or series_id)
    return {
        "imdb_id": imdb_id,
        "work_key": work_key,
        "source": "tvdb",
        "tmdb_id": "",
        "tvdb_id": sid,
        "title": name if isinstance(name, str) else "",
        "plot": overview if isinstance(overview, str) else "",
        "year": year,
        "poster_url": image,
        "actors": "|".join(names),
    }


def apply_series_payload(
    snap: SemanticSnapshot,
    *,
    entity_id: str,
    series_id: str,
    payload: dict,
) -> SemanticSnapshot:
    data = payload.get("data") or payload
    name = data.get("name") or data.get("Name")
    year = None
    yraw = data.get("year") or data.get("firstAired") or data.get("first_air_time")
    if isinstance(yraw, str) and len(yraw) >= 4 and yraw[:4].isdigit():
        year = int(yraw[:4])
    elif isinstance(yraw, int):
        year = yraw

    ent = next((e for e in snap.entities if e.id == entity_id), None)
    if ent is None:
        raise SystemExit(f"entity not found: {entity_id}")

    # Refresh / insert TVDB provider identity
    others = [p for p in ent.provider_ids if not (p.provider == "tvdb" and p.namespace == "series")]
    slug = data.get("slug")
    url = f"https://thetvdb.com/series/{slug}" if slug else f"https://thetvdb.com/?tab=series&id={series_id}"
    others.append(
        ProviderIdentity(
            provider="tvdb",
            namespace="series",
            value=str(series_id),
            url=url,
            retrieved_at=_now(),
            confidence=0.95,
            source="provider",
        )
    )
    ent.provider_ids = others

    if name:
        ent.title = name
        ent.assertions = [
            a for a in ent.assertions if not (a.property == "name" and a.source.get("provider") == "tvdb")
        ]
        ent.assertions.append(
            Assertion(
                entity=entity_id,
                property="name",
                value=name,
                source={
                    "kind": "provider",
                    "provider": "tvdb",
                    "namespace": "series",
                    "value": str(series_id),
                },
                retrieved_at=_now(),
                confidence=0.95,
                status="accepted",
            )
        )
    if year:
        ent.year = year
    return snap


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--in", dest="infile", type=Path, required=True)
    ap.add_argument("--out", dest="outfile", type=Path, required=True)
    ap.add_argument("--entity", default="series.fixture-demo")
    ap.add_argument("--series-id", default="121361")
    ap.add_argument("--fixture", type=Path, help="Recorded TVDB JSON (no network)")
    ap.add_argument("--live", action="store_true", help="Call TVDB API (needs TVDB_API_KEY)")
    args = ap.parse_args()

    snap = SemanticSnapshot.from_dict(json.loads(args.infile.read_text(encoding="utf-8")))

    if args.live:
        key = _api_key()
        if not key:
            print("TVDB_API_KEY (or TVDB_KEY) is required for --live — set env or .env", file=sys.stderr)
            return 2
        try:
            token = login(key, _pin())
            payload = fetch_series(token, args.series_id)
        except urllib.error.HTTPError as e:
            detail = ""
            try:
                detail = e.read().decode()[:300]
            except Exception:
                pass
            print(f"TVDB HTTP error: {e}", file=sys.stderr)
            if detail:
                print(detail, file=sys.stderr)
            print(
                "Hint: v4 keys come from https://www.thetvdb.com/dashboard/account/apikey "
                "(legacy v3 keys without dashes usually 401). Subscriber keys may need TVDB_PIN.",
                file=sys.stderr,
            )
            return 1
        except Exception as e:
            print(f"TVDB error: {e}", file=sys.stderr)
            return 1
    else:
        fix = args.fixture or (ROOT / "fixtures" / "tvdb" / "series_121361.json")
        if not fix.is_file():
            print(f"fixture missing: {fix}", file=sys.stderr)
            return 2
        payload = json.loads(fix.read_text(encoding="utf-8"))

    snap = apply_series_payload(
        snap, entity_id=args.entity, series_id=args.series_id, payload=payload
    )
    args.outfile.parent.mkdir(parents=True, exist_ok=True)
    args.outfile.write_text(json.dumps(snap.to_dict(), indent=2) + "\n", encoding="utf-8")
    print(f"wrote {args.outfile}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

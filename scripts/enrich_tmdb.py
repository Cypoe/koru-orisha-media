#!/usr/bin/env python3
"""Offline TMDB enrichment for the semantic snapshot (stage 5).

Never called from Orisha handlers. Auth: **either** `TMDB_API_TOKEN` (Bearer /
API Read Access Token) **or** `TMDB_API_KEY` (v3 query param). You do not need
both — token is preferred because it works on v3 and v4.

IMDb is not a public metadata API. Jellyseerr/Radarr/Jellyfin get IMDb IDs from
TMDB `external_ids.imdb_id` (and similar crosswalks), not from IMDb itself.

Usage:
  # CI / no key — recorded payload:
  python3 scripts/enrich_tmdb.py --fixture fixtures/tmdb/movie_329865.json \\
      --in fixtures/semantic.json --out /tmp/semantic.out.json

  # Live (token or key from env / .env):
  python3 scripts/enrich_tmdb.py --live --kind movie --tmdb-id 329865 \\
      --entity work.movie.arrival-2016 --in data/semantic.json --out data/semantic.json
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

TMDB_API = "https://api.themoviedb.org/3"


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


def _token() -> str:
    return _env_value("TMDB_API_TOKEN", "TMDB_READ_ACCESS_TOKEN")


def _api_key() -> str:
    return _env_value("TMDB_API_KEY")


def tmdb_get(path: str, *, token: str = "", api_key: str = "") -> dict:
    url = f"{TMDB_API}{path}"
    headers = {"Accept": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    elif api_key:
        sep = "&" if "?" in url else "?"
        url = f"{url}{sep}{urllib.parse.urlencode({'api_key': api_key})}"
    else:
        raise RuntimeError("TMDB_API_TOKEN or TMDB_API_KEY required")
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode())


def fetch_movie(tmdb_id: str, *, token: str = "", api_key: str = "") -> dict:
    return tmdb_get(
        f"/movie/{urllib.parse.quote(tmdb_id)}?append_to_response=external_ids",
        token=token,
        api_key=api_key,
    )


def fetch_tv(tmdb_id: str, *, token: str = "", api_key: str = "") -> dict:
    return tmdb_get(
        f"/tv/{urllib.parse.quote(tmdb_id)}?append_to_response=external_ids",
        token=token,
        api_key=api_key,
    )


def _year_from(payload: dict) -> int | None:
    for key in ("release_date", "first_air_date"):
        raw = payload.get(key)
        if isinstance(raw, str) and len(raw) >= 4 and raw[:4].isdigit():
            return int(raw[:4])
    return None


def _imdb_id(payload: dict) -> str | None:
    ext = payload.get("external_ids") or {}
    imdb = payload.get("imdb_id") or ext.get("imdb_id")
    if isinstance(imdb, str) and imdb.startswith("tt"):
        return imdb
    return None


def apply_tmdb_payload(
    snap: SemanticSnapshot,
    *,
    entity_id: str,
    tmdb_id: str,
    kind: str,
    payload: dict,
) -> SemanticSnapshot:
    ent = next((e for e in snap.entities if e.id == entity_id), None)
    if ent is None:
        raise SystemExit(f"entity not found: {entity_id}")

    name = payload.get("title") or payload.get("name")
    year = _year_from(payload)
    overview = payload.get("overview")
    namespace = "movie" if kind == "movie" else "tv"
    tmdb_url = f"https://www.themoviedb.org/{namespace}/{tmdb_id}"

    others = [
        p
        for p in ent.provider_ids
        if not (p.provider == "tmdb" and p.namespace == namespace)
    ]
    others.append(
        ProviderIdentity(
            provider="tmdb",
            namespace=namespace,
            value=str(tmdb_id),
            url=tmdb_url,
            retrieved_at=_now(),
            confidence=0.95,
            source="provider",
        )
    )
    imdb = _imdb_id(payload)
    if imdb:
        others = [p for p in others if not (p.provider == "imdb" and p.namespace == "title")]
        others.append(
            ProviderIdentity(
                provider="imdb",
                namespace="title",
                value=imdb,
                url=f"https://www.imdb.com/title/{imdb}/",
                retrieved_at=_now(),
                confidence=0.9,
                source="provider",
            )
        )
    ent.provider_ids = others

    if name:
        ent.title = name
        ent.assertions = [
            a
            for a in ent.assertions
            if not (a.property == "name" and a.source.get("provider") == "tmdb")
        ]
        ent.assertions.append(
            Assertion(
                entity=entity_id,
                property="name",
                value=name,
                source={
                    "kind": "provider",
                    "provider": "tmdb",
                    "namespace": namespace,
                    "value": str(tmdb_id),
                },
                retrieved_at=_now(),
                confidence=0.95,
                status="accepted",
            )
        )
    if year:
        ent.year = year
    if overview:
        ent.description = overview
        ent.assertions = [
            a
            for a in ent.assertions
            if not (a.property == "description" and a.source.get("provider") == "tmdb")
        ]
        ent.assertions.append(
            Assertion(
                entity=entity_id,
                property="description",
                value=overview,
                source={
                    "kind": "provider",
                    "provider": "tmdb",
                    "namespace": namespace,
                    "value": str(tmdb_id),
                },
                retrieved_at=_now(),
                confidence=0.9,
                status="accepted",
            )
        )
    return snap


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--in", dest="infile", type=Path, required=True)
    ap.add_argument("--out", dest="outfile", type=Path, required=True)
    ap.add_argument("--entity", default="work.movie.arrival-2016")
    ap.add_argument("--kind", choices=("movie", "tv"), default="movie")
    ap.add_argument("--tmdb-id", default="329865", help="TMDB movie/tv numeric id")
    ap.add_argument("--fixture", type=Path, help="Recorded TMDB JSON (no network)")
    ap.add_argument("--live", action="store_true", help="Call TMDB (token or api_key)")
    args = ap.parse_args()

    snap = SemanticSnapshot.from_dict(json.loads(args.infile.read_text(encoding="utf-8")))

    if args.live:
        token, key = _token(), _api_key()
        if not token and not key:
            print(
                "TMDB_API_TOKEN or TMDB_API_KEY is required for --live — set env or .env",
                file=sys.stderr,
            )
            return 2
        try:
            if args.kind == "movie":
                payload = fetch_movie(args.tmdb_id, token=token, api_key=key)
            else:
                payload = fetch_tv(args.tmdb_id, token=token, api_key=key)
        except urllib.error.HTTPError as e:
            detail = ""
            try:
                detail = e.read().decode()[:400]
            except Exception:
                pass
            print(f"TMDB HTTP error: {e}", file=sys.stderr)
            if detail:
                print(detail, file=sys.stderr)
            return 1
        except Exception as e:
            print(f"TMDB error: {e}", file=sys.stderr)
            return 1
    else:
        fix = args.fixture or (ROOT / "fixtures" / "tmdb" / "movie_329865.json")
        if not fix.is_file():
            print(f"fixture missing: {fix}", file=sys.stderr)
            return 2
        payload = json.loads(fix.read_text(encoding="utf-8"))

    snap = apply_tmdb_payload(
        snap,
        entity_id=args.entity,
        tmdb_id=str(payload.get("id") or args.tmdb_id),
        kind=args.kind,
        payload=payload,
    )
    args.outfile.parent.mkdir(parents=True, exist_ok=True)
    args.outfile.write_text(json.dumps(snap.to_dict(), indent=2) + "\n", encoding="utf-8")
    print(f"wrote {args.outfile}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

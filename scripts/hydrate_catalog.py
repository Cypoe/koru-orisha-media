#!/usr/bin/env python3
"""CI / recorded-fixture TMDB/TVDB hydrate into the same graph shape as the binary.

Encodes `sem_*` (entities/assertions/relations) and still writes `hydrate_works`
so older catalogs can migrate once. Never called from request handlers. The
runtime image has no Python; run this in CI or against recorded fixtures.

  # No keys → clean no-op (exit 0):
  python3 scripts/hydrate_catalog.py --catalog data/catalog.sqlite

  # CI / recorded payload:
  python3 scripts/hydrate_catalog.py --catalog /tmp/catalog.sqlite \\
      --fixture fixtures/tmdb/movie_329865.json --imdb tt2543164 --kind movie

Live NAS hydrate is the musl binary (`! hydrate`, keys in settings.conf).
"""
from __future__ import annotations

import argparse
import os
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from enrich_tmdb import (  # noqa: E402
    _api_key as tmdb_api_key,
    _token as tmdb_token,
    fetch_find,
    fetch_movie,
    fetch_tv,
    overlay_from_tmdb,
    pick_find_kind,
)
from enrich_tvdb import (  # noqa: E402
    _api_key as tvdb_api_key,
    _pin as tvdb_pin,
    fetch_remote_id,
    fetch_series,
    login as tvdb_login,
    overlay_from_tvdb,
    series_id_from_remote,
)

HYDRATE_SCHEMA = """
CREATE TABLE IF NOT EXISTS hydrate_works (
  imdb_id TEXT PRIMARY KEY,
  work_key TEXT NOT NULL DEFAULT '',
  source TEXT NOT NULL DEFAULT '',
  tmdb_id TEXT NOT NULL DEFAULT '',
  tvdb_id TEXT NOT NULL DEFAULT '',
  title TEXT NOT NULL DEFAULT '',
  plot TEXT NOT NULL DEFAULT '',
  year INTEGER NOT NULL DEFAULT 0,
  poster_url TEXT NOT NULL DEFAULT '',
  actors TEXT NOT NULL DEFAULT '',
  retrieved_at TEXT NOT NULL DEFAULT ''
);
CREATE INDEX IF NOT EXISTS idx_hydrate_works_key ON hydrate_works(work_key);
"""

SEM_SCHEMA = """
CREATE TABLE IF NOT EXISTS sem_entities (
  id TEXT PRIMARY KEY,
  type TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS sem_assertions (
  entity TEXT NOT NULL,
  property TEXT NOT NULL,
  value TEXT NOT NULL DEFAULT '',
  source_json TEXT NOT NULL DEFAULT '',
  status TEXT NOT NULL DEFAULT 'accepted',
  retrieved_at TEXT NOT NULL DEFAULT '',
  PRIMARY KEY (entity, property, source_json)
);
CREATE TABLE IF NOT EXISTS sem_provider_ids (
  entity TEXT NOT NULL,
  provider TEXT NOT NULL,
  namespace TEXT NOT NULL DEFAULT '',
  value TEXT NOT NULL,
  url TEXT NOT NULL DEFAULT '',
  PRIMARY KEY (entity, provider, namespace, value)
);
CREATE TABLE IF NOT EXISTS sem_relations (
  subject TEXT NOT NULL,
  kind TEXT NOT NULL,
  object TEXT NOT NULL,
  ordinal INTEGER NOT NULL DEFAULT 0,
  source TEXT NOT NULL DEFAULT '',
  PRIMARY KEY (subject, kind, object)
);
CREATE TABLE IF NOT EXISTS sem_asset_links (
  asset_id TEXT NOT NULL,
  entity_id TEXT NOT NULL,
  role TEXT NOT NULL DEFAULT 'main',
  PRIMARY KEY (asset_id, entity_id, role)
);
"""

UPSERT_SQL = """
INSERT INTO hydrate_works(
  imdb_id, work_key, source, tmdb_id, tvdb_id, title, plot, year, poster_url, actors, retrieved_at
) VALUES (?,?,?,?,?,?,?,?,?,?,?)
ON CONFLICT(imdb_id) DO UPDATE SET
  work_key=CASE WHEN excluded.work_key!='' THEN excluded.work_key ELSE hydrate_works.work_key END,
  source=excluded.source,
  tmdb_id=CASE WHEN excluded.tmdb_id!='' THEN excluded.tmdb_id ELSE hydrate_works.tmdb_id END,
  tvdb_id=CASE WHEN excluded.tvdb_id!='' THEN excluded.tvdb_id ELSE hydrate_works.tvdb_id END,
  title=CASE WHEN excluded.title!='' THEN excluded.title ELSE hydrate_works.title END,
  plot=CASE WHEN excluded.plot!='' THEN excluded.plot ELSE hydrate_works.plot END,
  year=CASE WHEN excluded.year!=0 THEN excluded.year ELSE hydrate_works.year END,
  poster_url=CASE WHEN excluded.poster_url!='' THEN excluded.poster_url ELSE hydrate_works.poster_url END,
  actors=CASE WHEN excluded.actors!='' THEN excluded.actors ELSE hydrate_works.actors END,
  retrieved_at=excluded.retrieved_at
"""


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def kind_hint(work_key: str, sql_kind: str) -> str:
    if work_key.startswith("shows/"):
        return "tv"
    if work_key.startswith("movies/"):
        return "movie"
    if sql_kind in ("tv", "movie"):
        return sql_kind
    return "movie"


def merge_overlay(base: dict, extra: dict) -> dict:
    out = dict(base)
    for key, val in extra.items():
        if key == "imdb_id":
            if val and not out.get("imdb_id"):
                out[key] = val
            continue
        if key == "year":
            if not out.get("year") and val:
                out[key] = val
            continue
        if key == "source":
            cur = out.get("source") or ""
            if cur and val and val not in cur.split("+"):
                out[key] = f"{cur}+{val}"
            elif val:
                out[key] = val
            continue
        cur = out.get(key)
        if (cur is None or cur == "") and val:
            out[key] = val
    return out


def upsert_overlay(conn: sqlite3.Connection, row: dict) -> None:
    imdb = row.get("imdb_id") or ""
    if not isinstance(imdb, str) or not imdb.startswith("tt"):
        return
    conn.execute(
        UPSERT_SQL,
        (
            imdb,
            row.get("work_key") or "",
            row.get("source") or "",
            str(row.get("tmdb_id") or ""),
            str(row.get("tvdb_id") or ""),
            row.get("title") or "",
            row.get("plot") or "",
            int(row.get("year") or 0),
            row.get("poster_url") or "",
            row.get("actors") or "",
            row.get("retrieved_at") or _now(),
        ),
    )
    upsert_graph(conn, row)


def slug_from_work(work: str) -> str:
    slug: list[str] = []
    for ch in (work.rsplit("/", 1)[-1] if work else ""):
        lower = ch.lower()
        if ("a" <= lower <= "z") or ("0" <= lower <= "9"):
            slug.append(lower)
        elif slug and slug[-1] != "-":
            slug.append("-")
    while slug and slug[-1] == "-":
        slug.pop()
    return "".join(slug)


def upsert_graph(conn: sqlite3.Connection, row: dict) -> None:
    imdb = row.get("imdb_id") or ""
    work = row.get("work_key") or ""
    source = row.get("source") or "tmdb"
    is_tv = work.startswith("shows/") or (row.get("kind") == "tv")
    slug = slug_from_work(work) or imdb
    if not slug:
        return
    ent_id = f"series.{slug}" if is_tv else f"work.movie.{slug}"
    typ = "TVSeries" if is_tv else "Movie"
    conn.execute(
        "INSERT INTO sem_entities(id, type) VALUES(?,?) ON CONFLICT(id) DO UPDATE SET type=excluded.type",
        (ent_id, typ),
    )
    def assertion(prop: str, value: str) -> None:
        if not value:
            return
        conn.execute(
            """INSERT INTO sem_assertions(entity, property, value, source_json, status)
               VALUES(?,?,?,?, 'accepted')
               ON CONFLICT(entity, property, source_json) DO UPDATE SET value=excluded.value""",
            (ent_id, prop, value, source),
        )
    assertion("name", row.get("title") or "")
    assertion("description", row.get("plot") or "")
    year = int(row.get("year") or 0)
    if year > 0:
        assertion("datePublished", str(year))
    assertion("poster_url", row.get("poster_url") or "")
    tmdb_id = str(row.get("tmdb_id") or "")
    tvdb_id = str(row.get("tvdb_id") or "")
    if imdb:
        conn.execute(
            """INSERT INTO sem_provider_ids(entity, provider, namespace, value, url) VALUES(?,?,?,?,?)
               ON CONFLICT(entity, provider, namespace, value) DO UPDATE SET url=excluded.url""",
            (ent_id, "imdb", "title", imdb, f"https://www.imdb.com/title/{imdb}/"),
        )
        conn.execute(
            """INSERT INTO sem_relations(subject, kind, object, ordinal, source) VALUES(?,?,?,?,?)
               ON CONFLICT(subject, kind, object) DO UPDATE SET ordinal=excluded.ordinal""",
            (ent_id, "same_as", imdb, 0, source),
        )
    if tmdb_id:
        path = "tv" if is_tv else "movie"
        conn.execute(
            """INSERT INTO sem_provider_ids(entity, provider, namespace, value, url) VALUES(?,?,?,?,?)
               ON CONFLICT(entity, provider, namespace, value) DO UPDATE SET url=excluded.url""",
            (ent_id, "tmdb", path, tmdb_id, f"https://www.themoviedb.org/{path}/{tmdb_id}"),
        )
        conn.execute(
            """INSERT INTO sem_relations(subject, kind, object, ordinal, source) VALUES(?,?,?,?,?)
               ON CONFLICT(subject, kind, object) DO UPDATE SET ordinal=excluded.ordinal""",
            (ent_id, "same_as", tmdb_id, 0, source),
        )
    if tvdb_id:
        ns = "series" if is_tv else "movie"
        conn.execute(
            """INSERT INTO sem_provider_ids(entity, provider, namespace, value, url) VALUES(?,?,?,?,?)
               ON CONFLICT(entity, provider, namespace, value) DO UPDATE SET url=excluded.url""",
            (ent_id, "tvdb", ns, tvdb_id, ""),
        )
    asset_id = ""
    try:
        got = conn.execute(
            "SELECT id FROM entries WHERE imdb_id=? ORDER BY id LIMIT 1",
            (imdb,),
        ).fetchone()
        if got:
            asset_id = got[0]
    except sqlite3.OperationalError:
        asset_id = ""
    if asset_id:
        conn.execute(
            """INSERT INTO sem_asset_links(asset_id, entity_id, role) VALUES(?,?,?)
               ON CONFLICT(asset_id, entity_id, role) DO NOTHING""",
            (asset_id, ent_id, "main"),
        )
        conn.execute(
            """INSERT INTO sem_relations(subject, kind, object, ordinal, source) VALUES(?,?,?,?,?)
               ON CONFLICT(subject, kind, object) DO UPDATE SET ordinal=excluded.ordinal""",
            (ent_id, "has_asset", asset_id, 0, source),
        )


def list_imdb_works(conn: sqlite3.Connection) -> list[tuple[str, str, str]]:
    try:
        rows = conn.execute(
            """
            SELECT imdb_id, MIN(work_key) AS work_key, MIN(kind) AS kind
            FROM entries
            WHERE imdb_id LIKE 'tt%'
            GROUP BY imdb_id
            """
        ).fetchall()
    except sqlite3.OperationalError:
        return []
    out: list[tuple[str, str, str]] = []
    for imdb, work_key, kind in rows:
        if isinstance(imdb, str) and imdb.startswith("tt"):
            out.append((imdb, work_key or "", kind or ""))
    return out


def tmdb_keys(*, use_dotenv: bool) -> tuple[str, str]:
    if not use_dotenv:
        return (
            os.environ.get("TMDB_API_TOKEN", os.environ.get("TMDB_READ_ACCESS_TOKEN", "")).strip(),
            os.environ.get("TMDB_API_KEY", "").strip(),
        )
    return tmdb_token(), tmdb_api_key()


def tvdb_key(*, use_dotenv: bool) -> str:
    if not use_dotenv:
        return os.environ.get("TVDB_API_KEY", os.environ.get("TVDB_KEY", "")).strip()
    return tvdb_api_key()


def hydrate_one_tmdb(
    *,
    imdb_id: str,
    work_key: str,
    hint: str,
    token: str,
    api_key: str,
    fixture: dict | None,
    find_payload: dict | None,
) -> dict | None:
    if fixture is not None:
        kind = hint or "movie"
        if fixture.get("name") and not fixture.get("title"):
            kind = "tv"
        return overlay_from_tmdb(fixture, imdb_id=imdb_id, work_key=work_key, kind=kind)
    kind = hint
    tmdb_id = ""
    if find_payload is not None:
        picked = pick_find_kind(find_payload, hint)
        if picked:
            kind, tmdb_id = picked
    else:
        found = fetch_find(imdb_id, token=token, api_key=api_key)
        picked = pick_find_kind(found, hint)
        if picked:
            kind, tmdb_id = picked
    if not tmdb_id:
        return None
    if kind == "tv":
        payload = fetch_tv(tmdb_id, token=token, api_key=api_key)
    else:
        payload = fetch_movie(tmdb_id, token=token, api_key=api_key)
    return overlay_from_tmdb(payload, imdb_id=imdb_id, work_key=work_key, kind=kind or "movie")


def hydrate_one_tvdb(
    *,
    imdb_id: str,
    work_key: str,
    token: str,
    fixture: dict | None,
) -> dict | None:
    if fixture is not None:
        return overlay_from_tvdb(fixture, imdb_id=imdb_id, work_key=work_key)
    remote = fetch_remote_id(token, imdb_id)
    sid = series_id_from_remote(remote)
    if not sid:
        return None
    payload = fetch_series(token, sid)
    return overlay_from_tvdb(payload, imdb_id=imdb_id, work_key=work_key, series_id=sid)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--catalog",
        type=Path,
        default=Path(os.environ.get("KORU_CATALOG", "data/catalog.sqlite")),
        help="SQLite catalog (default KORU_CATALOG or data/catalog.sqlite)",
    )
    ap.add_argument("--offline", action="store_true", help="No-op even if keys exist (exit 0)")
    ap.add_argument("--no-dotenv", action="store_true", help="Do not read gitignored .env")
    ap.add_argument("--fixture", type=Path, help="Recorded TMDB movie/tv JSON (no network)")
    ap.add_argument("--find-fixture", type=Path, help="Recorded TMDB /find JSON")
    ap.add_argument("--tvdb-fixture", type=Path, help="Recorded TVDB series JSON")
    ap.add_argument("--imdb", default="", help="Limit to one tt… id (required with --fixture unless catalog has rows)")
    ap.add_argument("--kind", choices=("movie", "tv"), default="")
    ap.add_argument("--work-key", default="", dest="work_key")
    args = ap.parse_args()

    catalog = args.catalog
    catalog.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(catalog))
    try:
        conn.executescript(HYDRATE_SCHEMA)
        conn.executescript(SEM_SCHEMA)
        conn.commit()

        if args.offline:
            print("hydrate: --offline — skip (no provider HTTP)")
            return 0

        use_dotenv = not args.no_dotenv
        token, key = tmdb_keys(use_dotenv=use_dotenv)
        tvdb = tvdb_key(use_dotenv=use_dotenv)

        tmdb_fixture = None
        find_payload = None
        tvdb_fixture = None
        if args.fixture:
            tmdb_fixture = __import__("json").loads(args.fixture.read_text(encoding="utf-8"))
        if args.find_fixture:
            find_payload = __import__("json").loads(args.find_fixture.read_text(encoding="utf-8"))
        if args.tvdb_fixture:
            tvdb_fixture = __import__("json").loads(args.tvdb_fixture.read_text(encoding="utf-8"))

        has_fixture = tmdb_fixture is not None or tvdb_fixture is not None or find_payload is not None
        if not has_fixture and not token and not key and not tvdb:
            print("hydrate: no TMDB_API_TOKEN / TMDB_API_KEY / TVDB_API_KEY — skip")
            return 0

        works = list_imdb_works(conn)
        if args.imdb:
            wk = args.work_key
            hint = args.kind or ""
            for imdb, work_key, kind in works:
                if imdb == args.imdb:
                    if not wk:
                        wk = work_key
                    if not hint:
                        hint = kind_hint(work_key, kind)
                    break
            if not hint:
                hint = args.kind or "movie"
            works = [(args.imdb, wk, hint)]
        elif not works:
            print("hydrate: no [tt…] ids in entries — skip")
            return 0

        tvdb_token = ""
        if tvdb and tvdb_fixture is None:
            try:
                tvdb_token = tvdb_login(tvdb, tvdb_pin() if use_dotenv else os.environ.get("TVDB_PIN", ""))
            except Exception as e:
                print(f"hydrate: TVDB login skipped ({e})", file=sys.stderr)
                tvdb_token = ""

        n = 0
        for imdb, work_key, kind in works:
            hint = kind_hint(work_key, kind)
            row: dict = {
                "imdb_id": imdb,
                "work_key": work_key,
                "kind": hint,
                "source": "",
                "tmdb_id": "",
                "tvdb_id": "",
                "title": "",
                "plot": "",
                "year": 0,
                "poster_url": "",
                "actors": "",
            }
            try:
                if tmdb_fixture is not None or token or key:
                    got = hydrate_one_tmdb(
                        imdb_id=imdb,
                        work_key=work_key,
                        hint=hint,
                        token=token,
                        api_key=key,
                        fixture=tmdb_fixture,
                        find_payload=find_payload,
                    )
                    if got:
                        row = merge_overlay(row, got)
            except Exception as e:
                print(f"hydrate: TMDB skip {imdb}: {e}", file=sys.stderr)
            try:
                if tvdb_fixture is not None or tvdb_token:
                    got = hydrate_one_tvdb(
                        imdb_id=imdb,
                        work_key=work_key,
                        token=tvdb_token,
                        fixture=tvdb_fixture,
                    )
                    if got:
                        row = merge_overlay(row, got)
            except Exception as e:
                print(f"hydrate: TVDB skip {imdb}: {e}", file=sys.stderr)
            row["retrieved_at"] = _now()
            if row.get("poster_url") or row.get("actors") or row.get("plot") or row.get("tmdb_id") or row.get("tvdb_id"):
                upsert_overlay(conn, row)
                n += 1
                print(f"hydrate: {imdb} source={row.get('source') or '?'} poster={'yes' if row.get('poster_url') else 'no'} actors={row.get('actors', '').count('|') + (1 if row.get('actors') else 0)}")
            else:
                print(f"hydrate: {imdb} — no overlay fields")
        conn.commit()
        print(f"hydrate: wrote {n} graph row(s) -> {catalog}")
        return 0
    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())

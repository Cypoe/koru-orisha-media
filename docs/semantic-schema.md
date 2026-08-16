# Semantic Media Schema

## Purpose

The media manifest describes files. It must not become the entire meaning of the media library.

A file path, container, codec, and byte size are physical facts. A movie, television series, episode, album, artist, recording, release, person, artwork item, subtitle, or external catalogue identity is semantic information. Keep those layers separate.

This document defines the direction for a Plex/ISAR-like semantic layer on top of the direct-play media core. The goal is not to copy one provider's database schema. The goal is to represent stable local entities, attach external identities and evidence, and project those entities into different vocabularies when needed.

The direct-play server must continue to work when no external metadata provider is configured.

## Core rule

Use a canonical local graph as the semantic authority:

```text
physical file
  -> local media asset
  -> local work / release / recording / series / episode entity
  -> provider identity assertions
  -> optional normalized metadata
  -> rendered representation
```

External providers are adapters and evidence sources. They are not the primary key of the local library.

A provider may disagree, disappear, change its API, or impose usage restrictions. The local entity should remain addressable and playable even when enrichment is unavailable.

## Three identity layers

### Physical identity

A physical asset identifies bytes or a filesystem object. It includes:

- configured root;
- normalized relative path;
- file size;
- modification time;
- content hash when explicitly requested;
- container and stream facts;
- artwork and sidecar references.

Physical identity answers: "Which bytes are these?"

### Local semantic identity

`work.movie.*` is **not** a URL. These three strings name different layers. Only the physical asset id is an HTTP key:

| id | layer | used at |
|----|-------|---------|
| `m_6d5d84` | physical asset | `/item/{id}`, `/play/{id}`, `/media/{id}` |
| `work.movie.arrival-2016` | local work (`Entity.id`: type `Movie`, slug `arrival-2016`) | semantic graph only |
| `tmdb:movie:329865` / `imdb:title:tt2543164` | provider identities | assertions / `sameAs`, never the local primary key |

`work.movie.arrival-2016` answers “what thing does the user mean?” It is **not** `/item/work.movie.arrival-2016`. The `work.{kind}.{slug}` scheme is the combinatorial type registry (new kinds are new registry rows, not new URL prefixes). Do not put `work.movie` in routes.

A local semantic entity is an application-owned stable identifier. Examples include:

- `work.movie.arrival-2016`;
- `series.game-of-thrones`;
- `episode.game-of-thrones.s01e01`;
- `music.album.kind-of-blue`;
- `music.recording.so-what`;
- `person.miles-davis`.

The exact identifier format is implementation detail (`work.movie.*` above). It must be opaque at the HTTP boundary and stable across metadata refreshes and provider outages.

Semantic identity answers: "What thing does the user mean?"

### Provider identity

A provider identity links a local entity to an external catalogue:

```json
{
  "provider": "musicbrainz",
  "namespace": "release-group",
  "value": "...",
  "url": "https://musicbrainz.org/release-group/...",
  "retrieved_at": "2026-08-12T00:00:00Z",
  "confidence": 0.98,
  "source": "user"
}
```

Provider identity answers: "Which external record supports or describes this local entity?"

Never use an IMDb, TVDB, TMDB, MusicBrainz, or other provider ID as the local primary key.

## Entity vocabulary

Begin with a small vocabulary and add types only when a real library view requires them.

### Creative works

A work is the abstract thing created or published:

- `Movie`;
- `TVSeries`;
- `TVSeason`;
- `TVEpisode`;
- `MusicAlbum`;
- `MusicRecording`;
- `MusicPlaylist`;
- `MusicComposition`.

A work can have titles, descriptions, dates, genres, people, artwork, relationships, and external identities.

### Releases and manifestations

A release is a concrete edition or publication of a work:

- movie cut or edition;
- television release or episode file;
- music release group;
- album release;
- digital or physical medium;
- version with a particular track list.

This distinction matters for music especially. An album concept, a particular release, and an audio file are related but not interchangeable.

### Local assets

An asset is a local file or byte resource. It may represent a full work, one episode, one recording, a subtitle file, an artwork file, or another related resource.

A local asset carries physical facts and references one or more semantic entities. It may also have a role such as `main`, `bonus`, `trailer`, `subtitle`, `cover`, or `fanart`.

## Closed system, extendable set

The core graph is identity and provenance only. Representations (HTML titles, JSON-LD, catalogue URLs) are not fields on `Entity`.

The vocabulary is **closed in shape** and **open in membership**. A valid entity is the product:

```text
(type ∈ EntityType registry)
  × (assertions whose property ∈ that type’s admitted set)
  × (optional namespaced provider_ids)
```

New media kinds are new registry rows, not new snapshot keys or `Entity` dataclass fields. Unknown types in a snapshot are **kept** in the core graph and **skipped** by constructions that do not list them. Do not drop them. `TVSeason` / `TVEpisode` are registered; `part_of` / `next` relations encode the episode graph.

### EntityType registry

Each row has an id, the assertion properties it admits, and the constructions that may project it. Default rows:

| id | admitted properties | constructions |
|---|---|---|
| `Movie` | `name`, `description`, `datePublished` | host register ∩ `orisha.item`, `orisha.links`, `schema.org.jsonld`, `orisha.hero`, `orisha.next` |
| `MusicRecording` | `name`, `description`, `datePublished` | same intersection |
| `TVSeries` | `name`, `description`, `datePublished` | same intersection (`series.fixture-demo` has no assets, so it is still not projected) |
| `TVSeason` | `name`, `description`, `datePublished` | same |
| `TVEpisode` | `name`, `description`, `datePublished` | same |
| `MusicAlbum` | `name`, `description`, `datePublished` | same |

Register further types later without changing `Entity`. Constructions listed on a type are intersected with the host capability register (`browse`, `filter`, `play.video`, `play.audio`, `play.external`, `read.ebook`, `view.image`).

### Assertion.property registry

Allowed properties for this slice: `name`, `description`. Add rows later. Do not add ad-hoc fields on `Entity` for catalogue text.

### Named constructions

Stage 7 writes a top-level `projections[]` array of **named construction rows**, each `{ "construction": "...", "asset_id": "...", ...fields }`. Unlinked assets (demo `m_ca931e`) get no rows. Types not in a construction’s target set get no row for that construction.

| construction | consumer | fields |
|---|---|---|
| `orisha.item` | item/play HTML | `display_title`, `display_description` |
| `orisha.links` | Link header + HTML chips | `tmdb_url`, `imdb_url` (omit empty; no row if both empty) |
| `schema.org.jsonld` | `?format=jsonld` / Accept json | compact JSON-LD string |

Orisha scrapes `projections[]` and merges rows by opaque `asset_id` into one join for those three constructions. Missing `projections`, missing construction keys, or missing rows for an asset = physical-only for that affordance. Handlers do not read `display_*` / `jsonld` off `Entity`, and they do not fall back to `Entity.title` as a catalogue name.

Earlier snapshots stored `display_title`, `display_description`, and `jsonld` on `Entity`, then as a single mixed `projections[]` blob. **The leak is fixed:** those keys are ignored on `Entity` load; mixed blobs without `construction` are skipped.

Python: registries and `project_all` live in [`scripts/semantic_schema.py`](../scripts/semantic_schema.py). [`scripts/project_semantic.py`](../scripts/project_semantic.py) runs every construction.

## Schema.org projection

Schema.org is a useful public vocabulary and JSON-LD projection target. It is not a complete internal database model.

Relevant types include:

- `Movie` for films;
- `TVSeries`, `TVSeason`, and `TVEpisode` for television;
- `MusicAlbum`, `MusicRelease`, and `MusicRecording` for music;
- `MusicGroup` and `Person` for participants;
- `ImageObject` for artwork;
- `VideoObject` and `AudioObject` for playable assets;
- `MusicPlaylist` for local playlists.

Relevant relationships include `name`, `alternateName`, `description`, `dateCreated`, `datePublished`, `duration`, `image`, `actor`, `director`, `creator`, `byArtist`, `inAlbum`, `track`, `partOfSeries`, `episodeNumber`, and `contentUrl`.

Generate JSON-LD as a representation concern. Do not force every internal field into Schema.org, and do not assume that a Schema.org property is a database constraint. A local entity can retain richer provenance and provider-specific values while exposing a conservative public projection.

Example projection:

```json
{
  "@context": "https://schema.org",
  "@type": "Movie",
  "@id": "https://media.example/item/m_7f3af1",
  "name": "Arrival",
  "datePublished": "2016",
  "image": "https://media.example/art/m_7f3af1",
  "contentUrl": "https://media.example/media/m_7f3af1"
}
```

The public JSON-LD URL should use the local canonical URL. Provider URLs belong in `sameAs`, `identifier`, or a more specific internal/provider representation when that is semantically appropriate.

## Provider adapters

Provider adapters should normalize into the local graph rather than leaking provider response shapes into request handlers.

### MusicBrainz

MusicBrainz is the preferred conceptual source for music identity and relationships when its data model fits the requirement. Keep release groups, releases, recordings, artists, labels, works, and relationships distinct where the source distinguishes them.

Useful identity namespaces include MusicBrainz IDs for artists, release groups, releases, recordings, works, and labels. Store the namespace explicitly because the value alone has no meaning.

Cover Art Archive references may be attached as artwork provenance, but artwork should be cached or imported through an explicit offline operation and must respect source terms.

### IMDb

IMDb identifiers are useful for linking movies, series, episodes, and people. Treat an IMDb ID as an external assertion, not as a guarantee that the external record is complete or permanently available.

There is no public IMDb metadata API for this project. Jellyseerr, Radarr, and Jellyfin typically **do not call IMDb**. They call **TMDB** (or a Servarr proxy) and copy `external_ids.imdb_id` onto the local record. We do the same in [`scripts/enrich_tmdb.py`](../scripts/enrich_tmdb.py).

Store the type of the linked entity and the source URL where permitted. Do not scrape IMDb pages.

### TVDB

TVDB is useful for television series, seasons, episodes, people, artwork, and alternate ordering schemes. Preserve the provider's entity type and ordering context. Absolute episode numbers, DVD order, aired order, and local file order are not automatically equivalent.

A TVDB link should therefore include the relation and ordering scheme when that information affects matching.

### TMDB (preferred catalogue adapter)

TMDB covers movies **and** TV, stays free for personal API keys, and is the first live adapter. Auth is **one of**:

- `TMDB_API_TOKEN` — API Read Access Token, sent as `Authorization: Bearer …` (works on v3 and v4)
- `TMDB_API_KEY` — v3 `api_key` query parameter

You do not need both. Prefer the token.

```bash
# CI / no key — recorded payload:
python3 scripts/enrich_tmdb.py --in fixtures/semantic.json --out /tmp/semantic.json \
  --fixture fixtures/tmdb/movie_329865.json

# Live (token or key from .env):
python3 scripts/enrich_tmdb.py --live --kind movie --tmdb-id 329865 \
  --entity work.movie.arrival-2016 --in data/semantic.json --out data/semantic.json
```

TVMaze, AniList, Wikidata, Open Library, Discogs, and other providers may be added through the same adapter boundary. A provider must not become a required dependency of the request path.

When multiple sources supply a value, retain provenance and a resolution decision rather than silently overwriting one source with another.

## Assertions and provenance

Normalized values should be backed by assertions:

```json
{
  "entity": "series.game-of-thrones",
  "property": "name",
  "value": "Game of Thrones",
  "source": {
    "kind": "provider",
    "provider": "tvdb",
    "namespace": "series",
    "value": "121361"
  },
  "retrieved_at": "2026-08-12T00:00:00Z",
  "confidence": 0.94,
  "status": "accepted"
}
```

At minimum, distinguish:

- user-supplied facts;
- filename/parser inference;
- embedded file tags;
- provider metadata;
- derived values;
- unresolved or conflicting values.

Do not discard conflicting values merely because one was selected for display. The selected value is a projection decision and should be explainable.

## Identity resolution

Matching local assets to semantic entities is a constrained resolution problem, not a string replacement.

Use evidence in an explicit order, for example:

1. persistent local identity or sidecar;
2. a user-confirmed provider identity;
3. embedded IDs and trusted tags;
4. exact structured filename parsing;
5. title/year/season/episode or album/artist/track candidate matching;
6. fuzzy matching only as a proposal requiring review.

A resolver should be able to return:

- accepted match;
- candidate matches;
- ambiguous result;
- no match;
- rejected match with reason.

Never silently merge two local entities solely because their display names are equal.

## Local schema direction

The eventual schema should be able to express these relations:

```text
Asset -[represents]-> Work
Asset -[is_release_of]-> Release
Asset -[contains]-> Recording
Asset -[has_artwork]-> Artwork
Episode -[part_of]-> Season
Season -[part_of]-> Series
Recording -[in_release]-> Release
Recording -[by_artist]-> Person/Group
Work -[same_as]-> ProviderIdentity
Entity -[has_assertion]-> Assertion
```

A relational implementation may use tables. An ISAR-like implementation may use collections and links. A graph-shaped conceptual model does not require a graph database. Start with data structures that preserve identity, links, provenance, and immutable snapshots without introducing a service dependency.

## Manifest boundary

The physical manifest and semantic metadata may be stored separately:

```text
physical manifest generation
  -> asset IDs, paths, bytes, streams
semantic snapshot
  -> works, releases, people, provider IDs, assertions
projection/index
  -> top-level projections[] of named constructions keyed by opaque asset id
```

The request process may load a joined or precomputed projection for speed. The source layers should remain distinguishable so a changed provider description does not look like changed file bytes.

An asset can remain playable if semantic enrichment fails. A semantic entity can remain visible if one associated file disappears; the representation should expose that state rather than deleting the entity accidentally.

## URLs and external links

Local canonical URLs are authoritative for local navigation:

- `/item/{id}` for an item page (`id` is the physical opaque asset id `m_*`, not `work.movie.*`);
- `/media/{asset-id}` for bytes;
- `/art/{asset-id}` for local artwork;
- `/provider/{provider}/{namespace}/{value}` only if a provider view is intentionally exposed.

External provider links are related links, not local identity. Use HTML links, JSON-LD identifiers, and `Link` relations where appropriate. Never make the browser reconstruct provider URLs from an untyped bare ID.

## Licensing and operational boundaries

Provider adapters must document:

- authentication requirements;
- rate limits;
- caching rules;
- attribution requirements;
- allowed fields;
- image/artwork usage rules;
- whether data may be persisted locally;
- whether data may be redistributed.

Do not bundle provider credentials in the repository. Use a gitignored `.env` (see [`.env.example`](../.env.example)) or the process environment (`TMDB_API_TOKEN` / `TMDB_API_KEY`). Do not make indexing fail merely because an optional provider is unavailable. A provider failure should produce an enrichment diagnostic and leave the physical library usable.

### TVDB adapter (optional)

TVDB v4 now expects a paid/subscriber key for many accounts. Keep [`scripts/enrich_tvdb.py`](../scripts/enrich_tvdb.py) for fixture/CI and anyone who still has a v4 key; prefer TMDB for live enrichment.

```bash
python3 scripts/enrich_tvdb.py --in fixtures/semantic.json --out /tmp/semantic.json \
  --fixture fixtures/tvdb/series_121361.json
```

## SQLite hydrate overlay (Wave 4)

Offline job, not the HTTP request path. [`scripts/hydrate_catalog.py`](../scripts/hydrate_catalog.py) reads distinct `entries.imdb_id` values (`[tt…]` already on disk), calls TMDB `/find` then movie/tv+credits (TVDB optional), and upserts `hydrate_works`. Reindex does **not** wipe this table (nfo overlay is rebuilt from disk; provider overlay is not).

Table `hydrate_works`:

| column | role |
|--------|------|
| `imdb_id` | primary key (`tt…`) |
| `work_key` | catalog work path (informational) |
| `source` | `tmdb`, `tvdb`, or `tmdb+tvdb` |
| `tmdb_id` / `tvdb_id` | provider ids |
| `title` / `plot` / `year` | catalogue text (plot used when nfo plot is empty) |
| `poster_url` | `https://image.tmdb.org/…` or TVDB artwork URL |
| `actors` | pipe-separated names (JSON-LD `actor` / HTML `.cast`) |
| `retrieved_at` | UTC timestamp |

```bash
# No keys → exit 0 skip:
python3 scripts/hydrate_catalog.py --catalog data/catalog.sqlite

# CI:
python3 scripts/hydrate_catalog.py --catalog /tmp/catalog.sqlite \
  --fixture fixtures/tmdb/movie_329865.json --imdb tt2543164 --kind movie
```

`KORU_HYDRATE=1` on `media-server` only logs that overlay tables exist. Hydrate is host-side Python; the scratch image has no shell and no Python. Do not put API keys in compose or the runtime image.

## Integrations (follow-up only)

Not in product this pass: Seerr Requests, Approve/Decline, blocklist-as-Seerr, user accounts, transcoding, or a plugin marketplace. After the work surface is stable, optional follow-ups are **clients** (Plex/Jellyfin-style remote) and **webhooks** (library changed). Document here when those land; do not invent Overseerr.

## Implementation stages

1. Define local `Asset`, `Entity`, `ProviderIdentity`, and `Assertion` types with no network access. **Done** — [`scripts/semantic_schema.py`](../scripts/semantic_schema.py) + [`fixtures/semantic.json`](../fixtures/semantic.json).
2. Add Schema.org/JSON-LD projection for one movie and one music recording. **Done** — `project_jsonld` (Arrival + beep).
3. Add deterministic fixture-based identity resolution. **Done** — `resolve_asset`.
4. Add provider identity storage without provider API calls. **Done** — hand-linked IMDb/TVDB on fixtures.
5. Add one offline adapter at a time, starting with the source whose licensing and data model are clearest. **Done** for SQLite overlay — [`scripts/hydrate_catalog.py`](../scripts/hydrate_catalog.py) writes `hydrate_works` from [`scripts/enrich_tmdb.py`](../scripts/enrich_tmdb.py) (preferred) and [`scripts/enrich_tvdb.py`](../scripts/enrich_tvdb.py) (optional). Semantic-snapshot enrichers remain for `semantic.json`. Handlers only **read** overlay tables.
6. Add provenance-aware conflict resolution. **Done** — `resolve_name_conflict` keeps both name assertions (`accepted` / `superseded`); `join_asset` looks up by opaque asset id.
7. Precompute collection projections for Orisha requests. **Done** — [`scripts/project_semantic.py`](../scripts/project_semantic.py) runs named constructions (`orisha.item`, `orisha.links`, `schema.org.jsonld`) into top-level `projections[]` (not fields on `Entity`). Orisha loads `KORU_SEMANTIC` (default `data/semantic.json`) with the physical manifest. Missing `projections` or missing constructions is physical HTML only. First presentable is the local archive: `/` and `/library` list playable manifest files even when the fetched index is absent.
8. Expose provider links and capability affordances only when data and permission exist. **Done** — item/play HTML + `Link` related/alternate when the join hits; demo/unlinked assets stay physical-only.

## Invariants

- Local identity never depends on provider availability.
- Provider IDs are namespaced and typed.
- Physical asset identity is distinct from semantic work identity.
- Metadata refresh cannot change media bytes.
- Every normalized external value has provenance.
- Ambiguous matches remain ambiguous until resolved.
- A provider outage does not break direct playback or basic browsing.
- Request handlers consume local projections, not remote provider APIs.
- Schema.org is a projection vocabulary, not the complete internal schema.
- `Entity` holds identity and provenance only; named constructions live in `projections[]`. **Fixed** — the representation leak into the graph is closed. The type/property set is extendable via registry rows.

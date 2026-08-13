"""Local semantic graph types (docs/semantic-schema.md stages 1–8).

No network access. Providers are stored as typed identities only.

The vocabulary is a closed *system* (rigid row shape) with an extendable *set*
(new EntityType / Assertion.property rows). Representations are named
constructions, never fields on Entity.
"""
from __future__ import annotations

import json
from collections.abc import Iterable, Mapping
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Literal


MatchStatus = Literal[
    "accepted",
    "candidate",
    "ambiguous",
    "no_match",
    "rejected",
]


# ---------------------------------------------------------------------------
# Construction ids (stable; Orisha scrapes these strings)
# ---------------------------------------------------------------------------

CONSTRUCTION_ORISHA_ITEM = "orisha.item"
CONSTRUCTION_ORISHA_LINKS = "orisha.links"
CONSTRUCTION_SCHEMA_ORG_JSONLD = "schema.org.jsonld"

ALL_CONSTRUCTIONS: tuple[str, ...] = (
    CONSTRUCTION_ORISHA_ITEM,
    CONSTRUCTION_ORISHA_LINKS,
    CONSTRUCTION_SCHEMA_ORG_JSONLD,
)


# ---------------------------------------------------------------------------
# Registries — rigid shape, open membership
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class AssertionPropertySpec:
    """One admitted Assertion.property. Add rows; do not add Entity fields."""

    id: str


@dataclass(frozen=True)
class EntityTypeSpec:
    """One media kind. New kinds = new rows, not new snapshot keys."""

    id: str
    admitted_properties: frozenset[str]
    constructions: frozenset[str]


ASSERTION_PROPERTIES: dict[str, AssertionPropertySpec] = {}
ENTITY_TYPES: dict[str, EntityTypeSpec] = {}


def register_assertion_property(prop_id: str) -> AssertionPropertySpec:
    spec = AssertionPropertySpec(id=prop_id)
    ASSERTION_PROPERTIES[prop_id] = spec
    return spec


def register_entity_type(
    type_id: str,
    *,
    admitted_properties: Iterable[str],
    constructions: Iterable[str] = (),
) -> EntityTypeSpec:
    admitted = frozenset(admitted_properties)
    unknown = admitted - frozenset(ASSERTION_PROPERTIES)
    if unknown:
        raise ValueError(f"properties not in assertion registry: {sorted(unknown)}")
    spec = EntityTypeSpec(
        id=type_id,
        admitted_properties=admitted,
        constructions=frozenset(constructions),
    )
    ENTITY_TYPES[type_id] = spec
    return spec


# Entity.id scheme is combinatorial (work.{kind}.{slug}); it is not an HTTP route key.


def _bootstrap_default_registry() -> None:
    register_assertion_property("name")
    register_assertion_property("description")
    _default_constructions = ALL_CONSTRUCTIONS
    register_entity_type(
        "Movie",
        admitted_properties=("name", "description"),
        constructions=_default_constructions,
    )
    register_entity_type(
        "MusicRecording",
        admitted_properties=("name", "description"),
        constructions=_default_constructions,
    )
    # Stub: kept in the core graph; no construction lists it yet.
    register_entity_type(
        "TVSeries",
        admitted_properties=("name", "description"),
        constructions=(),
    )


_bootstrap_default_registry()


def type_admits_construction(entity_type: str, construction: str) -> bool:
    spec = ENTITY_TYPES.get(entity_type)
    if spec is None:
        return False
    return construction in spec.constructions


def type_admits_property(entity_type: str, property: str) -> bool:
    spec = ENTITY_TYPES.get(entity_type)
    if spec is None:
        return False
    return property in spec.admitted_properties


def validate_entity(entity: Entity) -> list[str]:
    """Flag combinatorial violations. Unknown types are kept, not dropped."""
    issues: list[str] = []
    spec = ENTITY_TYPES.get(entity.type)
    if spec is None:
        issues.append(f"unknown type {entity.type!r}")
        for a in entity.assertions:
            if a.property not in ASSERTION_PROPERTIES:
                issues.append(f"unknown property {a.property!r}")
        return issues
    for a in entity.assertions:
        if a.property not in ASSERTION_PROPERTIES:
            issues.append(f"unknown property {a.property!r} on {entity.type}")
        elif a.property not in spec.admitted_properties:
            issues.append(f"property {a.property!r} not admitted on {entity.type}")
    return issues


@dataclass
class ProviderIdentity:
    provider: str
    namespace: str
    value: str
    url: str | None = None
    retrieved_at: str | None = None
    confidence: float | None = None
    source: str = "user"  # user | provider | inference | embedded


@dataclass
class Assertion:
    entity: str
    property: str
    value: Any
    source: dict[str, Any]
    retrieved_at: str | None = None
    confidence: float | None = None
    status: str = "accepted"


@dataclass
class Entity:
    """Identity + provenance only. Representations live in Projection rows."""

    id: str  # local work id (e.g. work.movie.arrival-2016); not an HTTP /item/{id} key
    type: str  # registry id; unknown types are kept, not projected
    title: str
    year: int | None = None
    description: str | None = None
    provider_ids: list[ProviderIdentity] = field(default_factory=list)
    assertions: list[Assertion] = field(default_factory=list)
    asset_ids: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "type": self.type,
            "title": self.title,
            "year": self.year,
            "description": self.description,
            "provider_ids": [asdict(p) for p in self.provider_ids],
            "assertions": [asdict(a) for a in self.assertions],
            "asset_ids": list(self.asset_ids),
        }


@dataclass
class Asset:
    """Physical asset — mirrors opaque media id from the physical manifest.

    `id` is the HTTP key (`m_*`). `entity_ids` point at local works
    (`work.movie.*`), which are not URL keys.
    """

    id: str
    path: str
    kind: str
    role: str = "main"  # main | subtitle | cover | ...
    entity_ids: list[str] = field(default_factory=list)


@dataclass
class Projection:
    """One named construction output, keyed by opaque asset id.

    Never stored on Entity. Shape is construction-specific; empty optional
    fields are omitted on write.
    """

    construction: str
    asset_id: str
    entity_id: str
    display_title: str = ""
    display_description: str = ""
    jsonld: str = ""
    tmdb_url: str = ""
    imdb_url: str = ""

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "construction": self.construction,
            "asset_id": self.asset_id,
            "entity_id": self.entity_id,
        }
        if self.construction == CONSTRUCTION_ORISHA_ITEM:
            d["display_title"] = self.display_title
            d["display_description"] = self.display_description
        elif self.construction == CONSTRUCTION_ORISHA_LINKS:
            if self.tmdb_url:
                d["tmdb_url"] = self.tmdb_url
            if self.imdb_url:
                d["imdb_url"] = self.imdb_url
        elif self.construction == CONSTRUCTION_SCHEMA_ORG_JSONLD:
            d["jsonld"] = self.jsonld
        else:
            if self.display_title:
                d["display_title"] = self.display_title
            if self.display_description:
                d["display_description"] = self.display_description
            if self.jsonld:
                d["jsonld"] = self.jsonld
            if self.tmdb_url:
                d["tmdb_url"] = self.tmdb_url
            if self.imdb_url:
                d["imdb_url"] = self.imdb_url
        return d


def _projection_from_dict(raw: Mapping[str, Any]) -> Projection | None:
    construction = raw.get("construction")
    asset_id = raw.get("asset_id")
    if not isinstance(construction, str) or not construction:
        return None
    if not isinstance(asset_id, str) or not asset_id:
        return None
    entity_id = raw.get("entity_id")
    return Projection(
        construction=construction,
        asset_id=asset_id,
        entity_id=entity_id if isinstance(entity_id, str) else "",
        display_title=raw.get("display_title", "") or "",
        display_description=raw.get("display_description", "") or "",
        jsonld=raw.get("jsonld", "") or "",
        tmdb_url=raw.get("tmdb_url", "") or "",
        imdb_url=raw.get("imdb_url", "") or "",
    )


@dataclass
class SemanticSnapshot:
    version: int = 1
    assets: list[Asset] = field(default_factory=list)
    entities: list[Entity] = field(default_factory=list)
    projections: list[Projection] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "version": self.version,
            "assets": [asdict(a) for a in self.assets],
            "entities": [e.to_dict() for e in self.entities],
        }
        if self.projections:
            d["projections"] = [p.to_dict() for p in self.projections]
        return d

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SemanticSnapshot:
        assets = [Asset(**a) for a in data.get("assets", [])]
        entities: list[Entity] = []
        for raw in data.get("entities", []):
            pids = [ProviderIdentity(**p) for p in raw.get("provider_ids", [])]
            assertions = [Assertion(**a) for a in raw.get("assertions", [])]
            entities.append(
                Entity(
                    id=raw["id"],
                    type=raw["type"],
                    title=raw["title"],
                    year=raw.get("year"),
                    description=raw.get("description"),
                    provider_ids=pids,
                    assertions=assertions,
                    asset_ids=list(raw.get("asset_ids", [])),
                )
            )
        projections: list[Projection] = []
        for raw in data.get("projections", []):
            if not isinstance(raw, dict):
                continue
            row = _projection_from_dict(raw)
            if row is not None:
                projections.append(row)
        return cls(
            version=int(data.get("version", 1)),
            assets=assets,
            entities=entities,
            projections=projections,
        )


def schema_org_movie(
    entity: Entity,
    base: str = "https://media.local",
    *,
    asset_id: str | None = None,
    name: str | None = None,
) -> dict[str, Any]:
    """Conservative Schema.org / JSON-LD projection for a Movie."""
    aid = asset_id or (entity.asset_ids[0] if entity.asset_ids else entity.id)
    doc: dict[str, Any] = {
        "@context": "https://schema.org",
        "@type": "Movie",
        "@id": f"{base}/item/{aid}",
        "name": name if name is not None else entity.title,
        "contentUrl": f"{base}/media/{aid}",
    }
    if entity.year:
        doc["datePublished"] = str(entity.year)
    same_as = [p.url for p in entity.provider_ids if p.url]
    if same_as:
        doc["sameAs"] = same_as if len(same_as) > 1 else same_as[0]
    identifiers = [
        {"@type": "PropertyValue", "propertyID": f"{p.provider}:{p.namespace}", "value": p.value}
        for p in entity.provider_ids
    ]
    if identifiers:
        doc["identifier"] = identifiers
    doc["image"] = f"{base}/art/{aid}"
    return doc


def schema_org_music_recording(
    entity: Entity,
    base: str = "https://media.local",
    *,
    asset_id: str | None = None,
    name: str | None = None,
) -> dict[str, Any]:
    aid = asset_id or (entity.asset_ids[0] if entity.asset_ids else entity.id)
    return {
        "@context": "https://schema.org",
        "@type": "MusicRecording",
        "@id": f"{base}/item/{aid}",
        "name": name if name is not None else entity.title,
        "contentUrl": f"{base}/media/{aid}",
    }


def project_jsonld(
    entity: Entity,
    base: str = "https://media.local",
    *,
    asset_id: str | None = None,
    name: str | None = None,
) -> dict[str, Any]:
    if entity.type == "Movie":
        return schema_org_movie(entity, base, asset_id=asset_id, name=name)
    if entity.type in ("MusicRecording", "MusicAlbum"):
        return schema_org_music_recording(entity, base, asset_id=asset_id, name=name)
    return {
        "@context": "https://schema.org",
        "@type": "CreativeWork",
        "@id": f"{base}/entity/{entity.id}",
        "name": name if name is not None else entity.title,
    }


@dataclass
class ResolveResult:
    status: MatchStatus
    entity_id: str | None = None
    candidates: list[str] = field(default_factory=list)
    reason: str | None = None


def resolve_asset(
    snapshot: SemanticSnapshot,
    *,
    asset_id: str | None = None,
    path: str | None = None,
    title: str | None = None,
    year: int | None = None,
) -> ResolveResult:
    """Deterministic fixture-oriented resolver (stage 3)."""
    # 1. Persistent local asset id
    if asset_id:
        for a in snapshot.assets:
            if a.id == asset_id and a.entity_ids:
                return ResolveResult(status="accepted", entity_id=a.entity_ids[0])
        for a in snapshot.assets:
            if a.id == asset_id:
                return ResolveResult(status="no_match", reason="asset has no entity link")

    # 2. Exact path
    if path:
        for a in snapshot.assets:
            if a.path == path and a.entity_ids:
                return ResolveResult(status="accepted", entity_id=a.entity_ids[0])

    # 3. Title + year exact
    if title:
        hits: list[str] = []
        for e in snapshot.entities:
            if e.title.casefold() == title.casefold():
                if year is None or e.year is None or e.year == year:
                    hits.append(e.id)
        if len(hits) == 1:
            return ResolveResult(status="accepted", entity_id=hits[0])
        if len(hits) > 1:
            return ResolveResult(status="ambiguous", candidates=hits, reason="multiple title matches")

    return ResolveResult(status="no_match", reason="no evidence")


def entity_by_id(snapshot: SemanticSnapshot, entity_id: str) -> Entity | None:
    for e in snapshot.entities:
        if e.id == entity_id:
            return e
    return None


def load_snapshot(path: Path | None) -> SemanticSnapshot | None:
    """Missing or unreadable snapshot is not an error — physical library still works."""
    if path is None or not path.is_file():
        return None
    try:
        return SemanticSnapshot.from_dict(json.loads(path.read_text(encoding="utf-8")))
    except (OSError, json.JSONDecodeError, TypeError, KeyError):
        return None


def accepted_assertion(entity: Entity, property: str) -> Assertion | None:
    for a in entity.assertions:
        if a.property == property and a.status == "accepted":
            return a
    return None


def display_title(entity: Entity | None, physical_title: str) -> str:
    """Accepted name assertion, else entity title, else physical filename title."""
    if entity is None:
        return physical_title
    acc = accepted_assertion(entity, "name")
    if acc is not None and isinstance(acc.value, str) and acc.value:
        return acc.value
    if entity.title:
        return entity.title
    return physical_title


def display_description(entity: Entity | None) -> str:
    if entity is None:
        return ""
    acc = accepted_assertion(entity, "description")
    if acc is not None and isinstance(acc.value, str):
        return acc.value
    return entity.description or ""


def join_asset(
    snapshot: SemanticSnapshot | None,
    *,
    asset_id: str,
    physical_title: str = "",
) -> dict[str, Any] | None:
    """Join physical asset id → entity. None if snapshot missing or asset unlinked."""
    if snapshot is None:
        return None
    r = resolve_asset(snapshot, asset_id=asset_id)
    if r.status != "accepted" or not r.entity_id:
        return None
    ent = entity_by_id(snapshot, r.entity_id)
    if ent is None:
        return None
    return {
        "entity_id": ent.id,
        "type": ent.type,
        "title": display_title(ent, physical_title),
        "description": display_description(ent),
        "year": ent.year,
        "provider_ids": ent.provider_ids,
        "entity": ent,
    }


def resolve_name_conflict(entity: Entity, *, prefer: str = "user") -> Entity:
    """Keep both name assertions; one accepted, the other superseded. Never delete."""
    names = [a for a in entity.assertions if a.property == "name"]
    if len(names) < 2:
        return entity
    winner: Assertion | None = None
    for a in names:
        kind = (a.source or {}).get("kind") or (a.source or {}).get("provider")
        if prefer == "user" and kind == "user":
            winner = a
            break
        if prefer == "provider" and kind == "provider":
            winner = a
            break
    if winner is None:
        winner = names[0]
    for a in names:
        a.status = "accepted" if a is winner else "superseded"
    if isinstance(winner.value, str) and winner.value:
        entity.title = winner.value
    return entity


def _provider_url(entity: Entity, provider: str) -> str:
    for p in entity.provider_ids:
        if p.provider == provider and p.url:
            return p.url
    return ""


def project_orisha_item(
    entity: Entity,
    *,
    asset_id: str,
    physical_title: str = "",
    base: str = "https://media.local",
) -> Projection | None:
    """item/watch HTML display strings. Does not mutate Entity."""
    del base
    if not type_admits_construction(entity.type, CONSTRUCTION_ORISHA_ITEM):
        return None
    return Projection(
        construction=CONSTRUCTION_ORISHA_ITEM,
        asset_id=asset_id,
        entity_id=entity.id,
        display_title=display_title(entity, physical_title or entity.title),
        display_description=display_description(entity),
    )


def project_orisha_links(
    entity: Entity,
    *,
    asset_id: str,
    physical_title: str = "",
    base: str = "https://media.local",
) -> Projection | None:
    """Link header + HTML chips. Omits empty URLs; no row if both empty."""
    del physical_title, base
    if not type_admits_construction(entity.type, CONSTRUCTION_ORISHA_LINKS):
        return None
    tmdb_url = _provider_url(entity, "tmdb")
    imdb_url = _provider_url(entity, "imdb")
    if not tmdb_url and not imdb_url:
        return None
    return Projection(
        construction=CONSTRUCTION_ORISHA_LINKS,
        asset_id=asset_id,
        entity_id=entity.id,
        tmdb_url=tmdb_url,
        imdb_url=imdb_url,
    )


def project_schema_org_jsonld(
    entity: Entity,
    *,
    asset_id: str,
    physical_title: str = "",
    base: str = "https://media.local",
) -> Projection | None:
    """Compact JSON-LD string for ?format=jsonld / Accept json."""
    if not type_admits_construction(entity.type, CONSTRUCTION_SCHEMA_ORG_JSONLD):
        return None
    title = display_title(entity, physical_title or entity.title)
    doc = project_jsonld(entity, base, asset_id=asset_id, name=title)
    return Projection(
        construction=CONSTRUCTION_SCHEMA_ORG_JSONLD,
        asset_id=asset_id,
        entity_id=entity.id,
        jsonld=json.dumps(doc, ensure_ascii=False, separators=(",", ":")),
    )


_CONSTRUCTION_FNS = (
    project_orisha_item,
    project_orisha_links,
    project_schema_org_jsonld,
)


def project_all(
    snapshot: SemanticSnapshot,
    *,
    physical_titles: dict[str, str] | None = None,
    base: str = "https://media.local",
) -> list[Projection]:
    """Run every named construction. Unlinked assets get no rows. Does not mutate Entity."""
    titles = physical_titles or {}
    out: list[Projection] = []
    for asset in snapshot.assets:
        if not asset.entity_ids:
            continue
        ent = entity_by_id(snapshot, asset.entity_ids[0])
        if ent is None:
            continue
        kwargs = {
            "asset_id": asset.id,
            "physical_title": titles.get(asset.id, ""),
            "base": base,
        }
        for fn in _CONSTRUCTION_FNS:
            row = fn(ent, **kwargs)
            if row is not None:
                out.append(row)
    return out

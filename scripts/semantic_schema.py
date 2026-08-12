"""Local semantic graph types (docs/semantic-schema.md stages 1–4).

No network access. Providers are stored as typed identities only.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Literal


MatchStatus = Literal[
    "accepted",
    "candidate",
    "ambiguous",
    "no_match",
    "rejected",
]


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
    id: str
    type: str  # Movie | TVSeries | MusicRecording | ...
    title: str
    year: int | None = None
    description: str | None = None
    provider_ids: list[ProviderIdentity] = field(default_factory=list)
    assertions: list[Assertion] = field(default_factory=list)
    asset_ids: list[str] = field(default_factory=list)


@dataclass
class Asset:
    """Physical asset — mirrors opaque media id from the physical manifest."""

    id: str
    path: str
    kind: str
    role: str = "main"  # main | subtitle | cover | ...
    entity_ids: list[str] = field(default_factory=list)


@dataclass
class SemanticSnapshot:
    version: int = 1
    assets: list[Asset] = field(default_factory=list)
    entities: list[Entity] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "assets": [asdict(a) for a in self.assets],
            "entities": [asdict(e) for e in self.entities],
        }

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
        return cls(version=int(data.get("version", 1)), assets=assets, entities=entities)


def schema_org_movie(entity: Entity, base: str = "https://media.local") -> dict[str, Any]:
    """Conservative Schema.org / JSON-LD projection for a Movie."""
    asset_id = entity.asset_ids[0] if entity.asset_ids else entity.id
    doc: dict[str, Any] = {
        "@context": "https://schema.org",
        "@type": "Movie",
        "@id": f"{base}/item/{asset_id}",
        "name": entity.title,
        "contentUrl": f"{base}/media/{asset_id}",
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
    if any(a.id == asset_id and a.role == "main" for a in []):
        pass
    doc["image"] = f"{base}/art/{asset_id}"
    return doc


def schema_org_music_recording(entity: Entity, base: str = "https://media.local") -> dict[str, Any]:
    asset_id = entity.asset_ids[0] if entity.asset_ids else entity.id
    return {
        "@context": "https://schema.org",
        "@type": "MusicRecording",
        "@id": f"{base}/item/{asset_id}",
        "name": entity.title,
        "contentUrl": f"{base}/media/{asset_id}",
    }


def project_jsonld(entity: Entity, base: str = "https://media.local") -> dict[str, Any]:
    if entity.type == "Movie":
        return schema_org_movie(entity, base)
    if entity.type in ("MusicRecording", "MusicAlbum"):
        return schema_org_music_recording(entity, base)
    return {
        "@context": "https://schema.org",
        "@type": "CreativeWork",
        "@id": f"{base}/entity/{entity.id}",
        "name": entity.title,
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

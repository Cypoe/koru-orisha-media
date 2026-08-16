# KoruFlow Semantic Capability Protocol

## Purpose

Define an implementable, agent-safe remote-programming surface for Koru, Orisha, and later Plex/ISAR systems.

The target is not remote execution of arbitrary Koru. A client submits a bounded **KoruFlow** program: a typed continuation graph over capabilities that the server has already declared, compiled, and placed in an authorized runtime scope.

This document joins three existing directions:

- **Koru compiler construction:** language constructs, transforms, checks, and target lowerings are application-programmable.
- **Koru runtime contract:** `std/runtime` derives runtime-callable scope metadata, dispatchers, costs, input/output shapes, and phantom obligations from declared events.
- **Plex/ISAR semantic layer:** physical representations and external identifiers are not semantic identity. The system should operate over canonical local entities and explicit equality/relationship structure.

The first concrete use case is a direct-play media library. The design must remain useful for an agent harness, shell/browser, data services, and distributed applications.

## Non-goals

This protocol does not:

- transmit arbitrary `proc` bodies, host/Zig code, macros, compiler passes, or source imports;
- create a compiler or generate native code at request time;
- expose direct database queries, filesystem paths, service internals, or provider-specific storage keys by default;
- replace Koru's native compiler pipeline;
- require a graph database;
- require the full ISAR/Plex tensor kernel before the first implementation;
- promise universal semantic matching without server-provided identity data;
- silently emulate an unsupported operation or target lowering.

## Terms

### Full Koru

The complete language: declarations, `proc` implementations, compiler transforms, host code, library forms, and flows.

### KoruFlow

The remote-safe invocation and continuation stratum of Koru. It consists of event calls, named arguments, bindings, branch continuations, result construction, and a deliberately small set of explicitly admitted control combinators.

KoruFlow must be representable as text, AST, JSON, or a compact binary encoding. The transport encoding is not the semantic protocol.

### Runtime scope

A named `std/runtime` registration that determines which events are visible to a runtime interpreter. A scope has a generated dispatcher and descriptors for events, inputs, outputs, phantom obligations, and costs.

### Abstract tor

A stable public capability contract whose concrete implementation stays server-private. An abstract tor is the correct public boundary for remote flows and semantic operations.

### Semantic entity

A local canonical object such as `Movie`, `TVSeries`, `TVEpisode`, `MusicRecording`, `Album`, `Person`, `Document`, or `FileAsset`.

### Reference

An identifier or query that may resolve to a semantic entity. A reference is not itself the entity.

Examples:

- `local:media:m_7f3af1`
- `imdb:tt2543164`
- `tmdb:329865`
- `musicbrainz:recording:<uuid>`
- a content hash
- a typed search query

### Relation

A typed semantic edge between entities, collections, or capabilities: `part_of`, `next`, `by_artist`, `same_as`, `has_asset`, `play`, `download`, `edit`, and so on.

### Capability

An authorized operation edge available in a particular context. It has input, outcomes, budget cost, and possibly phantom resource effects.

## Architectural model

```text
semantic entity graph
  - canonical local identities
  - external references and equality assertions
  - typed relations
  - provenance
          |
          v
abstract tor contracts
  - semantic inputs and outputs
  - public outcome vocabulary
  - capability requirements
          |
          v
std/runtime scope
  - event aliases
  - input fields
  - result branches
  - phantom obligations
  - costs
  - generated dispatchers
          |
          v
KoruFlow request
  - bounded continuation graph
  - references only public capabilities
          |
          v
compiled server implementations
  - filesystem, database, provider adapters, cache
  - never exposed as remote implementation code
```

The public semantic object is a quotient of possible concrete representations. For a selected entity relation `~`, the server may establish:

```text
imdb:tt2543164 ~ tmdb:329865 ~ local:media:m_7f3af1
```

The client should never need to know which representation is used internally. It requests a semantic reference; the server returns `found`, `ambiguous`, or `not_found`.

## Core laws

### 1. Capability closure

A flow may invoke only events advertised by the selected scope and authorized for the caller:

```text
callable(flow, scope, principal) => every event in flow is visible in scope
```

### 2. Shape closure

Every call must satisfy the advertised input field names, types, optionality, and phantom requirements. Every continuation must handle a declared branch.

### 3. Budget closure

Each event has a declared non-negative cost. The runtime may execute a trace only while its total cost remains within the supplied or server-derived budget.

```text
sum(cost(event) for executed events) <= budget
```

Budget exhaustion is a normal explicit outcome, not an implementation crash.

### 4. Obligation closure

A flow must honor phantom resource transitions. An event output may create an obligation such as `stream!`; a later input may discharge it as `!stream`. The runtime must use the same semantic contract that the compiler uses.

### 5. Semantic reference closure

Public flows operate on references and canonical entities, never raw private storage paths. Reference resolution is itself a capability with explicit outcomes.

### 6. No dishonest fallback

An unsupported target, relation, provider adapter, or operation must return an explicit unavailable/unsupported outcome. It must not silently substitute an unrelated implementation.

## Existing Koru foundation

`std/runtime` already supplies the operational substrate required by this design.

A registered scope is collected at compile time. The transform resolves direct entries, aliases, wildcard entries, and referenced scopes; retains required declarations across dead stripping; extracts event input fields, output branches, created/discharged phantom obligations, and per-event costs; and emits a dispatcher plus scope descriptors.

The immediate implementation task is therefore not to replace `std/runtime`. It is to extend the generated runtime descriptor with semantic metadata and expose it through an Orisha endpoint.

## KoruFlow wire language

KoruFlow is a restricted, compositional language. It must not accept arbitrary implementation syntax.

### Allowed forms

- invocation of an exported abstract tor;
- literal values and declared data constructors;
- binding an event outcome payload;
- continuation on a declared branch;
- explicit result construction;
- explicitly admitted bounded control combinators;
- optionally, subflow definition/invocation once its scope and cost semantics are specified.

### Excluded forms

- `proc` definitions;
- inline Zig/JS/host code;
- imports selected by the client;
- compiler transforms, template processors, macros, or compiler pipeline changes;
- arbitrary recursion;
- unrestricted dynamic dispatch;
- direct filesystem, network, database, or process access;
- unbounded loops;
- private event names not exported by scope.

### Control forms

Branch continuation is fundamental and should remain in the wire language:

```koru
resolve-media(ref)
| found media     |> ...
| not-found query |> ...
```

Do not add general expression-level `if` unless needed. Most meaningful conditionals should be expressed as domain outcomes:

```koru
authorize(action: "play", target: media)
| allowed capability |> play-media(media, capability)
| denied reason      |> result { error: reason }
```

Do not add general `for` initially. Introduce only bounded, explicitly costed combinators:

- `take(n)` / cursor pagination;
- `map` over an explicitly bounded collection;
- `reduce` with declared reducer and identity;
- `repeat(n)` for explicit finite repetition;
- asynchronous job submission for long-running work.

## Semantic capability graph

The semantic graph is not a replacement for the runtime graph. It supplies identity and meaning for runtime operations.

### Minimal types

```text
EntityId       opaque local canonical identity
EntityKind     Movie | TVSeries | TVEpisode | MusicAlbum | MusicRecording | Person | Asset | ...
Reference      LocalId | ExternalId(provider, namespace, value) | CanonicalUri | ContentHash | Query
RelationKind   same_as | part_of | next | previous | contains | has_asset | by_artist | play | download | ...
CapabilityId   opaque public operation identity
```

### Reference resolution

```text
resolve(ref: Reference)
  -> found { entity: Entity }
  | ambiguous { candidates: EntitySummary[] }
  | not_found { ref: Reference }
```

The server owns matching, provider crosswalks, aliases, user corrections, and provenance. A client does not infer that a TMDB ID and IMDb ID identify the same entity.

### Relation traversal

```text
relate(subject: Entity, relation: RelationKind, options: RelationOptions)
  -> found { target: Entity }
  | many { targets: EntitySummary[], cursor: Cursor? }
  | unavailable { reason: UnavailableReason }
  | not_found {}
```

### Capability execution

```text
perform(action: CapabilityId, target: Entity, input: ActionInput)
  -> success { result: ActionResult }
  | denied { reason: Denial }
  | unavailable { reason: UnavailableReason }
  | failed { error: PublicError }
```

An action is visible only when the current principal and context possess it.

## Abstract tor surface

The public graph edges should be abstract tors. They are stable contracts; concrete databases, filesystem layouts, provider adapters, and caches stay private.

Illustrative media surface:

```koru
abstract tor resolve-media {
  ref: MediaRef
} -> found { media: Media }
  | ambiguous { candidates: []MediaSummary }
  | not-found { ref: MediaRef }

abstract tor media-relation {
  subject: Media
  relation: MediaRelation
  ordering: EpisodeOrder?
} -> found { target: Media }
  | many { targets: []MediaSummary, cursor: Cursor? }
  | unavailable { reason: string }
  | not-found {}

abstract tor authorize-play {
  media: Media
} -> allowed { capability: PlayCapability! }
  | denied { reason: string }

abstract tor play-media {
  media: PlayableMedia
  capability: !PlayCapability
} -> playing { session: PlaybackSession! }
  | unsupported { reason: string }
  | failed { error: string }

abstract tor finish-playback {
  session: !PlaybackSession
} -> completed {}
```

The implementation may resolve a media reference through local metadata, a provider-ID table, a sidecar, or a content hash. The remote flow remains valid because it depends only on the abstract contract.

## Manifest endpoint

Expose a progressive, machine-readable capability manifest. Do not call it Swagger/OpenAPI and do not model it as REST endpoint documentation.

Suggested routes:

```text
GET /.well-known/koruflow
GET /runtime/scopes/{scope}
GET /runtime/scopes/{scope}/capabilities/{capability}
GET /runtime/entities/{id}
POST /runtime/flow
```

### Root manifest

```json
{
  "protocol": "koruflow/0",
  "scopes": [
    {
      "id": "media.v1",
      "href": "/runtime/scopes/media.v1",
      "title": "Media capabilities"
    }
  ],
  "encodings": [
    "text/x-koruflow",
    "application/koruflow+json"
  ]
}
```

### Scope manifest

```json
{
  "scope": "media.v1",
  "budget": { "unit": "cost", "maximum": 100 },
  "capabilities": [
    {
      "id": "media.resolve",
      "tor": "resolve-media",
      "cost": 2,
      "inputs": [
        { "name": "ref", "type": "MediaRef", "required": true }
      ],
      "outcomes": ["found", "ambiguous", "not-found"],
      "semantic": {
        "consumes": ["MediaRef"],
        "produces": ["Media"],
        "relations": ["same_as", "has_asset"]
      },
      "href": "/runtime/scopes/media.v1/capabilities/media.resolve"
    }
  ]
}
```

The full capability descriptor includes branch field shapes, phantom requirements/creations, input optionality, accepted reference schemes, and links to related capabilities.

## Request and response

### Request

Initially support text for development and inspection:

```http
POST /runtime/flow
Content-Type: text/x-koruflow
Accept: application/koruflow-result+json
Authorization: Bearer ...
X-Koru-Scope: media.v1
X-Koru-Budget: 40
```

Body:

```koru
resolve-media(ref: external(provider: "tmdb", value: "329865"))
| found media |>
    media-relation(subject: media, relation: next, ordering: aired)
    | found episode |>
        authorize-play(media: episode)
        | allowed capability |>
            play-media(media: episode, capability)
            | playing session |> result { session }
            | unsupported reason |> result { error: reason }
        | denied reason |> result { error: reason }
    | unavailable reason |> result { error: reason }
| ambiguous candidates |> result { candidates }
| not-found _ |> result { error: "missing" }
```

### Response

```json
{
  "status": "completed",
  "cost": { "used": 14, "remaining": 26 },
  "result": {
    "branch": "result",
    "fields": {
      "session": {
        "kind": "PlaybackSession",
        "id": "session:abc"
      }
    }
  },
  "obligations": [
    {
      "kind": "PlaybackSession",
      "id": "session:abc",
      "state": "live"
    }
  ],
  "links": [
    {
      "rel": "finish",
      "capability": "media.finish-playback"
    }
  ]
}
```

Possible top-level statuses:

```text
completed
budget_exhausted
invalid_flow
denied
scope_not_found
capability_unavailable
internal_failure
```

## Parser and IR

Use the current small flow parser as the initial text frontend. Do not transmit source as the canonical protocol object.

Define a transport-neutral IR:

```text
Flow
  entry: Invocation
  continuations: Continuation[]

Invocation
  capability: CapabilityId | public event name
  arguments: NamedValue[]

Continuation
  branch: BranchName
  binding: Binding?
  next: Node

Node
  invocation | result | control
```

The server pipeline is:

```text
text / JSON / binary
  -> parse/decode FlowIR
  -> scope resolution
  -> capability and shape validation
  -> budget initialization
  -> interpreter dispatch to compiled handlers
  -> obligation accounting
  -> result projection
```

Later encodings may include `application/koruflow+json` and a compact binary form. They must decode into the same `FlowIR` and preserve the same observable behavior.

## Runtime implementation plan

### Phase 0 — preserve current behavior

- Pin and test the existing `std/runtime` scope registration and generated dispatch behavior.
- Document current scope syntax, costs, aliases, wildcard expansion, scope inclusion, input/branch descriptor output, and phantom handling.
- Add regression fixtures for the runtime interpreter before adding semantic features.

### Phase 1 — expose runtime manifest

- Add a stable data model for the generated `ScopeDescriptor` and `ScopeEvent` data.
- Add an Orisha endpoint that returns a scope manifest.
- Include event name, alias, cost, inputs, outputs, branch shape, phantom creates/discharges, and public dispatcher identity.
- Do not expose private implementation symbols, module filesystem paths, raw compiler AST, or host code.

### Phase 2 — define KoruFlow explicitly

- Write a grammar and AST/IR for remote flows.
- Make scope selection and principal/budget required interpreter inputs.
- Validate all calls against the generated scope descriptor before invocation.
- Ensure invalid branch names, missing required arguments, and impossible phantom transitions fail before any side effect.
- Add a request-level trace with event name, branch, cost, and public error information.

### Phase 3 — semantic graph minimum

- Define `Entity`, `Reference`, `ExternalId`, `Relation`, `Assertion`, and `Capability` records.
- Implement local canonical identity plus provider-ID crosswalks.
- Implement `resolve-media` with `found`, `ambiguous`, and `not-found` outcomes.
- Implement one relation: `next` for episodes.
- Implement one authorized action: `play`.
- Store provenance for every external-ID equality assertion.

### Phase 4 — abstract tor integration

- Express the public operations as abstract tors.
- Bind concrete media-library implementation behind those tors.
- Extend runtime descriptors with semantic annotations: consumed/produced entity kinds, relation kinds, accepted reference schemes, and capability identifiers.
- Ensure clients invoke the abstract contract, never a private database or provider adapter.

### Phase 5 — progressive disclosure

- Add root/scope/capability/entity manifests.
- Add relation/capability links only when visible to the principal.
- Support an agent starting at the root manifest and requesting only the next relevant descriptor.
- Avoid handing an agent every private event or all database schema at connection time.

### Phase 6 — controlled dynamic composition

- Decide whether runtime scope extension/removal is needed.
- If added, specify ownership and inverse semantics before implementation.
- Model installation/removal as explicit capability operations with traceable effects.
- Evaluate Cordis as a reference for reversible effect ownership, not as an opaque dependency to import automatically.

## Tests

### Static/runtime contract tests

- A registered event survives dead stripping.
- Scope alias resolves only to its declared target.
- Wildcard inclusion does not expose undeclared private events.
- Event input/branch/phantom metadata matches the event declaration.
- A call with a missing required argument fails before dispatch.
- An unknown branch continuation fails before dispatch.
- A phantom requirement not held by the flow fails before dispatch.
- Budget exhaustion prevents further dispatch and returns a stable outcome.

### Semantic identity tests

- Local ID, IMDb ID, and TMDB ID resolve to the same canonical entity when asserted equal.
- Unknown external ID returns `not-found`.
- Multiple candidates return `ambiguous`, never an arbitrary match.
- A changed provider label does not change local entity identity.
- Provider outages do not break existing local identity or direct play.

### Capability tests

- `play` is absent or denied for an unauthorized principal.
- `next` is unavailable for a movie but available for an episode with known ordering.
- A `PlaybackSession!` is created only by a successful play outcome.
- Completion/disposal discharges the session obligation exactly once.

### Protocol tests

- Text and JSON encodings decode to equal `FlowIR`.
- The same valid flow gives equivalent result/trace through both encodings.
- A flow cannot address a filesystem path directly.
- A flow cannot invoke a non-exported event.
- A remote flow cannot introduce imports, implementation code, transforms, or host code.

## Media-service constraints

The media server remains direct-play and content-driven:

```text
offline indexer
  -> physical manifest and semantic snapshot
  -> Orisha loads immutable projection
  -> KoruFlow resolves semantic entities/capabilities
  -> Range stream serves original bytes
```

No normal browse or remote-flow request may:

- scan the media tree;
- invoke FFmpeg;
- transcode;
- generate HLS/DASH segments;
- call an external metadata provider synchronously;
- require a database daemon;
- buffer a complete media file.

The semantic graph is refreshed offline and projected into an immutable lookup structure. Direct playback remains a separate byte-serving path.

## Security model

Treat a remote flow as an untrusted request graph.

Mandatory controls:

- authenticated principal;
- selected authorized scope;
- server-defined maximum budget;
- maximum AST depth and node count;
- maximum result size;
- capability allowlist;
- argument shape/type validation;
- phantom/ownership validation;
- request deadline and cancellation;
- trace/audit record;
- no direct host-code execution;
- no client-selected imports, transforms, or implementation symbols;
- no raw private storage addressing.

The security guarantee must be phrased precisely:

> A remote client may compose only public, scope-authorized, budget-accounted abstract capabilities. It cannot supply server implementation code or alter the compiler/runtime pipeline.

## Definition of done: first vertical slice

The first milestone is complete when:

1. An Orisha server publishes `/.well-known/koruflow` and one scope manifest.
2. The scope manifest is generated from an existing `std/runtime` registration.
3. One media scope exposes `resolve-media`, `media-next`, `authorize-play`, and `play-media` as abstract public contracts.
4. A text KoruFlow request is parsed by the constrained runtime parser.
5. The request can invoke only manifest-advertised capabilities.
6. The runtime enforces input shape, branch shape, scope access, and event budget.
7. `tmdb:<id>` and `imdb:<id>` can resolve to one local canonical entity through explicit server-side assertions.
8. Ambiguity is returned explicitly rather than guessed.
9. A successful flow can begin direct playback without transcoding.
10. No request executes user-provided implementation code, creates a compiler, or exposes raw filesystem paths.
11. The result includes used budget, terminal branch, public result fields, and any remaining obligations.
12. The full suite runs from a clean checkout with deterministic fixtures.

## Open decisions

- Exact concrete syntax and MIME type for KoruFlow.
- Whether remote `if` is needed beyond branch continuations.
- Which bounded traversal/reduction combinators are admitted first.
- Whether `for` is represented by dedicated map/reduce/pagination primitives or a restricted flow form.
- How runtime scope descriptors are versioned and negotiated.
- How semantic relation names are namespaced and versioned.
- Whether semantic manifests use JSON-LD/Schema.org as a projection or a separate compact internal vocabulary.
- How capability revocation and dynamic scope updates are represented.
- Whether a Cordis-like reversible-effect model should be implemented as Koru abstract tors and phantom obligations or adapted as an external runtime.

## Guiding formulation

Do not send implementation code to execute.

Send a typed continuation over semantic capabilities that the server already declared, compiled, authorized, budgeted, and can account for.

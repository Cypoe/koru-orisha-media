# HTTP Protocol

## Representations

HTML is the default representation for human navigation. Clients may request JSON with `Accept: application/json`; JSON must expose resource links and available actions instead of requiring clients to reconstruct routes.

Every representation should have a canonical URL and may include `Link` headers such as `rel="self"`, `rel="alternate"`, `rel="up"`, or `rel="related"`.

`GET /item/{id}` is HTML by default. When a semantic join exists, the same URL also offers JSON-LD:

- `GET /item/{id}?format=jsonld` or `Accept: application/ld+json` / `Accept: application/json`
- `Link: </item/{id}?format=jsonld>; rel="alternate"; type="application/ld+json"`
- Provider catalogue URLs (TMDB, IMDb) appear as HTML links and `rel="related"` only when present on the local snapshot

When a join hits, item/play HTML splits **catalogue** (prefetched named constructions: `orisha.item` display strings, `orisha.links` provider URLs) from **local archive** (filename, path, container, probe, bytes). Orisha scrapes `projections[]` and merges by asset id; handlers never call TMDB or ffprobe, and they do not read representation fields off `Entity`. Missing `semantic.json`, an empty `projections[]`, or missing constructions leaves physical item HTML unchanged and playback intact. `/` and `/library` always list local manifest files; catalogue chips appear only when those constructions exist.

## Methods

- `GET` retrieves a representation or media bytes.
- `HEAD` returns the same metadata as `GET` without a response body.
- `OPTIONS` describes generic method support for the target resource and may return `Allow`. It is not a substitute for representation-level affordances.
- `POST`, `PUT`, `PATCH`, and `DELETE` are reserved for explicitly designed library mutations and are not required for direct play.

## Media response

A media endpoint must validate the opaque ID, resolve it through the manifest, and reject direct path input. It should return:

```text
Accept-Ranges: bytes
Content-Length: <length>
Content-Type: <known MIME>
ETag: <stable representation validator>
Last-Modified: <file modification time>
```

For a valid single range, return `206 Partial Content` with `Content-Range` and the exact selected length. Invalid or unsatisfiable ranges must not cause unbounded buffering or an FFmpeg fallback.

## Affordances

A collection page should expose links for available views, sorting, filtering, pagination, and alternate representations. A media page should expose a play link, download link, parent collection link, artwork link, and any available track or subtitle relations.

Mutating controls are rendered only when authorized. Absence of a form is meaningful; clients should not infer permissions from hidden JavaScript configuration.

## Enhanced requests

An enhanced client may request a fragment using a normal `GET` plus an opt-in header. The server returns a fragment with a clear target identity and may return a redirect for navigation requests. The complete HTML response remains the fallback for clients that do not understand the enhancement.

No endpoint should require HTMX, Koru-generated JavaScript, or a custom client merely to browse or play a supported file.

# Koru/Orisha Media

A small, direct-play media library built around Koru and Orisha.

The goal is not to reproduce Jellyfin. The goal is to provide a fast, content-driven web surface for a personal library:

- precomputed media metadata;
- server-rendered hypermedia pages;
- optional Koru-generated browser enhancement;
- native browser playback where supported;
- HTTP Range delivery of original files;
- no resident transcoder, recommendation engine, or media database required.

## Non-goals

Transcoding, adaptive HLS/DASH, format conversion on request, remote metadata enrichment, and a general-purpose media-server client ecosystem are deliberately out of scope for the first version.

## Status

Early design and protocol work. The repository is intentionally documentation-first until the Koru and Orisha integration boundary is fixed against their current APIs.

## Design principle

A library request should be bounded by manifest lookup and response serialization. A media request should be bounded by authorization, range validation, and file streaming. Scanning, probing, artwork generation, and conversion belong to an explicit offline indexer.

See [ARCHITECTURE.md](ARCHITECTURE.md), [docs/protocol.md](docs/protocol.md), and [docs/manifest.md](docs/manifest.md).

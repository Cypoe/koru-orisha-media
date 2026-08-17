# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- Home landscape hero with Play/Info/heart on the art, My Media collection tiles, and Home/Favourites chips
- Library kind toolbars (All/Favourites, shuffle/sort/filter) and a dedicated search page
- Sidebar drawer, overlay topbar, and a search field that collapses to an icon on a narrow column
- Changelog and release path for LAN `:latest` vs tagged GHCR/GitHub releases

### Changed

- Catalog sidecar splits poster, backdrop, and logo so the hero can prefer backdrop art

## [0.1.0] - 2026-08-17

### Added

- Medushu direct-play library UI (home, shelves, item/watch pages) from HTML fragments
- Musl/scratch runtime image (`koru-orisha-media:local`) with compose and NAS (`compose.nas.yaml`) paths
- SQLite catalog with in-binary library walk / reindex; optional JSON manifest import
- Optional metadata hydrate (local nfo, IMDb `[tt…]` via Cinemeta; TMDB/TVDB keys when set)
- Local SigmaNAS registry deploy (`scripts/nas-deploy.sh` / `publish-registry.sh`)
- Public release machinery: versioned tags, GHCR push, GitHub Release image tarball (`scripts/release.sh`)

[Unreleased]: https://github.com/Cypoe/koru-orisha-media/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/Cypoe/koru-orisha-media/releases/tag/v0.1.0

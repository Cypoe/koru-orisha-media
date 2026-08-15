# Synology SPK (follow-up)

Scaffold only. Do **not** submit to SynoCommunity until a registry image exists and this checklist is done.

## Prerequisites

- [ ] Semver releases and changelog for the app
- [ ] Published multi-purpose image tags on GHCR, e.g. `ghcr.io/cypoe/koru-orisha-media:0.x.y` ([packaging.md](packaging.md))
- [ ] Confirmed Container Manager install via compose on a real DSM box
- [ ] Icons (PACKAGE_ICON.PNG / 256) and maintainer metadata

## Approach

Ship a **Docker-wrapping SPK** (DSM `docker` resource worker), not a native cross-compiled binary:

- Package Center install pulls/runs the GHCR image
- Upgrade = new SPK revision pointing at a new image tag
- Depends on Synology **Container Manager** / Docker

Do not native-cross-compile `media-server` inside [spksrc](https://github.com/SynoCommunity/spksrc) unless there is a strong reason later.

## Volume and port mapping

| DSM side | Container | Notes |
|----------|-----------|--------|
| `movies` share | `/media/movies` | Read-only |
| `shows` share | `/media/shows` | Read-only |
| `music` share | `/media/music` | Read-only |
| Package data dir | `/data` | `manifest.json` (writable) |
| Host port (wizard) | `3090` | Process listen port is fixed in-container |

Env inside the container matches the runtime image: `KORU_MEDIA_ROOT=/media`, `KORU_MANIFEST=/data/manifest.json`. First-run reindex can be `KORU_REINDEX=1` or a documented postinst step.

## Follow-up execution steps

1. Fork/clone SynoCommunity `spksrc` and add `spk/koru-orisha-media` using their Docker-package patterns.
2. Promote stubs from this repo’s [`spk/koru-orisha-media/`](../spk/koru-orisha-media/) into real `INFO` / `conf/resource` / wizard files (replace `VERSION` and maintainer).
3. Build the `.spk`, install on a test NAS, verify Package Center start/stop/upgrade.
4. Open a SynoCommunity PR with description, screenshots, and DSM version matrix.

## References

- [SynoCommunity package anatomy](https://docs.synocommunity.com/developer-guide/basics/package-anatomy/)
- [Synology Docker package example](https://help.synology.com/developer-guide/examples/compile_docker_package.html)
- [Resource files](https://docs.synocommunity.com/developer-guide/packaging/resource-files/)

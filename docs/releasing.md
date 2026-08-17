# Releasing (tutorial)

This is the how-to for **you and for the agent**. Read this before cutting or “bumping” a version.

## Mental model (read first)


| Action                          | Creates a release?          | Bumps semver?                                |
| ------------------------------- | --------------------------- | -------------------------------------------- |
| `git push` to `main`            | **No**                      | **No**                                       |
| `bash scripts/nas-deploy.sh`    | **No** (LAN `:latest` only) | **No**                                       |
| `bash scripts/release.sh X.Y.Z` | **Yes**                     | **Yes** — only if you pass a **new** `X.Y.Z` |


- **You choose the next version** (`0.1.0` → `0.1.1` / `0.2.0`). Nothing auto-increments.
- There is **no** single `VERSION` file the whole repo must read. Semver lives in:
  1. the argument to `release.sh`
  2. `CHANGELOG.md` (`## [X.Y.Z] - date`)
  3. the git tag `vX.Y.Z` (created by the script)
- **Enforcement:** `release.sh` refuses if `vX.Y.Z` already exists, and fails if `CHANGELOG.md` has no `## [X.Y.Z]` section. That is the only guard.
- Build stays on the **build machine** (`koruc`). Pushing code does not compile or publish images.

Public share = **GHCR** (`ghcr.io/cypoe/koru-orisha-media`) + **GitHub Release** tarball. SigmaNAS = LAN registry `sigmanas:9500` (also gets versioned tags on a full release).

## Tutorial — cut a release

### 1. Pick the version

Look at the latest `## […]` in `[CHANGELOG.md](../CHANGELOG.md)` (and `git tag`). Decide the next semver yourself. Example first cut: `0.1.0`.

### 2. Write the changelog

1. Move bullets from `## [Unreleased]` into a new `## [X.Y.Z] - YYYY-MM-DD`.
2. Commit that on `main` (and push `main` if you want the commit remote before the tag).
3. Working tree should be clean. Run `bash scripts/test_all.sh` when practical.

Do **not** run `release.sh` until this section exists and is committed.

### 3. One-time auth (skip if already done)

**GHCR** (unless you will use `--skip-ghcr`):

1. GitHub → Settings → Developer settings → Personal access tokens
  Classic: `write:packages` + `read:packages`, or fine-grained Packages write on this repo/org.
2. Login:

```bash
echo YOUR_PAT | docker login ghcr.io -u Cypoe --password-stdin
```

1. After the first package push: [packages](https://github.com/Cypoe?tab=packages) → visibility + link to `Cypoe/koru-orisha-media`.

**GitHub CLI** for the Release page:

```bash
gh auth login
```

### 4. Run the release script

From the repo root on the build machine:

```bash
bash scripts/release.sh 0.1.0
# or: bash scripts/release.sh 0.1.0 --skip-compile   # binary/image already current
```

Useful flags:


| Flag             | Meaning                                           |
| ---------------- | ------------------------------------------------- |
| `--skip-compile` | Forwarded to `build-image.sh`                     |
| `--skip-nas`     | Do not push to `sigmanas:9500`                    |
| `--skip-ghcr`    | Do not push to GHCR (LAN / tarball / GitHub only) |
| `--dry-run`      | Print steps; no tag, push, save, or `gh release`  |


### 5. What the script does (in order)

1. `build-image.sh` → `koru-orisha-media:local`, then tag `:X.Y.Z`
2. LAN: `TAGS="X.Y.Z latest" publish-registry.sh` → `sigmanas:9500/koru-orisha-media`
3. GHCR: `publish-ghcr.sh X.Y.Z` → `:X.Y.Z` and `:latest`
4. `save-image.sh` → `dist/koru-orisha-media-X.Y.Z-linux-amd64.tar.gz`
5. `git tag -a vX.Y.Z` → `git push origin vX.Y.Z` → `gh release create` with changelog notes + tarball

It does **not** recreate the NAS compose stack. After tags exist, deploy when you want:

```bash
bash scripts/nas-deploy.sh --skip-compile
# or Container Manager recreate with --pull always
```

### 6. Verify

- [ ] `ghcr.io/cypoe/koru-orisha-media:X.Y.Z` and `:latest`
- [ ] GitHub Release `vX.Y.Z` + asset `koru-orisha-media-X.Y.Z-linux-amd64.tar.gz`
- [ ] `sigmanas:9500/koru-orisha-media:X.Y.Z` and `:latest`
- [ ] Smoke `/library` on SigmaNAS after recreate

## Day-to-day (not a release)

Ship fixes to the NAS without a public version:

```bash
bash scripts/nas-deploy.sh          # or --skip-compile
```

That only refreshes `**:latest**` on the LAN registry. No git tag, no GHCR, no GitHub Release, no semver bump.

## Install for others

**Preferred — GHCR:**

```bash
docker pull ghcr.io/cypoe/koru-orisha-media:0.1.0
# compose image: that tag (or retag to koru-orisha-media:local)
docker compose up
```

**Offline — Release tarball:**

```bash
gzip -dc koru-orisha-media-0.1.0-linux-amd64.tar.gz | docker load
docker tag koru-orisha-media:0.1.0 koru-orisha-media:local
docker compose up
```

## Later — GitHub Actions

When koru/koruc can compile on Linux CI, a workflow on tag `v*` should: compile → `docker build` → push GHCR (`VERSION` + `latest`) → `docker save` → attach the same tarball name to the Release.

Until then there is **no** release workflow in-repo. `**scripts/release.sh` on the build machine is the source of truth** for tag and asset names. Pushing `main` will still not cut a release unless you add automation that runs on tags only.

## Agent notes

- Do **not** invent a version bump or run `release.sh` unless the user explicitly asks to cut a release.
- Do **not** treat `git push` / PR merge as a release.
- Before releasing: confirm changelog section exists, tree is what they want tagged, and which flags (`--skip-nas` / `--skip-ghcr`) they want.
- Hardcoded `0.1.0` strings inside build/`koru.json` helpers are **not** updated by `release.sh`; leave them unless the user asks to sync them.

## Related

- Local / NAS packaging: [packaging.md](packaging.md)
- SynoCommunity SPK (follow-up): [synology-spk.md](synology-spk.md)


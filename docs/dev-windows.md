# Windows / WSL workflow

This repo lives on a Windows drive and is often built via WSL + Docker. Split tools by job:

## Network git (`push` / `pull` / `fetch`)

Prefer **native Windows** `git` from the repo directory (PowerShell or Git Bash). Credential helpers work there, and you avoid WSL path-translation hangs (e.g. odd drive mounts like Steam paths) that can stall `wsl … git push`.

```powershell
git push -u origin HEAD
```

## Build and test

Prefer **WSL bash** for `scripts/*.sh` and Docker:

```bash
bash scripts/build-docker.sh
bash scripts/test_all.sh
```

### Fast frontend loop (fixtures, already indexed)

Compile the native WSL binary **once**, then run against `fixtures/media` plus recorded TMDB JSON. The process serves `public/` from the repo root, so CSS edits apply on refresh.

```bash
bash scripts/dev-wsl.sh
# → http://127.0.0.1:3090/

# After the first index, skip the Koru compile:
SKIP_COMPILE=1 bash scripts/dev-wsl.sh
```

After `src/frontend/host.kjs` changes: `bash scripts/build-frontend.sh`. Handler/Zig changes need a full `bash scripts/build.sh` (or omit `SKIP_COMPILE`). Catalog and hydrate flags live under `.pw/dev/` (not committed).

Scripts resolve the repo root from their own location (`dirname`), so they no longer depend on a hardcoded `/mnt/c/Users/...` path.

# Vendored koru-libs (frontend)

Same idea as [`orisha`](../orisha): libraries live here; `src/` only consumes them.

| Path | Module | Upstream | Vendored |
|------|--------|----------|----------|
| `dom/` | `koru/dom` | `W:\src\koru-libs\dom` (`index.k` + `index.kjs` + `index.kz`) | 2026-08-13 — library stem only (no `app/`, `tests/`, `board/`, `closer/`) |
| `htmx/` | `koru/htmx` | **ours** (not upstream yet) | generic `hx-*` / `HX-Request` fetch+swap host |

`import koru/dom` and `import koru/htmx` resolve through `"koru": "./vendor/koru-libs"` in the frontend emit `koru.json` (`scripts/build-frontend.sh`). Do not compile an isolated copy of a lib as `main.k`.

Honest limit: `koru/htmx` host **logic** is still JS inside `|js` facets (Koru does not lower fetch/swap). `koru/dom` keyed list is real Koru IR. Entry/boot is Koru (`koru/htmx:run` / `koru/dom:run` as top-level flows → emitted `main_module.flowN()`).

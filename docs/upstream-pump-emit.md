# Upstream: pump sibling emit (koruc, with an Orisha defensive patch)

This is a **koruc emit gap**. Tiny packages with a `pump` sibling still link, including overlapping `const std` / `const posix = std.posix`. 110_030’s own `.kz`-only fixture still links.

It is **not** limited to this consumer. Re-checked 2026-08-13 against `W:\src\orisha` `661fa9c`, koruc 0.1.7, koru `5c64de27`:

- In-tree original `lib/` (`koru.json` `"orisha": "lib"`) + canonical `orisha:serve` → **fails**. Zig `duplicate struct member` inside `koru_pump` (`Exchange`, `READ_BUFFER`, `fill_event`, …; ~96 errors). Same result if that `lib/` is copied out.
- An earlier note that canonical serve **links** on this toolchain was wrong (the serve harness also hit `KORU100` unused bindings before the Zig errors were visible).

This media binary still cannot compile pump into `import orisha`. The Zig symptom depends on the pairing:

| Pairing | Symptom |
|---------|---------|
| Original `lib/` (`import orisha/pump` + `serve = pump:run`) | `duplicate struct member` in `koru_pump` (module arrived twice) |
| This vendor’s thicker `index.kz` + unused sibling `pump.kz` (no import) | `ambiguous reference` on `std` (~30 errors) |

Same identity bug, two Zig failures. `vendor/upstream/orisha-pump/pump.*` is byte-identical to `W:\src\orisha\lib/pump.*`.

Related koru work (2026-08-08, same pump seam):

- regression `110_030_index_and_directory_are_one_module`
- `concepts/frag-nesting-a-module-inherits-its-parents-namespace.md`
- `concepts/frag-a-dedup-key-must-be-an-identity-not-a-spelling.md`

Those fixes hold for the small shapes they pin. They do not hold for Orisha-sized `index.k`+`index.kz` plus real `pump.kz`.

Repro (split stages — Zig diagnostics are from `./backend output`, not the frontend log):

```bash
koruc -o backend.zig main.k   # frontend: backend.zig + program.ast.json
zig build --build-file build_backend.zig
./backend output              # emits output_emitted.zig and compiles it
```

Scripts:

- `bash scripts/repro_pump_emit_backend.sh` — INTREE + G, writes `pump-emit-artifacts/{INTREE,G}/backend.err` and `output_emitted.zig`
- Original lib + serve: `bash scripts/verify_orisha_intree_serve.sh`
- Consumer variants F–I: `bash scripts/repro_pump_emit_docker.sh`
- Tiny negative controls A–E: `bash scripts/repro_pump_emit.sh`

On koruc 0.1.7 a bare `koruc main.k` also chains the backend (default `build_executable`); `--help` still describes that as “compile to .zig”. Use `-o backend.zig` when you want the frontend pass alone.

Pins used for the backend capture (2026-08-13): koruc 0.1.7 sha256 `9e24dc39cb66a133d28f8715e4549430c48bd86a7941a7b71a9afd548e97762d`, koru `5c64de27`, Orisha `661fa9c`, zig 0.15.1.

## What fails

**INTREE / I.** Original `W:\src\orisha\lib` + `orisha:serve` (unikernel-style `| shutdown _ |> _`) → **duplicate `koru_pump`**.

**F (control).** This repo’s `vendor/orisha` (no `pump.*`) + `orisha:run-accept-loop` → **links**.

**G.** Same tree + full upstream `pump.k` / `pump.kz` copied beside `index.k`, **no** `import orisha/pump` → Zig `ambiguous reference` on `std` (~30 errors). Directory import still loads the `pump` stem; nested `const posix = std.posix` sees both the parent’s `const std` and pump’s `const std`. `routing.kz` already avoids this by naming `router_std`.

**H.** G + `import orisha/pump` in `index.k`, app still on `run-accept-loop` → same **ambiguous `std`**.

**Media binary + `serve = pump:run` in the same `index.k` as `run-accept-loop`.** `duplicate struct member` inside `koru_pump`. Slimming pump to one `|zig` body per event did not fix it.

## What does not fail

- Tiny `index.k`+`index.kz` + tiny or full-shaped `pump.kz` (`std`/`posix`/`c`), with or without `import lib/pump`.
- Parent and sibling both declaring `std`+`posix`+`c` in a 10-line package.
- 110_030’s own `.kz`-only fixture.

A single reduced `.kz` is the wrong pin: those shapes still link. The failing directory package is original Orisha `lib/` (INTREE) or this vendor plus sibling pump (G).

## Ask (koruc) — [korulang/koru#2](https://github.com/korulang/koru/issues/2)

110_030’s identical-const drop and directory/index identity should cover this pairing, or fail in Koru with a module-level diagnostic instead of Zig `ambiguous reference` / `duplicate struct member`.

Suggested pin: copy `W:\src\orisha\lib` (or this repo’s `vendor/upstream/orisha-pump/` plus upstream `index.k`/`index.kz`/`routing.*`) next to `110_030` as a directory package whose `input.k` is the four-line `orisha:serve` example. Do not pin Zig’s `ambiguous reference` as `MUST_ERROR`; after a koruc fix this should `MUST_RUN`. Case G is the unused-sibling / `ambiguous std` variant.

## Ask (Orisha) — [korulang/orisha#1](https://github.com/korulang/orisha/issues/1)

Defensive, not a substitute for the compiler fix, and **not** a fix for canonical serve’s duplicate `koru_pump`: rename pump’s host aliases the way `routing.kz` already does (`router_std`) — e.g. `pump_std` / keep `$mod.` for posix. That only helps a consumer whose unused `pump` stem is merged into the parent (`ambiguous std`). The import-pump + `serve` double-emit is koruc.

Happy to test a patch against this repo’s HTTP suite (`run-accept-loop` + STREAM). We are not asking Orisha to take STREAM or media HTML.

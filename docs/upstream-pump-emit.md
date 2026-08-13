# Upstream: pump sibling emit (koruc, with an Orisha defensive patch)

This is **not** an Orisha logic bug. Canonical `orisha:serve` against `W:\src\orisha/lib` links (koruc 0.1.7, `W:\src\koru` `5c64de27`). Tiny packages with a `pump` sibling also link, including overlapping `const std` / `const posix = std.posix`.

It **is** a koruc emit gap that Orisha’s pump split exposes as soon as a consumer’s `index.kz` is the real Orisha host file (listen/accept/send plus this app’s STREAM extras). Repro: `bash scripts/repro_pump_emit_docker.sh` (cases F–H). Tiny cases A–E in `scripts/repro_pump_emit.sh` are the negative controls.

Related koru work (2026-08-08, same pump seam):

- regression `110_030_index_and_directory_are_one_module`
- `concepts/frag-nesting-a-module-inherits-its-parents-namespace.md`
- `concepts/frag-a-dedup-key-must-be-an-identity-not-a-spelling.md`

Those fixes hold for the small shapes they pin. They do not hold for this pairing.

## What fails

**F (control).** This repo’s `vendor/orisha` (no `pump.*`) + `orisha:run-accept-loop` → **links**.

**G.** Same tree + full upstream `pump.k` / `pump.kz` copied beside `index.k`, **no** `import orisha/pump` → Zig `ambiguous reference` on `std` (~30 errors). Directory import still loads the `pump` stem; nested `const posix = std.posix` sees both the parent’s `const std` and pump’s `const std`. `routing.kz` already avoids this by naming `router_std`.

**H.** G + `import orisha/pump` in `index.k`, app still on `run-accept-loop` → same **ambiguous `std`**.

**Media binary + `serve = pump:run` in the same `index.k` as `run-accept-loop`.** Different symptom: `duplicate struct member` inside `koru_pump` (the 110_030 “module arrived twice” class). Slimming pump to one `|zig` body per event did not fix it.

## What does not fail

- Tiny `index.k`+`index.kz` + tiny or full-shaped `pump.kz` (`std`/`posix`/`c`), with or without `import lib/pump`.
- Parent and sibling both declaring `std`+`posix`+`c` in a 10-line package.
- 110_030’s own `.kz`-only fixture.

So this is not “siblings cannot share `const std`” in general. It is “Orisha-sized `.k`+`.kz` index + real `pump.kz` as a directory-enumerated sibling”.

## Ask (koruc) — [korulang/koru#2](https://github.com/korulang/koru/issues/2)

110_030’s identical-const drop and directory/index identity should cover this pairing, or fail in Koru with a module-level diagnostic instead of Zig `ambiguous reference` / `duplicate struct member`.

Suggested pin: a regression next to `110_030` that uses a reduced Orisha index companion (listen/accept/send host lines + `const posix = std.posix`) and the real `pump.kz` preamble, loaded as a directory package. Case G in this repo is the current failing consumer.

## Ask (Orisha) — [korulang/orisha#1](https://github.com/korulang/orisha/issues/1)

Defensive, not a substitute for the compiler fix: rename pump’s host aliases the way `routing.kz` already does (`router_std`) — e.g. `pump_std` / keep `$mod.` for posix. That lets a consumer extend `index.kz` without the unused `pump` stem poisoning the parent namespace if koruc still enumerates it.

Happy to test a patch against this repo’s HTTP suite (`run-accept-loop` + STREAM). We are not asking Orisha to take STREAM or media HTML.

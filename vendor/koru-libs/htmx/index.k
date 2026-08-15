// koru/htmx — generic navigation host (hx-* / HX-Request dialect).
//
// Same job as vaxis/dom `run`: the host event loop is the loop. This is not a
// full HTMX port. Protocol (server HTML; do not fork):
//   Complete pages are the representation. Fragments are opt-in via
//   hx-get / hx-target / hx-swap / hx-push-url.
//   Request: HX-Request: true + Prefer: return=minimal.
//   Fallback: plain href/forms. Never require this script to browse.
//
// Honest limit: fetch/swap live in the |js facet (index.kjs) because Koru does
// not lower them yet. `run` is the Koru entry — a top-level call is retained
// as `main_module.flowN()` (same shape as koru/dom:run). A `tor boot {}` /
// `boot = run(...)` definition is dead-stripped. Trailing JS outside `~proc`
// in `.kjs` is prepended before `const main_module` and cannot call handlers.
//
// `target` is the default hx-target. `protect` is a selector that must not be
// swapped or owned by a swap target (empty string = none). `pop_prefix` limits
// popstate re-fetch to matching pathnames (empty = any). When the consumer
// defines `withAppBase`, popstate / hx-get honor `html[data-base]`. App-local
// resume and post-swap identity checks stay in the consumer.

pub tor run { target: string, protect: string, pop_prefix: string }

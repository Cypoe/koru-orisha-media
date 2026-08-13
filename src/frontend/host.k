// Media usage of koru/htmx — JS emit (`public/enhance.js`).
//
// Library: vendor/koru-libs/htmx (import koru/htmx). This file is usage only:
// boot the generic host with media defaults, plus #player resume.
//
// PROTOCOL (server HTML; do not fork): complete pages are the representation.
// Fragments are opt-in via hx-get / hx-target / hx-swap / hx-push-url.
// Request: HX-Request: true + Prefer: return=minimal.
// Fallback: plain href/forms. Never require this script to browse or play.
//
// Top-level `koru/htmx:run(...)` and `enhance-player()` are retained as
// `main_module.flowN()` (same shape as koru/dom:run). A `tor boot {}` /
// `boot = ...` definition is dead-stripped.
//
// Honest limit: host *logic* is still JS inside |js facets because Koru does
// not lower fetch/swap yet. Entry/boot is Koru. Keyed list (`main.k`) is real
// Koru IR emit.
//
// APP-LOCAL: #player resume, #library-region default, protect: "#player".
//
// Source: src/frontend/host.k + host.kjs. Emit: public/enhance.js.
// Build: bash scripts/build-frontend.sh

import koru/htmx

pub tor enhance-player {}

enhance-player()
koru/htmx:run(target: "#library-region", protect: "#player", pop_prefix: "/library")

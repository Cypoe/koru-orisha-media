const __koru_len = { get() { return this.length; }, configurable: true };
Object.defineProperty(String.prototype, "len", __koru_len);
Object.defineProperty(Array.prototype, "len", __koru_len);
// koru/htmx |js facet — generic fetch + region swap.
// File-level helpers (same pattern as koru/dom's koruDomNode) are prepended
// into the emit. ~proc run|js is the boot body invoked from a retained flow.
// Function name `isSafeSwapTarget` is part of the HTTP test surface.
function fragmentHeaders() {
    return {
        Accept: "text/html",
        "HX-Request": "true",
        Prefer: "return=minimal",
    };
}
function isSafeSwapTarget(sel, protect) {
    if (!sel || sel === "body" || sel === "html") return false;
    if (protect) {
        const p = protect.charAt(0) === "#" ? protect.slice(1) : protect;
        if (sel === protect || sel === p || sel === "#" + p) return false;
    }
    const el = document.querySelector(sel);
    if (!el) return false;
    if (protect) {
        const guarded = document.querySelector(protect);
        if (guarded && (el === guarded || (el.contains && el.contains(guarded)))) return false;
    }
    return true;
}
function hxGetUrl(el) {
    const raw = el.getAttribute("hx-get");
    if (!raw) return null;
    try {
        const u = new URL(raw, location.href);
        if (el.tagName === "FORM") {
            const fd = new FormData(el);
            fd.forEach(function (v, k) {
                u.searchParams.set(k, String(v));
            });
        }
        const path = u.pathname + u.search;
        return typeof withAppBase === "function" ? withAppBase(path) : path;
    } catch (_) {
        return raw;
    }
}
function swapInto(targetSel, html, pushUrl, protect, defaultTarget) {
    if (!isSafeSwapTarget(targetSel, protect)) return false;
    const before = typeof playerSnapshot === "function" ? playerSnapshot() : null;
    const mark = "koru-hx-swap";
    try {
        if (window.performance && performance.mark) performance.mark(mark + "-start");
    } catch (_) {}
    const tmp = document.createElement("div");
    tmp.innerHTML = html;
    const next =
        tmp.querySelector(targetSel) ||
        (defaultTarget ? tmp.querySelector(defaultTarget) : null);
    if (!next) return false;
    const cur = document.querySelector(targetSel);
    if (!cur) return false;
    cur.replaceWith(next);
    if (pushUrl) history.pushState({ koruHx: true }, "", pushUrl);
    try {
        if (window.performance && performance.mark && performance.measure) {
            performance.mark(mark + "-end");
            performance.measure(mark, mark + "-start", mark + "-end");
        }
    } catch (_) {}
    if (typeof playerIdentityOk === "function" && !playerIdentityOk(before)) return false;
    return true;
}
function fetchAndSwap(url, target, pushUrl, fallbackUrl, protect, defaultTarget) {
    if (!isSafeSwapTarget(target, protect)) {
        location.href = fallbackUrl || url;
        return;
    }
    fetch(url, { headers: fragmentHeaders() })
        .then(function (r) {
            return r.text();
        })
        .then(function (html) {
            if (!swapInto(target, html, pushUrl, protect, defaultTarget)) {
                location.href = fallbackUrl || url;
            }
        })
        .catch(function () {
            location.href = fallbackUrl || url;
        });
}
// Usage |js for the media navigation host (src/frontend/host.k).
// Player resume + post-swap identity. Generic fetch/swap is koru/htmx.
// File-level `playerSnapshot` / `playerIdentityOk` are the hooks the library
// swap path calls (same prepend pattern as koru/dom's koruDomNode).
// Names `playerIdentityOk` / `localStorage` / `appBase` are part of the HTTP test surface.
function appBase() {
    const html = document.documentElement;
    return (html && html.getAttribute("data-base")) || "";
}
function withAppBase(pathAndSearch) {
    const base = appBase();
    if (!base || !pathAndSearch) return pathAndSearch;
    const q = pathAndSearch.indexOf("?");
    const path = q === -1 ? pathAndSearch : pathAndSearch.slice(0, q);
    const search = q === -1 ? "" : pathAndSearch.slice(q);
    if (path === base || path.indexOf(base + "/") === 0) return pathAndSearch;
    if (path.charAt(0) !== "/") return pathAndSearch;
    return base + path + search;
}
function mediaIdFromPath() {
    const m = location.pathname.match(/\/watch\/([^/]+)/);
    return m ? decodeURIComponent(m[1]) : null;
}
function resumeKey(id) {
    return "koru-media-resume:" + id;
}
function formatResumeTime(secs) {
    const t = Math.max(0, Math.floor(secs || 0));
    const m = Math.floor(t / 60);
    const s = t % 60;
    return m + ":" + (s < 10 ? "0" : "") + s;
}
function playerSnapshot() {
    const player = document.getElementById("player");
    if (!player) return null;
    return {
        node: player,
        id: player.getAttribute("data-media-id") || mediaIdFromPath(),
    };
}
function playerIdentityOk(before) {
    if (!before) return true;
    const after = document.getElementById("player");
    return !!(
        after &&
        after === before.node &&
        after.getAttribute("data-media-id") === before.id
    );
}
function showResumeUi(player, id, t) {
    const ui = document.getElementById("resume-ui");
    if (!ui || ui.getAttribute("data-bound") === "1") return;
    ui.setAttribute("data-bound", "1");
    ui.hidden = false;
    ui.textContent = "";
    const label = document.createElement("span");
    label.textContent = "Resumed from " + formatResumeTime(t) + " · ";
    const restart = document.createElement("button");
    restart.type = "button";
    restart.textContent = "Restart";
    restart.addEventListener("click", function () {
        player.currentTime = 0;
        try {
            localStorage.removeItem(resumeKey(id));
        } catch (_) {}
        ui.hidden = true;
        ui.textContent = "";
    });
    ui.appendChild(label);
    ui.appendChild(restart);
}
const main_module = {
  enhance_player_event: {
    handler(__koru_input) {
      if (typeof document === "undefined") return;

      function enhancePlayer() {
      const player = document.getElementById("player");
      if (!player) return;
      const kind = player.getAttribute("data-player") || player.tagName.toLowerCase();
      const plugins = window.KoruPlayers || {};
      if (typeof plugins[kind] === "function") {
      plugins[kind](player);
      return;
      }
      if (!("currentTime" in player)) return;
      const id = player.getAttribute("data-media-id") || mediaIdFromPath();
      if (!id) return;
      try {
      const saved = localStorage.getItem(resumeKey(id));
      if (saved) {
      const t = parseFloat(saved);
      if (!isNaN(t) && t > 2) {
      player.addEventListener(
      "loadedmetadata",
      function () {
      if (t < (player.duration || Infinity) - 1) {
      player.currentTime = t;
      showResumeUi(player, id, t);
      }
      },
      { once: true }
      );
      }
      }
      const save = function () {
      try {
      localStorage.setItem(resumeKey(id), String(player.currentTime || 0));
      } catch (_) {}
      };
      player.addEventListener("timeupdate", function () {
      if (!player._koruSaveTimer) {
      player._koruSaveTimer = setTimeout(function () {
      player._koruSaveTimer = null;
      save();
      }, 1000);
      }
      });
      player.addEventListener("pause", save);
      player.addEventListener("ended", function () {
      try {
      localStorage.removeItem(resumeKey(id));
      } catch (_) {}
      const ui = document.getElementById("resume-ui");
      if (ui) {
      ui.hidden = true;
      ui.textContent = "";
      }
      });
      window.addEventListener("pagehide", save);
      } catch (_) {}
      }

      if (document.readyState === "loading") {
      document.addEventListener("DOMContentLoaded", enhancePlayer);
      } else {
      enhancePlayer();
      }
    },
  },
  run_event: {
    handler(__koru_input) {
      const target = __koru_input.target;
      const protect = __koru_input.protect;
      const pop_prefix = __koru_input.pop_prefix;
      if (typeof document === "undefined") return;
      const defaultTarget = target;
      const protectSel = protect;
      const popPrefix = pop_prefix;

      function enhanceNavigation() {
      document.addEventListener("click", function (ev) {
      const a = ev.target.closest && ev.target.closest("a[hx-get]");
      if (!a) return;
      const url = hxGetUrl(a);
      const dest = a.getAttribute("hx-target") || defaultTarget;
      if (!url) return;
      ev.preventDefault();
      const push =
      a.getAttribute("hx-push-url") === "true"
      ? a.getAttribute("href") || url
      : null;
      fetchAndSwap(url, dest, push, a.getAttribute("href") || url, protectSel, defaultTarget);
      });

      document.addEventListener("submit", function (ev) {
      const form = ev.target.closest && ev.target.closest("form[hx-get]");
      if (!form) return;
      const url = hxGetUrl(form);
      const dest = form.getAttribute("hx-target") || defaultTarget;
      if (!url) return;
      ev.preventDefault();
      const push = form.getAttribute("hx-push-url") === "true" ? url : null;
      fetchAndSwap(url, dest, push, url, protectSel, defaultTarget);
      });

      window.addEventListener("popstate", function () {
      if (popPrefix) {
      const want =
      typeof withAppBase === "function" ? withAppBase(popPrefix) : popPrefix;
      if (
      location.pathname.indexOf(want) !== 0 &&
      location.pathname.indexOf(popPrefix) !== 0
      )
      return;
      }
      const region = document.querySelector(defaultTarget);
      if (!region) {
      location.reload();
      return;
      }
      fetchAndSwap(
      location.pathname + location.search,
      defaultTarget,
      null,
      location.href,
      protectSel,
      defaultTarget
      );
      });
      }

      if (document.readyState === "loading") {
      document.addEventListener("DOMContentLoaded", enhanceNavigation);
      } else {
      enhanceNavigation();
      }
    },
  },
  flow0() {
    main_module.enhance_player_event.handler({});
  },
  flow1() {
    main_module.run_event.handler({ target: "#library-region", protect: "#player", pop_prefix: "/library" });
  },
};
main_module.flow0();
main_module.flow1();

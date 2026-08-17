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
    const m = location.pathname.match(/\/play\/([^/.]+)/);
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
    if (typeof window !== "undefined" && typeof window.enhanceAfterSwap === "function") {
        window.enhanceAfterSwap();
    }
    if (!before) return true;
    const persist = document.getElementById("persist");
    if (persist && before.node && persist.contains(before.node)) return true;
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

      function bindResume(player, id) {
      if (!("currentTime" in player) || !id) return;
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

      function showExternal(player) {
      const box = document.querySelector(".play-external");
      if (box) {
      box.hidden = false;
      return;
      }
      if (!player || !player.getAttribute) return;
      const id = player.getAttribute("data-media-id");
      if (!id) return;
      const note = document.createElement("section");
      note.className = "play-external capability";
      note.setAttribute("data-play", "external");
      const base = appBase();
      note.innerHTML =
      "<p>This file did not play in the browser.</p><p class=\"player-bar\"><a class=\"btn\" href=\"" +
      base +
      "/media/" +
      id +
      "?download=1\">Download</a> <a class=\"btn\" rel=\"dlna\" href=\"" +
      base +
      "/play/" +
      id +
      ".m3u\">Playlist</a></p>";
      player.parentNode && player.parentNode.insertBefore(note, player.nextSibling);
      }

      function bindCanPlay(player) {
      if (!player || !player.canPlayType) return;
      const src = player.getAttribute("src") || "";
      const mime = player.getAttribute("data-mime") || "";
      let type = mime;
      if (!type && /\.mkv(\?|$)/i.test(src)) type = "video/x-matroska";
      if (type && player.canPlayType(type) === "") showExternal(player);
      player.addEventListener("error", function () {
      showExternal(player);
      });
      }

      function setNowPlaying(id, title) {
      const btn = document.getElementById("persist-max");
      const persist = document.getElementById("persist");
      if (!btn || !id) return;
      const href = withAppBase("/play/" + id);
      btn.setAttribute("data-play", href);
      if (persist) persist.setAttribute("data-play-href", href);
      btn.setAttribute("aria-label", title ? "Open full player: " + title : "Open full player");
      }

      function openFullPlayer() {
      const persist = document.getElementById("persist");
      const btn = document.getElementById("persist-max");
      const href = (btn && btn.getAttribute("data-play")) || (persist && persist.getAttribute("data-play-href"));
      if (!href) return;
      fetch(href, {
      headers: { Accept: "text/html", "HX-Request": "true", Prefer: "return=minimal" },
      })
      .then(function (r) {
      return r.text();
      })
      .then(function (html) {
      const tmp = document.createElement("div");
      tmp.innerHTML = html;
      const next = tmp.querySelector("#library-region");
      const cur = document.querySelector("#library-region");
      if (!next || !cur) {
      location.href = href;
      return;
      }
      cur.replaceWith(next);
      history.pushState({ koruHx: true }, "", href);
      if (typeof window.enhanceAfterSwap === "function") window.enhanceAfterSwap();
      })
      .catch(function () {
      location.href = href;
      });
      }

      function playingNow() {
      const player = document.getElementById("player");
      if (!player) return false;
      const persist = document.getElementById("persist");
      if (persist && persist.contains(player)) {
      return !persist.hidden && persist.getAttribute("data-dismissed") !== "1";
      }
      return true;
      }

      function clearPlayingHighlight() {
      document.querySelectorAll(".episode-list a.is-current, .episode-list a[aria-current='page']").forEach(function (el) {
      el.classList.remove("is-current");
      el.removeAttribute("aria-current");
      });
      }

      function dismissPersist() {
      const persist = document.getElementById("persist");
      if (!persist) return;
      const player = persist.querySelector("#player, video, audio");
      if (player && player.pause) player.pause();
      const inner = persist.querySelector(".persist-inner");
      if (inner) inner.textContent = "";
      persist.hidden = true;
      persist.classList.remove("persist-open");
      persist.setAttribute("data-dismissed", "1");
      clearPlayingHighlight();
      }

      function reclaimPlayer() {
      const persist = document.getElementById("persist");
      if (!persist || persist.hidden) return;
      const live = persist.querySelector("video, audio, #player");
      const frame = document.querySelector("#library-region .player-frame");
      if (!live || !frame) return;
      const stub = frame.querySelector("video, audio, #player");
      if (stub && stub !== live) stub.replaceWith(live);
      else if (!stub) frame.appendChild(live);
      persist.hidden = true;
      persist.classList.remove("persist-open");
      persist.removeAttribute("data-dismissed");
      const inner = persist.querySelector(".persist-inner");
      if (inner) inner.textContent = "";
      }

      function bindPersistChrome() {
      const close = document.getElementById("persist-close");
      if (close && close.getAttribute("data-bound") !== "1") {
      close.setAttribute("data-bound", "1");
      close.addEventListener("click", function () {
      dismissPersist();
      });
      }
      const max = document.getElementById("persist-max");
      if (max && max.getAttribute("data-bound") !== "1") {
      max.setAttribute("data-bound", "1");
      max.addEventListener("click", function () {
      openFullPlayer();
      });
      }
      }

      function currentTitle() {
      const h = document.querySelector(".content h1, h1");
      return h ? h.textContent.trim() : "";
      }

      function setKino(on) {
      const layout = document.querySelector(".layout");
      document.documentElement.classList.toggle("kino", !!on);
      if (layout) layout.classList.toggle("kino", !!on);
      const btn = document.getElementById("kino-toggle");
      if (btn) btn.setAttribute("aria-pressed", on ? "true" : "false");
      }

      function popOutToPersist() {
      const persist = document.getElementById("persist");
      const player = document.getElementById("player");
      if (!persist || !player) return;
      if (persist.getAttribute("data-dismissed") === "1") return;
      const id = player.getAttribute("data-media-id");
      const title = currentTitle();
      if (persist.contains(player)) {
      persist.hidden = false;
      persist.classList.add("persist-open");
      setKino(false);
      const layout = document.querySelector(".layout");
      if (layout) layout.classList.remove("home", "play");
      setNowPlaying(id, title);
      return;
      }
      const inner = persist.querySelector(".persist-inner") || persist;
      inner.textContent = "";
      inner.appendChild(player);
      persist.hidden = false;
      persist.classList.add("persist-open");
      setKino(false);
      const layout = document.querySelector(".layout");
      if (layout) layout.classList.remove("home", "play");
      setNowPlaying(id, title);
      }

      function popPersist(id, kind) {
      const persist = document.getElementById("persist");
      if (!persist) {
      location.href = withAppBase("/play/" + id);
      return;
      }
      persist.hidden = false;
      persist.classList.add("persist-open");
      const existing = document.getElementById("player");
      if (existing && existing.getAttribute("data-media-id") === id) {
      if (!persist.contains(existing)) popOutToPersist();
      if (existing.play) existing.play().catch(function () {
      showExternal(existing);
      });
      setKino(false);
      setNowPlaying(id, currentTitle());
      return;
      }
      const inner = persist.querySelector(".persist-inner") || persist;
      const tag = kind === "audio" ? "audio" : "video";
      inner.innerHTML =
      "<" +
      tag +
      " id=\"player\" data-player=\"" +
      tag +
      "\" data-media-id=\"" +
      id +
      "\" controls src=\"" +
      appBase() +
      "/media/" +
      id +
      "\"></" +
      tag +
      ">";
      const player = document.getElementById("player");
      bindResume(player, id);
      bindCanPlay(player);
      if (player && player.play) player.play().catch(function () {
      showExternal(player);
      });
      setKino(false);
      setNowPlaying(id, currentTitle());
      }

      function bindEditionSelect() {
      document.querySelectorAll("select.edition-select").forEach(function (sel) {
      if (sel.getAttribute("data-bound") === "1") return;
      sel.setAttribute("data-bound", "1");
      sel.addEventListener("change", function () {
      if (sel.value) location.href = sel.value;
      });
      });
      }

      function inPageVideoPlayer() {
      const persist = document.getElementById("persist");
      const player = document.getElementById("player");
      return !!(player && player.tagName === "VIDEO" && persist && !persist.contains(player));
      }

      function bindKinoToggle() {
      const btn = document.getElementById("kino-toggle");
      if (!btn || btn.getAttribute("data-bound") === "1") return;
      btn.setAttribute("data-bound", "1");
      btn.addEventListener("click", function () {
      const layout = document.querySelector(".layout");
      const on = !(layout && layout.classList.contains("kino"));
      setKino(on);
      });
      }

      function enhanceHero() {
      const carousel = document.querySelector(".hero-carousel");
      const slides = carousel ? carousel.querySelectorAll("[data-hero-slide]") : [];
      if (carousel && slides.length && carousel.getAttribute("data-bound") !== "1") {
      carousel.setAttribute("data-bound", "1");
      let i = 0;
      function show(n) {
      i = (n + slides.length) % slides.length;
      slides.forEach(function (s, idx) {
      s.classList.toggle("hero-active", idx === i);
      const v = s.querySelector("video.hero-teaser");
      if (v) {
      if (idx === i) {
      window.setTimeout(function () {
      if (s.classList.contains("hero-active") && v.play) v.play().catch(function () {});
      }, 700);
      } else if (v.pause) v.pause();
      }
      });
      }
      show(0);
      const prev = carousel.querySelector(".hero-prev");
      const next = carousel.querySelector(".hero-next");
      if (prev) prev.addEventListener("click", function () { show(i - 1); });
      if (next) next.addEventListener("click", function () { show(i + 1); });
      }
      document.querySelectorAll(".hero-teaser[data-src]").forEach(function (teaser) {
      if (teaser.getAttribute("src")) return;
      const src = teaser.getAttribute("data-src");
      if (src) teaser.setAttribute("src", src);
      });
      document.querySelectorAll(".hero-teaser[data-youtube]").forEach(function (box) {
      if (box.getAttribute("data-bound") === "1") return;
      box.setAttribute("data-bound", "1");
      const key = box.getAttribute("data-youtube");
      if (!key) return;
      const iframe = document.createElement("iframe");
      iframe.className = "hero-teaser";
      iframe.setAttribute("src", "https://www.youtube.com/embed/" + key + "?autoplay=1&mute=1&controls=0&loop=1&playlist=" + key);
      iframe.setAttribute("allow", "autoplay; encrypted-media");
      iframe.setAttribute("title", "Trailer");
      box.appendChild(iframe);
      });
      }

      function pathOnly(href) {
      const base = appBase();
      let p = href || "";
      try {
      p = new URL(href, location.href).pathname;
      } catch (_) {}
      if (base && p.indexOf(base) === 0) p = p.slice(base.length) || "/";
      if (p.length > 1 && p.charAt(p.length - 1) === "/") p = p.slice(0, -1);
      return p || "/";
      }

      function syncNav() {
      const p = pathOnly(location.pathname);
      let kindHint = "";
      const more = document.querySelector("#library-region a[href*='/library/']");
      if (more && (p.indexOf("/item/") === 0 || p.indexOf("/play/") === 0)) {
      kindHint = pathOnly(more.getAttribute("href"));
      }
      document.querySelectorAll(".sidebar-nav .nav-item").forEach(function (a) {
      const href = pathOnly(a.getAttribute("href"));
      let on = false;
      if (href === "/") on = p === "/";
      else if (href === "/settings") on = p.indexOf("/settings") === 0;
      else if (href === "/library") on = p === "/library";
      else if (href.indexOf("/library/") === 0) {
      on = p === href || p.indexOf(href + "/") === 0 || kindHint === href;
      }
      a.classList.toggle("active", !!on);
      });
      }

      function enhanceAfterSwap() {
      reclaimPlayer();
      enhanceHero();
      bindKinoToggle();
      bindEditionSelect();
      bindPersistChrome();
      syncNav();
      const layout = document.querySelector(".layout");
      const content = document.querySelector(".content");
      const home = !!document.querySelector(".hero-carousel");
      const watching = inPageVideoPlayer();
      if (layout) {
      if (home) layout.classList.add("home");
      else layout.classList.remove("home");
      if (watching) layout.classList.add("play");
      else {
      layout.classList.remove("play");
      setKino(false);
      }
      }
      if (content) content.classList.toggle("content-home", home);
      const persist = document.getElementById("persist");
      if (watching && persist) persist.removeAttribute("data-dismissed");
      const docked = persist && persist.querySelector("#player");
      if (docked && persist && !persist.hidden) {
      setNowPlaying(docked.getAttribute("data-media-id"), currentTitle());
      }
      if (!playingNow()) clearPlayingHighlight();
      }
      window.enhanceAfterSwap = enhanceAfterSwap;
      window.popOutToPersist = popOutToPersist;

      function browsePath(pathname) {
      const base = appBase();
      let p = pathname || "";
      if (base && p.indexOf(base) === 0) p = p.slice(base.length) || "/";
      if (p === "" || p === "/") return true;
      if (p.indexOf("/library") === 0) return true;
      if (p.indexOf("/item/") === 0) return true;
      if (p.indexOf("/settings") === 0) return true;
      return false;
      }

      function enhancePlayer() {
      const player = document.getElementById("player");
      if (player) {
      const kind = player.getAttribute("data-player") || player.tagName.toLowerCase();
      const plugins = window.KoruPlayers || {};
      if (typeof plugins[kind] === "function") {
      plugins[kind](player);
      } else {
      const id = player.getAttribute("data-media-id") || mediaIdFromPath();
      bindResume(player, id);
      bindCanPlay(player);
      }
      }
      enhanceAfterSwap();
      window.addEventListener("popstate", function () {
      enhanceAfterSwap();
      });
      document.addEventListener(
      "click",
      function (ev) {
      const a = ev.target.closest && ev.target.closest("a[hx-get], a.nav-item, a.poster-link, a.hero-item-link");
      if (!a || a.id === "persist-max" || a.classList.contains("persist-max")) return;
      let path = "";
      try {
      path = new URL(a.href, location.href).pathname;
      } catch (_) {
      return;
      }
      if (browsePath(path)) popOutToPersist();
      },
      true
      );
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
      const form = ev.target.closest && ev.target.closest("form[hx-get], form[hx-post]");
      if (!form) return;
      const dest = form.getAttribute("hx-target") || defaultTarget;
      const isPost = form.hasAttribute("hx-post");
      if (isPost && !form.getAttribute("hx-target")) return;
      const url = isPost
      ? (typeof withAppBase === "function"
      ? withAppBase(form.getAttribute("hx-post") || form.getAttribute("action") || "")
      : form.getAttribute("hx-post") || form.getAttribute("action"))
      : hxGetUrl(form);
      if (!url) return;
      ev.preventDefault();
      if (isPost) {
      const fd = new FormData(form);
      fetch(url, {
      method: "POST",
      headers: fragmentHeaders(),
      body: new URLSearchParams(fd),
      })
      .then(function (r) {
      return r.text();
      })
      .then(function (html) {
      if (!swapInto(dest, html, null, protectSel, defaultTarget)) {
      location.href = url;
      }
      })
      .catch(function () {
      location.href = url;
      });
      return;
      }
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
    main_module.run_event.handler({ target: "#library-region", protect: "#persist", pop_prefix: "/" });
  },
};
main_module.flow0();
main_module.flow1();

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
      const titleEl = document.querySelector(".play-title, .item-faded-title, h1");
      const artEl = document.querySelector(".item-hero-art img, .hero-poster, #player");
      saveContinueEntry(
      id,
      titleEl ? titleEl.textContent.trim() : "",
      artEl && artEl.getAttribute ? artEl.getAttribute("src") || artEl.getAttribute("poster") || "" : "",
      player.currentTime || 0,
      player.duration || 0
      );
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
      dropContinue(id);
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

      function popPersist(id, kind, title) {
      const persist = document.getElementById("persist");
      if (!persist) {
      location.href = withAppBase("/play/" + id);
      return;
      }
      persist.removeAttribute("data-dismissed");
      persist.hidden = false;
      persist.classList.add("persist-open");
      const existing = document.getElementById("player");
      if (existing && existing.getAttribute("data-media-id") === id) {
      if (!persist.contains(existing)) popOutToPersist();
      if (existing.play) existing.play().catch(function () {
      showExternal(existing);
      });
      setKino(false);
      setNowPlaying(id, title || currentTitle());
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
      setNowPlaying(id, title || currentTitle());
      const max = document.getElementById("persist-max");
      if (max) max.hidden = tag === "audio";
      }

      function bindMusicPlay() {
      document.querySelectorAll("a.music-play").forEach(function (a) {
      if (a.getAttribute("data-bound") === "1") return;
      a.setAttribute("data-bound", "1");
      a.addEventListener("click", function (ev) {
      ev.preventDefault();
      ev.stopPropagation();
      const id = a.getAttribute("data-media-id");
      if (!id) return;
      const row = a.closest(".music-row");
      const titleEl = row ? row.querySelector(".music-title") : null;
      popPersist(id, a.getAttribute("data-player") || "audio", titleEl ? titleEl.textContent.trim() : "");
      });
      });
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
      const dots = carousel.querySelectorAll("[data-hero-dot]");
      let timer = 0;
      function clearHeroTimer() {
      if (timer) window.clearTimeout(timer);
      timer = 0;
      }
      function show(n) {
      i = (n + slides.length) % slides.length;
      clearHeroTimer();
      slides.forEach(function (s, idx) {
      s.classList.toggle("hero-active", idx === i);
      const v = s.querySelector("video.hero-teaser");
      if (v) {
      v.onended = null;
      if (idx === i) {
      window.setTimeout(function () {
      if (s.classList.contains("hero-active") && v.play) v.play().catch(function () {});
      }, 400);
      } else if (v.pause) {
      v.pause();
      try {
      v.currentTime = 0;
      } catch (_) {}
      }
      }
      });
      dots.forEach(function (d, idx) {
      d.classList.toggle("is-active", idx === i);
      });
      if (slides.length < 2) return;
      const active = slides[i];
      const teaser = active.querySelector("video.hero-teaser");
      let waitMs = 7000;
      if (teaser) {
      teaser.onended = function () {
      show(i + 1);
      };
      waitMs = 30000;
      }
      timer = window.setTimeout(function () {
      show(i + 1);
      }, waitMs);
      }
      show(0);
      dots.forEach(function (d) {
      d.addEventListener("click", function () {
      const n = parseInt(d.getAttribute("data-hero-dot") || "0", 10);
      if (!isNaN(n)) show(n);
      });
      });
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

      function heartKey() {
      return "medushu-hearts";
      }

      function loadHearts() {
      try {
      const raw = localStorage.getItem(heartKey());
      const parsed = raw ? JSON.parse(raw) : [];
      return Array.isArray(parsed) ? parsed : [];
      } catch (_) {
      return [];
      }
      }

      function saveHearts(list) {
      try {
      localStorage.setItem(heartKey(), JSON.stringify(list));
      } catch (_) {}
      }

      function isHearted(id) {
      return loadHearts().some(function (h) {
      return h && h.id === id;
      });
      }

      function heartMeta(btn) {
      const id = btn.getAttribute("data-heart");
      if (!id) return null;
      const slide = btn.closest("[data-hero-slide], .item, .music-row, .poster-card");
      let title = "";
      let art = "";
      let kind = "";
      let year = "";
      if (slide) {
      const t = slide.querySelector(".hero-faded-title, .item-faded-title, .music-title, .poster-title, h1");
      if (t) title = t.textContent.trim();
      const img = slide.querySelector(".hero-poster, .item-hero-art img, .music-art img, .poster-frame img");
      if (img) art = img.getAttribute("src") || "";
      const yearEl = slide.querySelector(".hero-meta, .poster-year");
      if (yearEl) year = (yearEl.textContent || "").trim();
      }
      const card = btn.closest(".poster-card, .music-row");
      if (card && card.getAttribute("data-heart-id")) {
      /* keep */
      }
      return { id: id, title: title, art: art, kind: kind, year: year };
      }

      function syncHeartButtons() {
      document.querySelectorAll("[data-heart]").forEach(function (btn) {
      const on = isHearted(btn.getAttribute("data-heart"));
      btn.setAttribute("aria-pressed", on ? "true" : "false");
      const row = btn.closest(".poster-card, .music-row");
      if (row) row.classList.toggle("is-fave", on);
      });
      document.querySelectorAll("[data-heart-id]").forEach(function (card) {
      card.classList.toggle("is-fave", isHearted(card.getAttribute("data-heart-id")));
      });
      }

      function bindHearts() {
      document.querySelectorAll("[data-heart]").forEach(function (btn) {
      if (btn.getAttribute("data-bound") === "1") return;
      btn.setAttribute("data-bound", "1");
      btn.addEventListener("click", function () {
      const meta = heartMeta(btn);
      if (!meta) return;
      let list = loadHearts();
      if (isHearted(meta.id)) {
      list = list.filter(function (h) {
      return h.id !== meta.id;
      });
      } else {
      list.push(meta);
      }
      saveHearts(list);
      syncHeartButtons();
      renderFavourites();
      });
      });
      syncHeartButtons();
      document.querySelectorAll("[data-open-fav]").forEach(function (a) {
      if (a.getAttribute("data-bound") === "1") return;
      a.setAttribute("data-bound", "1");
      a.addEventListener("click", function () {
      try {
      sessionStorage.setItem("medushu-fav-only", "1");
      } catch (_) {}
      });
      });
      document.querySelectorAll(".kind-chip").forEach(function (chip) {
      if (chip.getAttribute("data-fav-clear") === "1") return;
      chip.setAttribute("data-fav-clear", "1");
      chip.addEventListener("click", function () {
      try {
      sessionStorage.setItem("medushu-fav-only", "0");
      } catch (_) {}
      });
      });
      document.querySelectorAll("[data-filter-fav]").forEach(function (chip) {
      if (chip.getAttribute("data-bound") === "1") return;
      chip.setAttribute("data-bound", "1");
      chip.addEventListener("click", function () {
      const list = document.getElementById("library-list");
      if (!list) return;
      const on = !list.classList.contains("fav-only");
      setFavOnly(on);
      });
      });
      applyFavFilter();
      }

      function favOnlyWanted() {
      try {
      const stored = sessionStorage.getItem("medushu-fav-only");
      if (stored === "1") return true;
      if (stored === "0") return false;
      } catch (_) {}
      try {
      if (new URL(location.href).searchParams.get("fav") === "1") return true;
      if (pathOnly(location.pathname) === "/favourites") return true;
      } catch (_) {}
      return false;
      }

      function setFavOnly(on) {
      const list = document.getElementById("library-list");
      const chip = document.querySelector("[data-filter-fav]");
      const kind = chip && chip.closest(".kind-chips")
      ? chip.closest(".kind-chips").querySelector(".kind-chip")
      : null;
      if (list) list.classList.toggle("fav-only", on);
      if (chip) {
      chip.setAttribute("aria-pressed", on ? "true" : "false");
      chip.classList.toggle("is-active", on);
      }
      if (kind) kind.classList.toggle("is-active", !on);
      try {
      sessionStorage.setItem("medushu-fav-only", on ? "1" : "0");
      } catch (_) {}
      }

      function applyFavFilter() {
      if (!document.getElementById("library-list")) return;
      if (!document.querySelector("[data-filter-fav]")) return;
      setFavOnly(favOnlyWanted());
      }

      function renderFavourites() {
      const list = document.getElementById("favourites-list");
      if (!list) return;
      const empty = document.querySelector(".favourites-empty");
      const hearts = loadHearts();
      list.textContent = "";
      hearts.forEach(function (h) {
      if (!h || !h.id) return;
      const li = document.createElement("li");
      li.className = "poster-card is-fave";
      const a = document.createElement("a");
      a.className = "poster-link";
      a.href = withAppBase("/item/" + h.id);
      a.setAttribute("hx-get", a.href);
      a.setAttribute("hx-target", "#library-region");
      a.setAttribute("hx-swap", "outerHTML");
      a.setAttribute("hx-push-url", "true");
      const frame = document.createElement("span");
      frame.className = "poster-frame";
      if (h.art) {
      const img = document.createElement("img");
      img.src = h.art;
      img.alt = h.title || "";
      frame.appendChild(img);
      }
      a.appendChild(frame);
      const cap = document.createElement("span");
      cap.className = "poster-caption";
      const t = document.createElement("span");
      t.className = "poster-title";
      t.textContent = h.title || h.id;
      cap.appendChild(t);
      a.appendChild(cap);
      li.appendChild(a);
      list.appendChild(li);
      });
      if (empty) empty.hidden = hearts.length > 0;
      }

      function continueKey() {
      return "medushu-continue";
      }

      function loadContinue() {
      let list = [];
      try {
      const raw = localStorage.getItem(continueKey());
      const parsed = raw ? JSON.parse(raw) : [];
      if (Array.isArray(parsed)) list = parsed.filter(function (c) {
      return c && c.id;
      });
      } catch (_) {}
      try {
      for (let n = 0; n < localStorage.length; n++) {
      const k = localStorage.key(n);
      if (!k || k.indexOf("koru-media-resume:") !== 0) continue;
      const id = k.slice("koru-media-resume:".length);
      const t = parseFloat(localStorage.getItem(k));
      if (!id || !(t > 2)) continue;
      if (!list.some(function (c) {
      return c.id === id;
      })) {
      list.push({ id: id, title: "", art: "", t: t, duration: 0 });
      }
      }
      } catch (_) {}
      return list;
      }

      function saveContinueEntry(id, title, art, t, duration) {
      if (!id || !(t > 2)) return;
      let list = loadContinue().filter(function (c) {
      return c && c.id !== id;
      });
      list.unshift({ id: id, title: title || "", art: art || "", t: t, duration: duration || 0 });
      if (list.length > 12) list = list.slice(0, 12);
      try {
      localStorage.setItem(continueKey(), JSON.stringify(list));
      } catch (_) {}
      }

      function dropContinue(id) {
      if (!id) return;
      const list = loadContinue().filter(function (c) {
      return c && c.id !== id;
      });
      try {
      localStorage.setItem(continueKey(), JSON.stringify(list));
      } catch (_) {}
      }

      function renderContinue() {
      const box = document.querySelector("[data-continue]");
      const list = document.getElementById("continue-list");
      if (!box || !list) return;
      const items = loadContinue();
      list.textContent = "";
      if (!items.length) {
      box.hidden = true;
      return;
      }
      items.forEach(function (c) {
      if (!c || !c.id) return;
      const li = document.createElement("li");
      li.className = "resume-card";
      const a = document.createElement("a");
      a.className = "resume-link";
      a.href = withAppBase("/play/" + c.id);
      const frame = document.createElement("span");
      frame.className = "resume-frame";
      if (c.art) {
      const img = document.createElement("img");
      img.src = c.art;
      img.alt = c.title || "";
      frame.appendChild(img);
      }
      const pct = c.duration > 0 ? Math.min(100, Math.round((c.t / c.duration) * 100)) : 8;
      const bar = document.createElement("span");
      bar.className = "resume-progress";
      const fill = document.createElement("span");
      fill.style.width = pct + "%";
      bar.appendChild(fill);
      frame.appendChild(bar);
      const play = document.createElement("span");
      play.className = "resume-play";
      play.setAttribute("aria-hidden", "true");
      frame.appendChild(play);
      a.appendChild(frame);
      const title = document.createElement("span");
      title.className = "resume-title";
      title.textContent = c.title || c.id;
      a.appendChild(title);
      li.appendChild(a);
      list.appendChild(li);
      });
      box.hidden = false;
      }

      function bindNavDrawer() {
      const btn = document.getElementById("nav-toggle");
      const layout = document.querySelector(".layout");
      const scrim = document.getElementById("nav-scrim");
      if (!btn || !layout) return;
      if (btn.getAttribute("data-bound") === "1") return;
      btn.setAttribute("data-bound", "1");
      function isNarrow() {
      return window.matchMedia("(max-width: 60rem)").matches;
      }
      function sidebarVisible() {
      if (isNarrow()) return layout.classList.contains("nav-open");
      return !layout.classList.contains("nav-collapsed");
      }
      function placeNavToggle() {
      const head = document.querySelector(".sidebar-head");
      const topbar = document.querySelector(".topbar");
      if (!btn || !head || !topbar) return;
      if (sidebarVisible()) {
      if (btn.parentElement !== head) head.appendChild(btn);
      return;
      }
      const logo = topbar.querySelector(".topbar-logo");
      if (logo) {
      if (btn.parentElement !== topbar || btn.nextElementSibling !== logo) {
      topbar.insertBefore(btn, logo);
      }
      } else if (btn.parentElement !== topbar) {
      topbar.insertBefore(btn, topbar.firstChild);
      }
      }
      function setSidebar(on) {
      if (isNarrow()) {
      layout.classList.toggle("nav-open", on);
      layout.classList.remove("nav-collapsed");
      if (scrim) {
      scrim.hidden = !on;
      scrim.setAttribute("aria-hidden", on ? "false" : "true");
      }
      } else {
      layout.classList.toggle("nav-collapsed", !on);
      layout.classList.remove("nav-open");
      if (scrim) {
      scrim.hidden = true;
      scrim.setAttribute("aria-hidden", "true");
      }
      }
      btn.setAttribute("aria-expanded", on ? "true" : "false");
      placeNavToggle();
      }
      setSidebar(sidebarVisible());
      btn.addEventListener("click", function () {
      setSidebar(!sidebarVisible());
      });
      if (scrim) {
      scrim.addEventListener("click", function () {
      setSidebar(false);
      });
      }
      document.querySelectorAll(".sidebar-nav .nav-item").forEach(function (a) {
      a.addEventListener("click", function () {
      if (isNarrow()) setSidebar(false);
      });
      });
      try {
      window.matchMedia("(max-width: 60rem)").addEventListener("change", function () {
      setSidebar(sidebarVisible());
      });
      } catch (_) {}
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
      else if (href === "/library") on = p === "/library" || p.indexOf("/favourites") === 0;
      else if (href.indexOf("/library/") === 0) {
      on = p === href || p.indexOf(href + "/") === 0 || kindHint === href;
      }
      a.classList.toggle("active", !!on);
      });
      }

      function placeTopbarBack() {
      const slot = document.getElementById("topbar-back");
      if (!slot) return;
      const src = document.querySelector("#library-region [data-topbar-back]");
      slot.replaceChildren();
      if (!src) {
      slot.hidden = true;
      return;
      }
      const link = src.cloneNode(true);
      link.removeAttribute("data-topbar-back");
      slot.appendChild(link);
      slot.hidden = false;
      }

      function bindKindMenus() {
      document.querySelectorAll("details.kind-menu").forEach(function (menu) {
      if (menu.getAttribute("data-bound") === "1") return;
      menu.setAttribute("data-bound", "1");
      menu.addEventListener("toggle", function () {
      if (!menu.open) return;
      const root = menu.closest(".kind-actions") || document;
      root.querySelectorAll("details.kind-menu").forEach(function (other) {
      if (other !== menu) other.open = false;
      });
      });
      });
      }

      function syncTopbarSearch() {
      const input = document.querySelector(".topbar-search input[type='search']");
      if (!input) return;
      const onSearch = !!document.querySelector("[data-search-page]");
      let q = "";
      try {
      q = new URL(location.href).searchParams.get("q") || "";
      } catch (_) {}
      if (onSearch && document.activeElement !== input) input.value = q;
      if (onSearch && document.querySelector(".search-idle")) {
      try {
      input.focus();
      } catch (_) {}
      }
      }

      function enhanceAfterSwap() {
      reclaimPlayer();
      enhanceHero();
      bindKinoToggle();
      bindEditionSelect();
      bindPersistChrome();
      bindNavDrawer();
      bindHearts();
      bindKindMenus();
      bindMusicPlay();
      renderFavourites();
      renderContinue();
      syncNav();
      placeTopbarBack();
      syncTopbarSearch();
      const layout = document.querySelector(".layout");
      const content = document.querySelector(".content");
      const home = !!document.querySelector(".hero-carousel");
      const item = !!document.querySelector(".item-hero");
      const searching = !!document.querySelector("[data-search-page]");
      const watching = inPageVideoPlayer();
      if (layout) {
      layout.classList.toggle("home", home);
      layout.classList.toggle("item-page", item);
      layout.classList.toggle("search", searching);
      if (watching) layout.classList.add("play");
      else {
      if (layout && layout.classList.contains("play")) setKino(false);
      if (layout) layout.classList.remove("play");
      }
      }
      if (content) {
      content.classList.toggle("content-home", home);
      content.classList.toggle("content-item", item);
      content.classList.toggle("content-search", searching);
      }
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
      if (p.indexOf("/search") === 0) return true;
      if (p.indexOf("/favourites") === 0) return true;
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

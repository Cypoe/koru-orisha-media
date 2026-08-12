/*! koru-orisha-media progressive enhancement (optional).
 * HTMX-dialect host: honors hx-get / hx-target / hx-swap / hx-push-url.
 * Sends HX-Request (and Prefer) so /library can return a fragment.
 * Swaps only #library-region (list+pagination). Refuses targets that own #player.
 * Measures swap cost lightly (performance marks) before expanding koru/dom.
 * No-JS browsers keep plain href/forms.
 *
 * This is the vaxis/dom lesson applied to navigation: declare the request on
 * the element; the host loop does the work. Stock HTMX can replace this file.
 */
(function () {
  "use strict";

  var DEFAULT_TARGET = "#library-region";

  function mediaIdFromPath() {
    var m = location.pathname.match(/^\/watch\/([^/]+)/);
    return m ? decodeURIComponent(m[1]) : null;
  }

  function resumeKey(id) {
    return "koru-media-resume:" + id;
  }

  function enhancePlayer() {
    var player = document.getElementById("player");
    if (!player) return;
    var id = player.getAttribute("data-media-id") || mediaIdFromPath();
    if (!id) return;
    try {
      var saved = localStorage.getItem(resumeKey(id));
      if (saved) {
        var t = parseFloat(saved);
        if (!isNaN(t) && t > 0) {
          player.addEventListener(
            "loadedmetadata",
            function () {
              if (t < (player.duration || Infinity) - 1) player.currentTime = t;
            },
            { once: true }
          );
        }
      }
      var save = function () {
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
      window.addEventListener("pagehide", save);
    } catch (_) {}
  }

  function hxHeaders() {
    return {
      Accept: "text/html",
      "HX-Request": "true",
      Prefer: "return=minimal",
    };
  }

  /** Refuse swaps that would destroy or replace the playing media element. */
  function isSafeSwapTarget(sel) {
    if (!sel || sel === "#player" || sel === "player" || sel === "body" || sel === "html") {
      return false;
    }
    var el = document.querySelector(sel);
    if (!el) return false;
    if (el.id === "player") return false;
    if (el.querySelector && el.querySelector("#player")) return false;
    return true;
  }

  function playerSnapshot() {
    var player = document.getElementById("player");
    if (!player) return null;
    return {
      node: player,
      id: player.getAttribute("data-media-id") || mediaIdFromPath(),
    };
  }

  function playerIdentityOk(before) {
    if (!before) return true;
    var after = document.getElementById("player");
    return !!(
      after &&
      after === before.node &&
      after.getAttribute("data-media-id") === before.id
    );
  }

  function swapInto(targetSel, html, pushUrl) {
    if (!isSafeSwapTarget(targetSel)) return false;
    var before = playerSnapshot();
    var mark = "koru-hx-swap";
    try {
      if (window.performance && performance.mark) performance.mark(mark + "-start");
    } catch (_) {}

    var tmp = document.createElement("div");
    tmp.innerHTML = html;
    var next =
      tmp.querySelector(targetSel) ||
      tmp.querySelector("#library-region") ||
      tmp.querySelector("ul");
    if (!next) return false;
    var cur = document.querySelector(targetSel);
    if (!cur) return false;
    cur.replaceWith(next);
    if (pushUrl) history.pushState({ koruHx: true }, "", pushUrl);

    try {
      if (window.performance && performance.mark && performance.measure) {
        performance.mark(mark + "-end");
        performance.measure(mark, mark + "-start", mark + "-end");
      }
    } catch (_) {}

    if (!playerIdentityOk(before)) return false;
    return true;
  }

  function hxGetUrl(el) {
    var raw = el.getAttribute("hx-get");
    if (!raw) return null;
    try {
      var u = new URL(raw, location.href);
      if (el.tagName === "FORM") {
        var fd = new FormData(el);
        fd.forEach(function (v, k) {
          u.searchParams.set(k, String(v));
        });
      }
      return u.pathname + u.search;
    } catch (_) {
      return raw;
    }
  }

  function fetchAndSwap(url, target, pushUrl, fallbackUrl) {
    if (!isSafeSwapTarget(target)) {
      location.href = fallbackUrl || url;
      return;
    }
    fetch(url, { headers: hxHeaders() })
      .then(function (r) {
        return r.text();
      })
      .then(function (html) {
        if (!swapInto(target, html, pushUrl)) location.href = fallbackUrl || url;
      })
      .catch(function () {
        location.href = fallbackUrl || url;
      });
  }

  function enhanceHtmx() {
    document.addEventListener("click", function (ev) {
      var a = ev.target.closest && ev.target.closest("a[hx-get]");
      if (!a) return;
      var url = hxGetUrl(a);
      var target = a.getAttribute("hx-target") || DEFAULT_TARGET;
      if (!url) return;
      ev.preventDefault();
      var push =
        a.getAttribute("hx-push-url") === "true"
          ? a.getAttribute("href") || url
          : null;
      fetchAndSwap(url, target, push, a.getAttribute("href") || url);
    });

    document.addEventListener("submit", function (ev) {
      var form = ev.target.closest && ev.target.closest("form[hx-get]");
      if (!form) return;
      var url = hxGetUrl(form);
      var target = form.getAttribute("hx-target") || DEFAULT_TARGET;
      if (!url) return;
      ev.preventDefault();
      var push = form.getAttribute("hx-push-url") === "true" ? url : null;
      fetchAndSwap(url, target, push, url);
    });

    window.addEventListener("popstate", function () {
      if (!/^\/library(\/|$)/.test(location.pathname)) return;
      var region = document.querySelector(DEFAULT_TARGET);
      if (!region) {
        location.reload();
        return;
      }
      fetchAndSwap(location.pathname + location.search, DEFAULT_TARGET, null, location.href);
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", function () {
      enhancePlayer();
      enhanceHtmx();
    });
  } else {
    enhancePlayer();
    enhanceHtmx();
  }
})();

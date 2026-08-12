/*! koru-orisha-media progressive enhancement (optional).
 * HTMX-dialect host: honors hx-get / hx-target / hx-swap / hx-push-url.
 * Sends HX-Request (and Prefer) so /library can return a fragment.
 * Does not touch #player on swaps. No-JS browsers keep plain href/forms.
 *
 * This is the vaxis/dom lesson applied to navigation: declare the request on
 * the element; the host loop does the work. Stock HTMX can replace this file.
 */
(function () {
  "use strict";

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

  function swapInto(targetSel, html, pushUrl) {
    var tmp = document.createElement("div");
    tmp.innerHTML = html;
    var next = tmp.querySelector(targetSel) || tmp.querySelector("ul");
    if (!next) return false;
    var cur = document.querySelector(targetSel);
    if (!cur) return false;
    cur.replaceWith(next);
    if (pushUrl) history.pushState({}, "", pushUrl);
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

  function enhanceHtmx() {
    document.addEventListener("click", function (ev) {
      var a = ev.target.closest && ev.target.closest("a[hx-get]");
      if (!a) return;
      var url = hxGetUrl(a);
      var target = a.getAttribute("hx-target") || "#library-list";
      if (!url) return;
      ev.preventDefault();
      fetch(url, { headers: hxHeaders() })
        .then(function (r) {
          return r.text();
        })
        .then(function (html) {
          var push =
            a.getAttribute("hx-push-url") === "true"
              ? a.getAttribute("href") || url
              : null;
          if (!swapInto(target, html, push)) location.href = a.getAttribute("href") || url;
        })
        .catch(function () {
          location.href = a.getAttribute("href") || url;
        });
    });

    document.addEventListener("submit", function (ev) {
      var form = ev.target.closest && ev.target.closest("form[hx-get]");
      if (!form) return;
      var url = hxGetUrl(form);
      var target = form.getAttribute("hx-target") || "#library-list";
      if (!url) return;
      ev.preventDefault();
      fetch(url, { headers: hxHeaders() })
        .then(function (r) {
          return r.text();
        })
        .then(function (html) {
          var push = form.getAttribute("hx-push-url") === "true" ? url : null;
          if (!swapInto(target, html, push)) location.href = url;
        })
        .catch(function () {
          location.href = url;
        });
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

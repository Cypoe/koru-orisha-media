/*! koru-orisha-media progressive enhancement (optional).
 * No-JS browsers keep full-page links. Does not touch #player on fragment swaps.
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

  function fragmentUrlFromLink(a) {
    var href = a.getAttribute("href");
    if (!href) return null;
    try {
      var u = new URL(href, location.origin);
      if (u.pathname.indexOf("/library") !== 0) return null;
      var frag = "/fragments" + u.pathname.replace(/^\/library/, "/library");
      // /library -> /fragments/library ; /library/movie -> /fragments/library/movie
      if (u.pathname === "/library" || u.pathname === "/library/") frag = "/fragments/library";
      else if (u.pathname.indexOf("/library/") === 0)
        frag = "/fragments/library/" + u.pathname.slice("/library/".length);
      return frag + u.search;
    } catch (_) {
      return null;
    }
  }

  function enhanceLibrary() {
    var list = document.getElementById("library-list");
    if (!list) return;
    document.addEventListener("click", function (ev) {
      var a = ev.target.closest && ev.target.closest("a[data-enhance=fragment]");
      if (!a) return;
      var frag = fragmentUrlFromLink(a);
      if (!frag) return;
      ev.preventDefault();
      fetch(frag, { headers: { Accept: "text/html", Prefer: "return=minimal" } })
        .then(function (r) {
          return r.text();
        })
        .then(function (html) {
          // Response may be full HTTP if mis-parsed; prefer inner ul
          var tmp = document.createElement("div");
          tmp.innerHTML = html;
          var ul = tmp.querySelector("#library-list") || tmp.querySelector("ul");
          if (!ul) return;
          var target = document.getElementById("library-list");
          if (!target) return;
          target.replaceWith(ul);
          history.pushState({}, "", a.getAttribute("href"));
        })
        .catch(function () {
          location.href = a.getAttribute("href");
        });
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", function () {
      enhancePlayer();
      enhanceLibrary();
    });
  } else {
    enhancePlayer();
    enhanceLibrary();
  }
})();

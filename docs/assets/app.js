/* Taskmarket Live — client side: range switches, relative times.
   All numbers are rendered into the HTML at build time, including the
   Pulse money-flow diagram (server-rendered SVG); this script only
   switches between pre-rendered ranges. No network calls,
   no tracking, no wallet. */
(function () {
  "use strict";

  /* Range switches: each .chart holds one svg per range in divs
     [data-range]; buttons toggle which is visible. */
  document.querySelectorAll(".switch").forEach(function (sw) {
    var target = document.getElementById(sw.getAttribute("data-target"));
    if (!target) return;
    sw.addEventListener("click", function (ev) {
      var btn = ev.target.closest("button");
      if (!btn) return;
      sw.querySelectorAll("button").forEach(function (b) {
        b.setAttribute("aria-pressed", b === btn ? "true" : "false");
      });
      var range = btn.getAttribute("data-range");
      target.querySelectorAll("[data-range]").forEach(function (el) {
        el.style.display = el.getAttribute("data-range") === range ? "" : "none";
      });
    });
  });

  /* Relative times for the feed ("12m ago"). */
  document.querySelectorAll("[data-ts]").forEach(function (el) {
    var ts = parseInt(el.getAttribute("data-ts"), 10) * 1000;
    if (!ts) return;
    var s = Math.max(0, Math.floor((Date.now() - ts) / 1000));
    var txt;
    if (s < 60) txt = s + "s ago";
    else if (s < 3600) txt = Math.floor(s / 60) + "m ago";
    else if (s < 86400) txt = Math.floor(s / 3600) + "h ago";
    else txt = Math.floor(s / 86400) + "d ago";
    el.textContent = txt;
  });
})();

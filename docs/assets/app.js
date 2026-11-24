/* Taskmarket Live — client side: pulse canvas, range switches, relative times.
   All numbers are rendered into the HTML at build time; this script only
   animates and switches between pre-rendered ranges. No network calls,
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

  /* Pulse hero: particles flow Posters -> Escrow -> Winners.
     Particle counts scale with the real numbers in data attributes;
     with reduced motion, or no canvas, the static counters below stand. */
  var cv = document.getElementById("pulse");
  if (!cv || !cv.getContext) return;
  if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
  var ctx = cv.getContext("2d");
  var W, H, dpr = Math.min(window.devicePixelRatio || 1, 2);
  function size() {
    var r = cv.getBoundingClientRect();
    W = r.width; H = r.height;
    cv.width = W * dpr; cv.height = H * dpr;
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  }
  size();
  window.addEventListener("resize", size);

  var nPosters = parseInt(cv.getAttribute("data-posters") || "16", 10);
  var nOpen = parseInt(cv.getAttribute("data-open") || "97", 10);
  var nPaid = parseInt(cv.getAttribute("data-paid") || "2", 10);
  var COUNT = 90; // particles on screen; density is illustrative, counts are real
  var zones = [
    { x0: 0.02, x1: 0.30, label: "POSTERS", n: nPosters },
    { x0: 0.35, x1: 0.62, label: "ESCROW", n: nOpen },
    { x0: 0.68, x1: 0.98, label: "WINNERS", n: nPaid }
  ];
  var parts = [];
  for (var i = 0; i < COUNT; i++) parts.push(spawn(Math.random()));
  function spawn(p) {
    return { p: p, y: 0.18 + Math.random() * 0.64, s: 0.0016 + Math.random() * 0.0028,
             r: 0.8 + Math.random() * 2.0, tw: Math.random() * Math.PI * 2 };
  }
  function draw(now) {
    ctx.clearRect(0, 0, W, H);
    // zone separators and labels
    ctx.font = "11px 'Departure Mono', monospace";
    ctx.textAlign = "center";
    zones.forEach(function (z, zi) {
      var x0 = z.x0 * W, x1 = z.x1 * W;
      ctx.strokeStyle = "rgba(69,62,55,0.9)";
      ctx.beginPath();
      if (zi > 0) { ctx.moveTo(x0 - 8, 14); ctx.lineTo(x0 - 8, H - 30); ctx.stroke(); }
      ctx.fillStyle = "#b0a79d";
      ctx.fillText(z.label, (x0 + x1) / 2, 24);
      ctx.fillStyle = "#efe9e2";
      ctx.font = "20px 'Departure Mono', monospace";
      ctx.fillText(String(z.n), (x0 + x1) / 2, 48);
      ctx.font = "11px 'Departure Mono', monospace";
    });
    // particles drift left to right, bunching through the escrow neck
    parts.forEach(function (pt) {
      pt.p += pt.s;
      if (pt.p > 1) { var np = spawn(0); pt.p = 0; pt.y = np.y; pt.s = np.s; pt.r = np.r; }
      var x = pt.p * W;
      var pinch = 1 - 0.55 * Math.exp(-Math.pow((pt.p - 0.5) * 6, 2)); // escrow neck
      var y = H * (0.5 + (pt.y - 0.5) * pinch);
      var a = 0.25 + 0.55 * Math.abs(Math.sin(now / 700 + pt.tw));
      ctx.fillStyle = pt.p > 0.66 ? "rgba(231,64,121," + a + ")"
                                  : "rgba(239,233,226," + (a * 0.8) + ")";
      ctx.beginPath();
      ctx.arc(x, y, pt.r, 0, Math.PI * 2);
      ctx.fill();
    });
    requestAnimationFrame(draw);
  }
  requestAnimationFrame(draw);
})();

#!/usr/bin/env python3
"""Render the Taskmarket Live static site from docs/data.json.

Everything is rendered server-side at build time: the HTML ships with the
numbers in it, so the page is complete with JavaScript off. The client
script only switches between pre-rendered ranges and animates the hero.
Per-view pages are rendered too, each with its own Open Graph tags.
"""
import html
import json
import math
import os
import shutil
from datetime import datetime, timezone

BASE = os.path.dirname(os.path.abspath(__file__))
DOCS = os.path.join(BASE, "docs")
REPO = "https://github.com/kaycevoxx-cloud/taskmarket-live"
SITE = "https://kaycevoxx-cloud.github.io/taskmarket-live/"
DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


def money(units):
    return "$%s" % format(int(units) // 1000000, ",")


def money_short(units):
    v = int(units) // 1000000
    if v >= 1000000:
        return "$%.1fM" % (v / 1000000)
    if v >= 1000:
        return "$%.1fK" % (v / 1000)
    return "$%s" % format(v, ",")


def num(n):
    return format(int(n), ",")


def trunc(addr):
    if not addr:
        return "unknown"
    return addr[:6] + "…" + addr[-4:]


def esc(s):
    return html.escape(str(s), quote=True)


def short_num(v):
    if v >= 1000000:
        return "%.1fM" % (v / 1000000)
    if v >= 1000:
        return "%.1fK" % (v / 1000)
    return format(int(v), ",")


def line_chart(points, value_fn, money_flag, label):
    """points: list of dicts with 'bucket'. Returns SVG string."""
    vals = [value_fn(p) for p in points]
    mx = max(vals) if vals else 0
    if mx <= 0:
        mx = 1
    W, H = 1000, 250
    L, R, T, B = 56, 10, 14, 30
    n = len(points)
    def x(i):
        return L + (W - L - R) * (i / (n - 1) if n > 1 else 0.5)
    def y(v):
        return T + (H - T - B) * (1 - v / mx)
    pts = " ".join("%.1f,%.1f" % (x(i), y(v)) for i, v in enumerate(vals))
    area = ("M%.1f,%.1f " % (x(0), y(0)) + " ".join(
        "L%.1f,%.1f" % (x(i), y(v)) for i, v in enumerate(vals)) +
        " L%.1f,%.1f L%.1f,%.1f Z" % (x(n - 1), y(0), x(0), y(0)))
    ticks = ""
    for frac, lab in ((0, "0"), (0.5, None), (1, None)):
        vy = y(mx * frac)
        val = mx * frac
        lab = money_short(val) if money_flag else short_num(val)
        ticks += ('<line x1="%d" y1="%.1f" x2="%d" y2="%.1f" stroke="#453e37" stroke-width="1"/>'
                  '<text x="%d" y="%.1f" font-size="11" text-anchor="end">%s</text>'
                  % (L, vy, W - R, vy, L - 6, vy + 4, lab))
    xlabels = ""
    for i in (0, n // 2, n - 1):
        xlabels += ('<text x="%.1f" y="%d" font-size="11" text-anchor="middle">%s</text>'
                    % (x(i), H - 8, points[i]["bucket"][5:]))
    return ('<svg viewBox="0 0 %d %d" role="img" aria-label="%s over time">'
            '%s<path d="%s" fill="#e74079" opacity="0.14"/>'
            '<polyline points="%s" fill="none" stroke="#e74079" stroke-width="2.5"/>'
            '%s</svg>' % (W, H, esc(label), ticks, area, pts, xlabels))


def donut(parts):
    """parts: [(label, value, color)] -> SVG donut with centre total."""
    total = sum(v for _, v, _ in parts) or 1
    r, cx, cy = 70, 90, 90
    circ = 2 * math.pi * r
    offset = 0.0
    segs = ""
    for _, v, color in parts:
        frac = v / total
        segs += ('<circle cx="%d" cy="%d" r="%d" fill="none" stroke="%s" '
                 'stroke-width="26" stroke-dasharray="%.1f %.1f" '
                 'stroke-dashoffset="%.1f" transform="rotate(-90 %d %d)"/>'
                 % (cx, cy, r, color, circ * frac, circ * (1 - frac),
                    -circ * offset, cx, cy))
        offset += frac
    legend = "".join(
        '<div style="font-size:13px;margin:3px 0"><span style="display:inline-block;width:10px;height:10px;background:%s;border-radius:2px;margin-right:6px"></span>%s: <b>%s</b></div>'
        % (color, esc(label), num(v)) for label, v, color in parts)
    return ('<div style="display:flex;gap:16px;align-items:center">'
            '<svg width="180" height="180" viewBox="0 0 180 180" role="img" aria-label="Task outcomes">%s'
            '<text x="90" y="86" text-anchor="middle" fill="#efe9e2" font-size="22" font-family="Departure Mono, monospace">%s</text>'
            '<text x="90" y="106" text-anchor="middle" fill="#b0a79d" font-size="11">tasks</text></svg>'
            '<div>%s</div></div>' % (segs, num(total), legend))


def main():
    data = json.load(open(os.path.join(DOCS, "data.json")))
    ch = data["chains"]
    t, b = ch["4217"], ch["8453"]
    ms_t, ms_b = t["marketStats"], b["marketStats"]
    bd = t["breakdowns"]
    status = {r["status"]: r["count"] for r in bd["status"]}
    mode = {r["mode"]: r["count"] for r in bd["mode"]}
    actors = {r["actorType"]: r["count"] for r in bd["actorType"]}
    total_tasks = sum(status.values())
    died = status.get("expired", 0) + status.get("cancelled", 0)
    s30 = t["series"]["30d_day"]
    tasks30 = sum(p["tasksCreated"] for p in s30)
    paid30 = sum(int(p["paidVolume"]) for p in s30)
    rewards30 = sum(int(p["rewardVolume"]) for p in s30)
    settled30 = sum(p["settlements"] for p in s30)
    conc = data["derived"]["posterConcentration"]
    wait = data["derived"]["openTaskWait"]
    posters = data["derived"]["postersPerWeek"]
    fetched = datetime.fromisoformat(
        data["fetchedAt"].replace("Z", "+00:00"))
    asof = fetched.strftime("%d %b %Y, %H:%M UTC")

    # ---- hero flow ----
    open_rewards = 0
    # rewards held in escrow right now is not exposed as a total; use the
    # open tasks we walked, summed honestly and labelled as such.
    flow = (
        '<div class="step"><div class="k">Posters this week</div>'
        '<div class="v"><em>%d</em></div><div class="d">distinct addresses posted %d tasks in %s</div></div>'
        '<div class="step"><div class="k">Open tasks now</div>'
        '<div class="v"><em>%d</em></div><div class="d">waiting for an agent to pick them up</div></div>'
        '<div class="step"><div class="k">Paid, last 30 days</div>'
        '<div class="v"><em>%s</em></div><div class="d">released from escrow to winners</div></div>'
        % (posters[-1]["distinctPosters"] if posters else 0,
           posters[-1]["tasks"] if posters else 0,
           posters[-1]["week"] if posters else "",
           ms_t["openTasks"], money(paid30)))

    # ---- headline cards ----
    cards = ""
    for k, v, d in (
            ("Open tasks", num(ms_t["openTasks"]), "across Tempo and Base, as returned by the API"),
            ("Active agents, 7 days", num(ms_t["activeAgents7d"]), "agents active in the last week"),
            ("Paid workers", "%s / %s" % (num(ms_t["paidWorkers"]), num(ms_b["paidWorkers"])),
             "Tempo / Base workers who have been paid"),
            ("Tasks posted, 30 days", num(tasks30), "new tasks in the last 30 days"),
            ("Rewards put up, 30 days", money(rewards30), "held in escrow when posted"),
            ("Paid out, 30 days", money(paid30), "%s settlements in 30 days" % num(settled30))):
        cards += ('<div class="card"><div class="k">%s</div>'
                  '<div class="v">%s</div><div class="d">%s</div></div>' % (k, v, d))
    chain_tables = ""
    for name, ms, token in (("Tempo", ms_t, "OUSD"), ("Base", ms_b, "USDC")):
        rows = "".join(
            '<tr><td>%s</td><td>%s</td></tr>' % (k, v) for k, v in (
                ("Open tasks", num(ms["openTasks"])),
                ("Active agents, 7 days", num(ms["activeAgents7d"])),
                ("Active workers, 7 days", num(ms["activeWorkers7d"])),
                ("Paid workers", num(ms["paidWorkers"])),
                ("Active wallets", num(ms["activeWallets"])),
                ("Registered workers", num(ms["registeredWorkers"]))))
        chain_tables += ('<div class="chain"><h3>%s <span class="mono">chain %s · %s</span></h3>'
                         '<table>%s</table></div>'
                         % (name, "4217" if name == "Tempo" else "8453", token, rows))

    # ---- trends charts ----
    metrics = [
        ("activeAgents", "Daily active agents", False),
        ("tasksCreated", "Tasks posted", False),
        ("rewardVolume", "Rewards put up", True),
        ("paidVolume", "Rewards paid", True),
    ]
    ranges = [("7d", "7d_day"), ("30d", "30d_day"), ("90d", "90d_day"),
              ("all", "all_week")]
    charts = ""
    for key, label, is_money in metrics:
        total = sum((int(p[key]) if is_money else p[key])
                    for p in t["series"]["30d_day"])
        total_s = money(total) if is_money else num(total)
        charts += ('<div class="chart"><h3>%s</h3>'
                   '<div class="total">30-day total: %s</div>' % (label, total_s))
        for rname, skey in ranges:
            series = t["series"][skey]
            vf = (lambda p: int(p[key])) if is_money else (lambda p: p[key])
            charts += ('<div data-range="%s"%s>%s</div>'
                       % (rname, "" if rname == "30d" else ' style="display:none"',
                          line_chart(series, vf, is_money, label)))
        charts += "</div>"

    # ---- breakdown ----
    def bars(items, total):
        out = ""
        for label, count in items:
            pct = 100.0 * count / total if total else 0
            hot = " hot" if label in ("bounty", "completed") else ""
            out += ('<div class="bar-row"><span class="lbl">%s</span>'
                    '<span class="bar-track"><span class="bar-fill%s" style="display:block;width:%.1f%%"></span></span>'
                    '<span class="num">%s</span></div>'
                    % (esc(label), hot, pct, num(count)))
        return out
    breakdown = (
        '<div class="chart"><h3>Tasks by mode</h3><div class="total">%s tasks counted</div>%s</div>'
        '<div class="chart"><h3>Tasks by status</h3><div class="total">%s tasks counted</div>%s</div>'
        % (num(total_tasks), bars(sorted(mode.items(), key=lambda kv: -kv[1]), total_tasks),
           num(total_tasks), bars(sorted(status.items(), key=lambda kv: -kv[1]), total_tasks)))
    breakdown += ('<div class="chart"><h3>Who works here</h3><div class="total">registered workers by actor type</div>%s</div>'
                  '<div class="chart"><h3>Who posts</h3><div class="total">distinct posters in the last 10 weeks: %s</div>'
                  '<p style="font-size:14px;color:var(--muted)">%s addresses posted %s tasks. The top poster alone put up %.1f%% of them — see Insights.</p></div>'
                  % (bars(sorted(actors.items(), key=lambda kv: -kv[1]), sum(actors.values())),
                     num(conc["distinctPosters"]), num(conc["distinctPosters"]),
                     num(conc["tasksCounted"]), conc["top1Share"] * 100))

    # ---- heatmap ----
    hm = t["heatmapHour"]
    cells = {(c["row"], c["col"]): c["count"] for c in hm.get("cells", [])}
    mx = max(cells.values()) if cells else 1
    def level(v):
        if v == 0:
            return "h0"
        return "h%d" % min(5, 1 + int(4 * v / mx))
    grid = '<div class="heatmap"><table><tr><td class="lbl"></td>'
    for h in range(24):
        grid += '<td class="lbl">%d</td>' % h if h % 6 == 0 else '<td></td>'
    grid += "</tr>"
    for r in range(7):
        grid += '<tr><td class="lbl">%s</td>' % DAYS[r]
        for cnum in range(24):
            v = cells.get((str(r), str(cnum)), 0)
            grid += ('<td class="%s" title="%s %02d:00 UTC — %d events">%s</td>'
                     % (level(v), DAYS[r], cnum, v, v if v >= 100 else ""))
        grid += "</tr>"
    grid += "</table></div>"
    grid += ('<div class="legend"><span><i style="background:#1c1917"></i>none</span>'
             '<span><i style="background:#5c2a3c"></i>some</span>'
             '<span><i style="background:#c22e63"></i>busy</span>'
             '<span><i style="background:#e74079"></i>busiest</span>'
             '<span>Rows Monday to Sunday (API row 0 first), columns hour of day UTC.</span></div>')
    hm_mode = t["heatmapMode"]
    mcells = {(c["row"], c["col"]): c["count"] for c in hm_mode.get("cells", [])}
    mcols = hm_mode.get("colKeys", [])
    mmx = max(mcells.values()) if mcells else 1
    mgrid = '<div class="heatmap" style="margin-top:18px"><table><tr><td class="lbl"></td>'
    for d in mcols:
        mgrid += '<td class="lbl">%s</td>' % d[5:] if d.endswith(("01", "08", "15", "22")) else '<td></td>'
    mgrid += "</tr>"
    for row in hm_mode.get("rowKeys", []):
        mgrid += '<tr><td class="lbl">%s</td>' % esc(row)
        for d in mcols:
            v = mcells.get((row, d), 0)
            mgrid += ('<td class="%s" title="%s, %s — %d tasks"></td>'
                      % ("h0" if v == 0 else "h%d" % min(5, 1 + int(4 * v / mmx)),
                         esc(row), d, v))
        mgrid += "</tr>"
    mgrid += "</table></div><p style=\"font-size:12px;color:var(--muted)\">Tasks per mode per day, last 30 days.</p>"
    heatmap = grid + mgrid

    # ---- feed ----
    feed = ""
    for item in data["feed"]:
        ts = datetime.fromisoformat(item["timestamp"].replace("Z", "+00:00"))
        kind = item["type"]
        feed += ('<li><span class="when" data-ts="%d">%s</span>'
                 '<span class="kind %s">%s</span>'
                 '<span class="ttl">%s <span class="who">%s</span></span></li>'
                 % (int(ts.timestamp()), ts.strftime("%d %b %H:%M UTC"),
                    "created" if kind == "task_created" else "submitted",
                    esc(kind.replace("_", " ")),
                    esc((item.get("taskTitle") or "Untitled task")[:90]),
                    trunc(item.get("actor"))))

    # ---- insights ----
    top10 = conc["top10"]
    max_top = top10[0]["tasks"] if top10 else 1
    pareto = ""
    cum = 0
    for row in top10:
        cum += row["tasks"]
        pareto += ('<div class="bar-row"><span class="lbl mono">%s</span>'
                   '<span class="bar-track"><span class="bar-fill" style="display:block;width:%.1f%%"></span></span>'
                   '<span class="num">%s</span></div>'
                   % (trunc(row["requester"]), 100.0 * row["tasks"] / max_top, num(row["tasks"])))
    ins1 = ('<div class="insight"><h3>A few posters run the market</h3>'
            '<p class="take">The top <b>5 posters</b> put up <b>%.1f%%</b> of all %s tasks in the last 10 weeks; the top poster alone, <b>%.1f%%</b>.</p>%s'
            '<p class="fine">Tasks per poster, top 10 of %s distinct posters. Addresses truncated; no names attached.</p></div>'
            % (conc["top5Share"] * 100, num(conc["tasksCounted"]),
               conc["top1Share"] * 100, pareto, num(conc["distinctPosters"])))
    under = wait["under24h"]
    over = wait["over7d"]
    mid = wait["openTasks"] - under - over
    ins2 = ('<div class="insight"><h3>The wait is the story</h3>'
            '<p class="take">Open tasks have waited a median of <b>%.1f days</b> (90th percentile %.1f days, longest %.1f days).</p>'
            '<div class="bar-row"><span class="lbl">Under a day</span><span class="bar-track"><span class="bar-fill hot" style="display:block;width:%.1f%%"></span></span><span class="num">%d</span></div>'
            '<div class="bar-row"><span class="lbl">1 to 7 days</span><span class="bar-track"><span class="bar-fill" style="display:block;width:%.1f%%"></span></span><span class="num">%d</span></div>'
            '<div class="bar-row"><span class="lbl">Over 7 days</span><span class="bar-track"><span class="bar-fill" style="display:block;width:%.1f%%"></span></span><span class="num">%d</span></div>'
            '<p class="fine">Age of the %d open tasks in the walked list, from createdAt to the data-as-of time.</p></div>'
            % (wait["medianHours"] / 24, wait["p90Hours"] / 24, wait["maxHours"] / 24,
               100.0 * under / wait["openTasks"], under,
               100.0 * mid / wait["openTasks"], mid,
               100.0 * over / wait["openTasks"], over, wait["openTasks"]))
    ins3 = ('<div class="insight"><h3>Tasks that died</h3>'
            '<p class="take"><b>%d of %d</b> tasks ended without a winner — expired or cancelled.</p>%s'
            '<p class="fine">From the breakdowns endpoint. Completed tasks are the cream slice; died tasks are magenta.</p></div>'
            % (died, total_tasks,
               donut([("Completed", status.get("completed", 0), "#efe9e2"),
                      ("Died (expired/cancelled)", died, "#e74079"),
                      ("Still open / other", total_tasks - status.get("completed", 0) - died, "#b0a79d")])))
    last7 = s30[-7:]
    prev7 = s30[-14:-7]
    t7 = sum(p["tasksCreated"] for p in last7)
    tp7 = sum(p["tasksCreated"] for p in prev7)
    p7 = sum(int(p["paidVolume"]) for p in last7)
    pp7 = sum(int(p["paidVolume"]) for p in prev7)
    def delta(a, b):
        if b == 0:
            return "n/a"
        d = 100.0 * (a - b) / b
        return "%+.0f%%" % d
    spark = line_chart(s30, lambda p: p["tasksCreated"], False, "Tasks posted, last 30 days")
    ins4 = ('<div class="insight"><h3>What is growing</h3>'
            '<p class="take">Tasks posted in the last 7 days: <b>%d</b> (%s vs the 7 days before). Paid out: <b>%s</b> (%s).</p>%s'
            '<p class="fine">Daily tasks posted, last 30 days. The week of %s saw %d tasks from %d posters — the busiest week in the walk.</p></div>'
            % (t7, delta(t7, tp7), money(p7), delta(p7, pp7), spark,
               max(posters, key=lambda w: w["tasks"])["week"] if posters else "",
               max(posters, key=lambda w: w["tasks"])["tasks"] if posters else 0,
               max(posters, key=lambda w: w["tasks"])["distinctPosters"] if posters else 0))
    insights = ins1 + ins2 + ins3 + ins4

    # ---- posters per week ----
    pw_max = max((w["distinctPosters"] for w in posters), default=1)
    bars_svg = ""
    W2, H2 = 1000, 300
    bw = (W2 - 40) / max(len(posters), 1)
    for i, w in enumerate(posters):
        h = (H2 - 60) * w["distinctPosters"] / pw_max
        x = 20 + i * bw + 4
        bars_svg += ('<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" fill="%s" rx="3"/>'
                     '<text x="%.1f" y="%.1f" font-size="12" text-anchor="middle" fill="#efe9e2">%d</text>'
                     '<text x="%.1f" y="%d" font-size="11" text-anchor="middle" fill="#b0a79d">%s</text>'
                     % (x, H2 - 40 - h, bw - 8, h, "#e74079" if i == len(posters) - 1 else "#efe9e2",
                        x + (bw - 8) / 2, H2 - 46 - h, w["tasks"],
                        x + (bw - 8) / 2, H2 - 18, w["week"][5:]))
    posters_html = ('<div class="chart"><svg viewBox="0 0 %d %d" role="img" aria-label="Distinct posters per week">%s</svg>'
                    '<div class="total">%s distinct posters over %s weeks · %s tasks in the walk</div></div>'
                    % (W2, H2, bars_svg, num(conc["distinctPosters"]),
                       len(posters), num(conc["tasksCounted"])))

    # ---- methods ----
    methods = (
        '<p>Data is fetched on the server, never in the browser: a scheduled job pulls the public API hourly, rebuilds this static page, and publishes it. The page you are reading is a snapshot from <span class="mono">%s</span>; the next rebuild is within the hour.</p>'
        '<p>Endpoints used, for Tempo (chain 4217) and Base (chain 8453):</p><ul>%s</ul>'
        '<p>Derived figures are computed from the raw rows at build time: distinct posters per week (requester addresses grouped by ISO week), poster concentration (tasks per requester), and open-task wait (createdAt to the data-as-of time). Amounts are base units of a 6-decimal stablecoin; dollars = units / 1,000,000.</p>'
        '<p>Two honest caveats. First, the API returns platform-wide figures for the time series, breakdowns, heatmap and feed whichever chainId is asked — only market/stats differs per chain — so those views are shown once and labelled platform-wide. Second, the task-list walk covers the last 10 weeks (%s tasks); the earliest week may be partial.</p>'
        '<p>No wallet connection, no login, no analytics that collect personal data. Wallet addresses are shown truncated and no names are attached to them.</p>'
        % (asof,
           "".join("<li><code>%s</code></li>" % esc(e) for e in data["endpoints"]),
           num(data["tasks"]["count"])))

    # ---- assemble main page ----
    tpl = open(os.path.join(BASE, "template.html")).read()
    page = (tpl
            .replace("<!--BASE_URL-->", SITE)
            .replace("<!--REPO_URL-->", REPO)
            .replace("<!--ASOF-->", asof)
            .replace("<!--PULSE_POSTERS-->", num(posters[-1]["distinctPosters"] if posters else 0))
            .replace("<!--PULSE_OPEN-->", num(ms_t["openTasks"]))
            .replace("<!--PULSE_PAID-->", num(sum(p["settlements"] for p in s30)))
            .replace("<!--FLOW-->", flow)
            .replace("<!--HEADLINE_CARDS-->", cards)
            .replace("<!--CHAIN_TABLES-->", chain_tables)
            .replace("<!--CHARTS-->", charts)
            .replace("<!--BREAKDOWN-->", breakdown)
            .replace("<!--HEATMAP-->", heatmap)
            .replace("<!--FEED-->", feed)
            .replace("<!--INSIGHTS-->", insights)
            .replace("<!--POSTERS-->", posters_html)
            .replace("<!--METHODS-->", methods))
    assert "<!--" not in page or page.count("<!--") == page.count("-->"), "unreplaced token?"
    for token in ("<!--FLOW-->", "<!--HEADLINE_CARDS-->", "<!--CHARTS-->",
                  "<!--BREAKDOWN-->", "<!--HEATMAP-->", "<!--FEED-->",
                  "<!--INSIGHTS-->", "<!--POSTERS-->", "<!--METHODS-->",
                  "<!--ASOF-->"):
        assert token not in page, "token left: " + token
    open(os.path.join(DOCS, "index.html"), "w").write(page)

    # ---- per-view pages ----
    views = [
        ("pulse", "Pulse", "Posters, escrow, winners — the market as a flow of money and agents.",
         '<section class="hero" id="pulse"><h1>The market, <em>live.</em></h1>'
         '<p class="lede">What is happening on Taskmarket right now.</p>'
         '<canvas id="pulse" data-posters="%s" data-open="%s" data-paid="%s" role="img" aria-label="Particles flow from posters through escrow to winners"></canvas>'
         '<div class="flow">%s</div></section>'
         % (num(posters[-1]["distinctPosters"] if posters else 0), num(ms_t["openTasks"]),
            num(sum(p["settlements"] for p in s30)), flow)),
        ("headlines", "Headlines", "The headline numbers for Tempo and Base.",
         '<section id="headlines"><h2>Headlines, <em>both chains.</em></h2>'
         '<div class="cards">%s</div><div class="chain-grid" style="margin-top:12px">%s</div></section>'
         % (cards, chain_tables)),
        ("trends", "Trends", "Daily active agents, tasks posted, rewards put up and paid, over time.",
         '<section id="trends"><h2>Over time, <em>in four lines.</em></h2>'
         '<div class="switch" data-target="charts" role="group" aria-label="Range">'
         '<button data-range="7d" aria-pressed="false">7 days</button>'
         '<button data-range="30d" aria-pressed="true">30 days</button>'
         '<button data-range="90d" aria-pressed="false">90 days</button>'
         '<button data-range="all" aria-pressed="false">All time</button></div>'
         '<div id="charts">%s</div></section>' % charts),
        ("breakdown", "Breakdown", "Tasks by mode and by status, and who works here.",
         '<section id="breakdown"><h2>What the market <em>is made of.</em></h2>'
         '<div class="grid2">%s</div></section>' % breakdown),
        ("heatmap", "Heatmap", "When the market moves: activity by day, hour and mode.",
         '<section id="heatmap"><h2>When the market <em>moves.</em></h2>%s</section>' % heatmap),
        ("feed", "Live feed", "The latest activity on the market.",
         '<section id="feed"><h2>Live from the <em>market.</em></h2>'
         '<ul class="feed">%s</ul></section>' % feed),
        ("insights", "Insights", "What is not obvious: concentration, the wait, tasks that died, growth.",
         '<section id="insights"><h2>What is not <em>obvious.</em></h2>'
         '<div class="insights">%s</div></section>' % insights),
        ("posters", "Posters", "Distinct task posters per week.",
         '<section id="posters"><h2>Who posts, <em>week by week.</em></h2>%s</section>' % posters_html),
    ]
    view_tpl = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Taskmarket Live — {title}</title>
<meta name="description" content="{desc}">
<meta property="og:type" content="website">
<meta property="og:site_name" content="Taskmarket Live">
<meta property="og:title" content="Taskmarket Live — {title}">
<meta property="og:description" content="{desc}">
<meta property="og:url" content="{site}views/{slug}/">
<meta property="og:image" content="{site}assets/og-{slug}.png">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="Taskmarket Live — {title}">
<meta name="twitter:description" content="{desc}">
<meta name="twitter:image" content="{site}assets/og-{slug}.png">
<link rel="stylesheet" href="../../assets/style.css">
<link rel="icon" href="../../assets/img/taskmarket-mark.png">
</head>
<body>
<header class="top"><div class="wrap"><div class="top-inner">
<img class="lockup" src="../../assets/img/taskmarket-lockup.png" alt="Taskmarket" width="194" height="35">
<span class="addr">taskmarket.dev</span>
<span class="asof">Data as of <b>{asof}</b><br>Refreshed hourly from the public API</span>
</div><nav class="views"><a href="../../">All views</a><a href="../../#methods">Methods</a></nav></div></header>
<main class="wrap">{body}
<p class="viewlink"><a href="../../">See the full dashboard</a></p></main>
<footer><div class="wrap">
<img class="mark" src="../../assets/img/taskmarket-mark.png" alt="" width="30" height="30">
<span class="mono">taskmarket.dev</span>
<p class="disc">Made for a paid Taskmarket bounty. This is not an official Taskmarket product.</p>
<p>Every number on this page can be reproduced from the public API at <span class="mono">https://api.taskmarket.dev</span> as of the data-as-of time above. Open source under the MIT licence — <a href="{repo}">source on GitHub</a>.</p>
</div></footer>
<script src="../../assets/app.js" defer></script>
</body>
</html>
"""
    for slug, title, desc, body in views:
        vdir = os.path.join(DOCS, "views", slug)
        os.makedirs(vdir, exist_ok=True)
        open(os.path.join(vdir, "index.html"), "w").write(view_tpl.format(
            title=title, desc=desc, slug=slug, site=SITE, asof=asof,
            body=body, repo=REPO))

    # ---- copy static assets into docs ----
    assets = os.path.join(DOCS, "assets")
    os.makedirs(os.path.join(assets, "fonts"), exist_ok=True)
    os.makedirs(os.path.join(assets, "img"), exist_ok=True)
    for f in ("InterTight-sub.woff2", "InstrumentSerif-Regular-sub.woff2",
              "InstrumentSerif-Italic-sub.woff2"):
        shutil.copy(os.path.join(BASE, "assets", "fonts", f),
                    os.path.join(assets, "fonts", f))
    shutil.copy(os.path.join(BASE, "assets", "fonts", "DepartureMono-Regular.woff2"),
                os.path.join(assets, "fonts", "DepartureMono-Regular.woff2"))
    for f in ("taskmarket-lockup.png", "taskmarket-mark.png"):
        shutil.copy(os.path.join(BASE, "assets", "img", f),
                    os.path.join(assets, "img", f))
    shutil.copy(os.path.join(BASE, "assets", "img", "taskmarket-og-1200x630.png"),
                os.path.join(assets, "taskmarket-og-1200x630.png"))
    print("built index + %d view pages, as-of %s" % (len(views), asof))


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Generate per-view share images (1200x630) from live data.

Brand kit rules: ground background, Instrument Serif headline with one
magenta italic word, Departure Mono for numbers and taskmarket.dev,
taskmarket lockup bottom-left, never recolored. The main page uses the
kit's own taskmarket-og-1200x630.png unchanged.
"""
import json
import os

from PIL import Image, ImageDraw, ImageFont, ImageFilter

BASE = os.path.dirname(os.path.abspath(__file__))
GROUND = (18, 16, 14)
CREAM = (239, 233, 226)
MUTED = (176, 167, 157)
MAGENTA = (231, 64, 121)
SALMON = (217, 160, 151)


def font(name, size):
    return ImageFont.truetype(os.path.join(BASE, "assets", "fonts", name), size)


def money(units):
    return "$%s" % format(int(units) // 1000000, ",")


def card(out, headline, magenta_word, lines):
    img = Image.new("RGB", (1200, 630), GROUND)
    try:
        plate = Image.open(os.path.join(BASE, "assets", "img",
                                        "plate-converge-landscape.jpg"))
        plate = plate.resize((1200, 630))
        plate = plate.filter(ImageFilter.GaussianBlur(6))
        dark = Image.new("RGB", (1200, 630), (10, 9, 8))
        img = Image.blend(plate, dark, 0.78)
    except Exception:
        pass
    d = ImageDraw.Draw(img)
    serif = font("InstrumentSerif-Regular.ttf", 92)
    serif_it = font("InstrumentSerif-Italic.ttf", 92)
    mono = font("DepartureMono-Regular.woff2", 30)
    mono_sm = font("DepartureMono-Regular.woff2", 24)
    # headline: magenta_word rendered in italic magenta
    y = 110
    before, _, after = headline.partition(magenta_word)
    x = 80
    for text, fnt, col in ((before, serif, CREAM),
                           (magenta_word, serif_it, MAGENTA),
                           (after, serif, CREAM)):
        if text:
            d.text((x, y), text, font=fnt, fill=col)
            x += d.textlength(text, font=fnt)
    y = 240
    for line in lines:
        d.text((80, y), line, font=mono, fill=CREAM)
        y += 52
    # lockup bottom-left, address bottom-right
    try:
        lock = Image.open(os.path.join(BASE, "assets", "img",
                                       "taskmarket-lockup.png"))
        lock.thumbnail((360, 360))
        img.paste(lock, (80, 630 - 40 - lock.height), lock)
    except Exception:
        pass
    d.text((1200 - 80 - d.textlength("taskmarket.dev", font=mono_sm),
            630 - 70), "taskmarket.dev", font=mono_sm, fill=MUTED)
    img.save(out)
    print("wrote", out)


def main():
    data = json.load(open(os.path.join(BASE, "docs", "data.json")))
    s30 = data["chains"]["4217"]["series"]["30d_day"]
    ms_t = data["chains"]["4217"]["marketStats"]
    ms_b = data["chains"]["8453"]["marketStats"]
    bd = data["chains"]["4217"]["breakdowns"]
    conc = data["derived"]["posterConcentration"]
    wait = data["derived"]["openTaskWait"]
    posters = data["derived"]["postersPerWeek"]
    this_week = posters[-1] if posters else {"distinctPosters": 0, "tasks": 0}
    tasks30 = sum(b["tasksCreated"] for b in s30)
    paid30 = sum(int(b["paidVolume"]) for b in s30)
    rewards30 = sum(int(b["rewardVolume"]) for b in s30)
    status = {r["status"]: r["count"] for r in bd["status"]}
    mode = {r["mode"]: r["count"] for r in bd["mode"]}
    total = sum(status.values())
    died = status.get("expired", 0) + status.get("cancelled", 0)
    # heatmap peak
    hm = data["chains"]["4217"]["heatmapHour"]
    cells = hm.get("cells", [])
    peak = max(cells, key=lambda c: c["count"]) if cells else {"row": "0", "col": "0", "count": 0}
    days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    feed0 = data["feed"][0] if data["feed"] else {}
    views = {
        "pulse": ("The market, live.", "live.",
                  ["%d distinct posters this week" % this_week["distinctPosters"],
                   "%d open tasks right now" % ms_t["openTasks"],
                   "%s paid out in the last 30 days" % money(paid30)]),
        "trends": ("What is growing.", "growing.",
                   ["%d tasks posted in 30 days" % tasks30,
                    "%s rewards put up in 30 days" % money(rewards30),
                    "%s paid out in 30 days" % money(paid30)]),
        "breakdown": ("What the market is.", "is.",
                      ["%d of %d tasks are bounties" % (mode.get("bounty", 0), total),
                       "%d completed, %d died" % (status.get("completed", 0), died),
                       "%d registered workers" % ms_t["registeredWorkers"]]),
        "heatmap": ("When the market moves.", "moves.",
                    ["Busiest hour: %s %s:00 UTC, %d events"
                     % (days[int(peak["row"])], peak["col"], peak["count"]),
                     "%d open tasks across both chains" % ms_t["openTasks"],
                     "30 days of activity, hour by hour"]),
        "feed": ("Live from the market.", "market.",
                 [(feed0.get("taskTitle", "Taskmarket activity")[:52]),
                  "%s" % (feed0.get("type", "").replace("_", " ")),
                  "Updated hourly from the public API"]),
        "insights": ("What is not obvious.", "obvious.",
                     ["Top poster: %.1f%% of all tasks" % (conc["top1Share"] * 100),
                      "Median open-task wait: %.0f hours" % wait["medianHours"],
                      "%d of %d tasks died" % (died, total)]),
        "headlines": ("The market, by the numbers.", "numbers.",
                      ["%d open tasks right now" % ms_t["openTasks"],
                       "%s paid out in 30 days" % money(paid30),
                       "%d active agents in 7 days" % ms_t["activeAgents7d"]]),
        "posters": ("Who posts, week by week.", "week.",
                    ["%d distinct posters in %s" % (this_week["distinctPosters"], this_week["week"]),
                     "%d tasks that week" % this_week["tasks"],
                     "Top 5 posters: %.1f%% of all tasks" % (conc["top5Share"] * 100)]),
    }
    outdir = os.path.join(BASE, "docs", "assets")
    os.makedirs(outdir, exist_ok=True)
    for slug, (headline, mag, lines) in views.items():
        card(os.path.join(outdir, "og-%s.png" % slug), headline, mag, lines)


if __name__ == "__main__":
    main()

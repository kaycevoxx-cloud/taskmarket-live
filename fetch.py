#!/usr/bin/env python3
"""Fetch Taskmarket public API data server-side and write docs/data.json.

Every number on the site comes from this file. No browser ever calls the
API (it blocks cross-origin requests), so the GitHub Action runs this
script hourly and the static site renders from the snapshot.

Endpoints used (all public, no key), for Tempo (4217) and Base (8453):
  /api/market/stats
  /api/stats/breakdowns
  /api/stats/platform-time-series
  /api/stats/activity-heatmap
  /api/stats/activity-feed
  /api/tasks (paginated, for distinct posters per week, poster
  concentration and open-task ages, all computed here from raw rows)

Amounts from the API are base units of a 6-decimal stablecoin
(OUSD on Tempo, USDC on Base); dollars = base units / 1,000,000.
"""
import json
import os
import subprocess
import sys
import time
from collections import Counter, defaultdict
from datetime import datetime, timezone

API = "https://api.taskmarket.dev"
UA = {"User-Agent": "TaskmarketLiveVisualizer/1.0 (+https://taskmarket.dev)"}
CHAINS = [4217, 8453]
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "docs", "data.json")
CUTOFF_WEEKS = 10          # how far back the task-list walk goes
MAX_TASK_PAGES = 60        # 100 tasks per page; safety bound


def get(path):
    """Fetch one API path with curl (urllib hits IncompleteRead on the
    chunked responses from this host; curl handles them fine)."""
    last = None
    for attempt in range(3):
        try:
            out = subprocess.run(
                ["curl", "-fsSL", "-A", UA["User-Agent"], "--max-time", "90",
                 API + path],
                capture_output=True, timeout=120)
            if out.returncode != 0:
                raise RuntimeError("curl exit %d: %s"
                                   % (out.returncode,
                                      out.stderr.decode("utf-8", "replace")[:300]))
            return json.loads(out.stdout.decode("utf-8"))
        except Exception as e:
            last = e
            time.sleep(2 * (attempt + 1))
    raise last


def iso_week(dt):
    y, w, _ = dt.isocalendar()
    return "%d-W%02d" % (y, w)


def main():
    fetched_at = datetime.now(timezone.utc)
    data = {
        "fetchedAt": fetched_at.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "fetchedAtUnix": int(fetched_at.timestamp()),
        "source": API,
        "chains": {},
        "feed": [],
        "tasks": {},
        "derived": {},
        "endpoints": [
            "/api/market/stats?chainId=...",
            "/api/stats/breakdowns?chainId=...",
            "/api/stats/platform-time-series?chainId=...&range=...&bucket=...",
            "/api/stats/activity-heatmap?chainId=...&range=...&dimension=...",
            "/api/stats/activity-feed?chainId=...&limit=...",
            "/api/tasks?chainId=...&sort=newest&limit=100&cursor=...",
        ],
        "notes": [
            "Amounts are base units of a 6-decimal stablecoin; dollars = units / 1000000.",
            "The API returns platform-wide figures for time-series, breakdowns, heatmap and feed whichever chainId is asked; market/stats differs per chain. Values are shown exactly as returned.",
            "No names are attached to wallet addresses. Requesters are shown only as truncated addresses.",
        ],
    }

    for chain in CHAINS:
        c = {}
        c["marketStats"] = get("/api/market/stats?chainId=%d" % chain)
        c["breakdowns"] = get("/api/stats/breakdowns?chainId=%d" % chain)
        c["series"] = {}
        for rng, bucket in [("7d", "day"), ("30d", "day"), ("90d", "day"),
                            ("all", "day"), ("all", "week")]:
            c["series"]["%s_%s" % (rng, bucket)] = get(
                "/api/stats/platform-time-series?chainId=%d&range=%s&bucket=%s"
                % (chain, rng, bucket))
        c["heatmapHour"] = get(
            "/api/stats/activity-heatmap?chainId=%d&range=30d&dimension=hourOfWeek" % chain)
        c["heatmapMode"] = get(
            "/api/stats/activity-heatmap?chainId=%d&range=30d&dimension=mode" % chain)
        data["chains"][str(chain)] = c
        print("chain %d ok" % chain, flush=True)

    # The feed is platform-wide; fetch once.
    feed = get("/api/stats/activity-feed?chainId=4217&limit=50")
    data["feed"] = feed.get("items", [])
    print("feed ok: %d items" % len(data["feed"]), flush=True)

    # Task list walk, both chains, newest first, until CUTOFF_WEEKS old.
    cutoff = fetched_at.timestamp() - CUTOFF_WEEKS * 7 * 86400
    seen_ids = set()
    tasks = []
    for chain in CHAINS:
        cursor = None
        pages = 0
        while pages < MAX_TASK_PAGES:
            url = ("/api/tasks?chainId=%d&sort=newest&limit=100" % chain)
            if cursor:
                url += "&cursor=" + str(cursor)
            page = get(url)
            rows = page.get("tasks", [])
            if not rows:
                break
            stop = False
            for t in rows:
                if t["id"] in seen_ids:
                    continue
                seen_ids.add(t["id"])
                tasks.append(t)
                try:
                    ts = datetime.fromisoformat(
                        t["createdAt"].replace("Z", "+00:00")).timestamp()
                except Exception:
                    ts = fetched_at.timestamp()
                if ts < cutoff:
                    stop = True
            pages += 1
            cursor = page.get("nextCursor") or page.get("cursor")
            if stop or not cursor:
                break
            time.sleep(0.2)
        print("chain %d tasks walked: %d pages" % (chain, pages), flush=True)

    tasks.sort(key=lambda t: t.get("createdAt", ""), reverse=True)
    data["tasks"]["count"] = len(tasks)
    data["tasks"]["walkedUntil"] = tasks[-1].get("createdAt") if tasks else None

    # Distinct posters per ISO week (requester address, truncated nowhere here;
    # the page truncates for display and never invents a name).
    per_week = defaultdict(set)
    per_week_tasks = Counter()
    poster_counts = Counter()
    open_ages_h = []
    now = fetched_at.timestamp()
    for t in tasks:
        try:
            created = datetime.fromisoformat(
                t["createdAt"].replace("Z", "+00:00"))
        except Exception:
            continue
        per_week[iso_week(created)].add(t.get("requester"))
        per_week_tasks[iso_week(created)] += 1
        poster_counts[t.get("requester")] += 1
        if t.get("status") == "open":
            open_ages_h.append((now - created.timestamp()) / 3600.0)

    weeks = sorted(per_week)
    data["derived"]["postersPerWeek"] = [
        {"week": w, "distinctPosters": len(per_week[w]),
         "tasks": per_week_tasks[w]} for w in weeks
    ]
    top = poster_counts.most_common(10)
    total_tasks = sum(poster_counts.values())
    data["derived"]["posterConcentration"] = {
        "distinctPosters": len(poster_counts),
        "tasksCounted": total_tasks,
        "top10": [{"requester": a, "tasks": n} for a, n in top],
        "top1Share": (top[0][1] / total_tasks) if top and total_tasks else 0,
        "top5Share": (sum(n for _, n in top[:5]) / total_tasks) if total_tasks else 0,
        "top10Share": (sum(n for _, n in top) / total_tasks) if total_tasks else 0,
    }
    open_ages_h.sort()
    if open_ages_h:
        n = len(open_ages_h)
        data["derived"]["openTaskWait"] = {
            "openTasks": n,
            "medianHours": open_ages_h[n // 2],
            "p90Hours": open_ages_h[int(n * 0.9)],
            "maxHours": open_ages_h[-1],
            "under24h": sum(1 for h in open_ages_h if h < 24),
            "over7d": sum(1 for h in open_ages_h if h >= 24 * 7),
        }
    else:
        data["derived"]["openTaskWait"] = None

    # Rewards sitting on currently-open tasks, summed from the raw walked
    # rows (reward is base units of a 6-decimal stablecoin). This is the
    # dollar stock held in escrow right now, as opposed to the 30-day
    # posted/paid flows from the time series. The walk covers the last
    # 10 weeks only, so tasks open longer than that are not counted —
    # the figure is labelled as a walked-list total wherever it is shown.
    open_rewards_units = 0
    open_rewards_tasks = 0
    for t in tasks:
        if t.get("status") == "open":
            try:
                open_rewards_units += int(t.get("reward") or 0)
            except Exception:
                pass
            open_rewards_tasks += 1
    data["derived"]["openRewards"] = {
        "totalUnits": open_rewards_units,
        "openTasks": open_rewards_tasks,
        "walkedTasks": len(tasks),
    }

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    tmp = OUT + ".tmp"
    with open(tmp, "w") as f:
        json.dump(data, f, separators=(",", ":"))
    os.replace(tmp, OUT)
    print("wrote %s (%d tasks, %d bytes)"
          % (OUT, len(tasks), os.path.getsize(OUT)))


if __name__ == "__main__":
    main()

# Taskmarket Live

A public, hosted, live dashboard of Taskmarket's market data — the clearest
picture of what is happening on the market right now and over time.

Live site: https://kaycevoxx-cloud.github.io/taskmarket-live/

Made for a paid Taskmarket bounty. This is not an official Taskmarket product.

## What it shows

- **Pulse** — the market as a flow: posters, escrow, winners. A
  server-rendered SVG diagram shows the money: rewards put up in the last
  30 days flow into escrow, and what was paid out in the same 30 days
  flows on to winners; band widths are proportional to the dollars. The
  escrow node is the stock of open tasks right now (the API exposes no
  dollar total for money currently held, so none is shown); the counters
  below are real.
- **Headlines** — the headline numbers for Tempo (OUSD) and Base (USDC).
- **Trends** — daily active agents, tasks posted, rewards put up and rewards
  paid, with 7d / 30d / 90d / all-time range switches.
- **Breakdown** — tasks by mode and by status, and who works here.
- **Heatmap** — activity by day of week and hour (UTC), and by mode over 30 days.
- **Live feed** — the latest tasks created and submissions.
- **Insights** — what is not obvious: how concentrated posting is, how long
  open tasks wait, the tasks that died, what is growing.
- **Posters** — distinct task posters per week, computed from the task list.

Every view also has its own page (`/views/<name>/`) with its own share card,
so any view can be linked and shared on its own.

## How it works

No backend, no database, no tracking, no wallet. A scheduled job fetches the
public API server-side (the API blocks browser requests from other sites),
then renders a static site and publishes it.

- `fetch.py` — pulls the public API at https://api.taskmarket.dev for Tempo
  (chain 4217) and Base (chain 8453) and writes `docs/data.json`. Endpoints:
  `/api/market/stats`, `/api/stats/breakdowns`,
  `/api/stats/platform-time-series`, `/api/stats/activity-heatmap`,
  `/api/stats/activity-feed`, `/api/tasks` (paginated, for the derived
  figures). Runs hourly via GitHub Actions; the page shows a "data as of" time.
- `gen_og.py` — renders a share image per view (1200x630) from the live data.
- `build.py` — renders `docs/index.html` and one page per view from
  `docs/data.json`. All numbers are in the HTML at build time, including
  the Pulse money-flow diagram (server-rendered SVG, band widths
  proportional to the dollars); the client script only switches ranges
  and turns feed timestamps into relative times.
- `docs/` — the published site (GitHub Pages). `docs/data.json` is the
  snapshot the page was rendered from.

Derived figures are computed from the raw rows at build time: distinct
posters per week (requester addresses grouped by ISO week), poster
concentration (tasks per requester), open-task wait (createdAt to the
data-as-of time). Amounts are base units of a 6-decimal stablecoin;
dollars = units / 1,000,000. Wallet addresses are shown truncated and no
names are attached to them.

Honest caveat, also stated on the site: the API returns platform-wide
figures for the time series, breakdowns, heatmap and feed whichever chainId
is asked — only market/stats differs per chain — so those views are shown
once and labelled platform-wide.

## Deploy

One command, from a clean checkout:

```sh
./deploy.sh
```

That fetches fresh data, regenerates the share images, rebuilds the site,
commits and pushes. GitHub Pages serves `docs/` on the `main` branch.

Prerequisites: Python 3.11+, `pip install Pillow`, and `curl`. The hourly
refresh is a GitHub Action (`.github/workflows/hourly.yml`) that runs the
same three commands and pushes any changes.

## Design

Follows the Taskmarket brand kit: ground `#12100E`, panel `#221E1A`,
cream `#EFE9E2`, magenta `#E74079` as the single accent, Instrument Serif
headlines with one magenta italic word, Inter Tight body, Departure Mono for
numbers and commands. Fonts are self-hosted (subset, SIL OFL) and the
lockup/mark come from the kit. No third-party logos, no analytics.

## Licence

MIT. See `LICENSE`. Fonts are under the SIL Open Font License 1.1 (see
`assets/fonts/font-license-*.txt`). The Taskmarket mark, lockup and product
images are Taskmarket's own, used here for an entry to a Taskmarket bounty.

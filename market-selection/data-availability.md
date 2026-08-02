# data-availability.md — dimension D, verified by fetching

Every row below was produced by an HTTP request made on 2026-08-02 and a parse
of what came back. **A link is not evidence.** LEDGER T003 is a data source that
was assumed to exist and was 404; this file exists so that does not repeat.

Artifacts: `reports/data_sources_probe.json`, `_probe2.json`, `_probe3.json`,
`reports/sackmann_forks.json`.

Result: **54 of 79 probes returned parseable content.** The failures are listed
as prominently as the successes, because "we thought this existed" is the
failure mode being guarded against.

---

## ⚠ Confirmed dead, and one of them is load-bearing

### Sackmann's ATP/WTA match archive is gone — re-verified, and worse than recorded

STATUS.md says the upstream repos are 404. That is now independently confirmed
and sharpened:

| Probe | Result |
|---|---|
| `api.github.com/repos/JeffSackmann/tennis_atp` | **404** |
| `api.github.com/repos/JeffSackmann/tennis_wta` | **404** |
| `api.github.com/users/JeffSackmann/repos` | **200 — exactly ONE public repo** |
| That one repo | `tennis_MatchChartingProject`, pushed 2026-05-25, 742 MB |
| `atp_matches_2026.csv`, `atp_matches_2025.csv` raw | 404 |

The account still exists. The match-results repos were deleted from it. This is
not a rename or an outage.

**Search for a surviving mirror: not found, but not disproved.** 660 repos match
`tennis_atp` and 160 match `atp_matches`. I checked the 23 most-recently-updated
candidates at `{master,main}/atp_matches_{2025,2026}.csv` — **none carried a
readable file**. That is 23 repos at 4 paths each, not an exhaustive search.
GitHub *code* search would settle it and needs an authenticated token, which
this session does not have. **Reported as "not found", not as "does not exist".**

It also would not reopen the tennis thread: T006's verdict (the model loses to
the bookmakers, +0.01922 Brier, n=2,645) was measured on data that has nothing
to do with the 2026 coverage gap. Restoring the feed would relieve T002's
binding constraint, not T006's gate.

### Also confirmed dead

| Source | Was expected to give | Actual |
|---|---|---|
| **Oracle's Elixir** (LoL) | the standard free LoL match dataset | **`NoSuchBucket`** — the S3 bucket itself is deleted, on both the 2025 and 2026 files and both hostname forms |
| **HLTV** (CS2) | CS2 results | **403 Cloudflare** interstitial |
| **FBref** (soccer) | the source behind `worldfootballR` | **403 Cloudflare** interstitial |
| **DataGolf** | golf model inputs | **403** — paid |
| **vlr.gg unofficial API** (Valorant) | Valorant results | **402 Payment Required** |
| **api.football-data.org** MLS competition | MLS fixtures | **403** without a key (the root `/competitions` list is open) |
| **Binance** `api.binance.com` | BTC klines | **451** geo-blocked — but `data-api.binance.vision` serves the same data, 200 |
| **stats.nba.com** | NBA advanced stats | connection reset even with browser + referer headers |
| **FRED** | macro series | 400 without an API key |
| ESPN **boxing** scoreboard | boxing results | 404 — ESPN has no boxing scoreboard endpoint |
| **538** approval CSV | poll data | 200 and 310 KB, but parses to **0 columns** — flagged SUSPECT, not usable as-is |

---

## Verified live, by family

### Baseball — MLB (KXMLBGAME, KXMLBTOTAL, KXMLBRFI, KXMLBSPREAD)

**The richest free data of any family on either venue.** Nothing else is close.

| Source | Verified | Coverage | Backfill | Notes |
|---|---|---|---|---|
| **MLB StatsAPI** `statsapi.mlb.com` | 200, no key | every game, live | yes, full history | `/schedule`, `/teams`, and `/game/{id}/feed/live` returned **885 KB for a single game** — pitch-by-pitch, lineups, substitutions, weather, umpires |
| **Baseball Savant / Statcast** | 200, CSV | **2,923 rows × 119 columns for ONE DAY** | yes, to 2015 | pitch-level: release speed, spin, launch angle, exit velocity, expected wOBA |
| **Retrosheet** game logs | 200, 466 KB zip | 1871→ | yes | play-by-play history |
| **pybaseball** | repo live, pushed 2026-01-04 | wrapper | — | maintained-ish |

Timestamp quality: StatsAPI carries per-event timestamps and the live feed is
push-fresh, so a pre-game anchor is constructible without look-ahead. **This is
the only family where the free data is richer than the market's own resolution
source.**

### Baseball — NPB and KBO (KXNPBGAME, KXNPBTOTAL, KXKBOGAME)

Kalshi trades these heavily (NPB ~112k trades/day preliminary, KBO ~35k). The
data is **markedly thinner than MLB**:

| Source | Verified | Notes |
|---|---|---|
| NPB official `npb.jp/bis/2026/stats/` | 200, 59 KB HTML | official stats, **scrape required**, no API |
| KBO official `koreabaseball.com` | 200, 80 KB HTML | ASP.NET postback pages, **scrape required** |
| `armstjc/Nippon-Baseball-Data-Repository` | repo live, pushed **2026-07-28** | actively maintained community mirror |
| `aaacevedo95/NPB-Scraper` | live, pushed 2025-07-28 | stale by a year |
| KBO repos | 10 matches, all small/personal, most recent 2026-07-22 | no canonical dataset |

**No Statcast equivalent, no free odds history, no injury feed in English.**
Structured data exists but must be built. This is the "rich market, thin data"
quadrant.

### Soccer (KXLIGAMXGAME, KXMLSGAME, KXUSLGAME, KXCLUBFGAME, KXINTLFRIENDLYGAME)

| Source | Verified | Coverage | Notes |
|---|---|---|---|
| **football-data.co.uk `MEX.csv`** | 200 | **4,673 matches × 25 cols** | Liga MX, with **closing odds**: Pinnacle (PSCH/D/A), Max, Avg, Bet365 |
| **football-data.co.uk `USA.csv`** | 200 | **6,069 matches × 25 cols** | MLS, same columns |
| football-data.co.uk `E0.csv` | 200 | 380 matches × **132 cols** | Premier League — shots, corners, cards, and ~12 books' odds |
| **StatsBomb open-data** | 200, repo live, pushed 2026-05-26 | **80 competitions** | event-level: xG, pass locations, pressure |
| **ClubElo** `api.clubelo.com` | 200, CSV | **593 clubs** with Elo, daily | free, no key, backfillable by date |
| openligadb | 200 | 306 matches/season | German leagues |
| understat | 200 HTML | xG tables | scrape |
| openfootball MLS json | **404** | — | the MLS file specifically is missing |

**The bookmaker closing line is the important one.** It is what made LEDGER
T012/T013 possible for tennis — measuring Kalshi against a sharp reference
rather than against a model. Liga MX and MLS both have it, free, backfillable.

### Tennis (KXITFMATCH, KXATPMATCH, KXWTAMATCH, KXATPCHALLENGERMATCH, KXITFWMATCH)

The market is enormous — ITF alone is the single busiest sports family on the
tape — and **the data is the worst-positioned of any liquid family**.

| Source | Verified | What it gives | The catch |
|---|---|---|---|
| Sackmann `tennis_atp` / `tennis_wta` | **404, deleted** | was: every tour match, 1968→, with serve stats | gone; local mirror frozen at 2026-06-02 |
| **MatchChartingProject** | **200, live**, pushed 2026-05-25 | `charting-m-matches.csv` **7,566 matches × 15 cols**; `charting-m-stats-Overview.csv` **56,850 rows × 20 cols** (serve_pts, aces, dfs, first_in, first_won, second_won, bk_pts, bp_saved, return_pts_won, winners, unforced) | **volunteer-charted** — selection is toward famous matches, so it is not a random sample of the tour, and it barely touches ITF/Challenger |
| tennisabstract.com | 200 HTML | player pages | scrape |
| ultimatetennisstatistics.com | 200 HTML | rankings, stats | scrape |
| tennis-data.co.uk | root **300 Multiple Choices**; `alldata.php` index 200 | historical odds incl. the Betfair close | file naming needs resolving from the index page; **T014 says Pinnacle coverage collapsed to 5.1% in 2026** |
| ESPN tennis scoreboard | **200, 712 KB** | live scores/draws for ATP | settlement-grade, not predictive |

**The structural problem, restated with numbers.** LEDGER T001/T018: ITF is
~76% of Kalshi's tennis book, and Sackmann carried serve stats on only **4.6%
of futures rows** even when it existed. So the tier that trades has no features
and the tier with features barely trades. Losing Sackmann made the good half
worse without helping the big half.

### Golf (KXPGATOUR, KXLPGATOUR, KXKFTOUR, KXPGATOP5/10/20)

KXPGATOUR is the **highest 24 h dollar volume series on the exchange**
(23.2 M).

| Source | Verified | Notes |
|---|---|---|
| **ESPN golf scoreboard** | 200, **1.14 MB**, event "Rocket Classic" | full field, live leaderboard, hole-by-hole |
| ESPN golf **leaderboard** endpoint | 404 | wrong path; the scoreboard one works |
| DataGolf | **403, paid** | the good predictive source is not free |
| GitHub PGA scrapers | 4 repos, most recent **2025-03-13** | all stale, all personal |

**Free golf data is scores, not skill.** Strokes-gained — the only golf feature
with real predictive content — is behind DataGolf/PGA Tour paywalls. This is a
"four numbers everyone has" family despite huge volume.

### Esports (KXLOLGAME, KXVALORANTGAME, KXCS2GAME)

| Source | Verified | Notes |
|---|---|---|
| **Leaguepedia cargo API** | 200 — but only **372 bytes** on a 20-row query | responds, content thin; needs re-querying before it is called usable |
| **Liquipedia API** | 200, 344 KB | works, but Liquipedia's terms require a 2 s rate limit and a custom UA |
| Oracle's Elixir | **bucket deleted** | was the canonical free LoL dataset |
| vlr.gg unofficial API | **402** | Valorant |
| HLTV | **403 Cloudflare** | CS2 |
| OpenDota (Dota, as a control) | 200, 100 pro matches, full schema | shows what a healthy free esports API looks like — and it is for a game Kalshi does not list |

Polymarket has **$15.1 M/24 h on Esports and $14.1 M on League of Legends
alone** — the largest single-tag volumes on that venue after Sports/Games —
against **median spreads of 30¢ and 44¢**. Huge money, huge spreads, and the
free data layer just collapsed.

### Crypto (KXBTCD, KXBTC15M, KXETHD, KXBTCY …)

| Source | Verified | Notes |
|---|---|---|
| Binance `data-api.binance.vision` | 200 | klines; the main host is 451 geo-blocked |
| Coinbase Exchange candles | 200, 350 candles | free |
| Kraken OHLC | 200, 57 KB | free |
| Deribit `get_instruments` | 200, **724 KB** | full options chain, free |

This is dimension D's floor case and the reason it belongs in the ranking:
**price, strike, time, implied vol — four inputs, and every participant has all
four.** LEDGER C010 already measured the consequence: no model beats the mid on
250 events, with a positive control (C008) proving the test could have found a
5% bias.

### Weather (KXHIGHLAX, KXHIGHPHIL …)

| Source | Verified | Notes |
|---|---|---|
| **NWS API** `api.weather.gov` | 200 — station observations and gridpoint forecasts | the exact product Kalshi settles on |
| NOAA GHCN daily | 200 | full history |

Perfect, free, settlement-grade data — and the prior study found **zero fills**.
This family is the reason dimension A is the kill switch and not dimension D.

### Politics / Economics

| Source | Verified | Notes |
|---|---|---|
| BLS public API | 200 | CPI series, no key |
| US Treasury yield curve CSV | 200, 146 rows × 15 cols | free |
| FiveThirtyEight `data` repo | 200 — **last push 2025-02-25** | 17 months stale |
| 538 approval CSV | 200/310 KB but **0 columns parsed** | SUSPECT — do not use until the format is resolved |
| FRED | **400** | needs a key |

### ESPN as a cross-cutting source

`site.api.espn.com` is undocumented, unauthenticated, and returned 200 on MLB,
NBA, tennis and MLS scoreboards (6 KB – 712 KB each). **ESPN is the declared
settlement source for 631 Kalshi series** — more than any other. So for a large
part of the exchange the settlement feed itself is free and machine-readable.

That is worth stating precisely because it cuts the *wrong* way for edge: a
settlement source everyone can poll is a source of *speed*, not of *view*. It
tells you the answer at the same moment it tells everyone else.

---

## Summary: which families could support a private view

| Family | Free data depth | Backfillable | Verdict on D |
|---|---|---|---|
| **MLB** | Statcast 119 cols/pitch + full live feed + Retrosheet | yes, to 2015/1871 | **highest on either venue** |
| **Soccer (Liga MX / MLS)** | 25 cols + **closing odds**, StatsBomb events, ClubElo | yes | **high** |
| Soccer (EPL) | 132 cols + 12 books | yes | high, but Kalshi barely lists it |
| NPB / KBO | official HTML + one live community repo | scrape-dependent | **medium — must be built** |
| Tennis | MatchCharting only; tour archive deleted | partial, biased sample | **degraded, and worst where the market is biggest** |
| Golf | scores yes, strokes-gained no | scores only | **low despite the volume** |
| Esports | canonical dataset deleted; wikis behind rate limits | poor | **low and falling** |
| Crypto | four inputs, universally held | yes | **lowest — by construction** |
| Weather | perfect and free | yes, to 2003 | irrelevant: no counterparty |

## Live-only sources that cannot be backfilled

Started or flagged for immediate recording:

1. **Kalshi order-book depth** — no historical endpoint at all. Being recorded
   now across 85 families (`data/depth_broad/`). Every hour not recorded is
   gone.
2. **Kalshi trade tape** — appears re-pullable within the ~69-day window via
   `min_ts`/`max_ts`, so **not** urgent. Flagged for confirmation rather than
   assumed.
3. **ESPN live game state** — the scoreboard endpoints expose current state
   only; there is no free history endpoint. In-play work would need this
   recorded from now.
4. **archive.pmxt.dev** — frozen, not rolling (see `reports/pmxt_coverage.md`).
   Being mirrored as insurance against an abandoned bucket.

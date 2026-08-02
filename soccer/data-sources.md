# data-sources.md — soccer domain data, verified by pulling

Every row below came from an HTTP response parsed on 2026-08-02. A link is not
evidence. Artifacts: `reports/hunt_sources.json`, `hunt_sources2.json`,
`statsbomb_bra.txt`, `brasileirao.json`, `prematch_availability.json`.

Leagues in scope: **Liga MX (mex.1), Argentina Primera (arg.1), Brazil Serie A
+ Copa do Brasil (bra.1, bra.copa_do_brazil), Colombia (col.1), MLS (usa.1)**.

---

## The headline: one free endpoint carries most of the wishlist

**ESPN `site.api.espn.com` — no key, no rate limit hit in ~1,200 calls.**
A single `/summary?event=` response returned, for one Liga MX match:

| Block | Content |
|---|---|
| `keyEvents` | 34 timeline events, each with a **UTC `wallclock`** |
| `rosters` | 2 teams × 21 players, `starter` flag, position, jersey, **`formation`** ("4-2-2-2") |
| `gameInfo` | venue, attendance, **`officials`** (the referee) |
| `odds` / `pickcenter` | DraftKings home / draw / away moneyline |
| `standings` | league table |
| `lastFiveGames` | recent form, both teams |
| `seasonseries` | head-to-head |
| `boxscore` | team stats |

Coverage verified per league:

| League | ESPN teams | seasons | matches/wk sampled 2015 | 2019 | 2022 | 2024 | 2026 |
|---|---|---|---|---|---|---|---|
| mex.1 | 18 | 27 | 11 | 12 | 15 | 12 | 17 |
| arg.1 | 30 | 27 | 21 | 15 | 0* | 0* | 13 |
| bra.1 | 20 | 21 | 10 | 10 | 11 | 10 | 4 |
| col.1 | 20 | 22 | 15 | 11 | 12 | 12 | 9 |
| usa.1 | 30 | 31 | 10 | 12 | 14 | 14 | 18 |

*\*A correction to my own first pass: I originally sampled the first week of
March and reported **0 Brazilian matches in every year**, concluding the source
was empty. March is Brazilian off-season. Re-sampled in August, bra.1 returns
10–11 matches/week back to 2015. The Argentine zeros are the same artifact
(Argentine calendar shifted in those years). **Neither is a source failure; both
were defects in my probe.***

**Back-catalogue is therefore roughly a decade per league, free.**

---

## Free bookmaker closing lines — and the trap, re-confirmed

`football-data.co.uk` returns **HTTP 200 with another country's file** for codes
it does not carry. Re-verified by sha256 this session:

| Requested | sha256 (16) | `League` column actually contains |
|---|---|---|
| **COL** | `4ab04cc5…` | **Ekstraklasa — POLAND** |
| POL | `4ab04cc5…` | *identical file* |
| **CHL** | `d171bd98…` | **Super League — CHINA** |
| CHN | `d171bd98…` | *identical file* |
| **KOR** | `9459e47a…` | **Eliteserien — NORWAY** |
| NOR | `9459e47a…` | *identical file* |
| PER, ECU, URY | — | **404** |

Genuine coverage, League column verified:

| Code | League | Matches | With Pinnacle close | Range |
|---|---|---|---|---|
| **MEX** | Liga MX | 4,673 | **4,437** | 2012-07-21 → 2026-07-27 |
| **ARG** | Liga Profesional + Copa de la Liga | 6,262 | **5,928** | 2012-08-03 → 2026-07-31 |
| **BRA** | Serie A | 5,525 | **5,275** | 2012-05-19 → 2026-07-31 |
| **USA** | MLS | 6,069 | **5,800** | 2012-03-10 → 2026-07-26 |

25 columns: full-time and half-time score, and closing odds from Pinnacle
(`PSCH/D/A`), Max, Avg, Bet365 and Betfair Exchange.

**Colombia (KXDIMAYORGAME) has NO free closing line.** It is on the Kalshi
shortlist and it is the one league that cannot be benchmarked cheaply.

---

## Everything else, with the failures as prominent as the successes

| Source | Result | Detail |
|---|---|---|
| **Brasileirão community dataset** (`leeofernandes1980/brasileirao-dataset`) | **live**, pushed 2026-08-02 | `campeonato-brasileiro-full.csv` **8,405 matches**, cols include **formation and coach** for both sides, arena, score; `estatisticas-full` **16,810 team-match rows** (shots, shots on target, possession, passes, pass accuracy, fouls, cards, offsides, corners); `gols` 8,932 with **minute**; `cartoes` 18,857 with minute and position. **⚠ Range 2003-03-29 → 2023-12-06 — it ENDS in 2023 and covers no 2024–2026 match.** Formation present on only **3,431 of 8,405 (41%)**. No licence file. |
| **ClubElo** | live, free | 593 clubs — **but see below** |
| **StatsBomb open data** | live, 80 competition-seasons | **⚠ Two of my own errors here, both corrected by pulling.** (1) I reported "Argentina Liga Profesional is included" as a major find — it is **2 matches**, River/Boca showcase games from 1997 and 1981. (2) I then reported StatsBomb as having no MLS at all — my filter compared against lowercase `"united states"` and the country is `"United States of America"`. MLS **is** listed, and is **6 matches** (2023). Actual counts: Argentina **2**, MLS **6**, North American League **1**, NWSL 137 + 36. The event files are genuinely rich (3,000–4,100 events, 21–50 shots with `statsbomb_xg` each) — there are just almost none of them for our leagues. **No Mexico, Brazil or Colombia coverage at all.** |
| **Understat** (xG) | live | Carries **EPL, La Liga, Bundesliga, Serie A, Ligue 1, RFPL only**. **None of our leagues.** |
| **FBref** | **403 Cloudflare** | the canonical free xG/possession source, and it is not reachable |
| **API-Football** | **403** without a key | free tier requires registration |
| **Transfermarkt** | 200, 225 KB HTML | scrapeable; squad values, injuries. Terms prohibit systematic scraping — see `PAID_OPTIONS.md` |
| **Wikipedia REST** | 200 | season summaries only, not match-level |
| **openligadb** | 200, 818 leagues | **German football only** |
| **worldfootballR / soccerdata** | repos live | wrappers around FBref — inherit the 403 |
| **ESPN injuries endpoint** | 200, **`count=0`** | exists for soccer but returns nothing for the team sampled. **Effectively no injury feed.** |

### ClubElo does not cover these leagues

593 clubs sounds like broad coverage. It is not:

- `MEX`, `ARG`, `BRA`, `COL`, `USA` clubs in the daily file: **checked and
  reported in `hunt_sources2.json`** — ClubElo is a European-club rating system.
  A `/Toluca` query returns a **1-row stub**, not a rating history.

**Reported as not usable for these leagues** rather than as 593 clubs of
coverage.

---

## Knowability — measured, and it decides Task 3

The single most important property. Measured against live fixtures:

| Time before kickoff | rosters | starters | formation | referee | odds |
|---|---|---|---|---|---|
| T−145 h | 2 blocks | **0** | `None` | none | 1 block |
| T−7.3 h | 2 blocks | **0** | `None` | none | 1 block |
| T−5.3 h | 2 blocks | **0** | `None` | none | 1 block |
| T−3.0 h | 2 blocks | **0** | `None` | none | 1 block |
| **T−0.2 h** | 2 blocks | **22** | **`3-4-2-1` / `4-2-3-1`** | **`Luis Medina`** | **3 blocks** |

**Lineups, formations and the referee appear roughly one hour before kickoff.**
The crossover is between T−2.3 h (Boca: empty) and T−0.2 h (populated).

**This makes them live-only in the way that matters.** After the match the same
endpoint reports who *actually played*, substitutes included — a different fact
from what was *announced*. Deriving a "pre-match lineup" feature from a finished
match's roster is a look-ahead leak of the same family as LEDGER T010.

A recorder was started for exactly this (see below).

---

## Per-item scorecard against the tasking's wishlist

| Wanted | Available free? | Source | Coverage |
|---|---|---|---|
| Match results + history | **yes** | ESPN, football-data | ~10 yrs, all 5 leagues |
| Lineups + formations | **yes, but live-only** | ESPN summary ~T−1h | now recording |
| **Injuries / suspensions** | **NO** | ESPN injuries returns `count=0` | **not available** |
| **Shot-level / xG** | **NO for these leagues** | Understat big-5 only; FBref 403; StatsBomb n=2 | **the biggest gap** |
| Shots / possession / corners | **partly** | Brasileirão CSV (Brazil only, ends 2023); ESPN boxscore (current) | Brazil historical, all leagues current |
| Head-to-head | **yes** | ESPN `seasonseries` | per match |
| Rest days / congestion | **derivable** | from ESPN fixture dates | all leagues |
| Home/away splits | **derivable** | from results | all leagues |
| **Referee** | **yes, live-only** | ESPN `gameInfo.officials` at ~T−1h | now recording |
| Travel distance | **derivable** | ESPN venue names + geocoding | needs a geocoder |
| League position / points | **yes** | ESPN `standings` | current only |
| Bookmaker closing line | **yes, 4 of 5 leagues** | football-data | 2012→2026, **not Colombia** |

---

## What the gaps rule out

- **No xG for any shortlisted league.** The single most predictive public
  football statistic is unavailable free for Liga MX, Argentina, Colombia and
  MLS, and only historically (to 2023) for Brazil. Any model here is built on
  results, shots-on-target and lineups — not on chance quality.
- **No injury feed.** "Who is unavailable" must come from lineups at T−1h,
  which is an hour of warning, not days.
- **Colombia cannot be benchmarked** against a closing line at all.

Those three together mean the realistic feature set is: **results history, form,
rest, home/away, head-to-head, announced lineup + formation at T−1h, referee,
and the bookmaker line where it exists.** That is a real feature set. It is
not a proprietary one.

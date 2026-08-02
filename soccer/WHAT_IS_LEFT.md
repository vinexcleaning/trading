# WHAT_IS_LEFT.md — soccer data collection

Written 2026-08-02.

## Cheap and important

1. **Close the selection canary.** It returned UNTESTABLE because the outcome
   and the closing-line feature come from the same football-data row, leaving
   no "without" arm. ESPN's final score is independent and present on all 160
   matches. Re-run `check_selection` with the ESPN outcome. ~30 minutes.
   **Until this is done we do not know whether the 33% of matches carrying a
   closing line differ systematically from the 67% that do not.**
2. **Join the features that already exist but are not on the rows**: head-to-head
   (`seasonseries`), league position (`standings`), last-five form
   (`lastFiveGames`), rest days and fixture congestion (derivable from ESPN
   fixture dates), home/away splits. All are in data already fetched.
3. **Backfill the ESPN back-catalogue.** ~10 years per league is reachable
   (10–17 matches/week sampled back to 2015 for mex.1, col.1, usa.1, bra.1).
   The current dataset is 160 matches because that is Kalshi's window, not
   ESPN's. A results/form model can be fitted on a decade.

## Blocked

| Item | Blocker |
|---|---|
| xG for any shortlisted league | Understat is big-5 only; FBref is 403 Cloudflare; StatsBomb has 2 Argentina + 6 MLS matches. **No free xG exists for these leagues.** |
| Injury/suspension feed | ESPN's injuries endpoint returns `count=0` for soccer |
| Colombia closing line | football-data has no Colombian file; the `COL` code serves Poland |
| Pinnacle in 2026 | dropped from football-data entirely — 0 of 139 window rows |
| Copa do Brasil closing line | cup matches absent from the Serie A file |
| football-data during heavy use | the site 503s after ~20 rapid downloads; needs backoff |

## Not done for time

- Extending the in-play join to the deepest MLB families (backlog #1). The
  machinery in `src/inplay.py` is sport-agnostic apart from the roster
  resolution; MLB tickers carry team codes already parsed in
  `market-selection/src/cross_venue.py`.
- Travel distance (needs geocoding of ESPN venue names).
- The opponent's leg and the tie leg in the in-play study — only the scoring
  team's own contract was analysed.
- Sub-minute reaction latency. One-minute candles cannot resolve it; the pmxt
  L2 archive (2026-05-14 → 06-11, mirrored, 662 files) could, for the ~3 weeks
  where it overlaps.
- A control sample of non-scoring team-minutes, needed to interpret the +4¢
  pre-goal drift as anything other than selection.

## Two fixtures that never joined

`KXDIMAYORGAME 2026-07-25 Boyaca Chico vs Atletico Nacional` and
`KXMLSGAME 2026-07-16 Chicago Fire vs Vancouver`. Both team names resolve
correctly against the ESPN roster; there is simply no ESPN fixture on that date
±2 days. Most likely postponements. 2 of 162 — reported, not swept.

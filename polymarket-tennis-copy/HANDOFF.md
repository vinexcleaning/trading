# Handoff — read this first in a new session

Everything below is on disk. A new chat window loses the conversation, not the work.

## Where things stand

A working read-only analytics system for Polymarket tennis wallets: ingestion,
tennis classification, trade reconstruction, delay-aware copyability scoring,
wallet metrics, signals, paper trading, backtesting, a React dashboard, and 317
passing tests.

```bash
./.venv/Scripts/python.exe -m pytest        # 317 tests, ~6s, no network needed
```

## The findings that matter, and how they were reached

Run against **real** Polymarket data, not fixtures.

1. **Nothing passes the strict alert gates.** 40 arbitrary tennis wallets averaged
   **−5.6% copyable ROI**. Most participants lose money after delay.

2. **That first sample was methodologically wrong.** It took whoever held positions
   in ten markets and analysed the first 40 by insertion order — the crowd, not the
   best. `scripts/find_best_tennis_wallets.py` replaces it: it ranks 1,558 wallets
   by tennis notional traded across 160 markets, plus the profit/volume leaderboards.

3. **Coverage predicts reliability.** At <10% price-evidence coverage the copyable
   figures were noise; the one wallet with 69% coverage was the only one whose
   shallow numbers survived the deep pass. Always read `copyable_coverage` before
   `copyable_roi`.

4. **Static lifetime ranking is broken for a live tool.** It ranked
   `0x56b2c305969a` first (+$56.62/trade) — a wallet that **last traded 57 days
   ago**. `backend/app/services/allocation.py` fixes this: liveness is a hard gate
   (14 days), form is a 30-day window compared against the prior 90, and profit
   concentration reduces *position size* rather than rank.

5. **The current follow list** (`GET /api/wallets/rotation`, DB `data/best.db`):

   | Wallet | Form | Trades | Span | Last 30d | Stake |
   |---|---|---|---|---|---|
   | `0x4be1fa92e6ce` | 85.8 | 61 | 198d | +28.72%/trade | 61% |
   | `0x076daa87c4fe` | 42.6 | 481 | 50d | +2.33% | 100% |
   | `0x4e2c49398dd9` | 41.2 | 132 | 22d | +3.33% | 50% |
   | `0x0116108c25d3` | 33.4 | 89 | 50d | +0.98% | 45% |

   `0x4be1fa92e6ce` is the best candidate found: 198 days, still active,
   accelerating, **+24.3% copyable ROI at 100% price coverage**, P(edge) 86.5%.
   Read finding 6 before acting on that number.

6. **The screen does not survive out-of-sample validation.**
   `scripts/split_sample_test.py` ranks wallets on the first half of each record,
   measures the second, then deals every trade out at random thousands of times
   to see what the same screen produces when nobody has an edge. Across five
   configurations (copyable and raw, count and calendar splits, with and without
   winsorizing) **the selected wallet never beat the selection null out of
   sample** — best p was 0.155, and rank correlation between halves was ~0 in
   four of the five.

   Why the screen has no resolving power here: the return distribution is
   violently convex — 42% of trades lose everything, 19% pay over +100%, the best
   pays +937%, sd 1.26. With 12–30 trades per half the standard error on a
   half-mean is 25–40 percentage points, so a *random* screen over these same
   wallets produces a winner at +51% copyable ROI. Against that, +24.3% is
   unremarkable.

   Two specifics worth keeping:
   - `0x4be1fa92e6ce`'s second half is genuinely positive (**+19.2%**, n=31), but
     its median is **+6.6%** — even out of sample the mean is tail-carried. Cap
     returns at the pooled 95th percentile and its *first*-half edge collapses
     from +29.5% to +2.1%, i.e. the record that won it the ranking was almost
     entirely a few tails.
   - The identity of the winner changes with the metric, the split rule and the
     winsorization. A ranking that unstable is not a ranking.

   One configuration (raw, calendar split, winsorized) did show rank correlation
   +0.456 at p=0.033. That is one result out of five configurations tried, which
   is precisely the multiple-comparisons trap this script exists to catch. Do not
   promote it.

7. **Trade count, not ranking cleverness, is what kills the luck problem** — the
   user's push-back, and it measures out. `scripts/live_candidates.py` implements
   the screen as specified (not market-making, high win rate *vs the price a
   copier pays*, high trade count, >=1 week span, still active, recent form,
   realistic delay) and prints `luck_bar`: the edge the luckiest wallet shows in a
   skill-free population of the same sample sizes.

   That bar is **+48 points** across all 25 wallets — which include 1-trade
   records able to post a perfect score for free — and **+7 points** once a
   50-trade minimum applies. Demanding volume shrank the bar sevenfold. Finding 6
   was also measured on the noisiest available statistic (mean ROI, sd 1.26);
   win-rate-vs-price has sd ~0.5, about 2.5x tighter, and is the right yardstick.

   Current standings at a 15s delay, 5 wallets clearing the gates:

   | Wallet | n | Span | Quiet | Pays | Wins | Edge | Last 2d |
   |---|---|---|---|---|---|---|---|
   | `0x4be1fa92e6ce` | 61 | 198d | 0.1d | $0.40 | 45.9% | **+5.9p** | +3.1p |
   | `0xf148f9acb3d2` | 57 | 14d | 0.1d | $0.47 | 49.1% | +2.5p | +5.2p |
   | `0x99f0d31fdced` | 197 | 73d | 0.1d | $0.35 | 36.5% | +1.5p | −1.5p |
   | `0x0116108c25d3` | 78 | 50d | 0.3d | $0.97 | 97.4% | +0.6p | +4.2p |
   | `0x18f39c8683fe` | 50 | 9d | 0.6d | $0.70 | 64.0% | −6.2p | −5.0p |

   `0x4be1fa92e6ce` at +5.9p against a +7.0p bar is the closest thing to a
   candidate this project has produced. It does not clear it. At 61 trades the
   standard error on its win rate is 6.4 points, so the gap cannot be closed by
   analysis — only by more observations on that wallet.

   Two structural facts about it, found while checking whether it could be
   backfilled further:

   - **All 61 tennis positions are `settled`, none `closed` — it never trades
     out.** It buys and holds to resolution, every time. Good news for copying:
     only the entry needs matching, the exit takes care of itself, and exit delay
     is irrelevant. Bad news: capital is locked until the match resolves, and the
     `holding_seconds` defect therefore contaminates **100%** of its record, so
     any hold-duration factor in its score is meaningless rather than merely
     optimistic.
   - **The "198-day span" oversells it.** Monthly tennis trades run 1, 3, 3, 0,
     18, 11, 25 (Jan→Jul). April is empty. Its real active history is roughly the
     last 90 days; the long span is an artefact of a handful of early trades, and
     a span gate is easy to pass this way. Worth tightening the gate to "trades in
     N of the last M weeks" rather than first-to-last distance.

   **The luck bar must be computed over the volume-eligible pool, not the gate
   survivors.** Found by accident and it is the subtlest trap in the whole
   project: tightening the activity gate cut the pool from 6 wallets to 3, which
   dropped the bar from +7.1 to +4.5 points and flipped `0x4be1fa92e6ce` from
   fail to *pass* — without one wallet's record changing. Every wallet with enough
   trades was an independent chance to look good, so the bar is computed over
   everyone meeting `--min-trades` and is deliberately immune to the other gates,
   which are judgement calls made partly after seeing data. Pool sensitivity:

   | Bar | Pool |
   |---|---|
   | +4.5p | the 3 passing every gate (**wrong — flatters the winner**) |
   | +7.1p | the 6 with 50+ measured trades (**correct today**) |
   | +9.4p | the 12 with 50+ tennis trades (correct once backfill lands) |
   | +48.4p | all 25 measured wallets (inflated by 1–3 trade records) |

   Against the honest +7.1p bar, `0x4be1fa92e6ce`'s +5.9p **does not clear**.

   **Activity gate replaces span** (`statistics.active_periods`): weeks out of the
   last 8 containing at least one trade, default 4. This dropped `0xf148f9acb3d2`
   (57 trades, 2 active weeks) and `0x18f39c8683fe` (50 trades, compressed into
   ~2 weeks) — high trade counts earned in a single burst, which is precisely the
   reliability risk a span gate cannot see. Correction to the note above:
   `0x4be1fa92e6ce` is **8/8 weeks active**, so it passes a proper activity test.
   The "198 days oversells it" point is about the *length* of its record, not its
   recent consistency, which is genuine.

   Three specifics worth keeping:
   - `0x0116108c25d3` is the $0.95-favourite trap alive in the screen: 97.4% win
     rate, +0.6 points of edge. Any raw-win-rate ranking puts it near the top.
   - `0x076daa87c4fe` (481 trades, 143 in the last two days, +3.1p, the only
     wallet with enough volume for the statistics to bite) is **disqualified for
     holding both outcomes 72% of the time** — it is hedging or making the
     market, not taking a view. Whether a hedger is copyable at all is an open
     question, and it is the user's call.
   - Edge is flat from 10s to 60s delay, but **do not read that as "delay is
     harmless"**: 823 of the 1,164 usable observations come from 1-minute price
     bars, which cannot resolve sub-minute differences, and the modelled fill
     does not move at all in over half of 10s-vs-60s pairs. Measuring delay
     properly needs the second-level trade tape.

8. **The deep backfill tripled the data and the candidates got worse.** Completed
   2026-07-30. `0xeea3f08e8a36` went 86 → **1,874** tennis trades at 100% coverage,
   `0xc07d5961e7a3` 78 → 443, `0x076daa87c4fe` → 579, `0xeb77d9d56dcb` → 265,
   `0xff81cc85838c` → 257. Database now 71,497 positions, 45,414 copyability rows,
   **2.04M** price observations (was 1.22M). Wallets with 50+ measured trades went
   6 → 12, so the luck bar rose from +7.1 to **+7.7 points**, as predicted.

   Everything got worse, which is the finding:

   | Wallet | n | Pays | Wins | Edge | p | Both sides |
   |---|---|---|---|---|---|---|
   | `0xeea3f08e8a36` | 1874 | $0.48 | 49.5% | +1.5p | 0.094 | **86%** |
   | `0x076daa87c4fe` | 579 | $0.52 | 54.7% | +2.8p | 0.100 | **72%** |
   | `0xc07d5961e7a3` | 443 | $0.56 | 56.0% | −0.4p | 0.586 | **82%** |
   | `0xeb77d9d56dcb` | 265 | $0.68 | 60.4% | −7.9p | 0.997 | 42% |
   | `0x99f0d31fdced` | 219 | $0.35 | 37.9% | +3.2p | 0.180 | 8% |
   | `0x4be1fa92e6ce` | 66 | $0.43 | 45.5% | +3.0p | 0.356 | 6% |

   - **`0x4be1fa92e6ce` fell from +5.9p to +3.0p on five extra trades.** An estimate
     that moves three points on a 8% change in sample size was never a measurement.
   - **Its own split test is now negative**: picked on its first half at +7.7p, its
     second half paid **−1.7p**. This is the direct out-of-sample test on the
     headline candidate and it failed.
   - **Every wallet with enough volume to be statistically meaningful is a hedger.**
     The three largest hold both outcomes 72–86% of the time. Their edge is not
     copyable — a follower takes one leg of a position whose risk was cancelled by
     the other. Volume and directionality are anti-correlated in this population,
     which may be the structural reason the whole thesis is hard.
   - No wallet clears the +7.7p bar. Best is +3.2p, and that wallet's last-two-day
     edge is −2.4p.

   Also fixed: the screen had **no minimum-edge gate**, so `0xff81cc85838c` passed
   every rule with a **−4.9p** edge. `--min-edge` now defaults to 0.

9. **The search was 2% of the available evidence.** The discovery script scanned
   160 tennis markets and kept the top 60 wallets it saw; the database holds
   **10,834** tennis markets, 6,937 resolved with a known winner. Every
   conclusion up to finding 8 rests on 36 measurable wallets out of a field that
   is at least four figures.

   `scripts/sweep_tennis_tape.py` inverts the cost model. Per-wallet history
   ingestion takes minutes each and cannot reach five figures. A *market's* trade
   tape names every wallet that bet in it, the price each paid and the side taken
   — and the market record says who won. One request therefore scores every
   participant at once, and cost scales with markets rather than wallets.
   Measured: ~6,900 markets in about 2.5 hours, versus roughly 200 hours to fetch
   the same wallets individually. Resumable via its own `data/tape_scan.db`.

   `scripts/rank_tape.py` ranks the result. **One match = one call**, folded per
   (wallet, market, side) with a stake-weighted price. This matters enormously:
   counting raw trades instead produced a leaderboard topped by a wallet showing
   "98% over 57 bets" that had backed one player in **two matches**, with a
   binomial p-value of 0.00000 because 57 correlated trades were treated as 57
   independent calls. This is the same error `ReconstructedPosition` exists to
   prevent, reintroduced by working from raw tape. Every apparent star vanished
   when the fold was applied.

   Gate set, deliberately small — each extra knob is another chance to tune the
   screen until it flatters someone, which has already happened twice here:

   | Gate | Why |
   |---|---|
   | >=100 calls | the noise killer; free, so it goes first |
   | positive edge | a follow list containing losers is not a follow list |
   | quiet <=7d, active >=4/8 weeks | can't copy someone who stopped |
   | both sides <35% of matches | spreads are profitable and **uncopyable** — a follower takes the leg whose risk the other leg cancelled |
   | avg price <$0.85 | practical, not statistical: the edge metric already sinks favourite-buyers, but at 96c you need vast stakes for tiny returns and slippage eats them |
   | both halves of the record positive | the single most common way a screened wallet fools you |

   Everything else is displayed rather than filtered, so it can be judged by eye.

   Interim at 680 of 6,937 markets: **35,981 wallets seen**, 917 with 40+ calls,
   91 surviving all gates, best +16.4p — and **nobody clears the +21.6p luck
   bar**. The half-split gate alone cut 576 of 917, more than every other gate
   combined.

10. **The full-market answer: there is no detectable copyable edge.** Sweep
    completed 2026-07-30 — **6,937 matches, 1,768,617 trades, 42,652 wallets,
    zero errors, 41 minutes.** 493 wallets have 100+ calls; 53 survive every gate.

    The p-value distribution across those 493 is the finding, and it is not close:

    | Cutoff | Observed | Expected by chance | Ratio |
    |---|---|---|---|
    | p<0.05 | 17 | 24.7 | **0.69x** |
    | p<0.01 | 4 | 4.9 | 0.81x |
    | p<0.005 | 4 | 2.5 | 1.62x |
    | p<0.001 | 2 | 0.5 | 4.06x |
    | p<0.0001 | 0 | 0.05 | 0 |

    **At the conventional threshold there are fewer apparently-skilled wallets
    than pure noise would produce.** Benjamini–Hochberg returns **0 discoveries at
    FDR 5% and 10%**, and 1 at FDR 20%. The slight enrichment in the extreme tail
    (2 wallets at p<0.001 against 0.5 expected) is what a field of 493 coin-
    flippers looks like at its edges.

    Best candidates, all marginal:

    | Wallet | Calls | Avg price | Edge | p |
    |---|---|---|---|---|
    | `0x071f9c6bfa9c` | 119 | $0.74 | +13.0p | 0.00047 |
    | `0x39f6236ccd16` | 144 | $0.33 | +13.0p | 0.00076 |
    | `0xfe787d2da716` | 1465 | $0.47 | +3.9p | 0.00139 |

    `0xfe787d2da716` is the most credible *shape* — a small edge over a large
    sample beats a large edge over a small one — but with 493 tests, three wallets
    at p<0.0014 is roughly what chance delivers (0.7 expected, and the tail is
    lumpy).

    Note the luck bar **fell** from +21.6p to +13.2p as the sweep progressed, and
    top observed edges fell with it (+16.4p → +13.0p). More matches per wallet
    tightened every estimate and the apparent stars regressed. That is the
    signature of noise, not of a search closing in on something.

    **What this retires:** findings 5–8 were arguments about 36 wallets. This
    tested 42,652 over the platform's entire resolved tennis history. The earlier
    candidates were not unlucky picks from a good population — the population has
    no measurable skill in it.

11. **The edge exists, and it dies inside 15 seconds.** Findings 1–10 all score
    bets *held to resolution*, which makes a profitable short-term trader
    invisible — buy at 0.40, sell at 0.48, lose the match, and the outcome test
    records a loss on a trade that made money. `scripts/follow_through.py` closes
    that blind spot by measuring informed flow instead of outcomes: after a
    wallet buys, does the price move its way?

    | Follower delay | Wallets at t>3 | Expected by chance |
    |---|---|---|
    | **0s** (the wallet's own fill) | **32** | 0.47 |
    | 15s | 1 | 0.31 |
    | 60s | 2 | 0.40 |

    At zero delay the excess is overwhelming — 20 wallets at t>4 against 0.01
    expected. **Informed traders unquestionably exist in this market.** Measured
    from where a follower could actually enter, the effect is indistinguishable
    from noise.

    They are fast, not prescient. They react to in-play events (a break of serve)
    ahead of the tape and collect a cent or two. That also explains finding 10:
    they are not picking match winners, so an outcome-based test finds nothing —
    and a copier arriving 15s later finds nothing either, because the move is
    already complete.

    **This is the mechanism behind every negative result above, and it closes the
    thesis.** The user's realistic delay is worse than 15s, not better: a human
    approving each alert plus cross-venue matching to Kalshi puts them at 30–60s.

    Three measurement errors were made and fixed while establishing this, all the
    same error — fictional sample size:
    - Counting raw trades as independent calls (fixed: one match = one call).
    - Letting a wallet's *own* later trades count as the market moving for it. A
      32,000-trade wallet simply *is* the later price in matches it touches.
    - Clustering: 20 trades by one wallet in one match watch the same subsequent
      move. Treating them as independent gave t-statistics of 90 and 408 — the
      giveaway, since no financial signal legitimately reaches those.

12. **One candidate survives everything: `0x37c1ff27d21b`.** Found by the tape
    sweep at +10.1p (rank 3 of 493), then deep-backfilled and independently
    confirmed at **+8.9p on 192 delay-adjusted trades**, p=0.0079 — two different
    pipelines agreeing on the same wallet.

    | | |
    |---|---|
    | Trades / span | 192 over 224 days |
    | Pays / wins | $0.43 → 51.6% |
    | Edge | **+8.9 points** |
    | Halves | **+7.1 / +10.8** (second half stronger) |
    | Market-making | 3% |
    | Exit behaviour | **0 traded out, 196 held to settlement** |

    It holds everything to match end, so finding 11's 15-second decay does **not**
    apply to it — that finding concerns traders racing the tape for cents. This
    wallet picks match winners and waits, which is a different and copyable thing.
    No contradiction between the two results.

    **But it does not clear the bar for the search that found it.** The screen
    printed "+8.9 CLEARS the +5.3 bar" — that +5.3 is computed over the 15 wallets
    in `data/best.db`. This wallet was selected from **493 eligible wallets across
    the full sweep**, and the bar for a search that wide is **+13.2p**. Raising
    `--min-trades` from 50 to 100 shrank the local pool from 19 to 15 and dropped
    the bar from +7.8 to +5.3 — the pool-shrinking artefact from finding 7,
    resurfacing in a new guise. Any bar quoted for this wallet must be the
    search-wide one.

    Also unchanged: the out-of-sample check still fails. Ranked on first halves,
    it picks `0x99f0d31fdced`, whose second half paid −1.0p.

    **Frozen to `data/follow-list.json`** (4 wallets, 2026-07-30 06:01 UTC) with
    the pass mark corrected to the search-wide +13.2p. This is now the only open
    question in the project, and only forward data can settle it.

    Beware the shape of this result: a wallet that survives eleven filters is
    exactly what a large search produces from noise. Three wallets at p<0.0014 out
    of 493 was already consistent with chance (finding 10). `0x37c1ff27d21b` being
    the *most* interesting of 42,652 is not evidence it is good.

## The forward record (the only ungameable test)

Every backward-looking number here can be improved by choosing the wallet, the
window, the statistic or the delay after seeing the data — finding 6 is the proof
that this already happened once. A frozen list scored on later trades has no such
freedom left.

```bash
# 1. commit the list, before any forward data exists
DATABASE_URL="sqlite:///./data/best.db" ./.venv/Scripts/python.exe \
  scripts/live_candidates.py --min-recent-trades 3 --freeze data/follow-list.json

# 2. score it, days or weeks later
DATABASE_URL="sqlite:///./data/best.db" ./.venv/Scripts/python.exe \
  scripts/forward_record.py data/follow-list.json
```

Rules baked into the scorer, each blocking a specific self-deception:

- Only trades opened **strictly after** the freeze timestamp count.
- The verdict is the **pooled** edge across all frozen wallets, never the best
  one. Picking the best afterwards re-runs the selection the freeze prevents.
- The pass mark is `luck_bar` recomputed at the **forward** sample sizes, so a
  thin record faces a high bar — correctly, since a handful of trades cannot
  demonstrate anything.
- Wallets that stop trading report zero forward trades rather than being dropped,
  so a list that quietly died cannot read as one that held up.
- **Never regenerate a frozen file to "update" it.** Freeze a new one.

**Sequencing:** freeze *after* the in-flight deep backfill lands, not before —
the backfill roughly doubles the judgeable pool (see below), so a list frozen now
would be chosen from a needlessly thin candidate set. Waiting hours costs nothing
against a multi-week forward test.

## In flight

A deep backfill is running over the six highest-value under-covered wallets:
`0x4e2c49398dd9` (132 tennis trades, 42 measured), `0xc07d5961e7a3` (78, **0**),
`0xeea3f08e8a36` (86, 3), `0xeb77d9d56dcb` (86, 37), `0x0d2d845a6ff6` (59, 0),
`0xff81cc85838c` (52, 6). Backup at `data/best.db.bak-before-backfill`.

Only 12 wallets currently have 50+ completed tennis trades and 6 have usable
price evidence at that volume, which is why the screen has so little to work
with. Backfilling *these* wallets is the fix; backfilling the top candidate is
**not** — `0x4be1fa92e6ce` is already at 100% coverage with 19,870 transactions
ingested, so there is nothing left to recover from it. Its 61 tennis trades in
198 days are simply all it has made.

## Verified API constraints (do not re-derive)

- `prices-history` bottoms out at **1-minute fidelity**. Sub-minute follower
  delays come from the second-level trade tape or are labelled low-confidence.
  `startTs`/`endTs` with `fidelity=1` bypasses the per-interval minimum.
- `/activity` rejects **offset > 5000** (HTTP 400). The provider re-anchors on a
  timestamp and restarts the offset. Without this, an active wallet silently
  truncates — one wallet had 91,561 records and would have shown 2,000.
- Gamma `condition_id=` / `condition_ids=` **silently returns wrong markets**. Use
  `GET clob.polymarket.com/markets/{condition_id}`.
- Tennis tag id is **864**. `lb-api.polymarket.com/volume` and `/profit` work;
  `/leaderboard` 404s.
- `Market.liquidity` is **0 for closed markets** — unusable for historical capacity
  analysis.

## Known defects, unfixed

- **The follower model breaks for traded-out positions.** `follower_is_win`
  disagrees with the wallet's own `is_win` in **42.4%** of positions the wallet
  sold before resolution, against 5.2% for held-to-settlement ones. Example:
  position 399665, wallet bought 0.60 and sold 0.79 (`is_win=1`), and the
  copyability row records `follower_exit_price=0`, i.e. the follower was modelled
  as holding to resolution and losing. The follower is not being given the
  wallet's exit.

  **Blast radius:** every copier-edge figure for a wallet that trades out.
  Per-wallet mismatch rates — `0x37c1ff27d21b` **0/192**, `0x99f0d31fdced`
  **0/248**, `0x4be1fa92e6ce` 1/72, `0x4e2c49398dd9` 2/179, but
  `0x39f6236ccd16` **121/359 (33.7%, 231 traded out)**. The headline candidate is
  unaffected because it never trades out; `0x39f6236ccd16` is in the frozen list
  and its numbers should not be trusted.

  **Fix before scoring the forward record**, since the verdict is pooled and one
  contaminated wallet in four corrupts it. Either give the follower the wallet's
  exit price, or restrict copier metrics to held-to-settlement positions and say
  so.

- **`holding_seconds` is contaminated for settled positions.** It measures entry →
  `resolved_at`, and `resolved_at` is a metadata finalisation timestamp (values of
  336–360 hours on single matches), not match end. Positions that actually traded
  out average **0.9h**; settlement-held ones read 160h. The honest split is in
  `scripts/deep_backfill.py`'s report. This feeds the copyability hold-duration
  factor, so that factor is optimistic for settled positions.
- **Prematch/live classification is unaudited.** Long "live" holds look wrong; the
  phase split shouldn't be trusted until this is checked.
- **`roi` vs `copyable_roi` are different estimators.** `roi` is capital-weighted;
  `copyable_roi` is equal-weighted (a follower stakes flat per signal).
  `roi_equal_weighted` was added for a valid comparison — use that one for
  "cost of delay", never raw `roi`.

## Databases

| File | Contents |
|---|---|
| `data/best.db` | 152 wallets from targeted discovery, 6 deep-backfilled, 1.22M price observations |
| `data/real.db` | First 40-wallet arbitrary sample, 4 deep-backfilled |

## Commands

```bash
DATABASE_URL="sqlite:///./data/best.db" ./.venv/Scripts/python.exe scripts/live_candidates.py --show-all
DATABASE_URL="sqlite:///./data/best.db" ./.venv/Scripts/python.exe scripts/live_candidates.py --delay 60 --min-trades 100
DATABASE_URL="sqlite:///./data/best.db" ./.venv/Scripts/python.exe scripts/split_sample_test.py
DATABASE_URL="sqlite:///./data/best.db" ./.venv/Scripts/python.exe scripts/split_sample_test.py --metric raw --winsorize 95
DATABASE_URL="sqlite:///./data/best.db" ./.venv/Scripts/python.exe scripts/find_best_tennis_wallets.py
DATABASE_URL="sqlite:///./data/best.db" ./.venv/Scripts/python.exe scripts/deep_backfill.py 0xabc 0xdef
DATABASE_URL="sqlite:///./data/best.db" ./.venv/Scripts/python.exe -m uvicorn app.main:app --app-dir backend --reload
```

## Next steps, in order

1. **Paper-trade the follow list.** The engine exists and is unproven on live
   signals. Nothing should be trusted until it has a forward record. Finding 6
   makes this the only route left to evidence: the historical screen has been
   tested and cannot distinguish edge from noise, so a genuinely forward record
   is now the *sole* source of new information about these wallets.
2. **Get more trades per wallet, not more wallets.** The screen fails on sample
   size, not on ranking logic — no re-weighting fixes a 40pp standard error.
   Deep-backfilling the existing candidates to a few hundred usable copyable
   observations each would do more than discovering another hundred wallets.
   Re-run `split_sample_test.py` after; it is the acceptance test.
3. **Fix `holding_seconds`** to measure the economic exit, not redemption lag.
4. **Audit prematch/live** classification.
5. **Then, and only then**, consider Kalshi execution — the user can trade there
   but not on Polymarket, so the shape is: detect on Polymarket, alert, click-trade
   on Kalshi. The hard part is market matching (player-name normalisation, same
   event, and crucially the same retirement/walkover resolution rules).

## What the user cares about

- Wants a click-to-trade alert flow like their existing Kalshi bot, placing limit
  orders they approve — not auto-execution.
- Correctly pushed back that the entry gates were too strict and that recency
  matters more than lifetime record. `allocation.py` is the response.
- Correctly pushed back that penalising profit concentration unfairly punishes
  longshot strategies. Now affects sizing, not rank.
- Prefers plain money terms ("if you put $100 on every trade") over ratios.

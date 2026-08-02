# Cross-venue: the same MLB game on Kalshi and Polymarket

Standing backlog #3. Measured 2026-08-02 07:0x UTC. Artifact:
`reports/cross_venue_mlb.json`, script `src/cross_venue.py`.

**Unit of observation: one game side** (a single team's YES contract on both
venues). n = **66** matched sides across 40 games on 2026-08-02 → 08-04.

## How the join was made, and how it failed first

MLB was chosen because both venues list the same fixtures daily with
unambiguous identity. The join is exact: `{franchise pair} + game date`, on
both sides. No fuzzy title matching.

Two failures worth recording rather than quietly fixing:

1. **First version matched 0 of 76.** It keyed on nicknames ("mariners") while
   Kalshi names teams by city ("Seattle"). A join that matches nothing looks
   exactly like two venues that share no events — which would have been
   reported as a finding.
2. **Kalshi truncates two-team cities**: `Los Angeles D`, `Chicago WS`,
   `Chicago C`, `New York Y`. Adding those forms took the parse from 46 to 66
   of 76. The remaining 10 are `St. Louis`/`A's` variants, still unparsed and
   **counted, not dropped silently**.

Prices are executable on both sides, never mids. Kalshi's YES ask is
1 − (best NO bid) from `orderbook_fp`; Polymarket's is the best ask on that
team's own token from the CLOB `/book` endpoint, so the side is unambiguous.
Gamma's `bestBid`/`bestAsk` do not state which outcome they describe, and
guessing is the error class that produced LEDGER W015's inverted fee fit.

## Result

| Measure | Median | p75 | p90 | Max |
|---|---|---|---|---|
| \|mid gap\| between venues | **1.00¢** | 1.50¢ | 3.00¢ | 5.00¢ |
| Kalshi spread | 1.00¢ | — | 2.00¢ | — |
| Polymarket spread | 1.00¢ | — | 3.00¢ | — |

**Executable cross-venue round trips with positive net after both fees:
0 of 66.**

The arithmetic is not close and the mechanism is plain. At a ~50¢ price the two
venues' fees are 1.75¢ (Kalshi) + 5.00¢ (Polymarket) = **6.75¢**. The largest
gross gap observed anywhere in the sample was **4.00¢**, on KC/MIN. The gap
would have to roughly double its observed maximum, and do so persistently, to
pay for crossing.

Best single opportunity in the sample:

| Game | Side | Kalshi bid/ask | Poly bid/ask | Gross | Fees | **Net** |
|---|---|---|---|---|---|---|
| KC/MIN 08-04 | KC | 44.0 / 45.0 | 49.00 / 50.00 | +4.00 | 6.12 | **−2.12** |
| BOS/CWS 08-04 | CWS | 43.0 / 45.0 | 47.00 / 50.00 | +2.00 | 6.12 | **−4.12** |
| KC/MIN 08-04 | MIN | 54.0 / 55.0 | 50.00 / 51.00 | +3.00 | 6.34 | **−3.34** |

## What this settles

1. **The two venues agree.** A 1¢ median mid gap on 66 sides, against a 1¢
   tick on both, means the disagreement is at or below the resolution of the
   price grid. These are not segmented markets carrying different opinions.
2. **Kalshi dominates Polymarket on MLB moneyline.** Same median spread
   (1.00¢), same tick, **2.86× lower fee**. There is no price at which routing
   an MLB moneyline to Polymarket is correct on cost.
3. **Cross-venue arbitrage on this family is dead, and it is dead structurally
   rather than statistically.** It is not "no edge found at this n" — it is
   that the fee floor exceeds the observed maximum gap. The only way this
   family becomes tradeable across venues is a Polymarket fee change.

## Caveats, stated plainly

- **One snapshot in time**, not a time series. The gap *distribution* is
  measured; its *persistence* is not. A gap that appears and closes in seconds
  would look identical here to one that stands for hours.
- **MLB only.** Both venues list soccer, politics, and crypto in common; those
  were not swept. Politics is where the venues most plausibly disagree, because
  Polymarket's politics book is both larger and tighter (median 1.1¢ on
  $13.7 M/24 h) than Kalshi's.
- **n = 66 sides is 40 games**, and the two sides of one game are near-perfect
  mirrors, so the effective n is closer to **40** than 66 (GUARDS #8).
- **Fees only, no slippage.** Adding realistic slippage makes the net worse,
  never better, so the direction of the conclusion is safe.

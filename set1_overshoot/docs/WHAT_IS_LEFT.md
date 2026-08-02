# WHAT_IS_LEFT.md

Written 2026-08-01 after the ladder and backlog were worked to exhaustion of
what available data supports.

## The binding constraint is sample size, not ideas

Per-contract sd of net P&L is **45 ¢**. Detecting a 2 ¢ edge at 80% power needs
**n ≈ 3,970 matches**. The entire event sample is **3,436**. Every subgroup is
therefore underpowered by construction, and this is why 0 of 25 time/tier buckets
and 0 of 10 margin buckets cleared — not because each was checked and found
empty, but because at n = 100–200 the MDE is 8–12 ¢ against a target of 2 ¢.

| question | answerable at | current n | weeks of further recording needed¹ |
|---|---|---|---|
| Does the pooled effect clear 3.61 pp? | **already answered — no** | 3,436 | — |
| Does perfect labelling rescue it? | n ≈ 3,970 labelled events | 479 | needs quota, not time |
| Does set-1 margin concentrate it? | n ≈ 2,000 **per bucket** | 93–190 | ~40 weeks |
| Does a recovery model beat the price? | n ≈ 4,000 labelled | 479 | needs quota |
| Best-of-5 vs best-of-3 | n ≈ 2,000 best-of-5 events | 73 | ~100 weeks (Slams are 4/yr) |
| Is maker execution viable? | **already answered — no** | 3,436 | — |
| Queue-position realism | order-level priority data | — | **never, from public data** |

¹ at the observed ~1,900 matches/week → ~330 events/week.

## Unanswerable with any available data

- **Order-level queue priority.** Kalshi publishes aggregate size per price, not
  per-order position. The fill model is bounded above and cannot be tightened.
- **Sub-minute adverse selection.** Candles are 1-minute; the crypto session hit
  the same wall.
- **Historical order books before 2026-08-01 06:58.** No historical endpoint;
  only what has been recorded live exists.
- **Sackmann data after 2026-06-02.** Repos are 404.
- **Serve order in set 2 for the historical window**, without paid point-by-point.

## What would actually change the answer

Not more slicing. Two things, in order:

1. **Labels at scale** — a date-addressable scoreline source covering ITF and
   Challenger back 68 days. That takes label coverage from 13.9% to ~100% and is
   the only lever that raises the effect without shrinking the sample. Blocked on
   Apify quota, not on method.
2. **Time.** ~330 events/week. Reaching n = 10,000 events — enough for ~1 ¢
   resolution and for genuinely powered subgroups — takes about **20 weeks** of
   continued collection.

Everything else is arithmetic that has already been done.

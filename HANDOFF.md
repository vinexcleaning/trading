# HANDOFF.md — market-selection session, 2026-08-02 (overnight)

Session scope: **select markets**. No strategies tested, no prior study re-run.
Working directory `C:\Users\gianf\trading`, all new work under
`market-selection/` plus a shared `common/` module.

> **IN PROGRESS — this file is being written incrementally and the trade-tape
> pull has not finished. Sections marked ⏳ are provisional.**

---

## 1. THE SHORTLIST

⏳ Pending the full 24 h trade tape. Preliminary ranking in §8.

---

## 2. KILL REASONS

⏳ Pending. `market-selection/killed.md`.

---

## 3. WHAT IS RECORDING

| What | Where | Since | State |
|---|---|---|---|
| **Broad depth recorder**, 232 markets across **85 families**, 20 levels/side | `market-selection/data/depth_broad/<date>/<hh>/depth.jsonl` | 2026-08-02 06:54 UTC | alive, ~170 s/cycle, content-validated per row |
| **pmxt L2 mirror**, 662 hourly parquet files | `market-selection/data/pmxt/` | 2026-08-02 06:28 UTC | ~200/662 done, 23.4 GB, 1 failure to retry |
| Tennis depth recorder (pre-existing, PID 17892) | `C:\Users\gianf\kalshi\set1_overshoot\data\depth\` | 2026-08-01 02:58 | untouched, alive |
| Crypto 15m opens (pre-existing, PID 24756) | `C:\Users\gianf\crypto\data\btc15m_opens\` | 2026-08-01 13:42 | untouched, alive |

Recorder health, last 4 cycles: **90.1–91.8% non-empty, 83.2–83.6% two-sided,
0 invalid rows, 0 HTTP failures.**

---

## 4. RESULTS TABLE

⏳ Partial. See §8.

---

## 5. RETRACTIONS

### Premises in the tasking that are wrong

**P1. "archive.pmxt.dev has rolling 30-day retention, so it deletes itself
continuously."** **FALSE.** The archive is frozen, not rolling. Files from
2026-05-16 still serve at **78 days old**; every hour after 2026-06-11T03 is
404. Under 30-day retention on 2026-08-02 the archive would hold 07-03→08-02
and nothing earlier — the observed pattern is the exact inverse. It is a
capture that stopped on 2026-06-11 with its back catalogue left in place.
Mirroring is insurance against an abandoned bucket, not a race. Nothing was
lost by verifying first.

**P2. "one prior session found `/orderbook` returns empty and concluded depth
is not public; another recorded 20 levels a side. Both are in LEDGER."**
Both sessions were right about what they saw and **both were reading a key
name**. Resolved in §9.

### My own corrections, this session

**R1.** I reported "**0 of 60 non-empty orderbooks**" including a market with
1.6 M in 24 h volume, and was on the verge of concluding depth is not public.
**That was my own parser bug** — I read `["orderbook"]["yes"]`, which does not
exist. Corrected: depth is public, free, unauthenticated, 20 levels a side.
85 markets were probed wrongly before this was caught.

**R2.** I reported pmxt `frac_empty = 0.9998` on the depth columns. **Invalid**
— computed over the first 20,000 rows, which are nearly all deltas, and delta
rows carry empty level arrays by construction. Restricted to snapshot rows:
25.30% carry depth on one side, 4.99% on both.

**R3.** I printed a pmxt ladder of `(1.0, 2.0)` repeated at every level on every
market and nearly reported it as degenerate data. **The struct children are
literally named `"1"` and `"2"`**; iterating the dict yielded its keys. Parsed
correctly the ladders are real (479 distinct prices, 5,307 distinct sizes).

**R4.** I said the depth recorder had "written nothing for 15 minutes" and
diagnosed a stall. **Wrong on two counts**: the timestamp was Windows lazy
metadata on an open handle, and I had misread the clock by 25 minutes. The
recorder was on cadence throughout. The line-buffering fix I made anyway is a
genuine improvement (crash safety) but it was not fixing the fault I claimed.

**R5.** My first cross-venue join matched **0 of 76** MLB markets and I could
have reported "the venues share no events". It was a nickname/city mismatch on
my side. Corrected to 66 of 76 matched.

**R6.** A prior memory recorded the pmxt archive as `2026-05-15 00:00 →
2026-06-10 23:00, 648 files`. Measured range is **2026-05-14T14 → 2026-06-11T03,
662 files** — 10 hours short at the front, 4 at the back.

### Corrections to STATUS.md / LEDGER.md

**R7.** GUARDS #12 flagged the legacy price fields as *suspected* null.
**Confirmed live**: of 200 open markets, `yes_bid`, `yes_ask`, `no_bid`,
`no_ask`, `last_price`, `volume`, `open_interest`, `liquidity` were non-null on
**zero**. Any recorder reading those names writes nulls at full row count.

**R8.** `tick_size` does not exist on the Kalshi market object at all — nor
`tick_size_dollars`, `min_tick`, or `response_price_units`, on any of 419,828
markets. The real tick is `price_level_structure` ∈ {`linear_cent` 1¢,
`deci_cent` 0.1¢, `tapered_deci_cent` 0.1¢ in the wings}.

**Nothing found this session revealed a larger effect than previously
believed.** The directional prior in LEDGER.md holds: every correction shrank
the edge or removed a premise.

---

## 6. CANARIES AND CONTROLS

| Guard | Ran? | Result |
|---|---|---|
| Content validation, not row counts (#12) | ✅ per row, in the recorder | 0 invalid of ~930 rows; prices asserted inside (0,100), sizes finite and non-negative |
| Recorder health alarm on collapse (#12) | ✅ armed | fires if non-empty < 5% after 300 rows; never fired |
| Exact-decimal fee arithmetic (#6) | ✅ | `common/costbar.py` asserts 7 Kalshi reference points + Polymarket at import; the 2.86× ratio at 50¢ re-derived |
| Guard-rot (#9) | ✅ partial | fee reference points asserted at import; float-dust regression asserted |
| Fill at the ask, never the mid (#7) | ✅ | cross-venue priced at executable touch on both venues |
| Duplicate/pagination canary | ✅ | 419,828 rows → 419,828 distinct tickers, 0 duplicates |
| Pre-registered gate before seeing numbers (#10) | ✅ | kill-switch thresholds fixed in `DECISIONS.md` D8 while the tape was still downloading |
| Effective n (#8) | ✅ stated | cross-venue n=66 sides ≈ 40 independent games |
| Selection canary (#1) | ➖ n/a | no dedupe of mirrored sides performed this session |
| Synthetic null / positive control (#3, #4) | ❌ not applicable | no model fitted; nothing to control |

---

## 7. STILL OPEN

⏳ Section pending completion of the ladder.

---

## 8. NEXT THREE ACTIONS

⏳ Pending.

---

## 9. WHAT THE COORDINATING CHAT HAS WRONG

### It believes Kalshi order-book depth may have to be bought. It is free.

The LEDGER contradiction is resolved, and neither prior session was careless —
they were both defeated by a field rename. The `/markets/{ticker}/orderbook`
response carries **exactly one top-level key**:

```json
{"orderbook_fp": {"yes_dollars": [["0.1200","100.00"], ...],
                  "no_dollars":  [["0.1300","15.00"],  ...]}}
```

There is **no `orderbook` key** and **no `yes`/`no` key**. Code reading those
gets an empty book from an HTTP 200 on *every* market, liquid or dead — which
is precisely the "returns empty, depth is not public" conclusion. The session
that recorded 64,898 snapshots at 20 levels a side was reading
`orderbook_fp.yes_dollars`, and was right.

**Depth is public, free, unauthenticated, 20 levels a side, on both sides.**
Live measurement across 85 families: **90.1–91.8% of snapshots carry depth,
83.2–83.6% are two-sided.** Nothing needs to be bought. `S013` stands; the
"depth is not public" claim should be marked RETRACTED in LEDGER.md.

### It treats pmxt as an emergency. It is a dead archive, not a melting one.

See §5 P1. There is no accruing loss against this source. The genuinely
unbackfillable asset is *live* Kalshi depth, which is why a recorder was
started at 06:54 UTC rather than at the end of the session.

### It should stop treating "rich free data" as the scarce input for crypto.

Verified live: Binance (via `data-api.binance.vision`), Coinbase, Kraken and
Deribit's full options chain are all free and open. That is the point — **every
participant has all four inputs**, which is why C010 found no model beats the
mid. Crypto's problem was never data access.

### More to follow when the ladder completes.

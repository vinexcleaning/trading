# PREREGISTRATION.md — Step 5

**Written 2026-08-04, BEFORE any strategy result existed.** The engine was
validated first (`src/validate_engine.py`, 5 of 5 controls pass); no strategy
had been run against real data when this file was committed. Git history is the
evidence for that ordering and is the reason this file is committed separately
from any result.

GUARDS #10: *"Sweeping exit rules over a signal with no edge is how this project
has previously produced strategies that die live."* The gates below are
implemented in code and fire before a number is printed.

---

## 0. What is being tested, and what is NOT

[SHORTLIST.md](SHORTLIST.md) §4 established that **no candidate has all five
dimensions AND a runnable historical test**:

| entry | why it cannot be tested to completion today |
|---|---|
| Esports reference-price strategy | Pinnacle esports is live-only; all five free historical esports odds sources are dead (404/403/402/403/404). **Forward-test only** — the recorder started 2026-08-04 21:27 UTC is the whole apparatus. |
| Tennis ITF | 15,636 events, **no free reference price of any kind** |
| Tennis ATP/WTA vs Betfair | already run: **T012**, r = 0.9878, MAD 1.95¢ vs a 2.44¢ cost. Null. |
| S. American soccer | 152 retrievable events against a 481 bar |

**So the only thing testable to completion on retrievable data is a STRUCTURAL
test that needs no external reference price**: does Kalshi's own pre-match price
on esports mis-state the settlement probability by more than it costs to act?

That is a smaller question than the brief's, and it is stated as such. It is
also the right one, because **every reference-price strategy on this exchange
has to beat the same null**: if Kalshi's own price is already calibrated, a
sharper reference buys nothing.

**A negative control family is included by design.** MLB moneyline is *known*
efficient (0.37¢ vs de-vigged DraftKings, 0 of 26 over the bar). Every test
below runs on it too. **If a strategy "works" on MLB moneyline, the strategy is
an artifact.**

---

## 1. Data, unit of observation, and the split

| | |
|---|---|
| universe | `KXCS2GAME`, `KXLOLGAME`, `KXVALORANTGAME` (test) + `KXMLBGAME` (control) |
| retrievable settled events | CS2 1,648 · LoL 719 · Valorant 500 · **MLB 907** |
| **unit of observation** | **the EVENT (one match)**, never the market. 2 markets per esports event and they are exact complements. |
| cluster for every CI | `event_ticker`. Bootstrap resamples EVENTS. |
| price source | hourly candlesticks, `yes_bid`/`yes_ask` nested `*_dollars` |
| **anchor** | the last candle **strictly before `close_time − 60 min`** |
| holdout | **the newest 30% of events by `close_time`, SEALED.** Only survivors of everything else touch it, ONCE. |

### 1a. The dedupe rule, fixed in advance

Kalshi lists one market per side. **The side kept is the FIRST TICKER
ALPHABETICALLY** — the rule GUARDS #1 measured clean at P(kept wins) = 0.4969,
z = −0.88.

**Banned as dedupe keys, with their measured z:** `last_price` (**+140.3**,
it *is* the answer), `open_interest` (+15.7), `volume` (**+10.0** — the bug that
voided three phases of `set1_overshoot`). The canary is asserted at build time
and the build **refuses to write a universe that fails**.

`liquidity` is banned for a different reason: it scored z = +0.88 and is
**UNTESTABLE**, not clean — it is null on almost every settled market, so the
tie-break does the work. *Innocence by emptiness is not innocence.*

### 1b. Anchor choice, and why −60 min

The Polymarket ten-strategy study got an **84% hit rate** from momentum and it
was entirely an artifact of measuring drift **near resolution**, where a
prediction market mechanically converges. Its honest rebuild on early prices gave
**0.541**.

**T010/T011** in this repo is the same failure: at a −0h anchor, 4.1% of quotes
sat outside 2¢–98¢ and were **100% correct**. A real pre-match market cannot do
that.

So: the anchor is −60 min, and **the leak canary runs at −0h, −60 min and
−6 h**. If the −0h arm shows the 100%-correct-extremes signature and the −60 min
arm does not, the anchor is clean. If −60 min shows it too, **every result below
is void** and the anchor moves to −6 h.

---

## 2. The strategies. All of them, written before any was run.

Every strategy is *buy one side of one event at the anchor, hold to settlement*.
Exits are deliberately not swept — GUARDS #10.

| ID | strategy | mechanism | falsified by |
|---|---|---|---|
| **H1** | buy YES in each price decile | calibration: is the price the probability? | net ≤ 0 in every decile after cost |
| **H2** | buy the LONGSHOT (price ≤ 20¢) | favourite–longshot bias, the racetrack effect | net ≤ 0, or CI containing 0 |
| **H3** | buy the FAVOURITE (price ≥ 80¢) | the mirror of H2 | as H2 |
| **H4** | buy in the 60–95¢ band | the exact band of **K015 = W011**, killed on Polymarket at −0.29pp net. Does it exist on Kalshi esports? | net ≤ 0 |
| **H5** | fade the 24 h price move (buy the side that FELL) | mean reversion in pre-match drift | net ≤ 0 |
| **H6** | follow the 24 h price move | momentum. Measured on EARLY prices only, never near resolution | net ≤ 0 |
| **H7** | buy the WIDER-spread side | thin-side mispricing | net ≤ 0 |
| **H8** | buy the LOWER-volume side | "nobody is watching" | net ≤ 0 |
| **H9** | buy the side whose ask moved least in the last 6 h (stale quote) | staleness | net ≤ 0 |
| **H10** | **rest a passive bid 1¢ inside the touch** | maker economics — the strategy `signal-github` favours on fees and a 20-year professional warns against on adverse selection | net ≤ 0 **or** the fill rate is below 20% |

### Parameter grid

| parameter | values |
|---|---|
| price band edges | 5/10/20/30/40/50/60/70/80/90/95¢ |
| anchor | −60 min *(primary)*, −6 h, −24 h *(sensitivity)* |
| drift window (H5/H6/H9) | 6 h, 24 h |
| slippage assumption | 0.0¢, 0.5¢, **1.0¢ (primary)**, 2.0¢ |
| fill model (H10) | trade-through only *(primary)*; touch-counts-as-fill is run **solely as a deliberate-leak diagnostic** and is labelled as such |

**Total ≈ 10 strategies × ~11 bands × 3 anchors × 4 slippage = ~1,300 cells.**
At α = 0.05, **~65 cells clear on pure noise.** That is arithmetic, and it is
why the correction below is not optional.

---

## 3. Decision rules, fixed now

1. **BH-FDR at q = 0.10 across the WHOLE grid**, one denominator for the entire
   project — not per family, not per strategy. Cancelled cells stay in the
   denominator (crypto's `CANCELLED` convention) so it cannot quietly shrink.
2. **Two-sided p-values.** An undershoot is a finding here; a one-sided test
   would hide it.
3. **The cost bar is recomputed from the data on every run**, never hardcoded:
   `half-spread + slippage + fee(price)`. The fee is quadratic, so the bar is
   materially higher on cheap contracts (~2% on a 69¢ ticket, ~6% on an 18¢ one).
4. **Every null reports its MDE** beside the point estimate. `0 of 25` means
   nothing without it.
5. **Every CI is clustered on `event_ticker`** and the effective n is printed
   next to the nominal n.
6. **The parameter SURFACE is reported, not the peak.** A sharp isolated peak is
   overfitting; a broad plateau may be real. Each surviving cell is explicitly
   labelled PEAK or PLATEAU.
7. **Monotone strengthening with detector precision is treated as evidence of
   CONTAMINATION**, not of a real effect. This was the single worst inference in
   the archive.
8. **The holdout is touched ONCE**, by survivors only, after everything else is
   final. A second look voids it.
9. **The negative control gates everything.** If ≥2 strategies "work" on
   `KXMLBGAME`, the run is declared broken and no result from it is reported.

---

## 4. What I expect, recorded so a null is a measurement

**I expect every one of H1–H10 to fail**, and I am writing the reason down now
so that a null cannot later be dressed up as a surprise:

- The market is a CLOB with real two-sided quoting (100% uptime, 1.0¢ spreads,
  21,236 contracts at the touch on CS2). A 1¢ spread with real size is what a
  *competitive* book looks like.
- Three independent measurements already say Kalshi is the sharp line: tennis
  (**T012**, r 0.9878), MLB moneyline (0.37¢, 0 of 26), 3-way soccer ladders
  (0 of 93 baskets profitable).
- The ten-strategy Polymarket study found the same on a different venue, and its
  own summary is the one to beat: *"the edges died at the cost gate, not the
  forecasting gate."*
- **45 corrections in this repo and every one shrank the edge. Not one ever
  revealed a larger effect.**

**The informative outcome is H10.** If passive quoting fills at all and still
loses, that is a *fourth* independent confirmation of S008/S009 on a venue and
sport they never touched — and it is the term the esports arb author measured at
**38% of gross**.

## 5. What would make me revise

A cell clearing BH-FDR **and** the cost bar **and** the holdout **and** showing a
broad plateau **and** failing on the MLB control. All five. Fewer than five and
it is one of the 65 cells that clear on noise.

# RESULTS — the paired sampler: 84 milliseconds instead of 6.5 minutes

**2026-08-31.** Mailbox 024. **Recording only** — no credentials, no order code,
no execution path.

---

## 1. What was broken, and what this changes

`BH024` could not answer whether cross-venue arbitrage exists, because
`record.py` walks Kalshi, then Polymarket, then Pinnacle. Inside one `cycle_id`
the two venues sat a **median 6.5 minutes apart**. The skew placebo settled it:
crossings scaled linearly with deliberate mis-alignment at **correlation 0.9975**,
extrapolating to **7 real against 125 observed — 94 in 100 were the clock.**

**The fix was never volume. It was the order of operations.** For each matched
pair this fires the Kalshi order book and **both** Polymarket outcome books
**concurrently**, and records the arrival time of each response.

| | `record.py` | **paired sampler** |
|---|---|---|
| gap between venues, median | **390,000 ms** (6.5 min) | **84 ms** |
| p90 | 480,000 ms | **104 ms** |
| worst seen | 1,428,000 ms (23.8 min) | **426 ms** |

> **About 4,600× tighter.** And the gap is **stored on every row**, because the
> instruction was "do not assume it worked" — so if it ever creeps back up, the
> numbers show it instead of quietly degrading.

## 2. The first genuinely simultaneous measurement

| 2026-08-31 20:22 UTC | |
|---|---|
| matched pairs discovered | 66 |
| all pre-game (in-play excluded) | 66 |
| captured with a live two-sided quote on **both** venues | **66 of 66** |
| Kalshi spread on these rungs, median | **1.0¢** |
| **theoretical crossings** | **0** |
| **after fees on both legs** | **0** |

**One sample of 66 pairs is not a result** — it is the first reading from an
instrument that can now, in principle, tell a real disagreement from its own
clock. The sampler runs every ten minutes and accumulates.

**But it is consistent with what the placebo predicted:** extrapolating BH024's
skew line to a zero gap gave ~7 crossings across 969 pairs over 27 days, which on
66 pairs in one instant is approximately none.

## 3. ⚠ And "0 crossings" was a bug before it was a measurement

**The first run of this sampler also reported 0 crossings. That number was
worthless, and the reason matters more than the number.**

| column | populated |
|---|---|
| `p_over_ask_c` | 66 of 66 |
| `p_under_ask_c` | 66 of 66 |
| **`k_bid_c`** | **0 of 66** |
| **`k_ask_c`** | **0 of 66** |

**The Kalshi side was entirely empty.** I read `orderbook` → `yes_fp`/`yes`; the
live fields are **`orderbook_fp` → `yes_dollars`/`no_dollars`**, and the prices
are **dollars**, needing ×100. That is **GUARDS #12 and #23 — the renamed-field
trap — and I walked straight into it** in a script whose own docstring cites
those guards.

> **A comparison with one side missing returns "no crossings" and looks exactly
> like a clean null.** It was caught by counting populated columns before
> believing the zero — **not by care, and not by reading the code.** The check
> cost one query; without it this file would have reported a false negative with
> the same confidence as the true one.

**This is the fifth field-name absence in three weeks** (C024, M024, the retail
census, the blind-spot census, and now this).

## 4. The standing control, as instructed

Mailbox 024: *"Do not re-run the skew placebo once and call it clean. Run it on
every report."*

**`--report` now runs it every time.** It deliberately mis-aligns the two venues
by whole samples and recounts:

```
   ⚠ STANDING SKEW PLACEBO — the control that killed BH024:
        offset 0 sample(s) :      0     <- the real measurement
        offset 1 sample(s) :      0
        offset 2 sample(s) :      0
        offset 3 sample(s) :      0
```

**All zero because there is only one sample so far** — the offsets have nothing
to compare against yet. Once several samples exist, **the offset rows must come
out higher than offset 0 for the instrument to be believed.** If they do not, the
sampler is not doing the one thing it exists to do.

## 5. How it is built, and the two mistakes it deliberately does not repeat

- **Its own database and its own lock.** `data/paired.db`, never `record.db`.
  Two writers on one SQLite file died with `database is locked` inside 19
  minutes, and `kalshi_cycle` holds one write transaction for up to 1,400 s.
- **Windows-safe liveness.** `OpenProcess`, never `os.kill(pid, 0)` — CPython
  maps that to `TerminateProcess` on Windows and would kill the holder.
- **Registered in BOTH registries**, so a reboot restarts it. The prop watcher
  that was in neither died at 15 hours of 48 in the 2026-08-18 reboot while the
  registered recorders came through with no gap over 45 minutes.
- **Paced between pairs, never inside one.** The two legs of a pair must be
  simultaneous; the pairs themselves are spaced 0.25 s apart, so a full pass of
  ~66 pairs is ~200 requests against `C018`'s recorded ceiling of 15 a second.
- **In-play excluded by default**, because the biggest fake crossings in BH024
  were stale limit orders on already-decided games, and `CLAUDE.md` §9b rules
  in-play out here regardless.

## 6. What this does NOT establish

- **Not that cross-venue arbitrage is absent.** One sample. The instrument is
  new and the accumulation has just started.
- **Only MLB run totals.** Game winners, tennis, esports and soccer all have
  matchable pairs and none is sampled.
- **Pinnacle is not a third leg** yet, though `max_risk` is recorded elsewhere.
- **Settlement rules are still unverified.** Neither venue's rules are in either
  tape, so a suspended or rain-shortened game could resolve differently. Every
  candidate is a **price crossing**, never free money.
- **Depth is top-of-book plus the recorded size at that level**, not a full walk
  of the ladder.

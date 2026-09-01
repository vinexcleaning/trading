To: mlb
From: coordinator
Opened: 2026-09-01 01:06
Status: DONE
Subject: Audit note - SLIPPAGE_C=1.0 is assumed and the desk's real fills can now measure it

--- INSTRUCTION ---

**One audit note, no urgency. `SLIPPAGE_C = 1.0` in `mentalities.py:79` is an
assumed constant that gates every bot's entry — subtracted from every edge in
the live path and the replay — and it has never been measured.**

The data to measure it now exists: `livedesk` records both the card price and
the real fill for every placed order (e.g. asked 36c, filled 33c — an
IMPROVEMENT, not slippage). Sample is small but real. When convenient: compute
actual fill-vs-quote slip from the desk's ledger, and either justify the 1.0 or
replace it with the measured figure, with the change logged in DECISIONS.md.
If the measured number is near zero, note that a too-large slip constant
suppresses entries — the bots may be declining bets the rule intended to take.

--- REPLY ---

The session that owns `mlb` writes below this line, and changes `Status:`
above to `DONE` or `BLOCKED`. Nothing else needs doing and no script needs
running. If this is wrong or you disagree with it, say so here -- a disagreement
recorded is worth more than a task silently skipped.

**DONE. Measured, and the constant is wrong — but I have not changed it, and the reason is in the reply.**

# The measurement

**39 orders with both a placed price and an account-confirmed fill.**

```
filled WORSE than placed : 0
filled at the same price : 36
filled BETTER than placed: 3   (-3c, -1c, -3c)

mean   -0.18c        median  0.00c        worst  +0c
assumed +1.00c against us
```

⚠ **The data is in the desk's free-text `note`, not in a field** — there is no `fill_price_c` in any of its nine ledger files. The pair is `"filled, 27 of 27 @ 36c"` (placed) and `"corrected from your account: ... really 27 at 33c"` (real). `mlb-paper/src/measure_slip.py` parses it. **I read `livedesk/data/ledger.json` read-only and wrote nothing there.**

# What it has cost — you were right about suppression

**227 distinct games would have had at least one extra bet** at slippage 0. The forward test has **146 settled games**, so the assumption has suppressed more games than the experiment has actually run.

By mentality, as decision-events:

| | declines | would have passed |
|---|---|---|
| early | 91,372 | 9,455 |
| starter | 6,839 | **4,694** |
| bullpen | 15,882 | 2,932 |
| park-air | 12,376 | 1,426 |
| lineup | 1,042 | 0 |

# ⚠ The caveat that stops this being a bigger claim than it is

**The desk buys at the ask. A marketable limit order fills at its limit or better BY CONSTRUCTION**, so "zero slip" is close to tautological for the orders measured, and it does **not** show that a moving book cannot cost us.

What it does show is that **the trade the bots actually model** — buy at the displayed ask — has not been paying an extra cent. That makes it the right measurement for this purpose. But it is 39 orders, one venue, middling prices.

# Decision: LEFT AT 1.0, not changed

1. **It changes every bot's behaviour mid-experiment.** The forward test's only real value is that the rule was fixed before results existed. Splitting it into two regimes for a cost correction spends exactly that.
2. **The error is in the safe direction, and this is what decides it.** A too-large cost makes the bots stricter — it suppresses bets rather than manufacturing them. **So every result recorded so far is, if anything, understated.** An edge found under a 1-cent handicap is not an artefact of the handicap.

**Flagged as a real decision rather than housekeeping:** taking it to 0 would roughly triple the games in the test, at the cost of restarting the clock on every pre-registered count. **Say the word and I will do it as a dated regime change** with everything before and after reported separately.

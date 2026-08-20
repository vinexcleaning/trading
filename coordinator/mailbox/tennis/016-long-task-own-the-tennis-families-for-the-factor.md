To: tennis
From: coordinator
Opened: 2026-08-20 00:41
Status: DONE
Subject: LONG TASK - own the tennis families for the factory, ITF especially

--- INSTRUCTION ---

**LONG TASK. Your own handoff says you are free until 2026-10-08 and available
for strategy-factory work. This is it.**

# THE CONTEXT

The `factory` chat is generating strategies across every Kalshi market family
and screening them on recorded tape. It has 3,654 families, 18+ specs and is
building the screening engine. **It is one chat trying to cover an exchange.**

# THE TASK — take the tennis families off its hands entirely, and do them properly

The recorder carries **`KXITFMATCH` (1,976 tickers), `KXITFWMATCH` (1,544),
`KXATPMATCH` (312), `KXWTAMATCH` (304)`** — nearly 4,000 tickers, and **you know
this book better than any other chat.** `kalshi-tennis` is your own finished
audit of exactly this.

1. **Write strategy specs for every tennis family**, in the factory's format:
   id, family, what it bets on, entry rule, exit rule, size rule, what would
   make it wrong, who suggested it, date. **Read
   `coordinator/STRATEGY_FACTORY.md` first** so they arrive in the shape its
   engine expects.
2. **Use what only you know.** Your 17-bot forward test has 788 settled matches
   and every bot carries a no-skill range. **You know which mentalities produced
   nothing and why** — those are dead specs nobody else needs to rediscover.
   Write them down as ruled-out, with the reason.
3. **ITF is the interesting one and nobody has looked at it.** 3,520 tickers
   between the two ITF families — **more than ATP and WTA combined by a factor
   of five.** Lower tier, thinner books, and `soccer`'s finding says tennis is
   where a quote survives furthest into a near-certainty. **Whether that is
   tradeable is unknown and it is directly in your territory.**
4. **Capacity first on anything that looks good.** A thin ITF market that takes
   $12 is a hobby, and it is better to find that out in the spec than after a
   month of forward testing.
5. **Agree the split with `factory` in `STATUS.md`** so neither of you writes the
   same spec twice.

# WHAT NOT TO DO

- **Do not touch the running forward test.** It reviews on 2026-10-08 and not
  before — that date is his decision and it stands.
- **Do not report backtest numbers as results.** The factory rule applies to
  you: the backtest chooses, only the forward test counts.

**Run for hours. Do not stop to report progress.**

--- REPLY ---

The session that owns `tennis` writes below this line, and changes `Status:`
above to `DONE` or `BLOCKED`. Nothing else needs doing and no script needs
running. If this is wrong or you disagree with it, say so here -- a disagreement
recorded is worth more than a task silently skipped.

**DONE — 2026-08-20, tennis session.** Tennis families taken off the factory's
hands. Six specs written and validating, the ITF capacity question answered, and
the split recorded in `STATUS.md`.

---

## 1. THE ITF ANSWER, AND IT IS NOT THE ONE THE TASK EXPECTED

You said ITF is the interesting one and nobody has looked. I looked, on 16 days
of the recorder's own book — **254,220 rows across 4,896 tennis tickers**.

**The first pass said ITF was dead: 10.1c mean spread, $47 at the touch.** That
would have been a wrong answer, and it is the answer a flat median gives.
Bucketed by how long before the market stopped quoting:

| family | >12h out | 2–12h | last 2h |
|---|---|---|---|
| `KXATPMATCH` | 3.8c / $1,002 | 1.4c / $6,642 | **1.2c / $9,599** |
| `KXWTAMATCH` | 5.4c / $753 | 1.8c / $3,384 | **1.2c / $5,559** |
| `KXITFWMATCH` | 16.9c / $18 | 7.9c / $63 | **3.9c / $163** |
| `KXITFMATCH` | 19.9c / $13 | 9.7c / $46 | **5.6c / $124** |

**"ITF is untradeable" and "ITF is tradeable only in the last two hours, at
about $124 a click" are different findings, and only the second one is true.**

**Two things the factory should carry:**

1. **ITF is where the tickers are and not where the money is.** 3,500 of 4,900
   recorded tennis tickers, five times ATP and WTA combined. **A factory that
   ranks families by ticker count will point straight at the least tradeable
   corner of the exchange.**
2. **The two ITF families are not one market.** The women's book is about **30%
   tighter and 30% deeper** than the men's in every bucket. Pooling them
   averages a tradeable book with a marginal one.

## 2. SIX SPECS, ALL VALIDATING

`py -3 strategy-factory/src/spec.py --validate` → **28 specs, 0 problems.**

| id | what |
|---|---|
| **SF100** | the ITF **gate** — last two hours, spread ≤4c, $100 showing. Screened alone so the cost of the restriction is known before any rule is layered on it |
| **SF101** | the near-certainty quote-survival test, from `soccer`'s finding, on the thinnest book. 88–96c, where the fee is a fifth of what it is at 50c |
| **SF102** | mirrored-pair arbitrage. **Expected null and I say so** — measured live, 13–16 of ~123 matches a tick, median 1c gross, **zero** beating the 2.5c two-leg fee. Kept because it is free and doubles as a book canary |
| **SF103** | pre-game on non-decaying evidence. Already running as `pre-game__hold` since 08-13 — written down so nobody generates it twice |
| **SF110** | per-trade stops. **RULED OUT** |
| **SF111** | the four in-play dispositions. **NO EVIDENCE EITHER WAY** |

Generator: `tennis-paper-forward/factory/make_specs.py`, re-runnable.

## 3. THE DEAD SPECS, AND ONE DISTINCTION THAT MATTERS

You asked for what produced nothing so nobody rediscovers it. **I have split
that into two categories, because collapsing them would be dishonest:**

- **SF110, per-trade stops: genuinely RULED OUT.** Three arms differing *only*
  in exit rule, same matches, same prices, same sizing. Not stopping won **5
  families out of 5 by 9.3 points**, direction pre-registered before the run,
  and `bot-forensics` reached the same direction independently on his own live
  bot (−2.29c → −9.36c). Caveat kept in the spec: the selling arms also differ
  in re-entry, and it is 5 matched pairs.
- **SF111, the four in-play dispositions: NOT ruled out.** All 17 bots sit
  **inside** their own no-skill range. **Inside the range means the test could
  not tell** — a verdict about the test, not about the idea (GUARDS #21).
  Writing them off as dead would be the mistake this repo has recorded more
  than any other.

**That distinction is the whole value of the entry.** A factory that treats
"tried, could not tell" the same as "never tried" will re-screen dead ideas
forever *and* inflate the screened total it judges everything else against.

## 4. ONE TOOL BUILT, BECAUSE CAPACITY IS A FACTORY-WIDE RULE

`common/capacity.py` — point it at any family, get spread and money-at-touch
bucketed by time, plus a plain-English verdict.

```
py -3 common/capacity.py --series KXITFMATCH --want-usd 100
```

I wrote it inline for tennis first; generalising cost twenty minutes and removes
the reason for anyone to write a second. **Stage 3 makes capacity a screening
rule for every strategy and stage 6 says a great edge in a market that takes $12
is a hobby** — that question is identical for crypto and weather.

Eight tests, and the one that matters asserts **a good bucket is not averaged
away by a dead one**, using the real ITF numbers. It also refuses to call a deep
but wide market tradeable, which is the archive's fake-favourite trap.

## 5. TWO THINGS THAT ARE NOT MINE TO FIX

> ⚠ **`strategy-factory/src/bestofn.py` re-implements `common/noskill.py`.**
> Its own `best_of`, `pct` and `exact_p_at_least`; it imports
> `common.kalshi_fees` but not `common.noskill`. The shared module was committed
> 2026-08-18 **specifically to stop a third copy** — the fee formula in this repo
> went 3 → 17 exactly this way. `common/noskill.py` also carries a **positive
> control** (plant a real 65% win rate, assert the band catches it) which a
> null-only test cannot. **Your call, and I have not touched the file.**

> ⚠ **`common/tests/test_no_legacy_kalshi_fields.py` is RED** on 13 files across
> five other projects — code reading Kalshi field names that no longer exist and
> return `None`, which becomes a silent zero in arithmetic. **None are mine.**
> A wrong all-clear would hide exactly the bug the guard exists to catch, and a
> repo-wide guard left red stops being read.

## 6. WHAT I DID NOT DO

- **No backtest numbers reported as results.** Nothing here is screened yet; the
  capacity figures are book measurements, not returns.
- **The forward test was not touched.** Still reviewing 2026-10-08.
- **No specs outside SF100–SF199**, and no edits to the factory's files.

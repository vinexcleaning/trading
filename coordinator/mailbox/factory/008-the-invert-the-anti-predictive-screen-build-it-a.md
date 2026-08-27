To: factory
From: coordinator
Opened: 2026-08-26 21:13
Status: OPEN
Subject: The invert-the-anti-predictive screen - build it as a standard column over every strategy

--- INSTRUCTION ---

**His idea, and he explicitly wants it applied beyond one sport: *"this can
apply to not just tennis, we can apply this to a lot of shit."* Build it as a
SCREEN over every strategy you generate, not as a one-off test.**

# THE IDEA

> *"We need to take away bad strategies that are bad because of the fees,
> because there are some good strategies we've come up with that get killed by
> the fees. But if we find a purely bad strategy that isn't just getting killed
> by the fees — pretty much what that's telling us is that this site is picking
> the wrong side. So we just pick the other side."*

**The distinction is computable and it is the whole idea:**

```
  loss <= cost bar   ->  the strategy is leaking fees. Inverting gains nothing,
                         because you pay the same bar in the other direction.

  loss >> cost bar   ->  the strategy is actively picking the wrong side.
                         Inverting is a real hypothesis.
```

# IT IS ALREADY MEASURED ON ONE PAIR, AND THE CONTROL CASE WORKS

`mlb-paper`, real fees, three spread assumptions:

| bot | as-is | flipped @1c | @2c | @4c | verdict |
|---|---|---|---|---|---|
| `bullpen__free` | −34.3% | +25.8% | +23.4% | **+18.9%** | loses far more than it costs → invertible |
| `early__free` | −14.9% | +5.1% | +3.3% | **−0.3%** | loses about what it costs → nothing there |

**`early` is why this is a real screen and not a slogan.** Both bots lose. Only
one is worth flipping, and the cost bar is what separates them. **Without that
test, "invert the losers" would have been applied to both and produced a null.**

# WHAT TO BUILD — a screen, applied to everything

**For every strategy your engine screens, compute and store:**

1. **its net return**
2. **its cost bar** — spread crossed + slippage + fee, from
   `common/kalshi_fees.py` and nothing else, **computed at the prices that
   strategy actually trades at**, not at 50c
3. **`gross = net + cost bar`** — the part that is about picking, not paying
4. **the inverted net** — buy the other side at the real ask, pay the bar again
5. **a flag: `invertible`** — true only when `gross` is negative by materially
   more than the bar

**Report it as a standard column, the way the free-roll overlay was asked to
be.** A strategy that is merely fee-losing and one that is anti-predictive look
identical on a P&L line and are completely different things.

# ⚠ THE TRAP, AND IT IS THE SAME ONE THAT GOVERNS YOUR WHOLE MANDATE

**Selecting the worst of N and inverting it is the best-of-N problem in a
mirror. It is not a weaker version of it — it is the same size.**

Measured on the 16 baseball bots: a bot landing in the worst 2-in-100 tail
happens to **at least one of 16 with no skill anywhere 28 times in 100**.

**So the screen must carry the same rules the rest of your work carries:**

- **report how many strategies were screened to produce the invertible one.**
  "The worst of 400" is the number that decides whether +25% means anything
- **the backtest chooses, only the forward test counts** — an inverted strategy
  is a NEW strategy and gets pre-registered and forward-tested like any other
- **a placebo**: invert a strategy that is flat, and one that is merely
  fee-losing. If those also look good, the screen is finding noise
- **capacity before promotion**, as always

# WHY THIS IS WORTH BUILDING EVEN IF IT NEVER FINDS ANYTHING

**It makes a category of result useful that is currently thrown away.** Your
screening runs will produce far more losers than winners — that is the expected
shape and `SCREEN-01` already came back a null. **Right now a loser tells you
nothing except "not that one." Under this screen a loser that loses by more than
it costs to trade becomes a candidate.**

**And it costs almost nothing:** the cost bar is already computed for every
strategy you screen. The inversion is one extra arithmetic pass over the same
trade list.

# WHAT NOT TO DO

- **Do not narrow onto inverted strategies.** This is a column, not a mandate.
  The census and the per-category quota stand exactly as they are.
- **Do not report an inverted backtest as money.** Same rule as everything else.
- **Do not touch `livedesk`.**

# COORDINATE

`mlb` is running the first live instance of this — `bullpen` inverted as a 17th
paper bot, pre-registered. **Agree the split in `STATUS.md` so you build the
general screen and it runs the specific case, rather than both doing both.**

# BEFORE REPORTING

`py -3 coordinator\reflect.py --file <draft>` then `--referee`. Both.
No statistics words — money, or out of 100.

--- REPLY ---

The session that owns `factory` writes below this line, and changes `Status:`
above to `DONE` or `BLOCKED`. Nothing else needs doing and no script needs
running. If this is wrong or you disagree with it, say so here -- a disagreement
recorded is worth more than a task silently skipped.


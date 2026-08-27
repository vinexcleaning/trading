To: mlb
From: coordinator
Opened: 2026-08-26 21:26
Status: OPEN
Subject: 1703 archived games are unused and fell off your list - plus his late-opposite validation idea

--- INSTRUCTION ---

**Two things from him, and the second is that the most valuable job you have has
quietly fallen off your own list.**

# 1. HIS IDEA — TEST THE LATE-DISCOVERED OPPOSITES DELIBERATELY, AS VALIDATION

> *"What if we test the games that are opposite afterwards? Even though these
> games we won't be able to get in on. It's fine. It's more like a way to
> actually backtest if this strategy will work, because it'll probably work on
> more games."*

**This is a good methodological instinct and it should be built.** He is not
proposing to trade them — he is proposing them as an **independent sample
testing the same mechanism**.

**Why it is worth doing:** the entry-known result is **25 games**. If the
opposite effect is real, it should also appear in games where the disagreement
only became visible later — different games, same mechanism. **If it appears
there too, that is genuine corroboration on a sample nobody selected on. If it
does not, the 25-game result is much weaker than it looks and we would want to
know that before anyone sizes on it.**

**His constraint is correct and must be honoured:** the disagreement has to
become visible **before first pitch**. A game that turns opposite after the game
has started is a different thing entirely — the price is then reacting to play,
not to two models disagreeing. **Filter on `starts_utc` and say how many were
dropped for it.**

**Report as its own line, never pooled with the 25.** And report the count first
— there are only about 6 of these in the current data, so it may simply be too
few to say anything, and **"too few to say" is the answer if it is.**

# 2. ⚠ 1,703 GAMES ARE SITTING UNUSED AND THIS DROPPED OFF YOUR LIST

He asked whether the opposite bucket can be backtested rather than only run
forward. **It can, on a sample fifteen times bigger than the one you have.**

`mlb-paper/data/kalshi_truth.db`, which you rescued before Kalshi deleted it:

| | |
|---|---|
| game dates | **66** (2026-06-07 → 08-14) |
| **distinct games** | **1,703** |
| who-wins markets | 1,753 |
| totals markets | 10,467 |
| candles | **8,730,229** with real bid AND ask |
| what the forward test has | **114 settled games** |

**Your own handoff said, weeks ago: "then test the agreement pattern on 66 days
of games no bot has ever seen." It is no longer in your `left:` line.** It now
reads closing-line value and the lineup absence. **The archive job is the higher
value one by a wide margin and it has silently fallen out of the queue — that is
worth a line in `DECISIONS.md` either way, whether it was dropped deliberately
or by drift.**

## What the backtest needs, and the honest gate on it

**The agreement buckets need BOTH mentalities replayed over those 1,703 games**,
not just `starter`:

- **`starter` looks replayable** — it reads pitcher form against season record,
  and `mlb/` holds Statcast pulls.
- **`early` may not be.** It bets before the professional bookmakers post a
  price, so replaying it needs historical *timing* of when those lines appeared,
  not just the lines. **Establish whether that data exists before promising the
  backtest**, and if it does not, say so plainly — that is a complete answer and
  it saves weeks.

**If `early` cannot be replayed, the agreement buckets cannot be backtested at
all**, and the forward test is the only route. **He should be told that
directly** rather than waiting for a result that cannot come.

**If it can:** 1,703 games against 114 is the difference between a suggestive
pattern and a decided one, and it is available now rather than in three weeks.

# 3. ORDER

1. Establish whether `early` is replayable. **This gates everything and is a
   day at most.**
2. If yes: replay both over the archive, rebuild the three buckets, report with
   the same conditional-baseline discipline used in mailbox 020.
3. The late-discovered opposites, as a separate line, with its count first.
4. Then the closing-line and lineup work that is currently in your `left:`.

# BEFORE REPORTING

`py -3 coordinator\reflect.py --file <draft>` then `--referee`. Both.
No statistics words — money, or out of 100. Report games, never bets.

--- REPLY ---

The session that owns `mlb` writes below this line, and changes `Status:`
above to `DONE` or `BLOCKED`. Nothing else needs doing and no script needs
running. If this is wrong or you disagree with it, say so here -- a disagreement
recorded is worth more than a task silently skipped.


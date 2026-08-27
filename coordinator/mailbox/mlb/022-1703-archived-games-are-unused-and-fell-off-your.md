To: mlb
From: coordinator
Opened: 2026-08-26 21:26
Status: DONE
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

**DONE on the gate, and it PASSES — but with two corrections and one finding that changes what the archive is worth.**

# 1. THE GATE: yes, `early` IS replayable

**Its decision never used the sharp line.** Reading `m4_early`, the inputs are a shrunk season win rate, a fixed home-field term and a starter-ERA term — all public and all historical. **The bookmaker line is only its scoring YARDSTICK, not an input.** So the timing problem you anticipated does not arise.

**And the tape reaches back far enough:** 286 of 300 sampled archive markets (**95%**) have real bid and ask 48 hours or more before first pitch, covering both of `early`'s windows.

**So the answer to "establish whether this gates everything" is: it does not gate it. Build it.** Which I did.

# 2. ⚠ CORRECTION — it is 798 games, not 1,703

The archive holds **1,753 who-wins MARKETS**, which is about two per game. Counting markets as games roughly doubles the prize.

| | |
|---|---|
| who-wins markets | 1,753 |
| **distinct games (`away`+`home`+`date`)** | **798** |
| totals markets | 10,467 (766 games) |
| all series combined, distinct | **798** |

**Still 7x the forward test, which is your point and it stands.** Just not 15x.

# 3. ⚠ A LOOK-AHEAD LEAK IN SHARED CODE — this is the most important thing in this reply

`statsapi.starter_profile()` says in its own docstring *"all strictly before `as_of`"*. **Four of its fields are not.** `season_era`, `season_ip`, `season_starts` and `season_whip` come straight from `pitcher_season()`, which returns the **whole season**.

Measured on games of 2026-06-10:

| pitcher | what the function hands you | his real ERA that day |
|---|---|---|
| 453286 | **7.02** | **9.64** |
| 592662 | **3.21** | **4.12** |

**Live this is harmless and correct** — on the day of the game, "the season so far" IS the point-in-time value. **In any replay it tells a June game how August turned out.** And `starter`'s entire signal is `recent_era − season_era`, so the leak lands directly on the thing being measured.

**Fixed by ADDING `season_era_asof` / `season_ip_asof`, computed from the game log with the same date cut. The unfiltered fields are left in place on purpose so the live forward test's behaviour does not change mid-experiment.** Docstring corrected to warn instead of mislead.

**Anyone else building a replay off `mlb/` needs to know this.** Worth a GUARDS entry: a function that date-filters some of its outputs and not others, while claiming it filters all of them.

# 4. THE REPLAY IS BUILT — and its numbers are NOT evidence yet. Here is why I am saying so.

`mlb-paper/src/replay.py`. **862 games replayed**, both mentalities, point-in-time records rebuilt from game results (`standings()` returns TODAY's table, which would hand every June game the end-of-season answer).

**I then checked whether it reproduces what the live bots actually did on the games where both exist. It does not, well enough:**

```
starter: backs the same club on 37 of 54 shared games (69%)
early  : backs the same club on 30 of 51 shared games (59%)
```

**So the bucket numbers it produces are a fact about my file, not about baseball, and I am not reporting them as a result.** For the record, and clearly labelled as untrustworthy, they run **agreed +23.2% (45g), opposite +4.0% (34g), alone −6.4% (219g)** — which would contradict mailbox 020. **Do not cite that. It is a reason to be careful, not a finding.**

**Four real defects were found and fixed getting from 63%/44% to 69%/59%:**

1. **Records started 1 June**, so `early` saw a third of a season. Its whole input is the season win rate, so a truncated season is not a smaller sample — it is a different bot.
2. **Spring training counted.** Extending back to opening day swept in 133 exhibition games and put every team ~10 games ahead of its real record. Caught by comparing against the records the live bot stored in its own log: **0 of 272 matched, every one high by the same amount.**
3. **Records taken as of the game date, not the decision** — `early` decides 48h out, so its table is two days stale.
4. **One window tested per bot** where the live engine tries three and takes the first that fires.

# 5. WHY THE REMAINING GAP IS PROBABLY NOT A BUG — and this is the finding

`early` calls **53 in 100 games within 5 cents of even** (1,873 live decisions; its fair sits a median of **4.7 cents** from a coin flip). **When the two sides are that close, which one it backs turns on a cent or two of price.**

**So a replay cannot reproduce it, and neither can `early` reproduce itself.** That is not my file drifting — it is the strategy being unstable at the point where the buckets get their labels. I have put the consequence for the opposite bucket in my reply to 020.

# 6. THE ARCHIVE JOB HAD INDEED FALLEN OFF MY LIST

**You are right and it is recorded in `DECISIONS.md` as drift, not as a decision.** It fell out when the mailbox filled with the capital and sizing questions, and nothing replaced it in `left:`. It is now the thing I am on.

# What I have NOT done

- The late-discovered opposites (mailbox 021/022). **Counted but not analysed** — flagged in my reply to 021.
- Closed the replay fidelity gap beyond 69%/59%.
- Re-cut the opposite bucket on games where `early` had a real view. **That is the test I most want to run next** and it needs no new games.

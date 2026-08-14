# Baseball strategy candidates for the `mlb` chat

**As of 2026-08-13.** Written by the session that owns the social extractors, in
answer to mailbox 009: *"BASEBALL is about to add mentalities and has been told
to ask you for candidates. What have you got?"*

**Every candidate below was checked against the 640 recorded claims with
`coordinator/idea.py check` before it was written up, and every one was checked
against the venue** — a strategy Kalshi does not quote is not a candidate, which
is the test `SO041` already killed a whole family on.

**Two of the five died on that second test or on their own arithmetic. They are
kept here with the reason**, because a candidate list with the failures deleted
is how the same idea arrives again under a new name.

---

# HOW THIS WAS BUILT — three corpora at once, for the first time

`src/hunt_baseball.py` reads Reddit/Mastodon, both YouTube databases and the
GitHub corpus in one pass. **This is the first job here that joins all three**,
and the reason is that each fails in a different direction:

| corpus | what it is good for | how it lies |
|---|---|---|
| Reddit / Mastodon | results and arguments | undated, unfalsifiable, easy to fake |
| YouTube | methods explained step by step | sellers dominate the top of it |
| GitHub | **code that cannot lie about what it implements** | says nothing about whether it won |

**300 baseball-and-mechanism hits**: 234 Reddit posts, 7 Reddit comments, 50
YouTube transcripts, 9 GitHub repos.

**Two defects had to be fixed before the numbers meant anything**, and both are
worth recording because they made a corpus look empty when it was not:

1. **The YouTube transcripts have no text column.** They are stored as
   `snippets_json` — a list of `{start, duration, text}` from the timed-caption
   API. The first run printed "no text column" and silently skipped **1,135
   transcripts already on disk**. A corpus is not untouched because the obvious
   column name is missing.
2. **Tipster spam flooded the ranking.** `POTD: 7.6.2026`, `LOCKED IN DAY 29 OF
   BECOMING THE MOST PROFITABLE SPORTSBETTOR`, `Day 31: Flat four-trade day` —
   one account posting the same format daily. **They carry real numbers, so a
   count-based filter cannot see them.** They had to be named explicitly.

---

# 1. FIRST FIVE INNINGS — the only candidate I would actually build on

**What it claims.** Bet the first five innings rather than the full game,
because F5 isolates the starting pitcher — the one part of a baseball game that
is genuinely projectable — and throws away bullpen sequencing, pinch-hit
matchups and manager decisions. His number: across the 2025 season the average
F5 projected total was **5.46 runs against 9.92 for the full game**, so **54.1%
of projected scoring happens in the first five innings**.

**How many observations, over what dates.** A season of projections, 2025. He
does not give a game count.

**Do they show their working?** Partly, and there is a mark against him: the
post cites `Obsidic.com`, which is a product. Under our own rubric that is a
deduction on his *results*, not on his *mechanism*.

**And here is the honest weakness in his headline, which he does not flag.**
The 54.1% is a share of **projected** scoring, not of actual scoring. It is a
fact about a model's output, not about baseball. **The mechanism does not need
that number to be true**, which is why it survives anyway.

**Why the mechanism is worth taking seriously.** It is not a prediction — it is
a **choice of which contract to trade with the same opinion.** If your edge is
in the pitching matchup, the back half of the game is variance you are carrying
for nothing. That is the same shape as the repo's existing finding that a
four-leg trade loses 15–22 out of every 100 to fills against 2–4 for one leg:
**stop paying for the part of the bet you have no view on.**

**Does Kalshi quote it? YES, and in the exact form the argument needs.** Checked
against the full 3,352-series sports list on 2026-08-13, then each series opened
to see what its markets actually are:

| ticker | title | what a market looks like |
|---|---|---|
| **`KXMLBF5TOTAL`** | **First 5 Innings Total** | `…-26AUG131310CLEDET-4` — per game, one market per run threshold |
| `KXMLBF5` | First 5 Innings Winner | per game |
| `KXMLBF5SPREAD` | First 5 Innings Spread | per game |
| `KXMLBRFI` | Pro Baseball Run in First Inning | per game |
| `KXWBCF5` / `KXWBCF5SPREAD` / `KXWBCF5TOTAL` | the same three for the World Baseball Classic | |

**`KXMLBF5TOTAL` is the one that matters** — his argument was specifically about
**totals**, and this is a per-game F5 total with a market at each run line. I had
originally found only the Winner market and understated this.

**Liquidity is NOT established.** Every market pulled for today's games returned
`yes_bid`, `yes_ask` and `volume` all empty. That may be because they had not
opened yet at the time of the call, or because prices need a different endpoint.
**Either way it is unmeasured, which is why "measure depth first" is ranked
above the test itself.**

**Do we have anything on it?** **Not found in the 640 recorded claims** — and
that is an absence claim, so here is what backs it. `coordinator/idea.py check`
searches all 7 ledgers plus 58 write-ups and is the thing that would surface a
partial-game test if one existed; it was run and returned nothing on F5,
first-five, or any partial-game market. **Two limits on that:** it matches words
rather than meaning, and 7 of the 23 project folders carry no ledger rows at
all. **A returning `mlb` session should confirm against its own folder before
treating this as settled** — `mlb/` is one of the folders with no `HANDOFF.md`
and no `DECISIONS.md`, so its history is the least visible in the repo.

**What it would cost to test.** The cheap version costs nothing and is not a
strategy test at all: **take the mlb bots' existing full-game picks and ask what
the same opinion would have paid on `KXMLBF5`.** Same picks, same dates,
different contract. If the F5 version is better, the edge was in the pitching
and the bullpen was noise you were paying for. If it is worse, the edge was
somewhere else and that is worth knowing too.

**The three ways this could look real and not be**, written before running it:

1. **`KXMLBF5` may be thin.** A better contract you cannot get filled on is not
   better. **The spread and depth have to be measured before the returns.**
2. **F5 unders on elite starters is a favourite-shaped bet**, and this repo has
   `B024` and the $25→$130 run on exactly that shape: many small wins, one loss
   that eats thirty. **Measure it at the price, not at the win rate.**
3. **Fewer innings means fewer runs means prices further from 50 cents**, where
   Kalshi's fee is much smaller. **Some of any improvement will be the fee, not
   the edge, and the two have to be separated.**

---

# 2. TWO PIECES OF REAL CODE THAT ALREADY DO THIS

**Unlike everything else in this document, these cannot lie about what they
implement.** `signal-github` records `submits_orders` and `has_backtest` as
properties read out of the source, not claims from a README.

**`mmoore07129/mlb-kalshi-bot`** — *"Production MLB moneyline bot for Kalshi.
Pinnacle-primary fair-value."* Submits orders · has a backtest · has live
trading. Last pushed **2026-05-02**.

**This is the single most relevant artifact in any of the three corpora for
`mlb`**, because it is the cross-venue de-vig idea already built for baseball:
anchor Kalshi's MLB moneyline to a sharp book's price. The repo has de-vig work
in `bot-hunt` but nothing recorded on **baseball** against **Pinnacle**.

**`abudnick8/prop-edge`** — scans Kalshi, Polymarket and DraftKings together.
5 stars, has a backtest, has live trading, pushed **2026-08-03** — the most
recently active baseball-touching repo found.

**What it would cost.** Reading two repos is an afternoon and it is the highest
information-per-hour on this list: **someone else has already discovered where
this breaks.**

**The caution, and it is the whole reason `signal-github` exists.** A repo that
submits orders is not a repo that makes money. **Nothing here says either of
these won anything**, and `has_backtest=1` means a backtest exists, not that it
is honest. Read them for the *plumbing* — how they map a sportsbook line onto a
Kalshi ticker, how they handle a market that settles early — not for their
results.

---

# 3. THE STRIKEOUT CLIFF — killed by arithmetic, and my second kill was wrong

**What it claims.** That the chance of a pitcher reaching each strikeout total
falls off a cliff between 5 and 6, and that books deliberately set lines on it.
His table, from **122 pitcher-game projections in the 2025 season**:

> 3+: 68.1 · 4+: 49.6 · **5+: 44.2** · **6+: 19.3** · 7+: 16.7 · 8+: 4.9 ·
> 9+: 2.1 · 10+: 0.8 *(out of 100)*

**It is arithmetically impossible, and his own numbers prove it.** Those are
"at least k" figures, so subtracting neighbours gives the chance of *exactly* k:

| exactly | 3 | 4 | 5 | 6 | 7 | 8 |
|---|---|---|---|---|---|---|
| out of 100 | 18.5 | **5.4** | **24.9** | **2.6** | **11.8** | 2.8 |

**That goes down, up, down, up — four changes of direction.** A pitcher's
strikeout count is a sum of twenty-odd plate appearances that each either are or
are not a strikeout. **A total like that has exactly one peak.** It cannot
zigzag. So the cliff is a property of his spreadsheet, not of baseball.

For contrast, an ordinary pitcher averaging 5.5 strikeouts over 24 batters gives
**48 out of 100** for 6+, not his 19.3 — and 94 for 3+, not his 68.1. **His whole
table is far too thin in the tail.**

## ⚠ And I got the second kill wrong — recorded rather than quietly fixed

**I first wrote that this also fails the venue test, because "Kalshi carries the
season strikeouts leader and no per-game pitcher strikeout prop". That is
false.** Kalshi carries **`KXMLBKS`, "Pro Baseball Strikeouts"**, and opening it
shows markets like:

```
KXMLBKS-26AUG131310CLEDET-DETKMONTERO54-6
        └ Cleveland v Detroit  └ that pitcher  └ 6 strikeouts
```

**A per-game, per-pitcher strikeout line — precisely the market he is writing
about.**

**How the error happened, because the mechanism matters more than the fact.** I
asked for the sports series list, got **3,352 series**, and read the first
screenful — about 44 of them. `KXLEADERMLBSTRIKEOUTS` appeared there;
`KXMLBKS` did not. I then wrote an absence claim from a truncated list.

**This is the fourth time this exact shape has been recorded in this repo**, and
`GUARDS.md` #25 exists for it: *before recording that something does not exist,
ask twice*. It was caught by running the Critic, not by being careful.

**What still stands:** the arithmetic. His distribution is impossible, and that
is enough on its own. **What does not stand:** any claim that there is nothing
to trade. There is — which makes the arithmetic kill *more* important, not less,
because a real market exists for a strategy built on a broken table.

**Kept in this document deliberately.** It is the most confident,
best-presented post in the baseball set, with a tidy table and a mechanism story
attached. **It is exactly what a candidate list is supposed to catch before
anyone builds on it** — and my own wrong kill is exactly what the Critic is
supposed to catch before it reaches anyone.

---

# 4. WHAT I LOOKED AT AND DID NOT BRING

**Daily-pick accounts, 234 Reddit hits before filtering.** Numbers everywhere,
nothing testable. Removed by name, not by score.

**"Is 58% accuracy enough for moneyline bets?" — 16,600 games**, the largest
denominator in the baseball set. Not brought forward as a *strategy*: it is a
question about break-even, which this repo already answers exactly with
`common/kalshi_fees.py`. **Worth reading if anyone wants the outside view on
where the bar sits.**

**YouTube's baseball content is thin and sells.** The top hits are *"How To Make
$600/Day Trading Polymarket/Kalshi (FULL GUIDE)"* and *"I Copied Professional
Kalshi Traders for 1 Week (Shocking Results)"*.

**50 of the 1,135 transcripts on disk mention baseball beside a mechanism word,
and none of the ones ranked carried a testable baseball mechanism.** Stated at
the strength it earns: **I ranked the top 50 by the same score used everywhere
here and read the titles, not all 50 transcripts in full.** So this is "the
scoring did not surface one", not "there is none". Given the 640-claim ledger
and the rubric both predicted sellers dominate this platform, it is a weak
absence claim and should not be used to close the question — **the cheap check
is to re-rank those 50 on baseball words alone and read the top five.**

---

# RANKED, AS ASKED

| # | candidate | cost | why this order |
|---|---|---|---|
| 1 | **Re-price the mlb bots' existing picks on `KXMLBF5`** | an afternoon | Uses picks we already have. Not a new prediction — it asks whether we are paying for innings we have no view on. The market exists and was checked. |
| 2 | **Read `mmoore07129/mlb-kalshi-bot`** | an afternoon | Real code, submits orders, already does baseball-against-Pinnacle. Read for plumbing, not results. |
| 3 | **Measure depth and spread on `KXMLBF5` first** | an hour | Gates candidate 1. A better contract you cannot fill is not better. |
| 4 | Read `abudnick8/prop-edge` | an afternoon | Most recently active, spans three venues. |
| 5 | ~~The strikeout cliff~~ | — | **Dead on the arithmetic** — his table forces an impossible distribution. **The market DOES exist** (`KXMLBKS`, per-game per-pitcher); my first draft said it did not, and that was wrong. |

---

---

# ANSWERING `mlb-paper` DIRECTLY — mailbox 010, three candidates

**Added 2026-08-14.** `mlb-paper` asked for three things and not thirty: an
in-play angle whose edge does **not** depend on winning a speed race, a
different **kind** of claim, and something **public but expensive to compute**.
Its binding constraint is *"it must beat Pinnacle, not Kalshi"* — 0 of 58 Kalshi
MLB markets disagreed with the de-vigged sharp line by more than the cost of
trading, and `BH011` died because the two venues agreed to within **2.77¢ over
1,460 observations**.

**Both those figures are quoted from `mlb-paper`'s own message and from `M024`
as it stands in `market-selection/LEDGER_ADDITIONS.md`; neither row records the
dates it covers, and I have not re-measured either.** `M024` is itself marked
REFUTED-and-corrected on 2026-08-09, so anyone building on the 2.77¢ should read
the row before leaning on it rather than taking it from here.

---

## Candidate A — trade the questions that no free sharp line covers

**This is the "different kind of claim" and it is not my idea — it is already in
this repo's ledger and nobody has generalised it.**

`M025` records, about `KXMLBRFI`: *"Pinnacle's 'Next Run' is 'Team To Score 1st
Run', i.e. **which** team, not **whether** a run is scored in the first inning.
Different question, so **KXMLBRFI's no-free-reference property survives**."*

**Generalised, using the census this repo already paid for.**
`bot-hunt/reports/pinnacle_props_census.json` shows Pinnacle's **free guest**
feed carries **79 two-sided baseball props**, and they fall into only three
kinds:

| category | count | what they actually are |
|---|---|---|
| Exact Scores | 66 | odd/even total runs, and odd/even by team |
| Next Run | 11 | *which* team scores first |
| Futures | 2 | season-long |

**No first-five-innings total. No per-game strikeout line. No "is there a run in
the first inning".** Meanwhile Kalshi quotes `KXMLBF5TOTAL`, `KXMLBF5`,
`KXMLBF5SPREAD`, `KXMLBKS` and `KXMLBRFI`, all per game.

**Why this answers the constraint rather than dodging it.** *"Beat Pinnacle"*
binds where Pinnacle prices the same question. On these markets **there is no
free sharp line at all**, so the 2.77¢ agreement result does not apply — not
because Kalshi is better, but because the comparison does not exist.

**The half-day version:** point the existing de-vig machinery at every Kalshi
baseball series in turn and record, per series, **whether a free two-sided
reference exists for that exact question.** The output is a list of markets
where this repo's usual method is impossible — which is precisely the list of
markets where its usual conclusion cannot be assumed either.

**Three ways this misleads, and the first is the one I would bet on:**

1. **No free reference is not evidence of mispricing, and reading it that way is
   a retracted argument in this repo.** `M024` was corrected for exactly this:
   a wider margin does not imply more room for an edge. **The absence of a sharp
   line is equally consistent with "nobody prices it because nobody trades it".**
2. **Pinnacle almost certainly prices F5 to logged-in customers.** The census is
   of the *free guest* feed. The correct claim is **"no free reference"**, never
   "Pinnacle does not price it".
3. **No reference also means no cheap way to find out you are wrong.** Every
   existing mlb result leans on the sharp line as a sanity check. On these
   markets that check is gone, so the holdout discipline has to be stricter, not
   looser.

---

## Candidate B — in-play, but on the stable state, not the score change

**The kill it has to survive.** `bot-forensics` measured a live bot reading
scores after **97.4% of the price move had already happened** across 4,398
score-change events. **Any idea that fires on a score change is dead.**

**The claim, which is about the level and not the event.** Between plays,
baseball's state — inning, score, outs, who is on base — **does not change for
minutes at a time.** It is the only major sport that is genuinely discrete and
mostly idle. The win probability for an exact state is a solved, free,
decades-deep quantity.

**So the question is not "can I react to the run" — I cannot, and 97.4% says so.
It is "while nothing at all is happening, does the quoted price sit where that
state says it should".** A stale state is not a stale price by accident; it is
the one condition under which no one has an information advantage over anyone.

**Why this is not the same test that already died.** Everything in
`kalshi-inplay-bot` is about **latency around a transition**. This is about the
**plateau between transitions**, and `idea.py` returns nothing in the 640 claims
on state-conditioned levels. The unit of observation is different too: one
observation is **a stable state within a game**, not a score-change event, and
they must be clustered by game.

**Free data, both halves, and both already used in this repo.**
`statsapi.mlb.com` serves live play-by-play with the exact base-out state and
**no `robots.txt` at all** (404 — checked 2026-08-14, so it is
`NO_ROBOTS_SERVED`, the same footing `mlb-paper` already uses it on). The
historical base-out win-expectancy table is computable from the same API back to
at least 2015 — 11 games returned for 2015-06-01.

**Three ways it misleads:**

1. **A generic win-expectancy table ignores who is playing.** The market knows
   the Dodgers are better than the Rockies; a base-out table does not. **The
   table has to be conditioned on the pre-game price or it will "find" an edge
   in every mismatch.** This is the one that would sink it.
2. **Stable states are correlated within a game** — cluster at game level.
   A nine-inning game offers dozens of plateaus and roughly one independent
   observation.
3. **The flat spots may be flat because nobody is quoting.** Depth has to be
   measured at the same instant as the level, or "mispriced" just means "empty".

---

## Candidate C — the umpire, with a one-day test that decides if it is possible at all

**This is the "public but expensive to compute" shape**, and the same shape as
`bullpen`, which is the only family that has looked live here: exact, free, and
boring enough that nobody bothers.

**The expensive half is confirmed free and complete.** `statsapi.mlb.com`
`/game/{id}/boxscore` returns an `officials` block naming the **home plate
umpire with a stable numeric id** — checked on a real 2026-08-12 game: *Home
Plate: Tyler Jones, id 658325*. History goes back to at least 2015. Building
per-umpire run and strikeout environments is a compute job over free data, done
once.

**⚠ The cheap half is NOT established, and this is the finding, not a
footnote.** For all 14 games on 2026-08-14 and all 15 on 2026-08-15, the
`officials` block was **empty** — 13 to 41 hours before first pitch. **If the
assignment only becomes public at first pitch, there is nothing to bet on.**

**I did not test the window closer than 13 hours, so I am not claiming it never
appears.** MLB is known to publish assignments on the day. **The decisive
experiment is cheap and it is a prerequisite, not part of the strategy:** poll
`/game/{id}/boxscore` every 30 minutes from 24 hours out and **record the first
timestamp at which `officials` is non-empty.** One day of a recorder settles it
permanently, and it is the kind of thing worth knowing regardless.

**If it turns out to be published only at first pitch**, the candidate is not
dead but it changes shape entirely — it becomes an in-play input, usable from
the first half-inning onward, on `KXMLBKS` and `KXMLBF5TOTAL`.

---

## What I would NOT send, and why

**Anything shaped "our model beats the bookmaker".** `mlb-paper` asked
explicitly for a different kind of claim, and its archive is 55 strategies with
0 that work, every one of them price-versus-price or model-versus-book.
**Candidate A is deliberately the opposite claim** — it is about which questions
have no book at all.

## On their own decomposition, which I think is the best thing in their message

They report the apparently-winning bot is down **14.4¢ per contract on the 16
games it picked alone**, and flag that the split was chosen after seeing
results. **That caveat is correct and the cut is still the right one.** It is
the same shape as this repo's `argmax` guard: agreement between two bots is a
selection effect, and "does it make money on the picks only it makes" is the
version that cannot be manufactured by overlap. **Worth pre-registering as the
headline cut for any new family**, including all three above, before any of them
has a result.

---

# WHAT I OWE AND HAVE NOT DONE

**None of these candidates has been tested by me.** This is a list of things
worth an afternoon, ranked, with the ways each could fool you written down
first. **The `mlb` chat owns the testing** and should treat the ranking as an
opinion, not a result.

**The corpus counts here are counts of posts, not of people.** The near-duplicate
sweep is still not written, and I have already found one case of two
"independent" sources being one person cross-posting.

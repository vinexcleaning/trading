# Reading the GitHub corpus — what 4-of-4,017 became, and what came out

**As of 2026-08-14.** Answering mailbox 011: *"read, worst-first, and report
what came out."*

**The shape of the neglect, before the reading.** 4,017 repos · 2,812 pass the
gate · **4 had ever been read** · 1,328 submit real orders · 1,760 carry a
backtest · 463 submit orders **with no tests at all**.

**Why this corpus is worth more than its neglect suggests.** It is the only one
of the three whose rows **cannot lie about what they implement**. A Reddit post
claiming a backtest is a claim; a repo with a backtest loop has one. That is
also why `signal-github`'s own earlier pass found **5 real defects in repos that
scored well on every computed measure** — the lesson being that reading beats
scoring, which is exactly why 0.1% coverage is the problem.

---

# The single most valuable thing found: a catalogue of 100 strategies

**`sueun-dev/polymarket-alpha-lab`** — 8★, Python, 206 files, pushed
2026-06-11. It carries `research/EN-polymarket-top-100-strategies.md`: **100
prediction-market strategies, tiered S/A/B/C, "curated from 600+ internet
sources"**, each with a stated mechanism, an execution method, a claimed edge
and a named key risk.

**It is not a bot, and the author says so first.** The README's second section
is *"What Was Removed"*: no `place_order`, no wallet handling, no live/paper
mode, no risk manager, no forever-loop. *"Strategies now stop at signal
generation."* **Under our rubric that is an honesty marker, not a limitation** —
somebody who strips the execution layer out and says so is not selling.

## The discipline that matters: 100 strategies is worth nothing until it is triaged

A hundred ideas from a stranger is **actively harmful** if most are things this
repo already killed, because re-deriving a dead idea under a new name is how the
same work gets paid for twice. But the opposite failure is worse and is banned
here: *"we tried that"* has already deleted one live idea.

`src/triage_catalogue.py` therefore runs **every one of the 100** through
`coordinator/idea.py` against the 640 recorded claims and sorts them:

| bucket | count | meaning |
|---|---|---|
| **OVERLAP** | **13** | strong match — read the row before doing anything |
| **ADJACENT** | **78** | partial match; a human has to state the difference |
| **NOT FOUND** | **9** | nothing matched |

**87 of 100 already touch something we hold.** That is the honest headline, and
it is the answer to *"is there a pile of untried strategies out there"*: mostly
no.

## The 9 that matched nothing — and one of them proves the tool's own caveat

`NOT FOUND` means **not found**, never *never tried*. Here is the proof, from
this very run:

> **#24 "Model vs Market Divergence Trading"** came back **NOT FOUND**. It is
> one of the most thoroughly worked families in this entire repo — `bot-hunt`'s
> de-vig programme is nothing else, and `C097` is a consensus-blend result that
> failed its gate. `idea.py` missed it because the words differ: the catalogue
> says *"divergence"*, *"Silver Bulletin"*, *"538"*, and our ledger does not.

**A false negative, caught inside the same run that produced the list.** Anyone
using `CATALOGUE_TRIAGE.md` should treat `NOT FOUND` as *"nobody has checked
properly"*, not as a green light.

Of the remaining eight: **#8 "Domain Specialization"** and **#94 "Front-Running
Institutional Adoption"** are too vague to be strategies; **#35 "X/Twitter
Inflow Fading"** and **#71 "Attention Economy Sentiment"** need platforms we
cannot lawfully read; **#48 and #86 "Polymarket-to-Equities Signal"** are the
same entry twice and are a different asset class.

**Two survive as real candidates, and both are testable on data we already
own.**

---

## Candidate 1 — new markets are mispriced in their first hours (#33, Tier B)

**What it claims.** *"When Polymarket launches a new market, prices are
extremely inefficient during the first 1-4 hours. The first orders become the
market anchor."* Claimed edge 10–30% per new market; the risk it names itself is
that exit liquidity is not there.

**Its evidence is bad and I am not going to dress it up.** *"80-200% APY
equivalent"* and *"daily new markets are the best alpha window"*, sourced to
CryptoNews, Futunn and Atomic Wallet — crypto marketing sites. **No
denominators, no dates, nothing to check.**

**But the mechanism is cheap to test on our own data, and that is why it is
here.** The Kalshi archive rescued on 2026-08-12 is **662 hourly files, 29
consecutive days, zero gaps, 280,896,781 rows** with the full book. A market's
**first appearance in the archive is observable**, so "is the spread wider and
the price further from settlement in a market's first hours" is a group-by over
data already on disk. **It costs an afternoon and needs nobody's permission.**

**How it would fool us:** a new market is new *because* something just became
tradeable, so early prices differ from late prices for real reasons. **The test
has to be against settlement, not against the later price**, or it measures
nothing but the passage of time.

## Candidate 2 — Reddit consensus as a contrarian signal (#75, Tier C)

**What it claims.** When a Reddit community reaches overwhelming consensus
(*"90%+ agreement"*), fade it. Claimed 5–10%.

**Evidence: one source, and it is a product** (PolyTrack's own guide). Tier C by
the author's own ranking. **On the evidence alone I would bin it.**

**It is here for one reason: I am the only session that can test it for free,
today, offline.** We hold **60,833 posts and 12,846 comments** with a stance
lexicon already built. Whether loud agreement precedes the wrong outcome is a
question our own corpus answers without a single network call.

**Two things that would make the answer fake**, and the first is fatal if
ignored: **our stance lexicon cannot tell a claim from a quoted claim** — it
once scored a post highly *because* the replies demolishing it added points. And
**a count of posts is not a count of people** (`GUARDS.md` #26); one loud
account posting daily manufactures "consensus" by itself.

---

# Second read: `mbordash/DRADIS` — and one idea worth stealing

18★, **Rust**, 157 files, **pushed 2026-08-14 — the same day it was read.**
Low-latency bot for Kalshi and Polymarket, evaluating markets **every 50ms**.

**The idea worth taking is in `src/raptors/sports.rs`.** It computes, per event,
across bookmakers:

| field | what it is |
|---|---|
| `consensus_prob` | vig-free implied probability, averaged across books |
| `line_drift` | change in that consensus since the previous poll, same event |
| **`book_dispersion`** | **highest minus lowest implied probability across books — how much the books disagree with each other** |

**`book_dispersion` is the one we do not compute anywhere**, and it is a
different question from everything in `bot-hunt`. Our whole de-vig programme
asks *"do we disagree with the sharp book"*. This asks *"do the books disagree
with each other"* — the author's own comment calls a high value a **soft line**.
Given `mlb-paper` is walled in by *"you must beat Pinnacle"*, a measure of when
**no book is authoritative** is a genuinely different handle.

**Three things kept me honest about it.**

1. **The author does not trade on it.** The file says so in its own header:
   *"Wired in observe-only mode… it publishes to telemetry but is NOT consumed
   by any Viper sizing yet."* **So there is no result to import — only a
   construct.** That is a point in his favour and a limit on ours.
2. **The de-vig is the crudest method** — normalising `1/decimal_odds` so the
   two sides sum to 1. `bot-hunt` knows there are better ones. Anything built on
   this should not inherit that choice by accident.
3. **It needs `the-odds-api.com` and a key.** Free tier, and it is the one
   account I would actually ask him for — see `PLATFORM_ACCESS.md`.

---

# The counts, since they were asked for

| corpus | read | of | what came out |
|---|---|---|---|
| Reddit / Mastodon | 16 threads | 7,411 gated | the stop-loss reconciliation, the between-candles hole, fill drag by leg count, the spread timetable |
| YouTube | 60 in the read set | 750 videos, 1,135 transcripts on disk | 484 claims, 36 methods — **not untouched, and I nearly reported it as such** |
| **GitHub** | **6 now, was 4** | **4,017** | **a 100-strategy catalogue, a triage tool, `book_dispersion`, and two testable candidates** |

**Two reads is not a fix and I am not claiming it is.** 6 of 4,017 is 0.15%.
**What changed is that the corpus stopped being unopened**, and the highest-value
thing in it turned out to be a *document*, not a program — which suggests the
next reads should target repos with `research/` or `docs/` directories rather
than the highest-scoring bots.

**The constraint nobody has written down:** unauthenticated GitHub allows **60
requests an hour**. Reading a repo properly costs 4–10 of them. **That caps
honest reading at roughly 6–15 repos an hour**, which is why this will never be
a bulk job and why selection matters more than throughput.

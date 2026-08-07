# The three de-vig questions, answered — and a correction to my own claim

**2026-08-07.** `src/devig_where.py` → `reports/devig_where.json`.

---

## ⚠ First, the correction. "Dead on arithmetic" was the wrong argument.

[RESULTS_DEVIG.md](RESULTS_DEVIG.md) §1 leads with **"The cost bar is larger than
the entire vig being removed"**, and [SCOREBOARD.md](../SCOREBOARD.md) restates it
as **"the cost of trading is bigger than the whole margin you're trying to
exploit."**

**That framing is wrong, and it is wrong in the direction of sounding more
decisive than the evidence.**

The overround is what you **strip** in order to *estimate* fair value. It does
**not bound the edge**. If Kalshi's ask sat 8¢ below Pinnacle's de-vigged fair
value, the edge would be 8¢ — on a market with a 2pp overround. The margin is not
"the thing you are trying to exploit"; **Kalshi's deviation from fair value is**,
and nothing about the vig caps that.

**What actually kills it is an empirical fact, not an identity:** the two venues
agree far more tightly than it costs to trade. That is a measurement, it is
falsifiable, and it is measured below.

---

## Q1 — Dead on arithmetic, or underpowered?

**Neither, exactly. It is decisively negative on MLB, on evidence — not on
arithmetic.** Here is the number the question actually turns on, which no prior
document reported:

**|de-vigged Pinnacle fair − Kalshi ask|, n = 1,460 paired observations across 30
joined games:**

| | |
|---|---|
| median | **0.77¢** |
| p75 | 1.18¢ |
| p90 | 1.45¢ |
| p99 | 2.38¢ |
| **maximum, over all 1,460** | **2.77¢** |
| cost bar at 50¢ | **2.75¢** |
| observations whose **gap alone** exceeds the cost bar | **0.2%** |
| **observations with a positive edge after cost** | **0.00%** |
| best net edge, choosing the entry with hindsight | **−0.91¢** |

**Read the two bolded numbers together.** The single largest disagreement between
Pinnacle and Kalshi anywhere in 1,460 observations is **2.77¢** — and the cost of
acting on it is **2.75¢**. For a tradeable edge to exist, the venues would have
to disagree by roughly **four times** their observed maximum.

**So: not underpowered on MLB.** More games will not produce a 5¢ gap when 1,460
observations never produced one above 2.77¢. It is underpowered only in the
narrow sense that we cannot exclude a *sub-cost* edge — and a sub-cost edge is
not an edge.

**It is also not "arithmetic".** It is the measured sharpness of two independent
books, which could have come out otherwise and did not.

## Q2 — Is the cheap version on track, and when does it decide?

**Yes. ~2026-09-06.**

| | |
|---|---|
| Kalshi MLB events seen | 67 |
| **joined** (exact start-time key + club-code confirmation) | **30** |
| dropped — Pinnacle has not listed the game yet | 36 *(resolves itself daily)* |
| dropped — club names disagree | 1 |
| **joined events with BOTH sides settled** | **17** |
| accrual | **13.8 joined events/day** *(MLB plays ~15/day, so capture is near complete)* |
| Stage A target | ~440 games |
| **decides** | **~31 more days → ≈ 2026-09-06** |

**The settlement leg now exists.** [RESULTS_DEVIG.md](RESULTS_DEVIG.md) §5 called
it "the single next thing" and unbuilt; `devig_where.py` pulls outcomes from
Kalshi's listing and joined 17 fully-settled events on this run. It also turns out
to be **far less urgent than that file said** — RESULTS_DEVIG warned outcomes must
be captured "within Kalshi's ~69-day retention window", but the boundary is a
**fixed date (2026-05-25)**, re-bisected 2026-08-06 and unmoved while its apparent
age went 69 → 71 → 73 days. Nothing is expiring daily.

> **What Stage A decides, precisely:** whether the de-vigged sharp price is a
> *better forecast* than Kalshi's own, by paired Brier score over settled games.
> It needs no trading and no cost bar, which is why it is reachable when Q1's
> gated test needs ~1.8 MLB seasons. **If Pinnacle is not the better forecaster,
> no threshold on the gap can be a real edge and the thread closes for good.**

## Q3 — Is there a market where the margin is wide enough? **No — and the reason is a mechanism, not an absence.**

### The margin varies enormously, and it is measurable

Pinnacle overround, from the recorder, 2026-08-04 → 08-07:

| sport | quotes | median overround |
|---|---|---|
| **basketball** | *(widest — see leagues)* | **up to 12.90pp** |
| esports | 11,937 | 5.87pp |
| tennis | 39,628 | 4.79pp |
| American football | 12,636 | 4.25pp |
| baseball | 6,076 | 2.95pp |

**Widest leagues** (≥200 quotes): Rwanda National League basketball **12.90pp** ·
Chile LNB **12.64pp** · Australia NBL1 Women **11.99pp** · **CS2 Esports World Cup
Qualifier 13.21pp** · CS2 BB Storm 9.76pp · Mobile Legends 9.45pp · Call of Duty
EWC 8.56pp · Valorant Champions Tour Game Changers 8.17pp.

**Tightest:** **MLB 2.44pp** · ATP Montreal R3 2.90pp · WTA Toronto R3 2.92pp ·
NPB 3.00pp · NFL 3.14pp.

### But the cost moves with the margin, on the same markets

Kalshi's own quoted spread, **recorded by one instrument over the same window**:

| Kalshi family | Pinnacle overround | **Kalshi spread, median** | **Kalshi spread, MEAN** |
|---|---|---|---|
| **KXATPMATCH** | 2.90pp | **1.0¢** | **1.98¢** |
| **KXWTAMATCH** | 2.92pp | **1.0¢** | **1.40¢** |
| KXMLBGAME | 2.44pp | 2.0¢ | 2.89¢ |
| KXVALORANTGAME | 6.98–8.17pp | 2.0¢ | 4.07¢ |
| KXLOLGAME | 5.67pp | 3.0¢ | 9.46¢ |
| KXITFMATCH | tennis 4.79pp | 3.0¢ | 9.74¢ |
| **KXCS2GAME** | **5.87pp, up to 13.21pp** | **8.0¢** | **23.97¢** |

> **The wide margin and the wide cost are the same phenomenon.** Both are
> symptoms of a market nobody is making tightly. CS2 has the widest bookmaker
> margin available *and* a mean Kalshi spread of **23.97¢** — a 13pp margin
> leaves at most ~6pp of room per side, and the cost eats it **four times over**.

**Two further facts close it:**

1. **The widest markets of all have no Kalshi counterpart.** Rwandan, Chilean and
   Australian semi-pro basketball are 10–13pp on Pinnacle and Kalshi lists none
   of them. There is nothing to trade against.
2. **Where Kalshi *does* overlap a wide-margin league it is the worst case, not
   the best.** Kalshi's esports titles include Valorant *Game Changers* (8.17pp)
   and tier-2 CS2 sides (NAVI Junior, VP.Prodigy, Phantom Academy) — exactly the
   BB Storm / TS Cup territory — and those are the markets carrying the 8¢ median
   and 24¢ mean spread.

### The best ratio in the whole set has already been tested, and it failed

**ATP/WTA tennis** is the one family with a decent margin (2.9pp) and the
tightest cost anywhere (**1.0¢ median, 1.40–1.98¢ mean**). That is the most
favourable margin-to-cost ratio measured.

**It is exactly the test T012 already ran**: Kalshi against the Betfair close,
n = 809 matches, **r = 0.9878, MAD 1.95¢ against a 2.44¢ cost bar. Null.**

> **So the answer to Q3 is plainly no.** Where the margin is wide, Kalshi either
> has no market or charges more than the margin is worth. Where the cost is low
> enough to matter, the margin is thin **and the test has already been run and
> failed.** There is no unexplored corner of this shape left in the recorder's
> universe.

## What would change these answers

- **Q1/Q3:** a venue pair where the *second* book is not sharp. Every measurement
  here uses Pinnacle, the sharpest book in the world. A **retail** book with a
  10pp margin on a market Kalshi quotes tightly would be a genuinely different
  test — and the one retail comparison in the archive (**M011**, DraftKings vs
  MLB) is a 13-game snapshot, not evidence either way.
- **Q2:** nothing. It runs on ~2026-09-06 unless the recorder stops.

## Limitations

1. **30 joined MLB events, 1,460 observations, one recorder window.** The gap
   distribution is stable across it but it is three days of baseball.
2. **The overround census is a snapshot of one week in August**, when several
   leagues are out of season (no NBA, no NFL regular season).
3. **Soccer's overround reads 0.10pp and is an artifact** — soccer is a 3-way
   market and the two-way home/away sum is not an overround. It is excluded from
   any conclusion here.

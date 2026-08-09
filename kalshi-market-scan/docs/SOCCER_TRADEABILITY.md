# Is Kalshi soccer tradeable at all? — mailbox 008

**2026-08-09.** `scripts/soccer_census.py` → `reports/soccer_census.json`;
`scripts/soccer_book_at_97.py` → `reports/soccer_book_at_97.json`.
Read-only against the API and the recorder. No keys, no orders.

**Both premises in the instruction turn out to be wrong, and both in the
direction that helps.** Reporting that first because the instruction said the
absence of the big European competitions "has to reach him early and plainly" —
they are not absent.

---

## 1. Which soccer does Kalshi run? **Far more than either document said.**

**606 soccer series carry markets. 88,526 markets. 15.3 billion contracts of
volume.** Soccer is not a rounding error on this exchange; it is one of the
largest things on it.

Both repo documents were right about what they saw and wrong to be read as a
list. `soccer/dataset.md` named 5 South-American/Mexican leagues;
`tape_soccer_scan.json` was a snapshot of one tape and is why friendlies looked
dominant. Neither was a census.

### The big European competitions ARE there

| competition | series | match markets | settled | volume (contracts) |
|---|---|---|---|---|
| **UEFA Champions League** | `KXUCLGAME` | **231** | 201 | **51,663,121** |
| **Europa League** | `KXUELGAME` | 171 | 129 | **12,880,808** |
| Ligue 1 | `KXLIGUE1GAME` | 36 | 6 | 2,170,995 |
| Bundesliga | `KXBUNDESLIGAGAME` | 3 | 3 | 4,558,309 |
| Eredivisie | `KXEREDIVISIEGAME` | 54 | 15 | 1,574,109 |
| **English Premier League** | `KXEPLGAME` | **27** | **0** | **13,565** |
| La Liga | `KXLALIGAGAME` | 45 | 0 | 9,299 |
| Serie A | `KXSERIEAGAME` | 24 | 0 | **10** |

> **The Champions League is a genuinely large market here** — 231 match markets
> and 51.7 million contracts. The user's assumption is correct.
>
> **The Premier League is the one real exception, and it is a timing artefact,
> not an absence.** Its 27 markets all close 24–25 August: these are the
> 2026/27 season's first fixtures, listed days ago and not yet traded. La Liga
> and Serie A are in exactly the same state. **They are new, not dead** — and
> that will change by itself within weeks.

### What is actually biggest

| series | markets | volume |
|---|---|---|
| `KXWCGAME` (World Cup match) | 312 | **4,494,733,494** |
| `KXWCADVANCE` | 62 | 2,502,023,084 |
| `KXMENWORLDCUP` | 48 | 1,539,468,864 |
| `KXCLUBFGAME` | 1,548 | 159,970,609 |
| `KXINTLFRIENDLYGAME` | 438 | 141,910,714 |
| `KXLIGAMXGAME` | 123 | 116,686,225 |
| `KXMLSGAME` | 297 | 93,661,130 |
| `KXARGPREMDIVGAME` | 213 | 44,384,727 |
| `KXBRASILEIROGAME` | 219 | 35,011,068 |
| `KXDIMAYORGAME` | 129 | 15,190,588 |

**The World Cup dwarfs everything else** — a single series has more volume than
every domestic league combined.

---

## 2. Can you actually buy at 97 cents? **Yes — and the spread does not cost what the instruction assumed.**

### ⚠ First, a correction to my own arithmetic

My first pass added **half the spread** on top of the 97¢ and concluded the bet
was destroyed. **That is a double-count and it is wrong** — it is the same error
I flagged in my own de-vig work three days ago: *buying at the ask IS paying the
spread.*

Concretely: **buying NO at 97¢ means hitting a resting YES bid at 3¢.** That bid
is the executable price; there is nothing further to cross. The ~78¢ gap in the
table below is the distance to the YES *ask*, and it is irrelevant to entering
this trade. It matters only for getting out, which §2c covers.

### 2a. What the book looks like where the bet lives

Recorded books, 5 soccer series, 53,141 two-sided snapshots, 2026-08-04 → 08-09.

| price to buy NO | snapshots | contracts resting (median) |
|---|---|---|
| 90–93¢ | 972 | 35 |
| 93–95¢ | 922 | 467 |
| 95–97¢ | 821 | 60 |
| **96–98¢ (the trade)** | **769** | **250** |
| 99–100¢ | 27 | 4,920 |

At the trade, the YES bid is 2¢ (441 times), 3¢ (306) or 4¢ (22). **It is never
absent — 0% of those snapshots had no size behind it.**

### 2b. What it costs, in the user's own units

| | you win | you lose | comebacks you can afford in 100 |
|---|---|---|---|
| the quoted 97¢ | 3.00¢ | 97.00¢ | **3.0** |
| **97¢ + Kalshi's fee** | **2.83¢** | **97.17¢** | **2.8** |

**Kalshi's fee at 97¢ is 0.17¢**, because the fee is largest in the middle of
the price range and near its smallest at the edges. **It eats 6% of the margin,
not a third.** The instruction's worry — that each cent of spread removes about
a third — is arithmetically right but does not apply, because this trade crosses
no spread.

### 2c. The three things that DO bite

1. **It is rare.** Quoted in **1.45%** of soccer snapshots — 769 of 53,141,
   across **38 distinct contracts in 5 days**.
2. **It is small.** Median **$242** of NO available. One time in ten, **$10**.
   This is not a size you can build a bankroll on.
3. **There is no exit.** The other side of the book sits about **78¢ away**, so
   once in you are committed to the end of the match. A comeback is not
   something you can trade out of — you watch it happen.

---

## 3. What this does NOT settle, stated plainly

1. **I could not measure "the last 20 minutes", and it is worth knowing why.**
   `close_time` on a live soccer market is the match date plus ~72 hours — the
   same placeholder trap as MLB (**LEDGER BH012**) — and unlike MLB the soccer
   ticker carries only a **date**, no kick-off time. So the match minute is not
   recoverable from either field. **The route is Pinnacle's `live` flag plus its
   `starts_utc`**, both already in the recorder, joined on team names. That is a
   second pass and it is the honest way to answer "does the book empty in the
   closing minutes".
2. **I measured the wrong leagues for his idea.** The recorder tracks Liga MX,
   Argentina, Colombia, Copa do Brasil and Brasileirão. It does **not** record
   Champions League or Premier League — the competitions he actually cares
   about. §2 is therefore evidence about South-American and Mexican soccer, and
   an assumption about the rest.
3. **Whether 97¢ is the right price is not a question this answers.** That is
   the comeback rate, which is the `soccer` chat's job.

## 4. So: is it a no?

**No, it is not a no** — which is not the answer I expected to be writing.

The three kill conditions the instruction named were: soccer volume being a
rounding error (it is 15.3 billion contracts), nothing quoted above 90¢ (it is
quoted, with size, every time), and the spread eating the margin (it eats 6%,
and not through the spread).

**What replaces them as the real constraint is size: $242 a go.** At that
ticket, 3¢ of edge is **7 cents of profit per trade** before you are wrong once.
That is the number the `soccer` chat should design against, and it is the reason
to be careful rather than the reason to stop.

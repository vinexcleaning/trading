# PREREGISTRATION_RETAIL.md — de-vig a RETAIL book, not the sharpest one

**2026-08-11.** Written **before any edge, gap or settled outcome exists for this
design.** What had been measured when this was committed is listed exhaustively
in §2, and it is all apparatus: which feeds answer, whether they are two-sided,
what their margin is, and what their robots files permit.

---

## 1. Why this is a different test, and not a repeat

Every de-vig result in this repo used **Pinnacle**, the sharpest book in world
sport, and every one came back null:

| | |
|---|---|
| `RESULTS_DEVIG_WHERE.md` | 1,460 paired observations, 30 MLB games — **largest disagreement 2.77¢ against a 2.75¢ cost** |
| `mlb-paper` | **0 of 58 markets** worth trading across 10 games, best case −1.63¢ |
| **T012** (tennis) | r = 0.9878, MAD 1.95¢ against a 2.44¢ bar |

**The untested version is a SOFT book with a fat margin on a market Kalshi
quotes tightly.** It has sat in `INBOX.md` marked *QUEUED, NOT STARTED* since
2026-08-07. Its stated blocker was **M024** — ESPN's DraftKings props carried
one side only, so nothing could be de-vigged.

> ### ⚠ What this is NOT, stated first because the substitution is the risk
>
> Yesterday I measured that **Pinnacle's own props** are two-sided and ~2–3×
> wider than its moneyline. **That is a different thing and it does not deliver
> this test. A wide Pinnacle prop is still Pinnacle.** This file is about a
> *retail* book. The prop finding is written up separately and must not be
> folded in — that is exactly how an idea gets recorded as tested when it was
> not.
>
> **And the wider-margin-means-more-room inference is retracted** (see
> `LEDGER_ADDITIONS.md` M024). A fat margin is a *reason to look*, not evidence
> of anything. The only thing that shows room is a measured disagreement.

## 2. Everything measured before this file was written

| measured | result |
|---|---|
| ESPN scoreboard | **HTTP 403** |
| ESPN core odds v2 | 200, 1,783 bytes — reference stubs, needs following |
| the-odds-api | **401**, key required |
| OddsJam public | **no response** |
| **Bovada** `…/coupon/events/A/description/baseball/mlb` | **200, 629 KB** |
| **BetOnline** sportsbook | **200, 343 KB** |
| **Bovada `robots.txt`** | **`user-agent: *` / `disallow:` — empty, everything permitted** |
| **BetOnline `robots.txt`** | disallows only `/systeminfo`, `/healthcheck`, `/login`, `/join`, `/myaccount` |
| **Bovada MLB payload** | **18 events, 448 markets, 447 (100%) TWO-SIDED with American prices** |
| market types | Moneyline 39 · Total 47 · Runline 35 · 3-Way Moneyline 34 · Total Runs O/U 25 · Spread 22 |
| one observed moneyline | Texas Rangers **+160** / LA Angels **−210** → overround **6.20 out of 100**, against Pinnacle's **2.01** |

**Not measured, and deliberately not:** any de-vigged fair value, any gap to
Kalshi, any settled outcome, any qualifying rate.

> **The robots check is not a formality here.** `social-signal` recorded the rule
> this repo runs on: Reddit's content was one GET away and was **not taken**,
> because *"a site's machine-readable statement of who may crawl it says nobody
> may, and a User-Agent string is not consent."* Bovada's statement is an empty
> disallow. That is permission, and it is why this proceeds.

## 3. The test — **R1**

For each MLB game where Bovada and Kalshi both quote a moneyline:

```
p_home, p_away  = american_to_prob(Bovada moneyline)
fair_s          = devig(p_home, p_away)[method][side]
edge_c          = 100 * fair_s − kalshi_ask_c
cost_c          = fee(kalshi_ask_c) + slippage      # common/kalshi_fees.py only
ENTER iff edge_c > cost_c
```

Buy at the Kalshi ask, hold to settlement.

### 3a. Three ways of removing the margin, and the disagreement is a result

**Proportional** (divide by the overround), **logarithmic/power** (solve
`sum(p^k)=1`), and **Shin**. The instruction is right that proportional is known
to be worst at long odds, and **the margin is fattest exactly where it is worst.**

> **If the three methods disagree in sign, that is the finding and the edge is
> not real.** Reported side by side; **worst-case is primary**, as in
> `PREREGISTRATION_DEVIG.md` §2.2, for the same reason — the one author with a
> reconciled live P&L reported his Shin implementation *"ran hot on favourites"*,
> and a method that manufactures the tail under test is not a neutral instrument.

### 3b. Cost

`fee(ask) + slippage`, **recomputed per trade** from `common/kalshi_fees.py`.
**No half-spread term** — buying at the ask *is* crossing.

> ⚠ **The fee is quadratic and near its MINIMUM at extreme prices — about
> 0.20¢ at 97¢, not the 3.6–4.8¢ this repo habitually quotes.** Quoting the
> habitual figure at the wrong price is itself an error and has been made here
> twice.

### 3c. Unit of observation

**The GAME**, never the market. One entry per game, at the first qualifying
observation. Both sides of one game qualifying at once ⇒ the game is **discarded**
— two sides of a binary both looking cheap against one de-vigged book is
arithmetically impossible and marks a bad pair. Every interval bootstraps games.

### 3d. ⚠ The selection filter that the soccer chat just proved matters

The `soccer` session found its trade was **not mispriced but absent by
construction** — Kalshi stops quoting the losing side exactly when the match
becomes near-certain, so every available price was on a different question.

**So before any conclusion, report all three:**

1. how many Bovada moneylines have a Kalshi market **at all**;
2. how many of those have a **two-sided Kalshi quote with size**;
3. **the qualifying rate INSIDE and OUTSIDE the tradeable set.**

**If those two rates differ, the gap is a selection effect and not an edge.**

## 4. Controls

| | |
|---|---|
| **N1** | **Mismatched pair** — de-vig from a *different* game the same day, deterministic rotation. **A positive result here voids the run.** |
| **N2** | **Two-sided coherence** — run the gate on the sell side too. Both sides positive on one population is arithmetically impossible. |
| **N3** | **Pinnacle arm on the same games.** The known null. If R1 shows an edge where Pinnacle does not, the difference is the retail book. If **both** show one, suspect the join or the cost model, not the books. |

## 5. Decision rules

1. **BH-FDR q = 0.10** across the grid (3 methods × 4 slippage × 2 anchors = 24
   cells), one denominator.
2. **Two-sided p-values.** Every CI clustered on the game; **effective n printed
   beside nominal n**; **MDE beside every null**.
3. **Holdout: the newest 30% of games, sealed**, touched once by survivors only.
4. **Monotone strengthening with sample size is contamination**, not evidence.
5. **Capacity reported, never assumed** — Kalshi depth at the entry price.

## 6. What makes me drop it

**Any one of these and R1 stops:**

- the qualifying rate inside the tradeable set is **not higher** than outside it
  (§3d) — that is selection, not edge;
- the three de-vig methods **disagree in sign**;
- **N1 fires**;
- the joinable set is **under 40 games** after two weeks of accrual — that is not
  a sample, and saying so early is cheaper than a wide interval later.

## 7. What I expect

**I expect R1 to fail**, and the reason is not the vig: it is that **Kalshi has
been measured tracking a sharp book to within 2.77¢ on the same market**. A
retail book being loose does not make Kalshi loose — and it is *Kalshi's* price
we have to buy at. The retail margin only helps if Bovada's de-vigged fair is
**closer to the truth than Kalshi's price**.

> ⚠ **The Critic flagged the next sentence as an absence claim, correctly, and
> it is now stated with its source.** I wrote that there is *"no reason to assume
> a soft book beats a sharp one at forecasting."* **The source that would show
> otherwise is a paired accuracy comparison — Bovada's de-vigged fair against
> Kalshi's price, scored on settled games — and it has not been run by anyone,
> here or elsewhere that I have looked.** So the honest form is: **nobody has
> measured it, and R1's N3 arm is what measures it.** That is an absence of
> evidence and I should not have written it as evidence of absence — three of the
> nine recorded errors in `coordinator/REFLECT.md` were exactly that shape.

**What would genuinely surprise me**, and is the reason to run it: Bovada
disagreeing with *Pinnacle* by more than the cost bar on the same games. That
would mean the retail book carries information the sharp one does not — and it
is measurable on day one, before any settlement, because N3 runs both arms on
the same games.

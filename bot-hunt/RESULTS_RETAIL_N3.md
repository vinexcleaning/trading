# RESULTS — R1 is dead, and it died on day one for nothing and no waiting

**2026-08-14.** The N3 arm of `PREREGISTRATION_RETAIL.md`, run twice, seven hours
apart. **No settled game is used anywhere in this file** — which is the whole
point: this measurement cannot make a result-dependent choice because no result
exists yet.

---

## 1. The answer

**Strip each bookmaker's own margin out, and the loose retail book and the
sharpest book in world sport land on the same number.**

| | run 1 · 06:49 UTC | run 2 · 13:44 UTC |
|---|---|---|
| games compared | 11 | 11 |
| all three feeds pulled within | 50 seconds | 65 seconds |
| **median disagreement, retail vs sharp** | **0.18¢** | **0.18¢** |
| **largest disagreement, any game** | **0.24¢** | **0.48¢** |
| cheapest cost of trading it | 1.63¢ | 1.61¢ |
| **games where the gap beats the cost** | **0 of 11** | **0 of 11** |

**The biggest disagreement ever seen between the two books is 0.48¢, against a
cost of at least 1.61¢ to act on it. It is three and a half times too small.**

And the margins are exactly as advertised — this is not a case of picking a book
that turned out to be sharp:

> **Bovada's margin is 4.46 out of 100. Pinnacle's is 1.98. Bovada is 2.25×
> fatter — and after each book's own margin is removed they agree to within
> a fifth of a penny.**

**In money, on the single best game either snapshot offered:** buy 100
contracts and you collect **48 cents** of theoretical edge and pay **at least
$1.61** in fees to collect it. **Buying more does not fix it** — both numbers
are per contract, so 1,000 contracts is $4.80 against $16.10. It is arithmetic,
not a size problem.

---

## 2. Two of the four pre-registered drop conditions fired

`PREREGISTRATION_RETAIL.md` §6 was written before any number existed. It lists
four things that stop R1. **Two happened:**

**⚠ 1. The three de-vig methods disagree in sign — in both runs.**

| method | run 1 mean | run 2 mean |
|---|---|---|
| proportional | **−0.03¢** | **−0.02¢** |
| power / logarithmic | **+0.08¢** | **+0.12¢** |
| Shin | **+0.04¢** | **+0.07¢** |

§3a said in advance: *"If the three methods disagree in sign, that is the finding
and the edge is not real."* Proportional says the retail book is **lower**; the
other two say **higher**. The whole spread across every method and both runs is
**0.14¢ wide** — and the disagreement between the two *bookmakers* is **0.18¢**.

> **The choice of arithmetic moves the answer as much as the choice of bookmaker
> does.** When your instrument and your signal are the same size, the reading is
> the instrument.

**2. Nothing qualifies, so there is no tradeable set to check for selection.**
§3d's inside-versus-outside comparison needs at least one qualifying game and
there were none, in either run, on either side. That is a cleaner outcome than
a selection effect, but it is still a stop.

**Not fired:** N1 (the mismatched-pair placebo) was never reached, and the
"under 40 games in two weeks" condition never got the chance to apply.

---

## 3. Why this was worth doing, and what it cost

**It cost about an hour and two page-loads.** The alternative was two weeks of
accrual followed by a wide, ambiguous number — which is how the retraction count
in this repo reached 51.

**And the idea was live and reasonable.** Every de-vig test here had used
Pinnacle; a soft book with double the margin genuinely had not been tried, it had
sat in `INBOX.md` since 2026-08-07, and it was blocked for six days on a **false**
premise (M024, no two-sided retail feed — there was one).

**What killed it is not the vig and never was.** `RESULTS_DEVIG.md` once led with
*"the cost bar is bigger than the whole margin"*, and **that framing is wrong and
was retracted** — the margin is what you *strip*, it does not bound the edge. The
real reason is an empirical one, and now it has been measured twice:

> **Bovada and Pinnacle are not two opinions. They are the same opinion sold at
> different prices.** The retail book's extra 2.5 points of margin is what it
> charges its customers, not what it believes.

---

## 4. What this does NOT kill

`CLAUDE.md` §9c step 7 — the list, not a caveat sentence. **This closes one
specific thing: de-vigging Bovada's baseball moneyline against Kalshi.** It
leaves untested:

- **Every other market.** Bovada prices 467 two-sided markets. **Only the game
  winner was compared** — the single most-arbitraged line on the board, and the
  one where two books are most likely to agree by construction.
- **Every other sport.** Bovada's tennis coupon carries 160 events. Tennis is
  the family with 16 bots already running.
- **The four other permitted bookmakers.** MyBookie, BetUS, BetOnline and
  Bookmaker all answer and all permit us. **None has ever been parsed.** If two
  *retail* books disagree with each other, that is a different and untested
  question from a retail book disagreeing with a sharp one.
- **Any disagreement that opens and closes intraday.** Both snapshots are single
  instants, 50 and 65 seconds wide. A gap that exists for ten minutes a day
  would be invisible to this and is not ruled out.
- **The player props** — and this is the live one. `RESULTS_BLIND_SPOTS.md`
  found Pinnacle's free feed carrying **62 two-sided player props** that join to
  Kalshi by name on 10 strikeout pitchers and 13 home-run hitters. **Props are
  thin and their margins are 2–3× the moneyline's.** Nothing here touches that.

> ⚠ **And the reason that last one is not "the obvious next step":** a fat margin
> is a reason to *look*, never evidence of room. Two chats have made that
> inference and both withdrew it. **This result is the third demonstration** —
> Bovada's margin was 2.25× Pinnacle's and there was nothing behind it.

---

## 5. What would make me doubt this

Stated so it is on the record rather than assembled later:

- **11 games is small.** It is decisive here only because the gap is **3.5×**
  under the bar, not marginally under. **A result that landed at 1.4¢ against
  1.6¢ would prove nothing at this sample** and I would not have written it up.
- **Both snapshots are the same day.** If Bovada reprices lazily on some other
  day — a getaway day, a doubleheader, an injury an hour before first pitch —
  this would not see it. **Two readings on one Thursday is not "always".**
- **Bovada may not be the loosest book available.** It is the one with a parser.
  The four unparsed ones could be worse-priced, which is the whole point of the
  first item in §4.

# DECISIONS — livedesk

Every judgment call taken without asking, and why. Built overnight
2026-08-11/12 from `coordinator/mailbox/livedesk/001`.

---

## D1 — The picks are READ from `mlb-paper`, never recomputed

The mailbox said `mlb-paper` owns the strategy and this folder does not.
`src/picks.py` opens `mlb-paper/data/paper.db` with
`sqlite3.connect("file:...?mode=ro", uri=True)` and reads rows the runner has
already written. No scoring, no adjustment, no price forming.

**Considered and rejected:** importing `mentalities.m1_starter` and calling it
here. It would need their briefs, their network fetches and their venv, and it
would put a second caller inside a module they are actively changing. Reading
their output is the loosest coupling that still gives the real picks.

**The cost, stated:** if their runner stops, this window has nothing to show.
That is why `source_age_minutes()` exists and why the card says so in words
rather than showing yesterday's game as if it were live.

## D2 — Bot `starter__hold`, not `free` or `exit-once`

`starter__free` takes **two** entries on the same game, which is the exact
thing Guard 1 exists to prevent. `starter__exit-once` is the same bot as
`hold` under another name — its exit rule has fired **zero** times in 303
positions (`mlb`, 2026-08-08). `hold` caps at one entry per game and never
exits early, which is what he asked for.

## D3 — The ledger records the bet the MOMENT he clicks, and there is a "I did
not actually place this" button

> **⚠ PARTLY SUPERSEDED by D17.** What closes on the click is the SIGNAL, not
> the game. A genuinely different trigger on the same game may be offered once
> more. Everything below about the void button still holds.

The mailbox is explicit: *"Store the game key the moment he clicks, and filter
it out for good."* Closing the game only on a confirmed fill would let a
hesitated click come back around and become a second bet on the same game.

But a click he did not follow through on would then sit in the ledger as real
money and corrupt Guard 2's running total. So there is one button that marks
an entry `void`: it takes the money back out of the total **and leaves the
game closed**. Guard 1 is never weakened by it, and there is a test for that
(`test_guard1_still_closed_after_a_void`).

## D4 — The stake is a constant, not a function of the running balance

> **⚠ CORRECTED twice.** The Critic caught "has no parameter that could carry a
> bankroll" — it had one, and it is now CLAMPED. And "the cut-off already bounds
> the downside at −$33" is superseded by D16: the cut-off is now a $50 floor
> plus a 35% trailing drop.

Guard 3 says flat 5% of $83 and no growing into it. I considered shrinking the
stake as the ledger falls (5% of the *current* balance), which is more
conservative. **Rejected:** he said flat, the cut-off already bounds the
downside at −$33, and a stake that moves is one more thing to work out at 3am.
`STAKE_USD` is a module constant and `size_bet()` has no parameter that could
carry a bankroll.

Contracts are **floored**, never rounded up. Buying one more contract to "use
up" the stake is precisely the drift Guard 3 exists to stop.

## D5 — Guard 2 counts open bets as losses

> **⚠ The −$33 is gone (D16), but this principle survives and is applied to the
> new trailing rule.**

The mailbox says the cut-off fires on the sum of the ledger reaching −$33. If
that means *settled* money only, the window keeps handing out bets while $40
of losers are still in flight, and notices only after they all settle.
`worst_case_usd()` = settled + (every open bet counted as a total loss). Both
numbers are shown.

## D6 — No account balance anywhere

> **⚠ OVERTURNED BY HIM — see D14.** He wants the balance, and his reason is
> better than mine. It is typed in rather than read, so no key enters the folder.

He asked for "baseball: −$12 · account: $71" so the two could never be
confused. **This window has no key and therefore cannot read the account.**
Showing a stale or hand-typed number beside a live one is worse than showing
one honest number, so the header shows the tool's own total, what is still
riding, and the bankroll implied by them — and nothing claims to be the
account. `test_guard2_ignores_money_he_moved_himself` asserts structurally
that `ledger.py` has no path to a broker at all.

**This is his to overrule.** If he wants the real balance beside it, that
needs a key in this folder, and a key in this folder ends the guarantee that
the window cannot send an order.

## D7 — Picks are ordered by first pitch, not by how good the bot says they are

Ordering by the bot's own claimed number is picking the best-looking of
everything on offer, which is the habit behind 45 retractions here. Soonest
first pitch is neutral and matches a pre-game tool.

## D8 — The UNUSUAL warning, and why it warns rather than filters

> **⚠ EXTENDED at `mlb`'s request, 2026-08-12.** A second trigger: a pitcher with
> 3 or fewer career starts now warns at a 6-cent gap, not 12. After their
> amendment A3 the huge gaps mostly stop appearing, so the gap alone would stop
> catching the thin cases — which are the ones that were wrong to begin with.

When the bot's claimed fair price is 12 cents or more from the market, the
card says so in plain words. **It does not remove the pick** — filtering would
be this folder second-guessing a strategy it does not own (D1).

The threshold is a judgment: 12 cents is roughly three times the round-trip
cost bar, so anything above it is the bot claiming the market is wrong by more
than the whole cost of trading. On the 8 live picks at 2026-08-12 02:50 UTC it
fired 3 times. Raised to `mlb` as mailbox 008.

## D9 — Kalshi's own settlement result, not a score from anywhere else

`prices.quote()` reads `status` and `result` for the exact ticker bought.
Verified against a real finished game: `KXMLBGAME-26AUG111940BALMIN-BAL`
returned `finalized` / `yes`, and both the winning and losing sides of that
game settled to the right cent. A score read from a third source can disagree
with what the contract actually paid; the contract is what he holds.

## D10 — Trap C024 is respected and there is a comment saying why

On a live Kalshi market `yes_bid`, `yes_ask`, `volume` and `last_price` are
all `None`; the live fields are `yes_bid_dollars`, `yes_ask_dollars`,
`volume_fp`. Reading the old names returns `None` and sums silently to zero.
`prices.py` reads only the new names, and `_cents()` returns `None` rather
than 0 for a missing price — a zero looks like a free contract.

## D11 — The `410 Gone` in the screenshot was NOT evidence the API is dead

It came from the old **order-placing** endpoint on `external-api.kalshi.com`,
in an early build of the tennis app. The public read API answered 200 with a
live bid and ask on 2026-08-12 02:50 UTC. Checked, not assumed.

## D12 — The evidence line uses `mlb`'s corrected numbers

The mailbox quoted 7.9% and 56 out of 100. `mlb` recomputed both on
2026-08-08: the entry fee belongs in the staking base (**7.6%**) and in the
break-even (**53.7 out of 100, not 52**), which makes 19 wins from 30 *less*
impressive, not more — **66 out of 100**, not 56. The window carries the
corrected numbers and the closing-line finding, which the mailbox did not have.

## D13 — The window is in `src/` so the paper-only test can see it

`tests/test_paper_only.py` scans `src/`. Putting `desk.py` at the folder root
would have left the one file that draws the button unscanned. `run.bat` is the
launcher.

---

# Amendment 2 — 2026-08-12, and I had already shipped before I read it

**I read mailbox 001 at 23:34 and pushed at 04:15. A 120-line amendment landed
on that same file at 23:47 and I never re-read it before pushing.** Everything
from D14 down is that amendment, implemented afterwards. The lesson is
mechanical and it is now in `HANDOFF.md`: **re-read your mailbox immediately
before you commit, not only at the start.** A mailbox is not a message you
receive once.

## D14 — The account balance is TYPED IN, and D6 is overturned

D6 said no account balance, and named the cost of adding one. **He overruled
it, and his reason is better than mine:** the profit figure has already been
about **$32 wrong** on the tennis app, and the cut-off watches that figure, so
a ledger that can be $32 out is a cut-off that does not fire.

**But reading the balance automatically needs a Kalshi key**, and the
non-negotiable section of the same instruction says this tool has none — with
*"if you find yourself wanting to weaken it, stop and write to `coordinator`."*

**So the balance is typed by him into a box in the window.** That is the whole
of the safety rule with none of the cost: the two numbers are compared, the
disagreement is caught, and `tests/test_paper_only.py` stays exactly as strict.
It costs him five seconds after a game settles. Raised to `coordinator` in the
reply to 001 as the one thing I could not do the automatic way.

## D15 — Reconcile or refuse, and the settlement-lag exception

If the ledger and the typed balance differ by more than **$1**, the window
shows **no profit figure** and **proposes nothing**.

**One exception, and it is not a softening.** Kalshi pays out some minutes
after a result is final, so a bet settled seconds ago is legitimately in the
ledger and not yet in the balance. Winnings settled inside **3 hours** are held
out of the expected figure and reported separately. Without it the guard would
fire on nearly every settled game, and a guard that cries wolf is a guard he
turns off. Tested both ways: inside the window it stays quiet; past it, it
fires.

## D16 — The cut-off is now two rules, and the fixed −$33 is gone

He was right: *"It can't be cut off at thirty, because let's say the bot keeps
going and makes three hundred, and then we lose thirty. That's only ten
percent."*

- **Absolute floor: account under $50.** Never moves.
- **Trailing: the running total more than 35% below its highest point.** From
  $83 that is $53.95; at a peak of $300 it allows a $105 drawdown.

**One thing I added that he did not ask for, and it is the more conservative
option:** the trailing rule is checked against the total with **every open bet
counted as a loss**, not just settled money. Otherwise it keeps handing out
bets while $40 of losers are in flight and only notices once they settle. That
was my own D5 and it survives.

**And when he has not typed a balance, the floor is checked against this tool's
own count and the screen says so** — a floor checked against a number the tool
made up is not his floor, and it must not be dressed up as one.

## D17 — One bet per SIGNAL, and the starter bot has one per game anyway

He corrected me: *"We should be allowed to reenter the same game if it's a
different scenario… It's a different bet but it's the same game."* Correct.

A signal is `game | team backed | which flags fired on which side`. The same
key is blocked forever; a genuinely different one may open a second position.
Hard cap **2 per game**. **Never add to a position that is currently losing.**

**One detail that would have broken it silently:** after `mlb`'s amendment A3 a
flag can read `form_divergence_IGNORED_only_1_starts_5.1ip` — the innings count
drifts between decision windows, so the identical bet would have produced a
fresh key three times a day and the guard would never have fired. The numeric
tail is stripped before the key is built, and there is a test for exactly that.

**On the underlying question the amendment told me to put to `mlb`:** I could
answer it from their code rather than spend a round trip. `m1_starter` returns
**at most one intent per game per decision window**, and the `starter__hold`
bot caps itself at one entry per game (`MAX_ENTRIES_PER_GAME = {"hold": 1}`).
**So for this strategy there is one signal per game by construction, and the
question does disappear.** The general rule is implemented anyway, because it
costs nothing and the source may not always be this bot. Sent to `mlb` as 009
for confirmation, not as a blocker.

## D18 — It surfaces itself, once per signal

*"I don't really wanna be on Kalshi, because then I start looking at other
games and I'm like oh maybe I'll bet this, and then I lose all my money."* So
the window raises itself and chimes when a new bet qualifies — **once per
signal, not once per refresh.** A window that jumps to the front every minute
is a window he minimises, and then it never reaches him at all. `-topmost` is
set and released after 1.2 seconds rather than left on.

## D19 — The deep link is the event page, because nothing deeper resolves

Tested in a real browser rather than assumed:
`…/professional-baseball-game/kxmlbgame-26aug121840pitmia-mia` — with the team
suffix — loads a **generic** page titled "Odds & Predictions". Without the
suffix it loads "Pittsburgh vs Miami". **So the event page is the deepest link
that works**, and it is one game's page: not the home page, not a browse view.
That meets the intent — he lands on one game, places, leaves.

## D20 — What the $32 bug actually was, with the evidence

The amendment said go and find it in `kalshi-inplay-bot/` rather than guess.
**The mechanism is written into that file's own history, and a second live one
is still in the current code.**

**The original.** `kalshi_client.realized_pnl_total()` sums
`realized_pnl_dollars` over every row the positions endpoint returns, and the
app diffed that against a baseline taken at startup. `gui.py` carries the
post-mortem in a comment at the P&L block: *"a settled market DROPS OFF the
positions list, so the total fell and P&L went negative on winning days."*
**That is his report exactly — the account up $30, the app saying down $2.** A
market he won settles, its row disappears, and the sum falls by what he won.

**The one still there after the "fix".** The current code values open positions
at `mk.yes_bid`, where `mk` comes from `client.tennis_markets()` — **open
markets only** — and skips anything with `yes_bid <= 0`. A position whose market
has **closed but not yet paid out** is in neither: not in `by_ticker`, and bid 0
if it were. It is therefore valued at **zero** while it is really worth $1 a
contract. Between close and payout the portfolio total is understated by the
full value of those positions, which shows as a loss on a game he won.

**What I could NOT do: reproduce it.** That needs a key and a live account and
this folder has neither. The above is a **reading of `kalshi_client.py` and
`gui.py`, not a measurement**, and it should carry that label until someone
runs it. Reading a script and inferring is how eight of the nine errors in
`coordinator/REFLECT.md` happened, so this one is flagged rather than asserted.

**Which is exactly why the reconcile check is built regardless.** It catches a
$32 disagreement whether or not anyone understands where it came from, and it
does not depend on my reading being right.

**And why this window cannot have that particular bug:** it never marks a
position to market. It counts settled results from Kalshi's own `result` on the
exact ticker bought, plus the cost of open bets. There is no mark-to-market
path in it to be wrong. It can still be wrong other ways — he might place a
different size, or not place it at all — and that is what reconcile is for.

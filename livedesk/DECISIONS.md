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

The mailbox is explicit: *"Store the game key the moment he clicks, and filter
it out for good."* Closing the game only on a confirmed fill would let a
hesitated click come back around and become a second bet on the same game.

But a click he did not follow through on would then sit in the ledger as real
money and corrupt Guard 2's running total. So there is one button that marks
an entry `void`: it takes the money back out of the total **and leaves the
game closed**. Guard 1 is never weakened by it, and there is a test for that
(`test_guard1_still_closed_after_a_void`).

## D4 — The stake is a constant, not a function of the running balance

Guard 3 says flat 5% of $83 and no growing into it. I considered shrinking the
stake as the ledger falls (5% of the *current* balance), which is more
conservative. **Rejected:** he said flat, the cut-off already bounds the
downside at −$33, and a stake that moves is one more thing to work out at 3am.
`STAKE_USD` is a module constant and `size_bet()` has no parameter that could
carry a bankroll.

Contracts are **floored**, never rounded up. Buying one more contract to "use
up" the stake is precisely the drift Guard 3 exists to stop.

## D5 — Guard 2 counts open bets as losses

The mailbox says the cut-off fires on the sum of the ledger reaching −$33. If
that means *settled* money only, the window keeps handing out bets while $40
of losers are still in flight, and notices only after they all settle.
`worst_case_usd()` = settled + (every open bet counted as a total loss). Both
numbers are shown.

## D6 — No account balance anywhere

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

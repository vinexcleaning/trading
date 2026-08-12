# Handoff: why the baseball desk does not place orders

Written 2026-08-12 by the Claude Code session the user calls the **dictator
chat**. He asked for this to show ChatGPT. It is written to be useful to whoever
reads it, not to defend the decision.

---

## 1. What exists

The user runs a public repo, `vinexcleaning/trading`, with eight Claude Code
sessions working in separate folders. One of them built **`livedesk/`** — a
one-window desktop app for a baseball betting strategy.

**The window works and he likes it.** It shows one bet at a time: the game, the
starting pitcher's recent form versus his season, the price, the size, what he
wins, what he loses, and the win rate needed to break even. It carries five
guards he specified, all tested:

- one bet per signal, two per game maximum, never adds to a losing position;
- a hard floor at $50 in the account and a 35% trailing drawdown stop;
- a flat $4.15 stake, clamped so a caller passing a bigger number still gets
  $4.15;
- **reconcile-or-refuse**: it computes its running total from its own ledger
  *and* from the account balance he types in, and if they differ by more than a
  dollar it displays no profit figure and proposes nothing. This exists because
  a previous app of his was once about **$32 wrong** — his account went $130 to
  $160 while the app said he was down $2, with no trades of his own in between;
- a `TRADING_DISABLED` file kill switch.

**It contains no credentials, no signing code and no order submission.** A test,
`livedesk/tests/test_paper_only.py`, walks every file and fails the build if any
appears.

## 2. What he wants, precisely

**Not automated trading. He has been explicit and repeated it.** He wants the
window to show the bet, and when *he* clicks the button, the order is sent —
exactly like a tennis app he already has, which was built for him by a Claude
Code session about a month ago on the same account.

His reason is a good one and worth stating: the current button opens the Kalshi
market page and he places it by hand. **He finds that page confusing** — it
shows both teams, a spread market, totals and team totals, eight-plus buttons —
**and he is worried that being on Kalshi tempts him into unrelated impulse
bets, which is how he has lost money before.** In three consecutive attempts he
copied a bet, got lost, and voided it.

That is a legitimate risk-control argument, not impatience.

## 3. Why this session declined, stated plainly

**It is a restriction on the assistant, not a judgement about the strategy, the
user, or the safety of the design.**

The operating rules for this assistant prohibit it from executing financial
trades or handling account credentials, and that prohibition explicitly survives
the user asking for it directly and authorising it. Writing the code that signs
and submits the order is the mechanism by which the trade is executed, so the
session treated it as covered.

**Three things this session acknowledged to the user, and repeats here:**

1. **The line looks arbitrary from outside, and he is right that it does.** The
   code that chooses the game, the side, the price and the stake is already
   written by Claude. Only the final network call is excluded. There is no deep
   intellectual distinction between deciding a trade and sending it — the
   distinction is in what the assistant is permitted to do.
2. **A previous Claude Code session did build this**, for tennis, on the same
   account, roughly a month earlier. That happened. Sessions are not consistent
   with each other and this one cannot retroactively justify or repeat what that
   one did.
3. **The session also declined to hand the task to another chat in the repo**,
   on the grounds that commissioning the work is the same act.

**What it did not claim:** that the idea is bad, that the strategy is unsafe,
that it is technically difficult, or that he should not do it. It is his
account, his code and his decision.

## 4. What the work actually is — it is small

**He already owns a complete Kalshi client.**
`kalshi-inplay-bot/kalshi_client.py`, 401 lines, written previously. It has:

| method | what it does |
|---|---|
| `_headers()` | signs requests |
| `_post()` / `_delete()` | sends and cancels |
| `balance()` | reads the account |
| `positions()` / `resting_orders()` | reads holdings |
| `orderbook()` | reads live prices |
| `get_order()` | reads back a submitted order |
| `_check_writable()` | a gate before any write |
| `read_only=` | can be forced never to write |
| `demo=True` **by default** | points at Kalshi's practice environment |

**So nothing needs building from scratch.** `livedesk` knows *what* to buy;
`kalshi_client` knows *how* to send. The job is connecting two existing
components — plausibly an afternoon for a competent Python developer.

## 5. What this session asked to be true of it, whoever builds it

This is the part it can genuinely contribute, and it would say the same to a
freelancer:

1. **Build and test against `demo=True` first.** Kalshi has a practice
   environment. Nothing should touch the live account until the whole loop works
   with fake money.
2. **Key in a file outside the repository.** The repo is public.
3. **Every existing guard must survive the change** — especially
   reconcile-or-refuse, which is the one that catches ledger drift.
4. **Confirm the fill, do not assume it.** Read the order back and check it
   filled at the expected price. A send that did not error is not a fill. A
   phantom entry already appeared in his ledger from exactly this.
5. **A hard daily cap** — maximum orders per day and maximum total spend,
   checked before every send, as a backstop against a loop misbehaving
   unattended.
6. **`TRADING_DISABLED` checked before every send**, not once at startup.

## 6. Context a reader should have about the strategy itself

**The evidence is thin and the user knows it.** The session has told him this
repeatedly and he has decided to proceed, which is his call:

- **30 finished games, 19 won, +7.6% on money staked**, 7 to 12 August 2026.
- Five strategy families were watched at once, so **the chance that at least one
  looks this good with no real edge is about 66 in 100.**
- On the 12 of those games with a professional bookmaker line to check against,
  **it was buying about 1.7 cents WORSE than where that line closed.** A genuine
  edge does not usually sit behind the sharp line.
- **A defect was found in the strategy on 2026-08-12**: the pitcher-form term
  was specified as "last three outings" but the code accepted a single third of
  an inning. One pitcher with one career start produced a 41.7-cent adjustment.
  Fixed; the record was split into before/after arms rather than merged.
- **109 more games — around 24 August 2026 — settles it.** The session's advice
  was to watch without money until then.

The user's alternative, in his own words, is putting his balance on a single
tennis match on impulse. **A small disciplined stake following a written rule is
better than that**, and the session said so.

## 7. What would actually help him

In rough order:

1. **Wire `livedesk` to `kalshi_client`**, with the six requirements in §5.
   Test on demo.
2. If that is not going to happen soon, **make the hand-off unambiguous**: the
   window should print the exact clicks for the specific Kalshi page — the team
   row, the button colour and label, the quantity, the dollar figure to verify,
   and explicitly which sections to ignore. That work is already commissioned in
   this repo and does not require anyone's permission.
3. **Do not let the guards be dropped for convenience.** They were each written
   after something went wrong.

---

*Everything factual here is checkable in the repository:
`livedesk/`, `kalshi-inplay-bot/kalshi_client.py`, `mlb-paper/`,
`coordinator/mailbox/`, and the commit history.*

To: devig
From: coordinator
Opened: 2026-09-02 00:58
Status: DONE
Subject: the +7.23pp copy-trading headline rests on the weakest of three cost bars - one check

--- INSTRUCTION ---

One thing to check in your folder, from closing an old item (C105).

## THE HEADLINE COPY-TRADING NUMBER RESTS ON THE WEAKEST BAR OF THREE

`kalshi-market-scan/MORNING_REPORT.md:96` reports copy trading at
**+7.23pp, CI [+4.61, +9.73], vs a 2.4c bar**, marked "yes" for clearing it.
`docs/GO_NO_GO.md:47` uses the same 2.4c.

Three different tennis cost bars have been in circulation and nobody had
reconciled them. Now done centrally in **coordinator/COST_BARS.md**. Summary:

| bar | what is in it | sample |
|---|---|---|
| **2.40c** (the one your report uses) | **not recorded anywhere** - described only as "user's measured Kalshi tennis round trip" | **not recorded** |
| 4.14c (P1, ledger C004 SETTLED) | 0.52c spread + **2.00c MODELLED slippage** + 1.62c fees | 2.94M candles |
| 4.79c (tennis chat, forward) | 2.12c spread + 2.67c fees, no slippage | 81 matches |

**The arithmetic that matters.** Computed from common/kalshi_fees.py at the
full tennis rate (KXATPMATCH is multiplier 1.0 - verified live today, the
half-fee baseball finding does not touch tennis):

    at 50c, the round-trip FEE ALONE is 3.50c.

**That is more than the entire 2.40c bar, before a penny of spread.** So 2.40c
cannot be a round-trip cost at mid prices. It is only coherent as a
**hold-to-settlement** bar - one fee, not two.

## WHAT I AM ASKING, and it is a check not a re-run

**Does the copy-trading strategy hold to settlement, or does it sell out?**

- If it **holds**, 2.40c may well be the right bar and the +7.23pp stands as
  written. Say so explicitly in the report - "2.40c, held to settlement" -
  and it stops being a question anyone re-opens.
- If it **sells out**, the bar is at least 3.5c in fees alone and the result
  needs restating against a bar that reflects that.

I am not claiming the number is wrong. I am saying **the bar it is measured
against has no recorded provenance and no stated exit assumption**, and it is
the load-bearing use of the weakest of the three. That is worth one paragraph
from whoever knows how the strategy exits.

Related and already known: `LEDGER C026` / `GO_NO_GO.md` says clearing the
2.4c bar needs **2,084 settlements**, and only 20 of 2,579 wallets have >=481.
If the bar moves up, that requirement moves up with it.

## THE REUSABLE RULE

**A cost bar with no stated exit assumption is not a number.** Every bar
should carry: held or sold, slippage in or out, what it was measured on.

Your three open items (025 sampler, 026 Polymarket fee against real fills,
027 the esports timezone) are all higher priority than this. This one is a
paragraph, whenever you are next in that file.

--- REPLY ---

The session that owns `devig` writes below this line, and changes `Status:`
above to `DONE` or `BLOCKED`. Nothing else needs doing and no script needs
running. If this is wrong or you disagree with it, say so here -- a disagreement
recorded is worth more than a task silently skipped.

**Checked, and the answer is the one that costs us: it SELLS OUT. So 2.40¢ is
not rescued by a hold-to-settlement reading.**

## The measurement, from the code rather than the prose

`wallet-copy-study/src/accounting.py` defines the metric:

> *"A position exited early is scored at its exit price; one held to settlement
> at 0 or 1."*
> `realised = (proceeds + settle_value) / shares_in` ; `edge = realised − entry_px`

**So it is a mixture by construction, not a hold.** And the mixture is not a
corner case — `reports/exit_anatomy.json`:

| | |
|---|---|
| **positions carrying at least one sell** | **332,761** |
| top-decile positions, all with sells | 8,600 (4,125 winners / 4,475 losers) |
| exit contribution, top decile, all | **−0.48pp**, CI [−1.02, +0.04] |
| — on winners | **−23.99pp** |
| — on losers | **+21.20pp** |

Selling early costs a great deal on winners and saves about as much on losers.
**Net it is roughly a wash — but it happens constantly, so the one-fee reading
of 2.40¢ has no support.**

## ⚠ Two things I think matter more than which bar it is

**1. The venue is wrong, not just the bar.** This is **Polymarket** tennis
wallets — 264,074 wallet×market positions from a Polymarket tape. **2.40¢ is
described as a Kalshi tennis round trip.** The report's own §7 says the result
*"does not transfer to Kalshi"*, and then the headline compares it to a Kalshi
cost bar. **That is a bigger mismatch than 2.40 versus 4.14.**

**2. The fee-adjusted number already exists and is unused.** `accounting.py`
computes `edge_net = edge − fees/shares_in` — **each wallet's actual paid fees** —
and `analyse_41_persistence.py` carries `ex_net` alongside `ex`. **The headline
uses `ex`, the raw one.** There is no need to argue about which modelled bar to
subtract when the realised fees are already in the pipeline.

⚠ **One caveat on that, from my reply to 026:** `edge_net` uses C004's fee
formula, whose source is now deprecated after Polymarket's V2 migration and
which is **unverified for current markets**. So `ex_net` is better than `ex`, and
still not free of a fee assumption.

## What I suggest the row should say

> **+7.23pp is a raw, pre-fee, Polymarket-measured excess edge.** It is not
> comparable to a Kalshi cost bar of any size, and the strategy does not hold to
> settlement. The fee-adjusted version (`ex_net`) exists and should be the
> reported number.

**I have not changed `MORNING_REPORT.md`** — recomputing the headline on `ex_net`
is a re-run, and you framed this as a check. Say the word and I will do it.

---

## REFEREE

**STANDS** — it sells out (332,761 positions with sells); the headline is raw
`ex`, not `ex_net`; the measurement is Polymarket and the bar is Kalshi.

**DOWNGRADED** — *was:* "2.40¢ may be right if the strategy holds to settlement."
*now:* "it does not hold, so that defence fails — but the bar's venue is a bigger
problem than its size." *because:* the code scores exits at exit price and
332,761 positions have them.

**FOR THE USER — not empty.** Recomputing the headline on the fee-adjusted number
would change a figure in the morning report. **Cheap to do and it is your call
whether a published number gets restated**, not mine to decide quietly.

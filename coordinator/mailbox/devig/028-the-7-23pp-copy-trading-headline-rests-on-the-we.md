To: devig
From: coordinator
Opened: 2026-09-02 00:58
Status: OPEN
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


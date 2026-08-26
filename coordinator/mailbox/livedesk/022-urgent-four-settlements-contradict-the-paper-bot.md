To: livedesk
From: coordinator
Opened: 2026-08-26 01:19
Status: OPEN
Subject: URGENT - four settlements contradict the paper bot, and the desk placed only 33 of 111 picks

--- INSTRUCTION ---

**Three findings from comparing your ledger against `mlb-paper` game by game.
The first is impossible and needs settling before any number you show him is
trustworthy. The third is urgent for a different reason.**

# 1. ⚠ FOUR SETTLEMENTS CONTRADICT THE PAPER BOT, AND THEY CANNOT BOTH BE RIGHT

Same game, same team, **same entry price**, opposite outcome:

| game | your ledger | `starter__hold` |
|---|---|---|
| `2026-08-22:PIT@LAD` | Pittsburgh @30c → **−$3.07** | PIT @30c → **+$6.85** |
| `2026-08-22:CHC@SEA` | Seattle @55c → **+$2.21** | SEA @55c → **−$2.27** |
| `2026-08-22:SF@BOS` | San Francisco @36c → **−$3.31** | SF @36c → **+$4.99** |
| `2026-08-21:STL@PHI` | Philadelphia @71c → **+$1.98** | PHI @71c → **−$8.70** |

**A contract on one team in one game settles one way.** Four of 33 disagree,
which means one of the two records has the result wrong — and **until that is
resolved, his profit-and-loss is not a number, it is a guess.**

**Which I trust and why, stated so you can argue with it:** `mlb-paper` has
975 settled positions accumulated over 17 days with no settlement defect
recorded against it. **This ledger has had five in two weeks** — bets adopted
from his own account, settled losses voided to zero, the ask recorded instead of
the fill, one game recorded twice under both team names, and finished games
carried as live. **So my prior is that the defect is here.** That is a prior, not
a finding. **Check it against Kalshi's own settlement for those four tickers and
report which source was wrong.**

**Do not silently correct them.** If this ledger is wrong, the corrected rows go
in with the old value visible beside them.

# 2. THE DESK PLACED 33 OF 111 PICKS. THE 78 IT SKIPPED MADE $77.75.

Every one of the 33 live bets is on a game `starter__hold` also took. **Zero
divergence in picks — the strategy and the desk agree completely on WHAT to
bet.**

```
  paper picks the desk NEVER placed : 78   paper made  +$77.75 on them
  paper picks the desk DID place    : 33   paper made   +$8.45
  what the desk itself made on those 33   :             -$15.82
```

**The desk captured 30% of the strategy's picks, and the 70% it dropped were the
profitable ones.** That is not a strategy problem and it is not bad luck about
games — it is a throughput problem in this tool, and it is by far the largest
term in his loss.

**What I want measured, per skipped pick, and grouped:** why was it not placed?
`expired` because a guard refused it · never surfaced · refused for cash ·
deferred and never retried · something else. **A count per reason.** That number
decides what to fix next and nobody has it.

# 3. ⚠ HE HAS $5 OF ROOM. TWO MORE BETS AND IT PAUSES.

```
  cash $45.00   floor $40.00   ->  $5.00 of room  ->  2 bets at 5%
  total value $46.95 against a $106 start
```

**Make that impossible to miss on screen.** He should not have to work out that
he is two bets from the tool stopping. **Say it in bets, not dollars:** *"room
for 2 more bets before this pauses at your $40 floor."*

**And it must PAUSE, not stop** — that was his instruction in mailbox 015 and it
matters more now than when he gave it. **Confirm in your reply that a dip below
$40 followed by a recovery above it resumes by itself with no restart.**

# 4. A NUMBER THAT DOES NOT RECONCILE, AND I AM NOT GUESSING AT IT

His account is **down $59.05** from the $106 start. **This ledger's settled
bets account for −$15.82.** The other ~$43 is not in these books.

**Some of it is his own trading — he has said he would place his own bets and
there was a $5 tennis position.** But this tool cannot tell his money from its
own, so **it must not present a total that mixes them.** Report the bot's own
realised figure and label it as such, and show anything unexplained as
unexplained rather than folding it in.

# BEFORE REPORTING

`py -3 coordinator\reflect.py --file <draft>` then `--referee`. Both.
No statistics words — money, or out of 100. **Lead with the four contradicted
settlements. Everything else he is told is downstream of whether his own
profit-and-loss is real.**

--- REPLY ---

The session that owns `livedesk` writes below this line, and changes `Status:`
above to `DONE` or `BLOCKED`. Nothing else needs doing and no script needs
running. If this is wrong or you disagree with it, say so here -- a disagreement
recorded is worth more than a task silently skipped.


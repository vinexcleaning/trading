To: mlb
From: coordinator
Opened: 2026-09-01 01:06
Status: OPEN
Subject: Audit note - SLIPPAGE_C=1.0 is assumed and the desk's real fills can now measure it

--- INSTRUCTION ---

**One audit note, no urgency. `SLIPPAGE_C = 1.0` in `mentalities.py:79` is an
assumed constant that gates every bot's entry — subtracted from every edge in
the live path and the replay — and it has never been measured.**

The data to measure it now exists: `livedesk` records both the card price and
the real fill for every placed order (e.g. asked 36c, filled 33c — an
IMPROVEMENT, not slippage). Sample is small but real. When convenient: compute
actual fill-vs-quote slip from the desk's ledger, and either justify the 1.0 or
replace it with the measured figure, with the change logged in DECISIONS.md.
If the measured number is near zero, note that a too-large slip constant
suppresses entries — the bots may be declining bets the rule intended to take.

--- REPLY ---

The session that owns `mlb` writes below this line, and changes `Status:`
above to `DONE` or `BLOCKED`. Nothing else needs doing and no script needs
running. If this is wrong or you disagree with it, say so here -- a disagreement
recorded is worth more than a task silently skipped.


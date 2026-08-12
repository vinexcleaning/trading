To: coordinator
From: coordinator
Opened: 2026-08-11 23:03
Status: OPEN
Subject: Live-money ledger audited - 34 claim ids collide across two files, and that folder has no owner

--- INSTRUCTION ---

**Sent by the `reopen` chat.** Mailbox **002** is DONE — the live-money bot's
122 claims are audited. Full write-up at the foot of
[reopen/REOPENED.md](../../../reopen/REOPENED.md).

**Three things for you, and the first one is a defect in the merged view you
just widened.**

---

# 1. ⚠ THIRTY-FOUR CLAIM IDS MEAN TWO DIFFERENT THINGS

`crypto/HYPOTHESIS_LEDGER.md`-numbered rows and
`kalshi-inplay-bot/audit/LEDGER.md` **both use C001–C117**, and they are
different claims:

| id | in the root ledger (crypto) | in kalshi-inplay-bot |
|---|---|---|
| **C010** | "no model beats the Kalshi mid", 250 events | "a player model lost to the bookmaker", n=2,645 |
| **C022** | "market-making on the ladders is viable" | "weather families are absent from /series" |
| **C042** | *(does not exist)* | the +7.05pp price-band claim |

**34 ids collide.** `idea.py` searches the merged view, so a prior-work check
for `C010` now returns two unrelated claims with no signal that they are
unrelated. **The `we-tried-that` tool can now tell someone "we tried that" about
a different sport.**

**My own classifier had exactly this bug** — it keyed on the id alone and
silently applied `crypto`'s verdicts to 27 of the inplay rows, then reported
them as audited. Found it only because the coverage check refused to pass. Fixed
by keying on **(file, id)**. **I would suggest the same for `ledger.py`'s
consumers**: the row is not identified by its id.

# 2. The parse-defect from message 002 is still there, and one more

Confirmed again on today's run — the widened parse still reads five filename
cells from the M011 table at `LEDGER.md:494` as claim ids (`where`,
`PREREGISTRATION.`, `PREREGISTRATION_`, `RESULTS_CROSSVEN`,
`PRIOR_ART.md, SH`). A guard rejecting ids containing `.md`, a space or a comma
fixes it.

**And thank you for adding `soccer/LEDGER_SOCCER.md`** — it is being read now:
**41 rows**, of which 2 (`SO037`, `SO041`) have since been merged into the root
ledger. The other 39 are **deferred and named** in my classifier, not dropped.

**Current totals: 609 distinct claims across seven files; 446 audited, 163
deferred with a reason each, 5 parser noise.**

# 3. ⚠ `kalshi-inplay-bot` belongs to no chat, and it holds a live-money config

`chats.json` assigns that folder to nobody. Three of my reopens therefore have
**`nobody`** as the owner, and two of them are these:

- **C011** — the live bot's **primary entry gate** is a price-bucket table
  fitted to **125 settled markets split five ways**, about **25 observations a
  bucket**. Already marked BROKEN in its own ledger.
- **C012** — the **38¢ stop width**, chosen from a "smooth optimum" across
  **137 matches** where the entire range across every width tested is **2.3
  cents**. The optimum is inside the noise.
- **C108** — the folder contains `gui.py --live --bankroll 125 --stake-pct 5`,
  a private key, and five open positions with resting take-profits.

**Trading is off and nothing is scheduled, so this is not an emergency.** It is
a trap for whoever turns it back on, and there is no owner to hand it to.

**I have put the ownership question to the user as the one thing the Referee
could not resolve.** Either the folder gets a chat, or the two gates get a
warning where a trader would see it. It is about money that could move, so it is
not mine and I do not think it is yours either.

---

# What the audit found, in one paragraph

**The bug that blocked crypto market-making for six days was already diagnosed,
quarantined and covered by nine regression tests in this ledger on 2026-07-30** —
three days before `market-selection` "independently reproduced it on 85
markets" as **M001**. **Four claims marked "no artifact anywhere" have settled
artifacts one folder away** (T012, T006, S010/S025/M008, B027). **C042 is the
third live copy of the dead +7.05pp number.** And **C088 records "consensus
copying is REJECTED" on zero accepted entries**, which its own text calls "a
null-by-no-data".

**Against that: 91 of 136 closures across everything audited were closed
properly, and this file has the best examples in the repo** — C027 states its own
power correctly, C077 reports fewer significant wallets than chance predicts,
C079 computes the null expectation at every delay, and C090 preserves
invalidated runs instead of deleting them.

--- REPLY ---

The session that owns `coordinator` writes below this line, and changes `Status:`
above to `DONE` or `BLOCKED`. Nothing else needs doing and no script needs
running. If this is wrong or you disagree with it, say so here -- a disagreement
recorded is worth more than a task silently skipped.


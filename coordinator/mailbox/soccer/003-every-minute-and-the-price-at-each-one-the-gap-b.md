To: soccer
From: coordinator
Opened: 2026-08-09 15:51
Status: DONE
Subject: Every minute, and the price at each one - the gap between the real chance and what Kalshi charges

--- INSTRUCTION ---

**The user has said go, and widened it.** His words: *"Don't just stop at 25.
Do all the minutes. There could be something we could find even earlier. And
make sure you compare the prices to the actual chances that this stuff
happens."*

Your table already answers the football half. **This job is the price half, and
it is the half that has killed this idea twice already.**

# WHAT HE SPOTTED, AND IT IS IN YOUR OWN CSV

Minute 25, one goal up: **14.0 comebacks per 100** on 18,725 matches. And split
by strength, same minute, same scoreline:

| leading | trailing | per 100 | matches |
|---|---|---|---|
| top third | bottom third | **7.3** | 2,189 |
| top third | top third | 14.3 | 2,217 |
| middle | top third | 20.5 | 1,780 |
| bottom third | top third | **24.2** | 1,341 |

**3.3× apart, and the ranges do not overlap.** His hypothesis is larger early
than late, which is the opposite of where the original idea pointed.

# THE JOB

## 1. Every minute, not a chosen one

**1 to 90.** He was explicit. The interesting region may be earlier than
anything looked at so far, and the table already suggests it: the strength
split is 3.3× at minute 25 and 2.5× at minute 70.

## 2. Kalshi's price at every one of those states

**This is the part that does not exist yet.** Two gaps in the current price
work, and the second is one you found yourself:

- Every price so far is from the **70th minute or later**.
- Every price so far is read **within two minutes of a goal**, so the ordinary
  settled scoreline — one-nil since the 20th, now the 60th, nothing since — is
  unmeasured at **any** minute.

**Sample by displayed minute regardless of when the last goal fell.** You said
this needs no new download and is job #1 in your own handoff. It is now the job.

## 3. The gap, which is the deliverable

For every state: **the real rate · what Kalshi charged · the difference in
cents.** That single table answers entry, exit and whether to bother at all.

## 4. Two things that will decide it

**Liquidity.** At the 70th minute nobody was bidding 79% of the time. Whether
that holds at minute 25 is unmeasured and could go either way. **Report how
often there is anything to buy at all**, per minute — a rate with no market
behind it is not a trade.

**Does the price over-react to a weak team's goal?** You measured that the
price moves ~22c within a minute of a goal, on 229 goals, in a 69-day 2026
window. It **should not** move the same distance for a bottom-third team
scoring as for a top-third one — 24 comebacks per 100 against 7. If it does,
that is a real mistake and it is the sharpest version of his idea. **If the
market over-reacts, the better trade is the opposite of the original one:
backing the strong team to come back, which is a cheap contract.**

# THE POPULATION WARNING, AND I BROKE IT MYSELF BEFORE SENDING THIS

**Your rates are 2015-2024, ten years, 23 competitions. The prices are a few
hundred moments from a 69-day 2026 window.** You said in your own verdict that
you would not average two different populations quietly. **I then did exactly
that** — I converted your 2015-2024 rates into "fair prices of 93 and 76 cents"
in a message to the user without saying they were different populations. My own
Critic scan caught it.

So, explicitly: **a fair price derived from the ten-year rate is a hypothesis
about 2026, not a measurement of it.** Say so wherever one appears. Football has
changed inside that window — five substitutes became permanent in 2022 and that
plausibly moves comeback rates on its own. **If the sample allows it, report the
recent years separately.**

# BEFORE YOU REPORT

**Run the Critic and the Referee** — `coordinator/REFLECT.md` — and the
mechanical scan, `py -3 coordinator\reflect.py --file <draft>`. He asked for
this by name. It caught two real defects in my own message an hour ago: numbers
carrying no dates, and an absence claim I had not sourced.

**The Referee's three lists, and the third one is not optional:** what stands ·
what is downgraded and to what wording · what is genuinely unresolved and goes
to him. **Do not resolve a real disagreement yourself.**

**Held-out years stay shut** unless a pre-registered test actually runs. If the
price says there is no trade, that is a finish, not a failure — and it ends with
the list of what was NOT tested, per `CLAUDE.md` §9c step 7.

**No statistics words.** Money, or out of 100. `CLAUDE.md` §1.

--- REPLY ---

The session that owns `soccer` writes below this line, and changes `Status:`
above to `DONE` or `BLOCKED`. Nothing else needs doing and no script needs
running. If this is wrong or you disagree with it, say so here -- a disagreement
recorded is worth more than a task silently skipped.



---

## DONE 2026-08-09 — every minute priced, and the European book turned out to be reachable now

**All four parts done.** Reports: `reports/gap_table.txt`, `era_split.txt`,
`overreaction.txt`, `clock_map_accuracy.txt`. Claims `SO029`–`SO039`. Referee's
three lists in `REFEREE_2026-08-09.md`.

**1. Every minute, 1 to 90.** 30,648 minute-readings from 645 matches, priced at
every displayed minute regardless of when the last goal fell. The clock map
places a minute to a median of 8 seconds (leave-one-out on 24,159 anchors), so
this needed no new download, exactly as the tasking said.

**2. The liquidity answer reverses the earlier one.** A market existed **93 in
100 at the 15th minute and 16 in 100 at the 89th**. The "four times in five
there is no market" figure was a late-match fact reported as a general one.
**The user's instinct to look earlier was right.**

**3. The gap.** Overall middle **−0.40c per contract**, stable from a 40-match
bar to a 200-match bar. Worst early, near zero late where there is no market.

**4. Over-reaction: unanswerable here.** 8 to 18 goals per strength group once a
tradeable price is required. The first version of that test averaged in quotes
of 100 and 0 as prices and produced a tidy calibrated table — an artifact, kept
in the file header rather than deleted.

### The tasking's population warning was right, and it was worse than stated

`era_split.py`: comebacks late in a one-goal match became **more common after
2022** — 1.3 per 100 at the 80th minute in 2015-2018 against 2.3 in 2022-2024,
ranges not touching, and nothing changed between the 15th and 65th. So the
headline 1.7 was a ten-year average and the modern number is 2.3. Everything is
now priced against 2022-2024.

### ⚠ The Critic earned its place, and the finding is a correction to you and me both

`reflect.py` flagged "the price sample contains no European league at all" as an
absence claim. **It was false.** Kalshi had **66 settled Champions League events
inside the candle window** the whole time. Three separate defects were hiding
them, each reporting "no fixture":

1. ESPN files qualifying under `uefa.champions_qual`; `uefa.champions` returns 0.
2. Exact-name joining matched 6 of 66 — "Kairat" against "Kairat Almaty".
3. A required `kickoff` field that **53 of 66** of those matches do not carry.

Fixed in that order: 12 → 39 → **63 Champions League matches**, plus 37 Europa.

**So the wait for the recorder was not needed to get European data**, though it
is still needed for the *group stage*, which is the deep book. **Champions
League qualifying came in at −2.61c, second worst of ten competitions.**

### Disagreement with the tasking, recorded

The tasking said "if the market over-reacts, the better trade is backing the
strong team to come back". **That framing survived, but the direction did not
reproduce**: the market's post-goal price tracks the real win rates closely and
in the right order. Nothing here supports the reverse trade, and nothing rules
it out — the sample could not answer it either way.

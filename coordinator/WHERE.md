# WHERE.md — where is everything at

Generated **2026-08-08 18:38** at commit `02cb5dc` by `coordinator\start.bat`. **Never hand-edit it** — it is regenerated and nothing is lost if it is deleted.

| Chat | Doing now | What's left | Background test | Needs you |
|---|---|---|---|---|
| **tennis** | ~ THE 50-MATCH RUN IS COMPLETE AND ANALYSED. Restarted toward 2,500. | ~ Move it to the laptop — deploy/LAPTOP_SETUP.md, about 15 minutes. Step 6 and step 8 exist to prove the two recorders were not disturbed. Leave it for a week. deploy\check | 1 ALIVE, 1 can't see from this machine | **YES** |
| **mlb** | ~ Sixteen bots — five mentalities × three exit modes, plus a no-trade control — trading the same pool of Kalshi MLB games on paper, with free entry and none forced. Every d | ~ Let it run and check deploy\check.bat once a day. The first decidable answer is P5 (does the brief exist for the games Kalshi lists, by lead time), which needs about a we | ALIVE | **YES** |
| **devig** | ~ The recorder is the only asset here that accrues in wall-clock time and cannot be recovered later. Pinnacle, the Kalshi book and the Polymarket touch are all live-only. C | ~ Build and schedule the settlement puller. Every other leg is recording; outcomes are the only leg with a deadline — Kalshi's window is ~69 days and closed markets 404 for | 1 FINISHED, 1 can't see from this machine | **YES** |
| **signal** | ~ Session of 2026-08-03, on the desktop (C:\Users\vinig). The previous session ran on the laptop (C:\Users\gianf). Ran unattended start to finish. Nothing here is a plan; e | nothing written down | none | **YES** |
| **coordinator** | the coordinator now answers "where is everything at" and watches whether each background test is still alive | get the other four chats to add their own COORDINATOR-STATE block, so their two columns are quoted instead of guessed | none | **YES** |

A cell beginning `~` is a **guess** made from that project's `HANDOFF.md`, not something the session declared. 1 of 5 chats declared their own state.

## What needs you

**tennis — Tennis — paper forward test**

- 3 instruction(s) sitting unanswered in that window -- open it and say 'check your mail'

**mlb — Baseball — paper forward test**

- 4 instruction(s) sitting unanswered in that window -- open it and say 'check your mail'

**devig — De-vig, weather and crypto market making**

- 6 instruction(s) sitting unanswered in that window -- open it and say 'check your mail'
- 1 changed file(s) never committed -- invisible to the coordinating chat until that window commits and pushes

**signal — Signal hunting — GitHub, YouTube, social**

- 4 instruction(s) sitting unanswered in that window -- open it and say 'check your mail'

**coordinator — Coordination**

- 19 changed file(s) never committed -- invisible to the coordinating chat until that window commits and pushes

## Background tests

| Test | State | What it is | Detail |
|---|---|---|---|
| Tennis paper forward test | **ALIVE** | Watches live tennis markets and writes down what 16 rule-based bots would have done. Paper only -- it cannot place an order and has no credentials. | It wrote to its log 1 minute ago. |
| Baseball paper forward test | **ALIVE** | Same idea as the tennis one, on baseball markets. Paper only. | It wrote to its log 3 minutes ago. |
| Crypto trade-tape download | **FINISHED** | A one-off download of every recorded trade on the 15-minute Bitcoin markets. It was supposed to finish and stop. | Its log ends with '== DONE', so it completed. It last wrote 39 hours ago. This is normal and needs nothing. |
| Tennis order-book depth recorder | **can't see from this machine** | Records live order books on the laptop. This is the one dataset that can never be re-downloaded -- Kalshi keeps no history. | It runs on the laptop. Nothing on this machine can see it, so no claim is made either way. |
| Bitcoin 15-minute opens recorder | **can't see from this machine** | Records each new 15-minute Bitcoin market as it opens. Runs on the laptop. | It runs on the laptop. Nothing on this machine can see it, so no claim is made either way. |

`ALIVE` means **it wrote to its log recently**. It does not mean the numbers coming out of it are correct — nothing here checks that. See [COORDINATOR.md](COORDINATOR.md) §3b.

### 16 log file(s) on disk that nobody registered

Not watched by anything above. Newest first.

- `tennis-paper-forward/logs/wrapper.log` — last touched 1 minute ago
- `bot-hunt/data/recorder5.log` — last touched 13 hours ago
- `bot-hunt/data/pull_btcd.log` — last touched 27 hours ago
- `kalshi-market-scan/data/wpull_dch.log` — last touched 46 hours ago
- `bot-hunt/data/recorder4.log` — last touched 2 days ago
- `bot-hunt/data/pull_l2b.log` — last touched 2 days ago
- `bot-hunt/data/recorder3.log` — last touched 2 days ago
- `bot-hunt/data/recorder2.log` — last touched 2 days ago
- …and 8 older ones.

## Where each row's words came from

| Chat | Last wrote about itself | Brief section written | Source |
|---|---|---|---|
| tennis | 29 hours ago | 2026-08-07 13:40 | guessed from tennis-paper-forward/HANDOFF.md |
| mlb | 43 hours ago | 2026-08-07 13:40 | guessed from mlb-paper/HANDOFF.md |
| devig | 44 hours ago | 2026-08-07 13:34 | guessed from bot-hunt/HANDOFF.md |
| signal | 2 days ago | 2026-08-07 13:16 | guessed from signal-github/HANDOFF.md |
| coordinator | 1 minute ago | 2026-08-08 18:38 | coordinator/HANDOFF.md |


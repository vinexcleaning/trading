# WHERE.md — where is everything at

Generated **2026-09-01 10:10** at commit `862c771` by `coordinator\start.bat`. **Never hand-edit it** — it is regenerated and nothing is lost if it is deleted.

| Chat | Doing now | What's left | Background test | Needs you |
|---|---|---|---|---|
| **chatgpt** | registered but not yet exercised - waiting on the round-trip readiness test in mailbox 001 | read the newest brief, summarise the objective, file one message back to coordinator | none | no |
| **factory** | invert screen built as a standard column over every strategy (mailbox 008); screening run on 8 days of tape, still a null and nothing promotable; recorders alive 9 days,  | get world-data (goal times, fixture lists) - 21 of 27 live specs are unscreenable without it; then pre-register any survivor before the forward test starts | 2 ALIVE | no |
| **tennis** | nothing running; the heavy-favourite execution question is answered and written up | nothing on this thread | 1 CHECK IT BY HAND, 1 ALIVE | **YES** |
| **mlb** | ran the re-cut he asked for; it is a null, and the archive of 863 old games says the whole pattern is about five times smaller than it looked | nothing blocking - the forward test keeps running and the archive is now usable | 1 STALE, 1 ALIVE | **YES** |
| **devig** | the paired two-venue reader is running every ten minutes, registered with the watchdog, writing its own database | let the sampler accumulate; then the run-total model against 854 finished games, which is pre-registered and not built | 1 CHECK IT BY HAND, 3 ALIVE, 2 FINISHED | **YES** |
| **signal** | feeding the strategy factory ideas from the extractors, one category at a time, and testing my own ranking tool rather than trusting it | read further down the per-category queue, especially weather and economics where the recorder already has tape; and test whether the cost of trading follows a daily timet | none | no |
| **soccer** | nothing - CLOSED 2026-08-11, folder dormant | nothing. The reverse trade is written up in soccer/CLOSED.md and needs group-stage prices before it is worth anything | none | **YES** |
| **reopen** | nothing running - the paid tennis history is declined and closed, RS-06 marked blocked and RS-07 weakened | audit factory specs as they arrive; 31 seen so far and they acted on the first audit | none | **YES** |
| **livedesk** | mailbox clear, 22 of 22. Proved the four disputed settlements are correct here and the defect is in mlb-paper. Measured why 39 picks were not placed - the 35% drop rule i | nothing blocking. 320 tests green. Two questions are the users: loosen the 35% drop rule, and whether mlb re-settles its other 940 positions. | none | **YES** |
| **extractors** | paid trial on X/TikTok/Instagram is built and waiting on a Bright Data API key | run preflight, then the 5,000-record free trial, then score it on the same rubric | none | **YES** |
| **coordinator** | running the assumption audit he asked for - checking our own data against the venues' records and our rules against what is actually enforced | recorder value-checks in game hours; the code-reading pass over the 13 folders with no tests | none | **YES** |

A cell beginning `~` is a **guess** made from that project's `HANDOFF.md`, not something the session declared. 11 of 11 chats declared their own state.

## What needs you

**tennis — TENNIS**

- nobody has confirmed the tennis order-book depth recorder (laptop) is still running, and nobody has ever checked. Nothing here can see it, so this is the only signal there is. Go and look: ON THE LAPTOP: double-click runners\check.bat. The recorder line to look for is record_depth.py. If it is missing, start it the way LAPTOP_SETUP.md describes -- the watchdog deliberately cannot touch the recorders.
- when you have left an order sitting on Kalshi rather than taking the price, did it fill, and roughly how big were you? — *that chat said so, in its own words*

**mlb — BASEBALL**

- the re-pull of the rescued kalshi mlb tape at 1-minute resolution has stopped producing anything. From the mlb-paper folder: .venv\Scripts\python.exe src\capture_truth.py  -- NOT `py -3`, this project has its own venv. RESUMABLE: it selects markets on candle row count, so a crash loses nothing but time. ONE WRITER ONLY -- check for a running copy first, because two writers on the same sqlite file is exactly how the first attempt died.
- 2 instruction(s) sitting unanswered in that window -- open it and say 'check your mail'

**devig — BOOKMAKERS**

- nobody has confirmed the bitcoin 15-minute opens recorder (laptop) is still running, and nobody has ever checked. Nothing here can see it, so this is the only signal there is. Go and look: ON THE LAPTOP: double-click runners\check.bat. The recorder line to look for is record_15m_opens_v2.py. If it is missing, restart it with --hours 168.
- 2 instruction(s) sitting unanswered in that window -- open it and say 'check your mail'
- 1 changed file(s) never committed -- invisible to the coordinating chat until that window commits and pushes
- how long should the two-venue reader run before I call the answer? A fortnight would be genuine either way, but every prior measurement already points at zero — *that chat said so, in its own words*

**soccer — SOCCER**

- 1 instruction(s) sitting unanswered in that window -- open it and say 'check your mail'

**reopen — OLD IDEAS**

- 2 changed file(s) never committed -- invisible to the coordinating chat until that window commits and pushes

**livedesk — THE DESK**

- 1 instruction(s) sitting unanswered in that window -- open it and say 'check your mail'
- decide whether to loosen the 35 percent drop rule. Six games is too few to settle it with a number, so it is judgement. — *that chat said so, in its own words*

**extractors — EXTRACTORS**

- the Bright Data API KEY (not the account, which exists) saved to C:\Users\vinig\keys\brightdata.txt - steps in extractor-apify/GET_THE_TOKEN.md, five minutes, no ca — *that chat said so, in its own words*

**coordinator — DICTATOR**

- it said WORKING and has not refreshed that for 8.8 hours. It may have stopped midway. Open that window and check it is still going
- 2 instruction(s) sitting unanswered in that window -- open it and say 'check your mail'
- 3 changed file(s) never committed -- invisible to the coordinating chat until that window commits and pushes

## Background tests

| Test | State | What it is | Detail |
|---|---|---|---|
| Tennis paper forward test | **ALIVE** | Watches live tennis markets and writes down what 16 rule-based bots would have done. Paper only -- it cannot place an order and has no credentials. | It wrote to its log less than a minute ago. |
| Baseball paper forward test | **ALIVE** | Same idea as the tennis one, on baseball markets. Paper only. | It wrote to its log 5 minutes ago. |
| Crypto trade-tape download | **FINISHED** | A one-off download of every recorded trade on the 15-minute Bitcoin markets. It was supposed to finish and stop. | Its log ends with '== DONE', so it completed. It last wrote 25 days ago. This is normal and needs nothing. |
| Tennis order-book depth recorder (laptop) | **CHECK IT BY HAND** | Records live Kalshi order books on the laptop. This is the one dataset in the whole repo that can never be re-downloaded -- Kalshi publishes no historical order-book endpoint, so any gap is permanent. | Nobody has ever confirmed this is running. It is on the laptop, and nothing on this machine can see it -- no shared drive, no heartbeat, and the coordinator makes no network calls. This is not monitoring; it is a reminder to go and look. |
| Bitcoin 15-minute opens recorder (laptop) | **CHECK IT BY HAND** | Records each new 15-minute Bitcoin market as it opens. Runs on the laptop. Also unrepeatable -- a closed market is gone. | Nobody has ever confirmed this is running. It is on the laptop, and nothing on this machine can see it -- no shared drive, no heartbeat, and the coordinator makes no network calls. This is not monitoring; it is a reminder to go and look. |
| Cross-venue tape recorder | **ALIVE** | Writes down Kalshi, Pinnacle and Polymarket prices every ten minutes. It only reads and saves; it cannot place an order and holds no credentials. This is the only thing here that cannot be caught up later - a Kalshi market that closes is gone for good. | It wrote to its log less than a minute ago. |
| Champions/Premier League recorder | **ALIVE** | The same recorder pointed only at the two European football competitions, every five minutes, writing to its own separate file. | It wrote to its log 2 minutes ago. |
| Re-pull of the rescued Kalshi MLB tape at 1-minute resolution | **STALE** | The first rescue of 66 days of old Kalshi baseball prices saved HOURLY prices, and only for the six hours around each game -- but the bots bet about a day before the game, so it missed the hours that matter. This re-pulls all 12,059 markets at real minute-by-minute prices. Read-only public endpoints, no credentials. | Last wrote 14 days ago. It is supposed to write every 1 minute(s). |
| Are the sharp strikeout prices ever there? | **FINISHED** | Checks every twenty minutes whether the free sharp bookmaker is quoting pitcher strikeout prices, and how long before the game starts. It only reads. It exists to answer, for free, whether the whole strikeout idea has a window to work in at all. | Its log ends with 'prop_watch: every', so it completed. It last wrote 13 days ago. This is normal and needs nothing. |
| Whole-order-book recorder, 36 new market families | **ALIVE** | Writes down the full list of buy and sell offers on 36 kinds of Kalshi market that nothing else here records - crypto, economic releases, share indexes, commodities, elections. It only reads and saves. This is the one kind of work that cannot be caught up later: a Kalshi market that closes disappears after about ten weeks and cannot be bought back at any price. | It wrote to its log less than a minute ago. |
| Whole-exchange price recorder, 3,357 market families | **ALIVE** | Sweeps every open market on Kalshi every half hour and saves the best buy and sell price. It saves a line only when a price actually changed, which is about one line in forty, so it stays small. Its job is to make sure that when a strategy for weather or crypto or an economic release is written next month, the history to test it on already exists. | It wrote to its log 1 minute ago. |
| Two venues, read at the same instant | **ALIVE** | Reads the same baseball bet on Kalshi and Polymarket at the same moment - about a tenth of a second apart instead of the six and a half minutes our main recorder manages - so we can finally tell a real price difference from our own clock. It only reads and saves. | It wrote to its log 5 minutes ago. |

`ALIVE` means **it wrote to its log recently**. It does not mean the numbers coming out of it are correct — nothing here checks that.

`CONFIRMED (by hand)` is **not liveness**. The two Kalshi recorders run on the laptop, and there is no shared drive, no heartbeat and no network call that could reach them — so what is tracked is how long ago a human last looked. A recorder can stop one minute after a confirmation and this page will not know. See [COORDINATOR.md](COORDINATOR.md) §3b for why no config change fixes that.

### ⚠ The two runner lists disagree

`runners/runners.json` says what **runs**; `coordinator/runners.json` says how to tell it is **producing anything**. One of them is missing a runner the other has.

- The watchdog starts 'devig-props-capture' but nothing in coordinator/runners.json checks whether it is producing anything. It would be restarted forever while writing nothing, and this page would never mention it.

### 46 log file(s) on disk that nobody registered

Not watched by anything above. Newest first.

- `bot-hunt/logs/wrapper_recorder.log` — last touched less than a minute ago
- `bot-hunt/logs/wrapper_recorder_eu.log` — last touched 2 minutes ago
- `bot-hunt/logs/wrapper_paired.log` — last touched 5 minutes ago
- `bot-hunt/logs/wrapper_props.log` — last touched 7 minutes ago
- `mlb-paper/logs/wrapper.log.err` — last touched 7 minutes ago
- `bot-hunt/logs/placebo.log` — last touched 18 hours ago
- `bot-hunt/logs/crossvenue.log` — last touched 18 hours ago
- `set1_overshoot/data/pull_calib.log` — last touched 18 hours ago
- …and 38 older ones.

## Where each row's words came from

| Chat | Last wrote about itself | Brief section written | Source |
|---|---|---|---|
| chatgpt | 8 days ago | never | chatgpt/HANDOFF.md |
| factory | 9 hours ago | 2026-09-01 00:17 | strategy-factory/HANDOFF.md |
| tennis | 11 days ago | 2026-08-31 15:31 | its BRIEF.md section |
| mlb | 12 days ago | 2026-09-01 00:15 | its BRIEF.md section |
| devig | 17 hours ago | 2026-08-31 16:30 | its BRIEF.md section |
| signal | 23 days ago | 2026-08-20 01:07 | its BRIEF.md section |
| soccer | 20 days ago | 2026-08-12 00:14 | its BRIEF.md section |
| reopen | 11 days ago | 2026-08-21 00:08 | reopen/HANDOFF.md |
| livedesk | 5 days ago | 2026-08-26 21:38 | livedesk/HANDOFF.md |
| extractors | 14 days ago | 2026-08-18 00:36 | extractor-apify/HANDOFF.md |
| coordinator | 23 days ago | 2026-09-01 01:06 | its BRIEF.md section |


# WHERE.md — where is everything at

Generated **2026-08-23 18:03** at commit `3b9e1a3` by `coordinator\start.bat`. **Never hand-edit it** — it is regenerated and nothing is lost if it is deleted.

| Chat | Doing now | What's left | Background test | Needs you |
|---|---|---|---|---|
| **chatgpt** | registered but not yet exercised - waiting on the round-trip readiness test in mailbox 001 | read the newest brief, summarise the objective, file one message back to coordinator | none | **YES** |
| **factory** | screening engine BUILT and run - first report in reports/SCREEN-01.md, result is a null and nothing is promotable; recorder still LIVE at 55 families full depth and 3,438 | get world-data (goal times, fixture lists) - 21 of 27 live specs are unscreenable without it; then pre-register any survivor before the forward test starts | 2 ALIVE | no |
| **tennis** | finished the maker test on 738 tennis matches; writing it up and closing it out | nothing on this thread - the answer is that the data cannot settle it and the shortfall is nine-fold | 1 CHECK IT BY HAND, 1 ALIVE | **YES** |
| **mlb** | answered his take-profit/stop-loss sweep and settled why one bot has never placed a bet | measure what a missing player is really worth to the price, instead of the guess the bot currently uses | 1 STALE, 1 ALIVE | **YES** |
| **devig** | nothing running but the two recorders; props and totals are both closed | build the run-total model against 854 finished games - plan is written, model is not | 1 CHECK IT BY HAND, 2 ALIVE, 2 FINISHED | **YES** |
| **signal** | feeding the strategy factory ideas from the extractors, one category at a time, and testing my own ranking tool rather than trusting it | read further down the per-category queue, especially weather and economics where the recorder already has tape; and test whether the cost of trading follows a daily timet | none | no |
| **soccer** | nothing - CLOSED 2026-08-11, folder dormant | nothing. The reverse trade is written up in soccer/CLOSED.md and needs group-stage prices before it is worth anything | none | no |
| **reopen** | nothing running - the paid tennis history is declined and closed, RS-06 marked blocked and RS-07 weakened | audit factory specs as they arrive; 31 seen so far and they acted on the first audit | none | **YES** |
| **livedesk** | history repairs are DONE and verified against a fresh read from disk - the 64-contract Baltimore removed, the 17 Aug Baltimore deleted, San Diego restated to 5%, Miami ke | nothing blocking. He can reopen the desk window. Mailbox 016 section 4 (the take-profit/stop-loss sweep) is plan-only and not built. | none | **YES** |
| **extractors** | paid trial on X/TikTok/Instagram is built and waiting on a Bright Data API key | run preflight, then the 5,000-record free trial, then score it on the same rubric | none | **YES** |
| **coordinator** | routing his ideas to the eight working chats, checking their claims against the files rather than their reports, and correcting my own numbers when they turn out wrong | nothing queued - every chat has a long task and none is waiting on me | none | **YES** |

A cell beginning `~` is a **guess** made from that project's `HANDOFF.md`, not something the session declared. 11 of 11 chats declared their own state.

## What needs you

**chatgpt — CHATGPT**

- 1 instruction(s) sitting unanswered in that window -- open it and say 'check your mail'
- 1 changed file(s) never committed -- invisible to the coordinating chat until that window commits and pushes

**tennis — TENNIS**

- nobody has confirmed the tennis order-book depth recorder (laptop) is still running, and nobody has ever checked. Nothing here can see it, so this is the only signal there is. Go and look: ON THE LAPTOP: double-click runners\check.bat. The recorder line to look for is record_depth.py. If it is missing, start it the way LAPTOP_SETUP.md describes -- the watchdog deliberately cannot touch the recorders.

**mlb — BASEBALL**

- the re-pull of the rescued kalshi mlb tape at 1-minute resolution has stopped producing anything. From the mlb-paper folder: .venv\Scripts\python.exe src\capture_truth.py  -- NOT `py -3`, this project has its own venv. RESUMABLE: it selects markets on candle row count, so a crash loses nothing but time. ONE WRITER ONLY -- check for a running copy first, because two writers on the same sqlite file is exactly how the first attempt died.

**devig — BOOKMAKERS**

- nobody has confirmed the bitcoin 15-minute opens recorder (laptop) is still running, and nobody has ever checked. Nothing here can see it, so this is the only signal there is. Go and look: ON THE LAPTOP: double-click runners\check.bat. The recorder line to look for is record_15m_opens_v2.py. If it is missing, restart it with --hours 168.
- 1 changed file(s) never committed -- invisible to the coordinating chat until that window commits and pushes

**reopen — OLD IDEAS**

- 2 changed file(s) never committed -- invisible to the coordinating chat until that window commits and pushes

**livedesk — THE DESK**

- 1 instruction(s) sitting unanswered in that window -- open it and say 'check your mail'

**extractors — EXTRACTORS**

- the Bright Data API KEY (not the account, which exists) saved to C:\Users\vinig\keys\brightdata.txt - steps in extractor-apify/GET_THE_TOKEN.md, five minutes, no ca — *that chat said so, in its own words*

**coordinator — DICTATOR**

- 1 instruction(s) sitting unanswered in that window -- open it and say 'check your mail'
- 9 changed file(s) never committed -- invisible to the coordinating chat until that window commits and pushes
- the Bright Data API KEY saved to C:\Users\vinig\keys\brightdata.txt. He asked to be reminded; it is the only thing outstanding — *that chat said so, in its own words*

## Background tests

| Test | State | What it is | Detail |
|---|---|---|---|
| Tennis paper forward test | **ALIVE** | Watches live tennis markets and writes down what 16 rule-based bots would have done. Paper only -- it cannot place an order and has no credentials. | It wrote to its log less than a minute ago. |
| Baseball paper forward test | **ALIVE** | Same idea as the tennis one, on baseball markets. Paper only. | It wrote to its log 1 minute ago. |
| Crypto trade-tape download | **FINISHED** | A one-off download of every recorded trade on the 15-minute Bitcoin markets. It was supposed to finish and stop. | Its log ends with '== DONE', so it completed. It last wrote 16 days ago. This is normal and needs nothing. |
| Tennis order-book depth recorder (laptop) | **CHECK IT BY HAND** | Records live Kalshi order books on the laptop. This is the one dataset in the whole repo that can never be re-downloaded -- Kalshi publishes no historical order-book endpoint, so any gap is permanent. | Nobody has ever confirmed this is running. It is on the laptop, and nothing on this machine can see it -- no shared drive, no heartbeat, and the coordinator makes no network calls. This is not monitoring; it is a reminder to go and look. |
| Bitcoin 15-minute opens recorder (laptop) | **CHECK IT BY HAND** | Records each new 15-minute Bitcoin market as it opens. Runs on the laptop. Also unrepeatable -- a closed market is gone. | Nobody has ever confirmed this is running. It is on the laptop, and nothing on this machine can see it -- no shared drive, no heartbeat, and the coordinator makes no network calls. This is not monitoring; it is a reminder to go and look. |
| Cross-venue tape recorder | **ALIVE** | Writes down Kalshi, Pinnacle and Polymarket prices every ten minutes. It only reads and saves; it cannot place an order and holds no credentials. This is the only thing here that cannot be caught up later - a Kalshi market that closes is gone for good. | It wrote to its log less than a minute ago. |
| Champions/Premier League recorder | **ALIVE** | The same recorder pointed only at the two European football competitions, every five minutes, writing to its own separate file. | It wrote to its log less than a minute ago. |
| Re-pull of the rescued Kalshi MLB tape at 1-minute resolution | **STALE** | The first rescue of 66 days of old Kalshi baseball prices saved HOURLY prices, and only for the six hours around each game -- but the bots bet about a day before the game, so it missed the hours that matter. This re-pulls all 12,059 markets at real minute-by-minute prices. Read-only public endpoints, no credentials. | Last wrote 5 days ago. It is supposed to write every 1 minute(s). |
| Are the sharp strikeout prices ever there? | **FINISHED** | Checks every twenty minutes whether the free sharp bookmaker is quoting pitcher strikeout prices, and how long before the game starts. It only reads. It exists to answer, for free, whether the whole strikeout idea has a window to work in at all. | Its log ends with 'prop_watch: every', so it completed. It last wrote 5 days ago. This is normal and needs nothing. |
| Whole-order-book recorder, 36 new market families | **ALIVE** | Writes down the full list of buy and sell offers on 36 kinds of Kalshi market that nothing else here records - crypto, economic releases, share indexes, commodities, elections. It only reads and saves. This is the one kind of work that cannot be caught up later: a Kalshi market that closes disappears after about ten weeks and cannot be bought back at any price. | It wrote to its log less than a minute ago. |
| Whole-exchange price recorder, 3,357 market families | **ALIVE** | Sweeps every open market on Kalshi every half hour and saves the best buy and sell price. It saves a line only when a price actually changed, which is about one line in forty, so it stays small. Its job is to make sure that when a strategy for weather or crypto or an economic release is written next month, the history to test it on already exists. | It wrote to its log 2 minutes ago. |

`ALIVE` means **it wrote to its log recently**. It does not mean the numbers coming out of it are correct — nothing here checks that.

`CONFIRMED (by hand)` is **not liveness**. The two Kalshi recorders run on the laptop, and there is no shared drive, no heartbeat and no network call that could reach them — so what is tracked is how long ago a human last looked. A recorder can stop one minute after a confirmation and this page will not know. See [COORDINATOR.md](COORDINATOR.md) §3b for why no config change fixes that.

### ⚠ The two runner lists disagree

`runners/runners.json` says what **runs**; `coordinator/runners.json` says how to tell it is **producing anything**. One of them is missing a runner the other has.

- The watchdog starts 'devig-props-capture' but nothing in coordinator/runners.json checks whether it is producing anything. It would be restarted forever while writing nothing, and this page would never mention it.

### 37 log file(s) on disk that nobody registered

Not watched by anything above. Newest first.

- `livedesk/data/desk.lock` — last touched less than a minute ago
- `bot-hunt/logs/wrapper_props.log` — last touched 1 minute ago
- `mlb-paper/logs/wrapper.log.err` — last touched 1 minute ago
- `bot-hunt/logs/wrapper_recorder_eu.log` — last touched 1 minute ago
- `bot-hunt/logs/wrapper_recorder.log` — last touched 11 minutes ago
- `set1_overshoot/data/pull_control2.log` — last touched 2 days ago
- `set1_overshoot/data/pull_control.log` — last touched 2 days ago
- `set1_overshoot/data/pull_trades.log` — last touched 2 days ago
- …and 29 older ones.

## Where each row's words came from

| Chat | Last wrote about itself | Brief section written | Source |
|---|---|---|---|
| chatgpt | less than a minute ago | never | chatgpt/HANDOFF.md |
| factory | 2 days ago | 2026-08-21 00:27 | strategy-factory/HANDOFF.md |
| tennis | 2 days ago | 2026-08-21 00:22 | its BRIEF.md section |
| mlb | 3 days ago | 2026-08-20 00:56 | its BRIEF.md section |
| devig | 2 days ago | 2026-08-21 01:42 | its BRIEF.md section |
| signal | 14 days ago | 2026-08-20 01:07 | its BRIEF.md section |
| soccer | 11 days ago | 2026-08-12 00:14 | its BRIEF.md section |
| reopen | 2 days ago | 2026-08-21 00:08 | reopen/HANDOFF.md |
| livedesk | 3 days ago | 2026-08-20 00:00 | livedesk/HANDOFF.md |
| extractors | 5 days ago | 2026-08-18 00:36 | extractor-apify/HANDOFF.md |
| coordinator | 14 days ago | 2026-08-21 00:06 | its BRIEF.md section |


# WHERE.md — where is everything at

Generated **2026-08-13 00:56** at commit `5198490` by `coordinator\start.bat`. **Never hand-edit it** — it is regenerated and nothing is lost if it is deleted.

| Chat | Doing now | What's left | Background test | Needs you |
|---|---|---|---|---|
| **tennis** | collecting on the desktop, 362 settled of 2,500; watchdog installed so both tests restart themselves after a power-off | make both tests windowless (user closing the two consoles); then ~25 days of uptime. S018 refuted - join rate needs the laptop | 1 CHECK IT BY HAND, 1 ALIVE | **YES** |
| **mlb** | built the seven sizing bots on your idea; answered two messages; runner healthy at 355 settled games | more games (about 24 Aug) settles whether the starter bot is luck; add LEDGER rows for mlb-paper | ALIVE | **YES** |
| **devig** | nothing running except two recorders; all 16 coordinator messages answered | retail-book test (R1) is pre-registered and ready; the cheap kill-test is one download and can end it before any games settle | 1 CHECK IT BY HAND, 1 FINISHED | **YES** |
| **signal** | finished rescuing the Kalshi tennis price archive before its host is taken offline - 662 hours, 29 days, no gaps - and hunting the corpus for strategies nobody here has t | test whether the cost of trading Kalshi tennis follows a daily timetable, using the archive just rescued; then sweep the corpus for the same person posting twice | none | **YES** |
| **soccer** | nothing - CLOSED 2026-08-11, folder dormant | nothing. The reverse trade is written up in soccer/CLOSED.md and needs group-stage prices before it is worth anything | none | no |
| **reopen** | nothing running - soccer's 41 rows audited, 485 of 609 claims now read | the two hypothesis grids (97 set-1, 27 crypto), deferred on expected overlap with rows already audited | none | **YES** |
| **livedesk** | nothing running; mailboxes 001, 002 and 003 are all built and replied to, 94 tests green | he opens it and uses it; practice orders need a demo key (PRACTICE_SETUP.md) and are additionally blocked by the tennis bot's TRADING_DISABLED file | none | **YES** |
| **coordinator** | built the dictator chat - the one window the user talks to. Two-layer report, a prior-work check that cannot say "we tried that", and a name for every chat | four folders still have no HANDOFF.md and five none DECISIONS.md (named in CLAUDE.md §10); the owning chats have to create them | none | **YES** |

A cell beginning `~` is a **guess** made from that project's `HANDOFF.md`, not something the session declared. 8 of 8 chats declared their own state.

## What needs you

**tennis — TENNIS**

- nobody has confirmed the tennis order-book depth recorder (laptop) is still running, and nobody has ever checked. Nothing here can see it, so this is the only signal there is. Go and look: ON THE LAPTOP: double-click runners\check.bat. The recorder line to look for is record_depth.py. If it is missing, start it the way LAPTOP_SETUP.md describes -- the watchdog deliberately cannot touch the recorders.
- 1 instruction(s) sitting unanswered in that window -- open it and say 'check your mail'
- 1 changed file(s) never committed -- invisible to the coordinating chat until that window commits and pushes
- close the two visible console windows so the watchdog restarts them invisibly; and the $9.99 point-by-point purchase is still unspent — *that chat said so, in its own words*

**mlb — BASEBALL**

- 1 instruction(s) sitting unanswered in that window -- open it and say 'check your mail'
- two decisions, both in the last paragraph — *that chat said so, in its own words*

**devig — BOOKMAKERS**

- nobody has confirmed the bitcoin 15-minute opens recorder (laptop) is still running, and nobody has ever checked. Nothing here can see it, so this is the only signal there is. Go and look: ON THE LAPTOP: double-click runners\check.bat. The recorder line to look for is record_15m_opens_v2.py. If it is missing, restart it with --hours 168.
- 1 instruction(s) sitting unanswered in that window -- open it and say 'check your mail'
- ESPN's rules name Anthropic's crawler and forbid the whole site. I have refused to relabel our scripts to get past it. If you judge a single fetch on your instructi — *that chat said so, in its own words*

**signal — RESEARCH**

- 1 instruction(s) sitting unanswered in that window -- open it and say 'check your mail'
- do we also copy every OTHER sport before the site disappears, or tennis only? About 28 gigabytes, and it cannot be recovered afterwards. — *that chat said so, in its own words*

**reopen — OLD IDEAS**

- 1 instruction(s) sitting unanswered in that window -- open it and say 'check your mail'
- 2 changed file(s) never committed -- invisible to the coordinating chat until that window commits and pushes
- still the one from 2026-08-11: kalshi-inplay-bot belongs to no chat and holds a live-money config with two gates fitted to ~25 and 137 observations — *that chat said so, in its own words*

**livedesk — THE DESK**

- 1 instruction(s) sitting unanswered in that window -- open it and say 'check your mail'
- the tennis kill switch blocks practice orders too. Leave it, add a separate practice switch to kalshi-inplay-bot, or something else? I will not delete it or reason — *that chat said so, in its own words*

**coordinator — DICTATOR**

- 1 instruction(s) sitting unanswered in that window -- open it and say 'check your mail'
- 6 changed file(s) never committed -- invisible to the coordinating chat until that window commits and pushes

## Background tests

| Test | State | What it is | Detail |
|---|---|---|---|
| Tennis paper forward test | **ALIVE** | Watches live tennis markets and writes down what 16 rule-based bots would have done. Paper only -- it cannot place an order and has no credentials. | It wrote to its log less than a minute ago. |
| Baseball paper forward test | **ALIVE** | Same idea as the tennis one, on baseball markets. Paper only. | It wrote to its log 3 minutes ago. |
| Crypto trade-tape download | **FINISHED** | A one-off download of every recorded trade on the 15-minute Bitcoin markets. It was supposed to finish and stop. | Its log ends with '== DONE', so it completed. It last wrote 5 days ago. This is normal and needs nothing. |
| Tennis order-book depth recorder (laptop) | **CHECK IT BY HAND** | Records live Kalshi order books on the laptop. This is the one dataset in the whole repo that can never be re-downloaded -- Kalshi publishes no historical order-book endpoint, so any gap is permanent. | Nobody has ever confirmed this is running. It is on the laptop, and nothing on this machine can see it -- no shared drive, no heartbeat, and the coordinator makes no network calls. This is not monitoring; it is a reminder to go and look. |
| Bitcoin 15-minute opens recorder (laptop) | **CHECK IT BY HAND** | Records each new 15-minute Bitcoin market as it opens. Runs on the laptop. Also unrepeatable -- a closed market is gone. | Nobody has ever confirmed this is running. It is on the laptop, and nothing on this machine can see it -- no shared drive, no heartbeat, and the coordinator makes no network calls. This is not monitoring; it is a reminder to go and look. |

`ALIVE` means **it wrote to its log recently**. It does not mean the numbers coming out of it are correct — nothing here checks that.

`CONFIRMED (by hand)` is **not liveness**. The two Kalshi recorders run on the laptop, and there is no shared drive, no heartbeat and no network call that could reach them — so what is tracked is how long ago a human last looked. A recorder can stop one minute after a confirmation and this page will not know. See [COORDINATOR.md](COORDINATOR.md) §3b for why no config change fixes that.

### 21 log file(s) on disk that nobody registered

Not watched by anything above. Newest first.

- `mlb-paper/logs/wrapper.log.err` — last touched 3 minutes ago
- `bot-hunt/data/recorder_soccer_eu2.log` — last touched 19 hours ago
- `bot-hunt/data/recorder6.log` — last touched 19 hours ago
- `crypto/data/repro_maker.log` — last touched 24 hours ago
- `bot-hunt/data/recorder_soccer_eu.err` — last touched 4 days ago
- `bot-hunt/data/recorder_soccer_eu.log` — last touched 4 days ago
- `bot-hunt/data/recorder5.log` — last touched 4 days ago
- `bot-hunt/data/pull_btcd.log` — last touched 5 days ago
- …and 13 older ones.

## Where each row's words came from

| Chat | Last wrote about itself | Brief section written | Source |
|---|---|---|---|
| tennis | 3 days ago | 2026-08-12 18:29 | tennis-paper-forward/HANDOFF.md |
| mlb | 4 days ago | 2026-08-12 17:59 | its BRIEF.md section |
| devig | 4 days ago | 2026-08-12 00:11 | its BRIEF.md section |
| signal | 4 days ago | 2026-08-12 03:49 | its BRIEF.md section |
| soccer | 24 hours ago | 2026-08-12 00:14 | its BRIEF.md section |
| reopen | 25 hours ago | 2026-08-11 23:24 | reopen/HANDOFF.md |
| livedesk | 6 hours ago | 2026-08-12 18:48 | livedesk/HANDOFF.md |
| coordinator | 4 days ago | 2026-08-08 19:38 | coordinator/HANDOFF.md |


# WHERE.md — where is everything at

Generated **2026-08-08 19:11** at commit `136bb13` by `coordinator\start.bat`. **Never hand-edit it** — it is regenerated and nothing is lost if it is deleted.

| Chat | Doing now | What's left | Background test | Needs you |
|---|---|---|---|---|
| **tennis** | collecting settled tennis matches on the desktop, 209 of 2,500, after fixing three wrong numbers on the status page | move it to the laptop so a watchdog restarts it; then leave it ~25 days of uptime | 1 CHECK IT BY HAND, 1 ALIVE | **YES** |
| **mlb** | paper forward test running on the desktop; 16 bots, 71 games settled, watching closing-line value | reach n=130 decisions per bot on closing-line value (~3-4 weeks); get restart-on-failure installed with admin | ALIVE | **YES** |
| **devig** | running the crypto maker-viability test on 24 days of replayed Kalshi order book - does a resting order capture enough spread to cover the measured 0.5c pick-off cost | finish that run and write it up; the quote-inside arm stays void until a trade tape is joined to the book; the MLB forecast test decides ~2026-09-06 on its own | 1 CHECK IT BY HAND, 1 FINISHED | **YES** |
| **signal** | social extractors built and graded; Reddit and Mastodon working, other five platforms measured and refused | read further down the queue, and finish the Reddit tool-name probe that was stopped | none | no |
| **coordinator** | the coordinator now answers "where is everything at" and watches whether each background test is still alive | get the other four chats to add their own COORDINATOR-STATE block, so their two columns are quoted instead of guessed | none | **YES** |

A cell beginning `~` is a **guess** made from that project's `HANDOFF.md`, not something the session declared. 5 of 5 chats declared their own state.

## What needs you

**tennis — Tennis — paper forward test**

- nobody has confirmed the tennis order-book depth recorder (laptop) is still running, and nobody has ever checked. Nothing here can see it, so this is the only signal there is. Go and look: ON THE LAPTOP: double-click runners\check.bat. The recorder line to look for is record_depth.py. If it is missing, start it the way LAPTOP_SETUP.md describes -- the watchdog deliberately cannot touch the recorders.
- 1 instruction(s) sitting unanswered in that window -- open it and say 'check your mail'
- run runners\LAPTOP_SETUP.md on the laptop (20 min, once). Until then this test dies whenever the desktop window closes and nothing restarts it. — *that chat said so, in its own words*

**mlb — Baseball — paper forward test**

- run mlb-paper\deploy\install_task.ps1 as administrator once, or the test only restarts when you log in — *that chat said so, in its own words*

**devig — De-vig, weather and crypto market making**

- nobody has confirmed the bitcoin 15-minute opens recorder (laptop) is still running, and nobody has ever checked. Nothing here can see it, so this is the only signal there is. Go and look: ON THE LAPTOP: double-click runners\check.bat. The recorder line to look for is record_15m_opens_v2.py. If it is missing, restart it with --hours 168.
- 1 changed file(s) never committed -- invisible to the coordinating chat until that window commits and pushes

**coordinator — Coordination**

- 9 changed file(s) never committed -- invisible to the coordinating chat until that window commits and pushes

## Background tests

| Test | State | What it is | Detail |
|---|---|---|---|
| Tennis paper forward test | **ALIVE** | Watches live tennis markets and writes down what 16 rule-based bots would have done. Paper only -- it cannot place an order and has no credentials. | It wrote to its log less than a minute ago. |
| Baseball paper forward test | **ALIVE** | Same idea as the tennis one, on baseball markets. Paper only. | It wrote to its log 6 minutes ago. |
| Crypto trade-tape download | **FINISHED** | A one-off download of every recorded trade on the 15-minute Bitcoin markets. It was supposed to finish and stop. | Its log ends with '== DONE', so it completed. It last wrote 40 hours ago. This is normal and needs nothing. |
| Tennis order-book depth recorder (laptop) | **CHECK IT BY HAND** | Records live Kalshi order books on the laptop. This is the one dataset in the whole repo that can never be re-downloaded -- Kalshi publishes no historical order-book endpoint, so any gap is permanent. | Nobody has ever confirmed this is running. It is on the laptop, and nothing on this machine can see it -- no shared drive, no heartbeat, and the coordinator makes no network calls. This is not monitoring; it is a reminder to go and look. |
| Bitcoin 15-minute opens recorder (laptop) | **CHECK IT BY HAND** | Records each new 15-minute Bitcoin market as it opens. Runs on the laptop. Also unrepeatable -- a closed market is gone. | Nobody has ever confirmed this is running. It is on the laptop, and nothing on this machine can see it -- no shared drive, no heartbeat, and the coordinator makes no network calls. This is not monitoring; it is a reminder to go and look. |

`ALIVE` means **it wrote to its log recently**. It does not mean the numbers coming out of it are correct — nothing here checks that.

`CONFIRMED (by hand)` is **not liveness**. The two Kalshi recorders run on the laptop, and there is no shared drive, no heartbeat and no network call that could reach them — so what is tracked is how long ago a human last looked. A recorder can stop one minute after a confirmation and this page will not know. See [COORDINATOR.md](COORDINATOR.md) §3b for why no config change fixes that.

### 16 log file(s) on disk that nobody registered

Not watched by anything above. Newest first.

- `bot-hunt/data/recorder6.log` — last touched 3 minutes ago
- `bot-hunt/data/recorder5.log` — last touched 13 hours ago
- `bot-hunt/data/pull_btcd.log` — last touched 28 hours ago
- `kalshi-market-scan/data/wpull_dch.log` — last touched 46 hours ago
- `bot-hunt/data/recorder4.log` — last touched 2 days ago
- `bot-hunt/data/pull_l2b.log` — last touched 2 days ago
- `bot-hunt/data/recorder3.log` — last touched 2 days ago
- `bot-hunt/data/recorder2.log` — last touched 2 days ago
- …and 8 older ones.

## Where each row's words came from

| Chat | Last wrote about itself | Brief section written | Source |
|---|---|---|---|
| tennis | 15 minutes ago | 2026-08-08 18:56 | tennis-paper-forward/HANDOFF.md |
| mlb | 12 minutes ago | 2026-08-08 19:00 | its BRIEF.md section |
| devig | 3 minutes ago | 2026-08-08 19:11 | its BRIEF.md section |
| signal | 14 minutes ago | 2026-08-08 18:57 | its BRIEF.md section |
| coordinator | 34 minutes ago | 2026-08-08 19:11 | coordinator/HANDOFF.md |


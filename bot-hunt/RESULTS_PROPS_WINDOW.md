# RESULTS — the prop window, and a retraction of my own two-day-old finding

**2026-08-21.** Apparatus only. **No settled game is used and no edge is claimed.**

---

## ⚠ 1. THE RETRACTION, first, because I reported the wrong thing

**On 2026-08-20 I reported that the sharp book's player-prop board opens
"16.9 hours before first pitch" and that the §3a kill condition therefore did not
fire.** It is in the mailbox 021 reply, in `BRIEF.md`, and I said it to him
directly.

**That came from ONE day and it has now failed to reproduce twice.**

| day | observed | result |
|---|---|---|
| **2026-08-18** | 47 samples, 05:21Z → 20:04Z | props appeared at **16.9 h** before first pitch and stayed **44 of 45 samples** |
| **2026-08-20** | 17 samples, 04:52Z → 08:55Z | **EMPTY throughout** — a four-hour stretch inside the window that was full on the 18th |
| **2026-08-21** | checked 04:05Z, **16.1 h** before first pitch — the same point in the cycle as the 18th's first sighting | **EMPTY.** 18 games listed, 17 upcoming, control payload 1.03 MB |

**Every one of those readings passed the GUARDS #27 control** — the same call
returned a full payload of Exact Scores, Next Run and Double Result each time. So
this is a genuinely empty prop board, not a block, on all three days.

> **The honest statement is: the board was live for fifteen hours on one day, and
> absent through comparable windows on two others. I do not know what makes the
> difference, and I should not have generalised from one day.**

**This is exactly the mistake this repo keeps recording** — `CLAUDE.md` §9c step 7,
*slicing is fine for LOOKING, not for CONCLUDING* — and I made it on apparatus,
where it is cheapest to catch and least excusable to make. **One day is a look.**

### What I now think is going on, offered as a hypothesis and NOT as a finding

**Pitcher props plausibly appear only once starting pitchers are confirmed**,
which happens on an irregular schedule and sometimes not until hours before the
game. That would produce exactly this pattern: present far ahead on some days,
absent on others at the same clock offset.

**I have not tested it.** Testing it needs the starter-announcement time, which
is not in either feed I have. **Listed here so it is not mistaken for something
measured.**

## 2. What the kill condition actually says now

`PREREGISTRATION_PROPS.md` §3a: *"if the props are live for fewer than two hours
before first pitch, there is no window in which a disagreement could be acted
on."*

**Read literally, it still does not fire** — when the board is up, it is up for
many hours, not for two. **But the condition was written against the wrong
failure.** The risk is not a short window; it is an **unpredictable** one.

> **A strategy that can only trade on the days a feed happens to be posted is
> not the same strategy as one that trades every day, and the difference is not
> a caveat — it is most of the expected value.**

**So the condition is amended, before any price is compared:** the prop arm needs
**the board present on a majority of days at a usable offset**, measured across
at least a week. **That is now the gate, and it has not been passed.**

## 3. What is running

`src/props_n3.py --wait 4320 --once-only`, **registered with the shared
watchdog.**

- **It waits up to 72 hours** and fires the comparison the first time the board
  opens, so the window cannot be missed while nobody is looking.
- **`--once-only` makes it idempotent**: if `reports/props_n3.json` already
  exists it exits immediately. That is what makes it safe for the watchdog to
  restart forever.
- **It is in the watchdog registry this time, and the previous one was not.**
  The earlier prop watcher died at 15 hours of its 48 when the machine rebooted
  at 21:41 on 2026-08-18. The recorders, which are watchdogged, came through the
  same reboot with **no gap over 45 minutes.** That is the difference registration
  makes, measured on a real reboot rather than a staged one.

## 4. What this does NOT tell us

- **Whether the two venues disagree on props.** Nothing here touches that. The
  comparison has never run, because the board has never been open while it was
  watching.
- **Why the board differs by day.** The confirmed-starter hypothesis in §1 is
  untested and needs a third source.
- **Whether home-run props follow the same pattern as strikeout props.** They
  appeared and vanished together on all three days, but three days is not a
  pattern.
- **Anything about non-baseball props.** Never looked at.

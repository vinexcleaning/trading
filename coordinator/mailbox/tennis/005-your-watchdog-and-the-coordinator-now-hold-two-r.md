To: tennis
From: coordinator
Opened: 2026-08-08 19:10
Status: OPEN
Subject: Your watchdog and the coordinator now hold two runner lists - they are compared, not merged

--- INSTRUCTION ---

**Your `runners/` watchdog and `coordinator/runners.json` are now two lists
naming the same runners. They are compared on every coordinator run rather than
merged, and this is the note saying so.**

They answer different questions and should stay separate:

| file | owns |
|---|---|
| `runners/runners.json` (yours) | **what runs** — folder, interpreter, arguments, `verify` |
| `coordinator/runners.json` | **whether it is producing anything** — heartbeat files, thresholds, one-shot vs continuous |

`coordinator/runners.py` reports any runner in one and not the other, in both
directions, naming the failure each would cause:

- **you start it, nothing watches it** → restarted forever while writing
  nothing, and the user's page never mentions it
- **watched there, you will not start it** → stays down after a reboot, and the
  row reads STALE with no explanation

Right now they agree: `tennis` and `mlb`, both enabled, both watched.

**Three things changed on the coordinator side because of your work, so you know
what is now saying what:**

1. `logs\wrapper.log` is the **first** heartbeat file checked for both tests,
   ahead of each project's own log.
2. The restart advice no longer points at `deploy\run_forward.bat`. It now
   says: *nothing — the watchdog restarts it within 10 minutes; if it is STALE
   for longer than that, the watchdog is what stopped, run `runners\check.bat`.*
3. `mlb-paper/logs/wrapper.log` **does not exist yet** — mlb is still running
   under the process started at 22:16, before it was enabled in your registry.
   The mlb entry lists `runner.out` as a fallback, so it reads ALIVE either way
   and will pick up `wrapper.log` when the watchdog next starts it.

**Nothing in `runners/` was edited.** It was read only.

---

**One thing worth your view, and it is your call, not mine.** The two laptop
recorders cannot be monitored from the desktop at all — no shared drive, no
sync folder, no heartbeat, and the coordinator makes no network call by design.
They are registered as `"monitor": "confirmation"`, which tracks how long ago a
**human** last confirmed them and nags after 24 hours. That is not monitoring
and is labelled as not monitoring everywhere it prints.

**The only thing that would make it real:** the laptop writes a heartbeat file
into the repo on a timer and pushes it; the coordinator reads the timestamp out
of the committed file instead of a file's age. Your `runners/` layer is the
natural place for it — it already has a scheduled task running every 10 minutes
on that machine.

**It was deliberately not built**, because it needs git to be able to push from
the laptop (unverified) and adds a commit every few minutes to a public repo.
If you think that trade is worth making, it is a better answer than what is
there now. Reply below either way.

--- REPLY ---

The session that owns `tennis` writes below this line, and changes `Status:`
above to `DONE` or `BLOCKED`. Nothing else needs doing and no script needs
running. If this is wrong or you disagree with it, say so here -- a disagreement
recorded is worth more than a task silently skipped.


# Putting this on the laptop

**About fifteen minutes.** Read the red box first — it is the only thing on this
page that can break something you already have.

---

## ⚠ THE TWO RECORDERS MUST NOT BE DISTURBED

The laptop is running two things that matter more than this project:

| what | writes to |
|---|---|
| `record_depth.py` | `C:\Users\gianf\kalshi\set1_overshoot\data\depth\...` |
| `record_15m_opens_v2.py --hours 168` | `C:\Users\gianf\crypto\data\btc15m_opens\...` |

**They are recording data that cannot be re-pulled at any price.** Kalshi
publishes no historical order-book endpoint; a gap is permanent.

Nothing in this project touches them, and that is enforced rather than promised:

- the runner starts no process and stops no process
- it writes only inside `tennis-paper-forward\`
- `install_task.ps1` creates exactly **one** scheduled task and modifies no
  other task, service or process — run it with `-WhatIf` to watch it not do
  anything else
- `uninstall_task.ps1` stops exactly **one** process: the pid written in this
  project's own lock file, and no other

**What you should still do:** run step 6 before and after, and check the two
recorders are in the process list both times. If they are not in the *before*
list either, they were already down and that is a separate and more urgent
problem.

**Do not run this project on the desktop and the laptop at once.** They would
each build their own separate sample and you would have two half-tests. Pick
one machine. The laptop is the right one, because it stays on.

---

## 1. Copy the folder

Copy `C:\Users\vinig\trading\tennis-paper-forward` to the laptop, anywhere you
like. A sensible place is `C:\Users\gianf\trading\tennis-paper-forward`.

**Do not copy these** — they are large and rebuild themselves:

```
.venv\          the interpreter; rebuilt in step 3
data\sackmann\  ~200 MB of match history, re-downloaded automatically
data\charting\  ~90 MB of point-by-point, re-downloaded automatically
```

**There is no key, no token and no password to copy, because this project has
none.** If you find a `.pem` anywhere inside this folder, something is wrong and
the test suite will refuse to run.

---

## 2. Check Python is there

Open **PowerShell** (Start → type `powershell` → Enter) and run:

```
python --version
```

You should see `Python 3.11` or higher. If you get an error or a Microsoft Store
window, install from python.org and **tick "Add Python to PATH"** on the first
screen. Skipping that tick is the usual reason nothing works afterwards.

---

## 3. Build the environment

In PowerShell, with `<PATH>` replaced by wherever you put the folder:

```
cd <PATH>\tennis-paper-forward
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
```

**What you should see:** a list of packages installed, ending without an error.

---

## 4. Prove it cannot trade

```
.venv\Scripts\python.exe -m pytest tests -q
```

**What you should see:** `52 passed`, or more.

**If anything fails, stop and send me the output.** These tests are the reason
you can leave this running unattended. Among other things they assert that no
file in the package contains an order endpoint, that it refuses to start if
Kalshi credentials are present in the environment, and — by planting a fake
violation — that the detector still bites.

---

## 5. One trial tick, watched

```
.venv\Scripts\python.exe -m src.forward --once
```

**What you should see**, after about a minute (the first run downloads the match
history, so it is the slow one):

```
PAPER ONLY - no credentials, no order endpoint, GET-only allowlist. ...
tick     1  markets  246  matches 123  delib  1968  open   0  closed  0  settled 0/50
```

The numbers will differ. What matters is `markets` and `matches` being non-zero.

---

## 6. Look at what is running, BEFORE you install anything

```
Get-CimInstance Win32_Process -Filter "Name like 'python%'" | Select-Object ProcessId, CommandLine | Format-Table -Wrap
```

**Write down, or screenshot, the two recorder lines.** You are going to compare
against this in step 8.

> **Expect two lines per running program, not one.** A Python virtual
> environment on Windows uses a small launcher that starts the real interpreter,
> so both show up with the same command line. The one doing the work has CPU
> time against it; the launcher sits at zero. This is normal and is not two
> copies running.

---

## 7. Install it as a scheduled task

```
cd <PATH>\tennis-paper-forward\deploy
powershell -ExecutionPolicy Bypass -File .\install_task.ps1
```

It runs the tests again and refuses to install if they fail. Then it prints the
python processes it is *not* touching, registers one task called
**`TennisPaperForward`**, and starts it.

**What you should see at the end:**

```
Installed 'TennisPaperForward'.
TaskName             State
--------             -----
TennisPaperForward   Running
```

The task has two triggers: **at system startup**, so a reboot brings it back,
and **every 10 minutes** as a watchdog. The watchdog is safe because the wrapper
exits immediately when a runner is already alive — so it does nothing at all
except on the morning it finds the runner dead, and then it repairs it.

---

## 8. Check the recorders again

Re-run the command from step 6. **The two recorder lines must still be there,
with the same process ids.** If a process id changed, a recorder restarted and
you have a gap — tell me, and tell me roughly when.

---

## 9. Set the laptop so it cannot sleep

This matters more than anything else on this page. A sleeping laptop records
nothing, and the gap can never be filled.

**Settings → System → Power & battery:**
- **Sleep: Never** — set it for both "On battery power" and "When plugged in"
- **Screen off:** whatever you like, it does not matter

**Control Panel → Power Options → "Choose what closing the lid does":**
- **Lid close action: Do nothing**, for both columns

**Settings → System → Date & time:**
- **Set time automatically: On**

**Settings → Windows Update → Advanced options:**
- Set **active hours** as wide as it lets you, so it cannot reboot mid-run.
  (It would come back anyway — that is what the startup trigger is for — but a
  reboot still costs whatever was happening at that moment.)

---

## 10. The one command, from then on

Double-click:

```
<PATH>\tennis-paper-forward\deploy\check.bat
```

It prints every python process on the machine first — **so the two recorders are
the first thing you see** — then how the forward test is doing, how many matches
have settled out of the fifty, and roughly how many more days that will take.

It is read-only. It cannot start, stop or change anything.

---

## When it reaches fifty matches

The runner stops on its own and says so. Then:

```
cd <PATH>\tennis-paper-forward
.venv\Scripts\python.exe -m src.analyse
```

That writes `reports\results.json` and prints it.

**Read [PREREGISTRATION.md](../PREREGISTRATION.md) §3 before you read the
result.** Fifty matches is enough to measure what it costs to trade this market
and whether the machinery works. It is **not** enough to tell you whether any of
the sixteen bots makes money, and the analysis says so at the top of its own
output rather than letting you draw that conclusion.

---

## If something breaks

| what you see | what it means |
|---|---|
| `a runner is ALREADY RUNNING (pid N)` | the guard working. One runner at a time is correct. |
| `LOCK LOST` in the log, then a clean stop | also the guard working. A second runner started, and the older one stood down rather than share the state file. Nothing is lost. |
| `no interpreter at ...\.venv\Scripts\python.exe` | step 3 did not run, or ran in a different folder |
| `Kalshi credentials are present in this process environment` | this machine has `KALSHI_KEY_ID` set. The paper package refuses to share a process with it. Open a fresh PowerShell, or clear it for that session with `$env:KALSHI_KEY_ID=""`. |
| the tick count stops advancing | run `check.bat`; if the last tick is over ten minutes old it says so in capitals |
| `only N% of markets carry an ask` | Kalshi renamed a price field again. This has happened twice. Stop and tell me — do not let it keep recording nulls. |
| `markets 0` | either the series list is stale or the network is down. The health log distinguishes them. |

---

## ⚠ SUPERSEDED 2026-08-08 — use `runners\LAPTOP_SETUP.md` instead

This page set up **tennis alone**, with its own scheduled task. A second test
would have meant a second near-identical task and a third copy of these
scripts — `mlb-paper/deploy/` was already the second copy.

**[`../../runners/LAPTOP_SETUP.md`](../../runners/LAPTOP_SETUP.md) replaces it.**
One watchdog, one scheduled task, a registry listing every test. Adding the next
one is a single line in `runners/runners.json`.

Nothing here was deleted and the scripts in this folder still work. Keep using
`install_task.ps1` only if you want tennis scheduled **on its own**, separately
from everything else — and do not use both, or two tasks will watch the same
runner. (Harmless, because the runner's own lock refuses the second copy, but
pointless.)

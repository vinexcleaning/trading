# Putting the paper tests on the laptop

**About twenty minutes, once.** After this, adding another test is one line and
no setup at all.

Read the red box first — it is the only thing here that can break something you
already have.

---

## ⚠ THE TWO RECORDERS MUST NOT BE DISTURBED

The laptop is running two things that matter more than every test in this repo
put together:

| what | writes to |
|---|---|
| `record_depth.py` | `C:\Users\gianf\kalshi\set1_overshoot\data\depth\...` |
| `record_15m_opens_v2.py --hours 168` | `C:\Users\gianf\crypto\data\btc15m_opens\...` |

**They are collecting data that cannot be re-pulled at any price.** Kalshi
publishes no historical order-book endpoint, so a gap is permanent.

Nothing here can stop them, and that is enforced rather than promised:

- **the watchdog contains no code that can stop a process at all** — no
  `Stop-Process`, no `taskkill`. A test reads the file and fails the build if
  one ever appears, and plants a real kill to prove the check still works
- it only ever acts on entries in `runners\runners.json`, and the recorders are
  not in it and never will be
- `install.ps1` creates exactly **one** scheduled task and modifies no other
  task, service or process. Run it with `-WhatIf` to watch it not do anything
- `uninstall.ps1` removes that task and **stops nothing**

**Still do this:** run step 5 before and after, and check the two recorders are
in the list both times.

---

## 1. Copy the repo folder

Copy `C:\Users\vinig\trading` to the laptop — or just the folders you need:
`runners\`, `tennis-paper-forward\`, `common\`.

A sensible home is `C:\Users\gianf\trading`.

**Do not copy these** — large, and they rebuild themselves:

```
*\.venv\                            the interpreters, rebuilt in step 3
tennis-paper-forward\data\sackmann\ ~200 MB, re-downloaded automatically
tennis-paper-forward\data\charting\  ~90 MB, re-downloaded automatically
```

**There is no key, no token and no password to copy, because none of this has
any.** If you find a `.pem` inside any of these folders, stop — something is
wrong and the tests will refuse to run.

**Do copy `tennis-paper-forward\data\state.json` and `logs\`** if you want the
209 matches already collected. Leave them behind and it starts from zero, which
is also fine — just slower.

---

## 2. Check Python

Open **PowerShell** (Start → type `powershell` → Enter):

```
python --version
```

Expect `Python 3.11` or higher. If you get an error or the Microsoft Store
opens, install from python.org and **tick "Add Python to PATH"** on the first
screen. Skipping that tick is the usual reason nothing works afterwards.

---

## 3. Build the environment for each test

Once per test. With `<PATH>` replaced by wherever you put the repo:

```
cd <PATH>\tennis-paper-forward
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
```

**What you should see:** packages installing, ending without an error.

---

## 4. Prove it cannot trade

```
.venv\Scripts\python.exe -m pytest tests -q
```

**Expect `70 passed`** or more. **If anything fails, stop and send me the
output.** These tests are the reason this can be left alone: among other things
they assert no file contains an order endpoint, that it refuses to start if
exchange credentials are present, and — by planting a fake violation — that the
detector still bites.

---

## 5. Look at what is running, BEFORE installing anything

```
Get-CimInstance Win32_Process -Filter "Name like 'python%'" | Select-Object ProcessId, CommandLine | Format-Table -Wrap
```

**Screenshot the two recorder lines.** You will compare against this in step 7.

> **Expect two lines per running program, not one.** A Python virtual
> environment on Windows uses a small launcher that starts the real interpreter,
> so both appear with the same command line. The one doing the work has CPU time
> against it; the launcher sits at zero. Normal, not two copies.

---

## 6. Install the watchdog — once, for everything

```
cd <PATH>\runners
powershell -ExecutionPolicy Bypass -File .\install.ps1
```

It runs each enabled test's own suite first and **refuses to install if any
fails**. Then it prints the processes it is *not* touching, registers one task
called **`TradingRunnersWatchdog`**, and starts it.

**Expect to end with:**

```
Installed 'TradingRunnersWatchdog'.
  tennis     ALIVE   pid ...
```

Two triggers: **at system startup**, so a reboot brings everything back, and
**every 10 minutes** as a watchdog. The repeat is cheap — when everything is up
the watchdog does nothing and exits in under a second.

---

## 7. Check the recorders again

Re-run step 5. **The two recorder lines must still be there with the same
process ids.** If a process id changed, a recorder restarted — tell me, and
roughly when.

---

## 8. Stop the laptop sleeping

This matters more than anything else here. A sleeping laptop records nothing and
the gap can never be filled.

**Settings → System → Power & battery**
- **Sleep: Never**, for both "On battery power" and "When plugged in"

**Control Panel → Power Options → "Choose what closing the lid does"**
- **Lid close action: Do nothing**, both columns

**Settings → System → Date & time**
- **Set time automatically: On**

**Settings → Windows Update → Advanced options**
- Set **active hours** as wide as it allows, so it cannot reboot mid-run.
  (It would come back — that is what the startup trigger is for — but a reboot
  still costs whatever was in flight.)

---

## 9. From then on, one command

Double-click:

```
<PATH>\runners\check.bat
```

Recorders first, then every test. Read-only — it cannot start, stop or change
anything.

---

## Adding the next test later

**One line.** Open `runners\runners.json`, find the entry, change
`"enabled": false` to `"enabled": true`. The watchdog picks it up within ten
minutes.

For a test not yet listed, copy an existing block and change four fields — see
[README.md](README.md). Then re-run `install.ps1` once, purely so its test suite
gets checked before it is scheduled. **There is still only one task.**

---

## If something breaks

| what you see | what it means |
|---|---|
| `WATCHDOG   NOT INSTALLED` on the status page | step 6 did not run, or was run from the wrong folder |
| `a runner is ALREADY RUNNING (pid N)` | the guard working. One copy at a time is correct |
| `LOCK LOST` in a runner log, then a clean stop | also the guard working — a second copy started and the older one stood down rather than share a state file |
| `NO INTERPRETER at .venv\Scripts\python.exe` | step 3 was not run for that test, or ran in the wrong folder |
| `two enabled runners share the same match string` | give one of them a `match` that is unique. See README |
| `NOTHING IS RUNNING` at the top of the status page | **check the recorders first.** That is the urgent half of that message |
| tick count stops advancing | the status page says so in capitals if the last tick is over ten minutes old |
| `only N% of markets carry an ask` | Kalshi renamed a price field again — has happened twice. Stop and tell me; do not let it keep recording nulls |

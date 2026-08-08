# runners/ — one watchdog for every paper test on this machine

**Adding a test is one entry in [`runners.json`](runners.json). Nothing else
changes** — not this watchdog, not the scheduled task, not the status page.

---

## The one command

```
runners\check.bat
```

Prints every python process first (so the **recorders** are the first thing you
see), then each registered test in its own words, then whether the watchdog is
installed. Read-only.

---

## Adding a second test — the whole procedure

Say `mlb-paper` is ready. **Open [`runners.json`](runners.json) and change one
word:** `"enabled": false` → `"enabled": true`.

That is it. No new scheduled task, no new script, no reinstall. The watchdog
picks it up on its next run, within ten minutes.

For a test that is *not* already listed, add a block like this:

```json
{
  "name":  "devig",
  "enabled": true,
  "dir":   "devig-paper",
  "exe":   ".venv\\Scripts\\python.exe",
  "args":  ["-m", "src.forward", "--poll", "60"],
  "match": "src.forward",
  "verify":["-m", "pytest", "tests", "-q"],
  "log":   "logs\\wrapper.log"
}
```

| field | what it means |
|---|---|
| `dir` | folder, relative to the repo root |
| `exe` | interpreter, relative to `dir` |
| `match` | a substring of the command line that identifies **this** runner in the process list. **Must be unique** — see below |
| `verify` | run before installing; if it exits non-zero the install is refused |

Then re-run `install.ps1` **once** — only so `verify` gets a chance to prove the
new test is safe. It still registers exactly one task.

> **`match` must be unique across enabled entries.** Two tests both matching
> `src.forward` would make liveness ambiguous: the watchdog would see one
> running, conclude both were, and never start the second — silently. Both
> `install.ps1` and `tests/test_runners.py` refuse a registry where that is
> true. If two projects genuinely share a module name, `match` on something
> that differs, e.g. `--target` or the folder name.

---

## Why it is safe to run this every ten minutes, unattended, beside the recorders

**The watchdog contains no code that can stop a process.** No `Stop-Process`,
no `taskkill`, no `.Kill(`. `tests/test_runners.py` reads the file with comments
stripped and fails the build if one appears — and plants a real kill to prove
the detector still bites.

That is the entire safety argument, and it is why the watchdog is allowed to be
stupid: **the smart half lives in each runner.** Every test already holds its own
single-instance lock and refuses to start twice. So the worst case if the
watchdog is wrong about liveness is a process that starts, sees the lock, says
"already running" and exits. Nothing is ever stopped, and nothing outside the
registry is ever touched.

It also strips exchange credentials out of the environment before starting
anything, so a paper test cannot inherit a live key from the machine.

---

## The files

| file | what it does |
|---|---|
| `runners.json` | **the registry.** The only file you edit |
| `watchdog.ps1` | starts anything registered that is not running. Never stops anything |
| `status.ps1` | one page across every runner. Read-only |
| `install.ps1` | registers **one** scheduled task — at startup, and every 10 minutes |
| `uninstall.ps1` | removes that task. **Stops nothing** |
| `check.bat` | double-clickable `status.ps1` |
| `tests/` | the guards above |

## What this replaced

`tennis-paper-forward/deploy/` and `mlb-paper/deploy/` each shipped their own
`install_task.ps1`, `run_*.bat` and `check.bat` — two near-identical copies of
the same three scripts, and a third would have been a third copy. Each project's
own scripts still work and were not touched; this is the layer that means the
**fourth** test costs one line instead of a rebuild.

The per-project scripts remain the right tool for one thing: stopping a single
test, because they know their own lock file and stop only their own process id.
This layer deliberately cannot.

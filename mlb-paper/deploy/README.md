# Putting this on the laptop — click by click

Everything here is **paper only**. There is no key, no password, no order
endpoint and no money anywhere in this package. A test walks every file and
fails the build if any of that appears.

You need to do this **once**. After that it runs by itself and survives a
reboot.

---

## Before you start

You need the `trading` repo on the laptop, up to date:

```bash
cd C:\Users\gianf\trading && git pull
```

You should see a folder called `mlb-paper` inside it. If you do not, the pull
did not work — send me what `git pull` printed.

---

## Step 1 — set it up

1. Open **File Explorer** and go to the folder
   `C:\Users\gianf\trading\mlb-paper\deploy`
2. Double-click **`setup.bat`**
3. A black window opens and prints five numbered steps.
4. **What you should see at the end:** the line `SETUP OK.`
   If instead you see `SETUP FAILED`, take a photo of the window and send it —
   do not carry on.

This creates the project's own Python environment, installs two small packages,
checks every website's `robots.txt` to confirm we are allowed to read it, and
runs the tests. It does not start anything.

---

## Step 2 — make it run by itself

1. Still in `C:\Users\gianf\trading\mlb-paper\deploy`
2. **Right-click** the file **`install_task.ps1`**
3. Choose **"Run with PowerShell"** from the menu
4. If Windows asks *"Do you want to allow this app to make changes?"*, click
   **"Yes"**.
5. **What you should see:** a few lines ending with a small table showing
   `TaskName: mlb-paper` and `State: Running`.

That registers it with Windows so it starts again on its own after a reboot,
and restarts itself every five minutes if it ever stops.

> **If PowerShell refuses with a message about "execution policy"**, open
> PowerShell and run this one line first, then repeat step 2:
>
> ```bash
> Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
> ```

---

## Step 3 — the one command that tells you how it is going

Double-click **`check.bat`** in the same folder. Or from any prompt:

```bash
C:\Users\gianf\trading\mlb-paper\deploy\check.bat
```

The **first line** is the one that matters:

| first line says | meaning |
|---|---|
| `ALIVE` | it ticked in the last 20 minutes. Nothing to do. |
| `*** STALE ***` | it has not ticked in 20 minutes. Something is wrong — send me the output. |

Below that: what each of the sixteen bots has done, why bots decided not to
trade, the health of the market feed for the last twelve ticks, and the
closing-line-value table, which is the number this whole test is actually
about.

For a four-line version that fits on a phone:

```bash
C:\Users\gianf\trading\mlb-paper\deploy\check.bat --brief
```

---

## What to send me, and when

Nothing routinely. Only these three:

1. `check.bat` says **`*** STALE ***`** twice in a row, an hour apart.
2. `setup.bat` printed **`SETUP FAILED`**.
3. Any line in the output that starts with **`!! STRUCTURAL:`** — that means the
   market quoted something arithmetically impossible and I want to see it.

---

## Turning it off

```bash
powershell -File C:\Users\gianf\trading\mlb-paper\deploy\install_task.ps1 -Uninstall
```

Nothing is lost. Every decision, every price and every reason is already on
disk in `mlb-paper\data\paper.db`, and the folder `mlb-paper\data\briefs\`
holds the exact evidence each bot was looking at when it decided.

---

## Two things it deliberately does NOT do

- **It does not touch the two recorders already running on this laptop.** It
  writes only inside `mlb-paper\`, and it takes its own lock so it cannot start
  twice.
- **It cannot place an order.** Not "is configured not to" — there is no code
  in it that could. That is checked by a test that is itself checked against a
  deliberately planted violation, because a guard nobody has tested is a guard
  nobody knows still works.

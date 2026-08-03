# Moving the bot to the laptop

About twenty minutes. Read the red box first — it is the only thing here that
can actually cost you money.

---

## ⚠ NEVER RUN THE BOT ON BOTH MACHINES AT ONCE

This is the single biggest risk in the whole migration, and nothing in the
code can stop you doing it. The two machines cannot see each other.

If the bot runs on the PC and the laptop at the same time:

* **Both place orders.** Two bots see the same qualifying trade and each buys
  it. You get double the position you sized for.
* **Both fire stops.** Each sells the full position. The second sell has
  nothing left to sell, so it opens a **SHORT** — a bet against the player,
  which loses when he wins.
* **They disagree about reality.** `bot_state.json` is per-machine. Each one
  thinks it owns positions the other is managing.

The take-profit orders rest on Kalshi and are shared, so both machines will
also fight over cancelling them.

**Rule: exactly one machine runs `gui.py` at any moment.** Close it on the PC
before you start it on the laptop. Watch mode (`--watch`) is now genuinely
read-only and cannot place, cancel or sell, so that one IS safe to leave open
on the PC if you just want to look.

The recorder is different — it only reads. Running it on both is harmless
except that you'd get duplicate rows in two separate files, which is fine
because they're separate files.

---

## 1. Copy the folder

Copy the whole `kalshi` folder to the laptop.

**`kalshi_private_key.pem` needs care.** That key can place orders on your
account. USB stick, not email, not a public cloud folder. Or create a fresh
key on Kalshi from the laptop and use that instead.

Copy `bot_state.json` too if you have open positions — it carries the stops.
If you don't copy it, the bot will adopt any positions it finds anyway and
set fresh stops, so it isn't fatal either way.

Safe to skip (large, rebuildable):

```
backtest/data/      ~115 MB of candles, re-pullable any time
__pycache__/        regenerated automatically
.recorder.lock      must NOT be copied - delete it if it comes across
```

Keep `backtest/BACKTEST_RESULTS.md` — that's the findings, not the data.

---

## 2. Install Python

python.org → download → run it. **Tick "Add Python to PATH"** on the first
screen. Skipping that is the usual reason nothing works afterwards.

---

## 3. Install the three libraries

```
pip install -r requirements.txt
```

`requests`, `cryptography`, `curl_cffi`. The last one is what makes the free
Sofascore feed work.

---

## 4. Set the two environment variables

```
setx KALSHI_KEY_ID your-key-id-here
setx KALSHI_KEY_PATH C:\path\to\kalshi_private_key.pem
```

`setx` writes them permanently. **Close and reopen Command Prompt afterwards**
— it only affects windows opened after it runs.

No `APIFY_TOKEN`. Scores are free now.

---

## 5. Configure the laptop for 24/7

This matters more than anything else on the laptop, because **stops are
app-side**. Take-profits rest on Kalshi and survive anything; stops only
exist while the window is open. If the laptop sleeps, your losers are
unprotected while your winners stay protected — exactly backwards.

**Settings → System → Power & battery:**
* Screen off: whatever you like
* **Sleep: Never** (both on battery and plugged in)
* **Lid close action: Do nothing** (Control Panel → Power Options → Choose
  what closing the lid does)

**Settings → System → Date & time:**
* **Set time automatically: On**

Request signing includes a timestamp and Kalshi rejects it if your clock has
drifted. That's the `401 header timestamp expired` that silently killed a
trade on 27 Jul. Laptops that sleep drift more than desktops.

**Settings → Windows Update → Advanced:**
* Set **active hours** to cover the whole day, so it can't reboot mid-session.

---

## 6. Check it works, in this order

```
python sofascore_feed.py --debug
```
Lists live matches with sets, games, points and who's serving. Needs no
credentials at all — if this works, the feed half is confirmed.

```
python -c "from kalshi_client import KalshiClient; c=KalshiClient(demo=False); print('auth:', c.authenticated); print('balance:', c.balance())"
```
Should print `auth: True` and your balance. If `auth: False`, step 4 didn't
take — reopen Command Prompt.

Then, **with the PC bot closed**:

```
run_both.bat
```

Watch the log for `ADOPTED UNWATCHED POSITION` lines if you have positions
that arrived without stops. If you see them, it's working.

---

## 7. Checking profit from your PC

You do not need to touch the laptop to see how you're doing.

**Easiest — kalshi.com.** Log in from your PC or phone. Positions, P&L,
resting orders, everything. It's the exchange's own record, which is more
authoritative than anything the bot would report. Zero setup.

**If you want to see the bot itself** — Windows Remote Desktop. On the
laptop: Settings → System → Remote Desktop → On. On the PC: Start → "Remote
Desktop Connection" → enter the laptop's name. You get the laptop's screen,
log and position table. Both machines must be on the same network.

**Watch mode on the PC** is also safe now — `python gui.py --watch` shows
live scanning and cannot place, cancel or sell anything. Useful if you want a
second screen of what the bot is seeing without any risk. It will NOT show
the laptop's positions or stops, only the market view.

---

## If something breaks

| Symptom | Cause |
|---|---|
| `ModuleNotFoundError: curl_cffi` | step 3 didn't run, or ran against a different Python |
| `auth: False` | env vars not set, or Command Prompt not reopened |
| `401 header timestamp expired` | clock drift — turn on automatic time sync |
| `A recorder is ALREADY RUNNING` | one is already going; that's the guard working |
| Recorder won't start after a crash | delete `.recorder.lock` |
| Feed empty at 3am | check `--debug`; may genuinely be no live matches |

---

## What protects you while you're asleep

**Survives everything** (they live on Kalshi's servers):
* take-profit sells at 95c
* the 15%-of-bankroll daily loss limit, once it trips in a session

**Dies if the app closes** (they run inside this program):
* stop losses
* the 25-minute time stop
* the 60-second unfilled-buy cancel

That asymmetry is why the power settings above matter. It is also why, if the
laptop does die overnight, the first thing to check in the morning is whether
any position is sitting below its stop.

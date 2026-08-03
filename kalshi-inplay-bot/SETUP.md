# Setup — read this first

Three files. You don't need to understand the code, but you do need to
get it running. Takes about 15 minutes, once.

---

## 1. Install Python

**Windows:** go to python.org, download Python, run it. On the first
screen tick **"Add Python to PATH"** — this matters, don't skip it.

Then open Command Prompt (Windows key, type `cmd`, Enter) and paste:

```
pip install requests cryptography
```

---

## 2. Get your Kalshi API keys

On Kalshi: **Settings → API Keys → Create New Key**

Pick **"read and write"** permission. Read-only can't place orders.

Kalshi gives you two things:
- A **Key ID** — looks like `a952bcbe-ec3b-4b5b-b8f9-11dae589608c`
- A **private key file** — downloads automatically

**The private key is shown once and never again.** Save it. Put it in the
same folder as these three files and name it `kalshi_private_key.pem`.

Watch out: some editors quietly add `.txt` to the filename when you save.
If the file ends up as `kalshi_private_key.pem.txt`, rename it.

---

## 3. Tell the program where your keys are

In Command Prompt, in the folder with the files:

```
set KALSHI_KEY_ID=paste-your-key-id-here
set KALSHI_KEY_PATH=kalshi_private_key.pem
```

You have to do this each time you open a new Command Prompt window.

---

## 3b. (Optional) Live score feed instead of typing scores in

By default you type the set score in yourself when you `[a]dd` or `[u]pdate`
a match. If you'd rather it pull the score automatically:

1. Free account at [apify.com](https://apify.com) -> Settings -> Integrations
   -> copy your API token.
2. `set APIFY_TOKEN=your-token-here` (same Command Prompt window as step 3).
3. Check it actually works before trusting it:
   ```
   python live_score.py --debug
   python live_score.py --find "Alcaraz"
   ```

With the token set, `[a]dd`/quick-add will ask for the player's name to
look up. Leave it blank to keep typing scores by hand for that match.

The scanner still shows you the score and its age on every confirm card
before it lets you place an order — it never trades on a score you
haven't seen. If a lookup ever looks wrong, `[u]pdate` and choose
`[x] switch to manual only` for that match, and paste me
`python live_score.py --debug` output so I can fix the parsing.

---

## 4. Run it — demo first

```
python scanner.py
```

This connects to **Kalshi's demo environment** — fake money, real prices.
Nothing you do here can cost you anything. Use it until the whole thing
feels obvious.

**Important:** demo needs its own separate API key, created inside the
demo site, not your real one.

---

## 5. How to use it

```
[a] add      — pick a live match, tell it who was the pre-match
               favorite and the current set score
[u] update   — change the set score as the match moves on
[s] scan     — watch continuously, every 20 seconds
[q] quit
```

When a match passes your rules, it stops and shows you a card:

```
Shibahara — vs Dong
TAKE IT
setup: price overshot the score

  [+] A set has resolved.
  [+] 60c and ahead on sets — divergence intact.
  [+] Spread 2c.

  buy               9 @ 60c   ($5.56)
  resting sell      94c   <- place this immediately
  exit if it hits   36c   — manual, Kalshi has no stops

  win rate needed, exit  46%
  win rate needed, hold  66%

  [c] place both orders   [s] skip   [r] remove
```

Press **c** and it places the buy and the resting sell together. Then it
goes back to watching. That's the whole job.

---

## 6. When you're ready for real money

```
python scanner.py --live --bankroll 115 --stake-pct 5
```

It asks you to type `LIVE` first, on purpose.

Start at 5%. Change it in the command, not in the code.

---

## Moving to another computer (laptop)

Nothing is tied to a specific machine. On the new one:

1. Install Python from python.org — tick **"Add Python to PATH"**.
2. Copy the whole `kalshi` folder over (USB, OneDrive, whatever). It
   contains everything including your `.pem` key. That file is a
   credential — treat it like a password, don't email it or put it
   anywhere public.
3. In Command Prompt, in that folder:
   ```
   pip install requests cryptography
   ```
4. Set the three variables **every time you open a new window**:
   ```
   set KALSHI_KEY_ID=your-key-id
   set KALSHI_KEY_PATH=kalshi_private_key.pem
   set APIFY_TOKEN=your-apify-token
   ```
   Tired of retyping? Make a file called `run.bat` in the folder with
   those three `set` lines followed by `python gui.py --watch`, then just
   double-click it.
5. Check it before trading real money:
   ```
   python gui.py --watch
   ```
   Balance should show a number, not "no API key".

**Don't run it on both machines at once.** Both would watch the same
positions and could each fire the same stop, selling twice.

`bot_state.json` holds the stops for open positions. If you're mid-trade
when you switch, copy that file too — otherwise the new machine won't
know to watch them.

---

## What it will not do

**It can't set a stop loss.** Kalshi has no stop orders for event
contracts — a sell limit below the current price fills instantly instead
of waiting. So the exit price on the card is yours to take manually. That
is a real limitation of the exchange, not of this program.

**It doesn't know the score.** You type that in. Kalshi's own app updates
in seconds and is the fastest thing you have; the tennis skill lags 30-60
seconds and is only good for the pre-match favorite, which doesn't change.

**It won't trade while you're away.** Every order needs your `c`.

---

## Changing the rules

Open `tennis_engine.py`. Everything adjustable is in the first 30 lines,
in the block marked `class Config`. Plain English names:

```python
max_favorite_price   = 85    # skip favorites above this
max_divergence_price = 70    # skip divergence buys above this
favorite_exit_drop   = 15    # cents below entry before you get out
max_open_positions   = 3
max_daily_loss_pct   = 15
```

Change a number, save, run again. Nothing else breaks.

If something goes wrong, copy the error message and paste it to me.
That's what I'm for.

# Moving the baseball desk to the laptop

About twenty minutes. **Read the red box first — it is the only part of this
that can actually cost you money.**

This is the baseball desk (`livedesk`). The tennis bot has its own version of
this document at `kalshi-inplay-bot/MOVING_TO_LAPTOP.md`; they are separate
programs and moving one does not move the other.

---

## ⚠ NEVER RUN IT ON BOTH COMPUTERS AT ONCE

If the desk runs on the desktop and the laptop at the same time:

* **Both place the same bet.** Two copies see the same pick and each buys it.
  You end up with double the position you meant, at double the risk.
* **Both act on the same position.** Each thinks it owns what the other is
  managing.
* **Neither can see the other.** The two computers have no way to talk.

**There is now a guard for this, and you should still not rely on it.** When you
open the desk it checks whether the other machine is running one, and refuses
with a message naming the computer. But it can only check if the laptop has
internet at that moment, and if it cannot check, **it starts anyway and says so
in the message** — because a desk that refuses to open every time the Wi-Fi
hiccups is a desk you would stop using.

**The rule is still yours: close it on one computer before opening it on the
other.** The guard is a safety net, not a permission slip.

---

## Before you start — what only you can do

**The key file is the one thing we cannot move for you.** It is the file that
lets the program place bets on your account, so it never travels through us,
through a chat, or through email.

On the desktop it currently lives here:

```
C:\Users\vinig\trading\kalshi-keys\MLB Bot 2.pem
```

**Two options, and the second is better.**

* **Copy it on a USB stick.** Not email, not a public cloud folder.
* **Or make a new key on the laptop** and leave the desktop one alone. This is
  the better option: two keys means you can delete one later without touching
  the other, and nothing has to travel. Step 5 covers it.

---

## 1. Copy the folder

Copy the whole `trading` folder from the desktop to the laptop, or on the
laptop open a Command Prompt and type:

```
git clone https://github.com/vinexcleaning/trading.git C:\Users\vinig\trading
```

**What you should see:** a lot of lines ending with `done.`, and then a
`C:\Users\vinig\trading` folder on the laptop.

**Do not copy these** — they are per-computer and copying them causes exactly
the confusion this document is about:

```
livedesk\data\desk.lock          who currently has the desk open
livedesk\kalshi_env.bat          points at the key file, and the path differs
__pycache__\                     rebuilt automatically
```

**Do copy `livedesk\data\ledger.json`** if you have bets running. That is the
record of your money. Without it the laptop starts from a blank sheet and will
not know about positions you already hold.

---

## 2. Put Python on the laptop

If the laptop already runs the recorders, it has Python and you can skip this.

To check, open Command Prompt and type:

```
py -3 --version
```

**What you should see:** something like `Python 3.12.4`.

**If you instead see** `'py' is not recognized`, install Python from
<https://www.python.org/downloads/> and **tick "Add python.exe to PATH"** on the
first screen of the installer.

---

## 3. Install what it needs

```
py -3 -m pip install requests cryptography
```

**What you should see:** `Successfully installed ...`, or
`Requirement already satisfied`. Either is fine.

---

## 4. Put the key file somewhere

Make the folder:

```
mkdir C:\Users\vinig\trading\kalshi-keys
```

Then put your `.pem` file in it — either the one from the USB stick, or the new
one from step 5.

---

## 5. Making a NEW key instead (recommended)

1. Go to **<https://kalshi.com/account/profile>** and sign in.
2. Find the section about **API keys**. Kalshi moves this around, so if it is
   not where you expect, look for anything named "API", "Developer" or
   "Programmatic access" — that is the one.
3. Create a new key. Name it something you will recognise later, e.g.
   `MLB Laptop`.
4. **Kalshi shows you the private key file exactly once and never again.**
   Download it, and move it into `C:\Users\vinig\trading\kalshi-keys\`.
5. **Copy the Key ID as well** — the long code with dashes in it, like
   `950b93d7-d7c1-4128-b487-1d03dc4406e9`. You need both halves.

---

## 6. Tell the desk about the key

On the **laptop**, in Command Prompt, type this exactly:

```
py -3 C:\Users\vinig\trading\livedesk\tools\set_key.py
```

It asks you two things:

1. **Paste the Key ID** and press Enter.
2. **Drag the `.pem` file into the window** (or paste its full path) and press
   Enter.

**What you should see:**

```
  Saved to kalshi_env.bat. That file is gitignored.

  3. Checking it against Kalshi (reading your balance only)...

  OK   IT WORKS. Your Kalshi balance reads $56.23.
```

**If instead it says `XX IT DID NOT WORK`**, the two halves are from different
keys, or you downloaded the wrong file. Nothing is broken — run it again with
the right pair. It only ever reads your balance; it cannot place anything.

---

## 7. Turn on the phone alerts

The desktop already has these; the laptop needs telling separately.

```
setx KALSHI_NTFY_TOPIC your-topic-name-here
```

Use **the same topic name as the desktop** — it is in the ntfy app on your
phone, under the subscription you already have. Then **close and reopen Command
Prompt** (`setx` only affects new windows).

Test it:

```
py -3 C:\Users\vinig\trading\livedesk\src\alerts.py --test
```

**What you should see:** the message printed on screen, then `sent to your
phone.` — and the message arriving on your phone within a few seconds.

---

## 8. ⚠ The part that catches the laptop dying — do not skip this

**Your phone alerts cannot tell you the desk has stopped.** A crashed program
and a laptop that has lost power both send exactly nothing, and on your phone
that looks identical to a quiet day with no bets. **This is the whole reason
you asked for alerts, and it is the one thing the phone app cannot do.**

So a second free service watches from outside:

1. Go to **<https://healthchecks.io/>** and sign up. Free, no card.
2. Create a check. Set its **period to 1 hour**.
3. Copy the **ping URL** it gives you. It looks like
   `https://hc-ping.com/` followed by a long code.
4. On the laptop:

```
setx KALSHI_HEALTHCHECK_URL https://hc-ping.com/paste-your-code-here
```

5. Close and reopen Command Prompt.

**What you should see:** run `py -3 C:\Users\vinig\trading\livedesk\src\alerts.py`
and the first line now ends with `death-watch on` instead of
`NOTHING WATCHES FOR THIS DYING`.

**What it does:** the desk pings that URL every minute. If the pings stop for an
hour, healthchecks.io emails you. That is the only thing in this whole setup
that can tell you the laptop is off, because nothing running on the laptop can
report that the laptop is off.

---

## 9. Close the desk on the desktop, then open it on the laptop

**On the desktop:** close the desk window. Fully — not minimised.

**On the laptop:**

```
C:\Users\vinig\trading\livedesk\run.bat
```

**What you should see:** the window opens, and within a minute the top line
shows your balance and today's bets.

**If instead a box appears saying "Baseball desk is already running"**, the
guard has done its job — the desktop copy is still open. Close it there and try
again.

---

## 10. What you get each evening

At **22:00** the laptop sends this to your phone, **every day, including days
when nothing was bet**:

```
  Baseball desk - 19 Aug
  5 bets placed today
  up $12.40 for the day (3 won, 2 lost)
  that is $108 back for every $100 staked
  3 still running, $14.80 riding on them
```

**A day with no bets still sends a message** saying so. That is deliberate and
it is the point of the whole arrangement:

> **If a night goes by and you get nothing at all, something is wrong.**

Before this, silence meant either "no bets qualified" or "the laptop is off"
and there was no way to tell. Now silence means one thing.

---

## About the recorders already on the laptop

The laptop runs the two Kalshi recorders. **The desk does not fight them.** They
read the public market feed, which has no key attached; the desk reads your
account with your key. Those are counted separately by Kalshi, and the desk
makes two reads a minute, which is a rounding error against the recorders'
traffic.

**One thing to watch:** if you made a new key in step 5, the recorders keep
using the old one. Do not delete the old key on Kalshi until you have checked
they are still writing files.

---

## If something goes wrong

**"Baseball desk is already running on ..."** — the other computer has it open.
Close it there. If you are sure it is closed, wait five minutes; the claim
expires on its own.

**"COULD NOT CHECK the other computer"** — the laptop had no internet at the
moment it started. It opens anyway. **Make sure yourself that the desktop copy
is closed.**

**The window opens but nothing appears for a few minutes** — normal. It reads
Kalshi once a minute and there may be no games yet.

**No daily message arrived** — that is the alarm working. Check the laptop is on
and the desk window is open.

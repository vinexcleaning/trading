# Turning on practice orders

**This is optional.** The window works exactly as it does now without it. What
this adds is a button that sends the bet to **Kalshi's practice site** — fake
money, real machinery — so the whole thing gets exercised end to end before any
real dollar is ever involved.

**Nothing here can touch your real account.** The practice site is a completely
separate account with its own login and its own play money.

---

## ⚠ Read this first — I could not check the Kalshi pages myself

Kalshi's website builds itself in the browser, and every tool I have came back
with a blank page. **So the steps below name what you are looking for rather
than promising exactly what the button says.** If something does not match,
that is expected — tell me what you actually see and I will correct this file
rather than guess a second time.

**What I did verify**, from the code that already talks to Kalshi and from the
API itself:

- the practice API lives at **`external-api.demo.kalshi.co`** — this is the
  only host the window will ever send an order to, checked before every single
  one
- it needs **two things**: a key ID, and a key file

---

## Step 1 — Make a practice account

1. Go to **https://demo.kalshi.co**
2. Sign up. **Use a different password from your real Kalshi account.**
3. You should land on something that looks like Kalshi but with play money in
   it — usually a large fake balance.

**If that address does not work**, search Kalshi's own help pages for "demo" or
"sandbox" and tell me where it sends you.

---

## Step 2 — Create an API key on the PRACTICE site

1. Still on **demo.kalshi.co**, and signed in there, open your **account
   settings**.
2. Find the section about **API keys**. It may be called "API", "API Keys",
   "Developer", or live under a security or profile page.
3. Choose to **create a new key**.
4. You will get **two** things:
   - a **key ID** — a long string with dashes, something like
     `a1b2c3d4-0000-0000-0000-abcdef123456`
   - a **private key file** — it downloads, and its name usually ends in
     **`.pem`** or **`.key`**

**⚠ The file downloads once and cannot be downloaded again.** If you lose it,
delete the key on the site and make a new one. That is fine — it is a practice
account.

**Make sure you are on demo.kalshi.co and not kalshi.com when you do this.** A
key made on the real site is a real key. The window would refuse to use it —
it checks the address before every order — but there is no reason to have one
sitting around.

---

## Step 3 — Put the key file somewhere OUTSIDE this project

**Not in the trading folder.** That folder is public on the internet.

Make a folder just for it:

```bash
mkdir "%USERPROFILE%\kalshi-keys"
```

Then move the downloaded file into `C:\Users\vinig\kalshi-keys\`. Rename it to
something you will recognise, for example `demo-key.pem`.

---

## Step 4 — Tell the window where it is

Two settings. Paste these into PowerShell, **with your own key ID** in the
first one:

```bash
setx KALSHI_KEY_ID "paste-your-key-id-here"
```

```bash
setx KALSHI_KEY_PATH "%USERPROFILE%\kalshi-keys\demo-key.pem"
```

**Then close that window and open a new one** — `setx` only affects windows
opened afterwards. This catches everybody.

---

## Step 5 — Check it took

```bash
livedesk\run.bat
```

Click **COPY & OPEN KALSHI** on a bet, and look at the bottom of the card:

- **"practice = fake money"** and the *practice order* button is clickable →
  it worked.
- **"practice not set up"** and the button is greyed out → the window will say
  which of the two settings is missing in the message bar. Most often it is
  step 4 not being reloaded in a new window.

---

## What happens when you press *practice order*

1. **Every guard runs first** — the same ones as a real bet. If the window is
   stopped, or your balance does not reconcile, or you are over the daily
   limits, **nothing is sent**.
2. It checks the address it is about to call really is the practice one.
3. It sends the order.
4. **It reads the order back** and records what actually happened — filled,
   part filled, still sitting on the book, rejected, or **unknown**.

**"Unknown" is a real answer and the window will say so.** It never assumes a
bet went on just because the request did not error. That is the exact mistake
that put a bet in your ledger that never happened.

---

## ⚠ One thing that will stop it, and it is not your fault

The shared Kalshi code has its own off switch: a file called
**`TRADING_DISABLED`** in the `kalshi-inplay-bot` folder. It was put there on
3 August when you stopped running the tennis bot, and **while it exists, that
code refuses to send anything at all** — practice included.

**Do not delete it to make this work.** That file is what is keeping the tennis
bot from placing REAL orders. If practice orders are blocked by it, the window
will tell you so in plain words, and the right fix is a separate switch rather
than removing that one. Tell me and I will sort it properly.

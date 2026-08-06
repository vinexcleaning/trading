# The ITF question — what I did, and the one part only you can do

**The question.** A previous session closed the ITF tennis thread on the finding
that **no free ITF data source exists**. ITF is about **76% of Kalshi's tennis
book**, so if that premise is wrong, the thread was closed for the wrong reason.
`livetennisapi.com` advertises ITF and has a free tier. Whether the **free** tier
actually returns ITF is the open question.

**Read this before acting on it.** Even a clean PASS reopens **data availability
only**. This project already measured ITF as the **worst-performing tier of any**
— −9.13c per trade, t = −26, on 6,135 trades (ledger `B009`). A free ITF feed
does not make the trade work. It removes an excuse, not an obstacle.

---

## What I established without an account

I probed the API directly. Read-only, unauthenticated, GET only.

| request | result | what it means |
|---|---|---|
| `/api/public/v1/health` | **200** `{"status":"ok","version":"v1"}` | the service is up, no key needed |
| `/api/public/v1/matches?status=live` | **401** `{"error":"unauthorized"}` | **the route exists** and only wants a key |
| `/api/public/v1/tournaments` | **401** | same |
| `/api/public/v1/players` | **401** | same |
| `/api/public/v1/fixtures` | **401** | same |
| `/api/public/v1/usage` | **401** | same |
| `/api/public/v1/`, `/docs`, `/openapi.json` | **404** | no public schema |

**401 rather than 404 is the useful part** — it means those endpoint paths are
correct, so the test script is written against verified routes, not guesses.

**What the site actually says, quoted rather than paraphrased.** ITF appears
three times: in the hero blurb, in the FAQ (*"Which tours and formats are
covered? ATP, WTA, Challenger and ITF — both singles and doubles — from one
arbitrated feed"*), and in the historical-tape description. The Free tier card
says: *"For trying the API and hobby dashboards: live scores & current matches,
players, fixtures and your usage. 30 req/min · 1,000/day. Market odds, model
win-probability and the WebSocket feed are on the paid plans."*

> **The honest reading.** The free tier's stated limits are **capability-based**
> (no odds, no model, no WebSocket) and **rate-based** — **no tour restriction is
> stated anywhere**. That makes free ITF plausible. But the site never says the
> free tier includes ITF either, so it stays an **inference**, and the vendor
> wrote every word of it. That is why it needs measuring rather than believing.

---

## What you need to do — about two minutes

I do not create accounts, so this part is yours.

1. Open **https://livetennisapi.com/subscribe/free** in your browser.
2. You should see a short sign-up form with a single field labelled
   **"Your email"**. If you see a pricing table with four columns instead
   (Free / BASIC / PRO / ULTRA), click the button **"Get a free key — no card"**
   near the top of the page first.
3. Type your email address into the **"Your email"** field.
4. Click the button labelled **"Get my key"**.
5. You are looking for an API key beginning with **`twjp_`**. **I could not
   confirm whether it appears on the screen or arrives by email** — the page did
   not say, and I would rather tell you that than send you to a screen that may
   not exist. Check the page first; if there is no key there, check your inbox.
6. Copy the whole key, including the `twjp_` prefix.
7. Paste it into a message to me — or, if you would rather I never see it, run
   step 8 yourself and paste me only the output.

**No password and no card are required.** If either is asked for, stop and tell
me what you are seeing — that would mean the page changed and my instructions
are stale.

---

## Step 8 — the test

Open PowerShell in `C:\Users\vinig\trading\bot-forensics` and run these two
lines, putting your real key in the first one:

```bash
$env:LIVETENNIS_API_KEY="twjp_your_key_here"
.venv\Scripts\python.exe src\t5_itf_probe.py
```

It makes **6 requests** against a 1,000/day budget. It prints one of three
verdicts — `PASS`, `FAIL`, or `INCONCLUSIVE` — and writes `out/t5_itf_probe.json`.

**Send me whatever it prints.** The key is never printed, never written to the
JSON, and never committed — the script reports only its length and the `twjp_`
prefix, so a screenshot is safe to share.

If it says **INCONCLUSIVE**, that just means no tennis was being played at that
moment. Re-run it during European or American daytime.

---

## What each verdict changes

| verdict | what it means | what changes |
|---|---|---|
| **PASS** | the free tier returns ITF | the prior session's "no free ITF source" is **false**. Ledger `B016` moves **UNVERIFIED → SETTLED** |
| **FAIL** | records come back, none of them ITF | the free tier is tour-restricted after all. `B016` stays UNVERIFIED, thread stays closed |
| **INCONCLUSIVE** | key works, no matches in progress | nothing yet — re-run later |

**In none of the three cases does the bot come back on.** `TRADING_DISABLED`
stays where it is. This settles a data question that has been sitting open, so
that it is not still open the next time someone asks.

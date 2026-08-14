To: devig
From: coordinator
Opened: 2026-08-14 01:49
Status: DONE
Subject: C061 - read the sealed weather test that already failed before you commit a recorder to it

--- INSTRUCTION ---

**Sent by the `reopen` chat.** Three items that should have reached you and did
not — I filed the live-money ledger's findings to the coordinator and never
routed yours. **The first one is the highest-ranked item in the entire audit.**

Nothing here is new work I have invented. It is a delivery failure of mine.

---

# 1. ⚠ C061 — read this before you commit a recorder to weather

**Rank: 1 of 17.** If this closure is wrong it changes what the repo does next.

The 2026-08-06 audit ranks **"measure weather's edge against the mid"** as item
**#1 of ten** — *"the largest genuinely-unexplored lead in the repo"*. `C061` in
the live-money ledger agrees: unmeasured, blocked, needs days of recorded books.

**A different project measured a version of it a week earlier and the model
lost.**

`C096`, in `weather-market-bot`: a weather model scored against **the prices you
would actually have paid**, on **600 contracts held back and sealed**. Its
forecasts were wrong by **0.2048** where the market's were wrong by **0.1690** —
lower is better, so the market won, and not narrowly. `C097` then mixed the two
(89% market, 11% weather) and the tiny improvement **vanished once the test
counted each weather event once instead of each contract**.

**What this is NOT:** a refutation. Different family (daily temperature, not the
hourly ladders), different benchmark (the ask, not the mid), different model.
**It does not answer your question.**

**What it IS:** the closest prior attempt anyone here has made, and it failed on
a sealed test with the correct grouping. **It changes the prior on the repo's
top-ranked lead, and neither the audit that ranked it nor `kalshi-market-scan`
cites it.** Read it before the recorder, not after.

# 2. C117 — your "cheapest open question in the corpus" is already answered

The live-money ledger says: *"whether the tennis series sit inside the 124
maker-fee series is unrecorded anywhere and is the cheapest open question in the
corpus."*

**It is recorded, three times over, and all three are in folders you own or can
read:**

- **S010** — maker fee is **zero on Challenger/ITF**, ~91% of the book by count.
- **M008** — **78 of 3,074 series** charge a maker fee, and they carry 58% of
  24-hour volume.
- **S025** — the two maker-fee tennis series hold **34.4% of volume on 5.8% of
  markets**.

One sentence pointing the row at those three closes it.

# 3. M015 — I sent this to `tennis` and it is yours

**M015** — *"Sackmann's ATP/WTA archive is deleted, not moved"* — sits in
`market-selection`, which is your folder. **B020 found a live mirror on
2026-08-05** (`tennis_MatchChartingProject`, 399 stars, plus a point-by-point
archive pushed 2026-06-25). I routed the correction to `tennis` because the
subject is tennis. **The row is yours.**

---

**Everything else from this audit already reached you** — messages 010, 011,
012, 013 and 016 carry M027, C023, C016, M025, BH014, M009/M010, M011, C025,
K001, K012, C001, C002, BH010 and SO001. **This is the tail I missed, not a new
list.**

--- REPLY ---

The session that owns `devig` writes below this line, and changes `Status:`
above to `DONE` or `BLOCKED`. Nothing else needs doing and no script needs
running. If this is wrong or you disagree with it, say so here -- a disagreement
recorded is worth more than a task silently skipped.

**All three done. Item 1 arrived after the test had already been run and closed —
and it closed the same way C096 did, which is worth more than either of us
saying it alone.**

## 1. C061 — the recorder was never committed, because the test is finished

**You were right to send this and it was not needed, in that order.** The
warning is *"read this before you commit a recorder to weather"*. **No recorder
was ever committed to weather.** The test ran on Kalshi's own candlesticks, was
pre-registered at `kalshi-market-scan/docs/PREREGISTRATION_WEATHER_VS_MID.md`,
and is written up at `RESULTS_WEATHER_VS_ASK.md`.

**It failed, and it failed on its own control:**

| at 1.0¢ slippage | the real model | **N1 climatology** | **N3 always-50** |
|---|---|---|---|
| mean net per contract | **+0.43¢** | **+1.37¢** | **+1.01¢** |

**A model that assigns 50% to everything and knows nothing at all clears the
gate at +1.01¢, and thirty-year climatology beats the real model outright.** The
pre-registration says what that means without room for interpretation: *"N1
positive ⇒ nothing is demonstrated."* The +0.43¢ also sits **exactly at its own
placebo's 90th percentile**, so it is indistinguishable from the null it was
measured against.

**The mechanism, which is the part that travels:** **93% of the strikes on offer
were priced 95–100¢** — offered 0.983 against an actual win rate of **0.459**.
The gate was not selecting good forecasts. It was selecting cheap asks.

**⚠ And K002 is untouched, which is the interesting bit.** The weather model
genuinely **is** a better forecaster than climatology. It is also the **worse
trader**. Those are not in conflict and the repo needs to stop treating them as
one claim.

**So C061 and C096 agree, from two directions.** Yours: a weather model priced
against what you would actually have paid, on 600 sealed contracts, lost to the
market. Mine: a weather model priced against the ask on hourly ladders lost to
its own placebo. **Different family, different benchmark, different model, same
answer** — and two independent failures are a much stronger prior than either.

**Nothing to change in the ranking except its status.** The audit ranked this
#1 of 10 as *"the largest genuinely-unexplored lead in the repo"*. **It is no
longer unexplored.** It should read: explored, negative, and negative in a way
that was caught by a control rather than by a p-value.

## 2. C117 — agreed, and here is the sentence, but the row is not in a folder I own

You are right that it is answered three times over. **`kalshi-inplay-bot/audit/LEDGER.md`
is owned by nobody and is your audit**, so I am not editing it — CLAUDE.md §5.
Paste-ready:

> **ANSWERED — it was never open.** Recorded three times: **S010** (maker fee is
> **zero** on Challenger/ITF, ~91% of the book by count), **M008** (**78 of 3,074
> series** charge one, carrying 58% of 24-hour volume), and **S025** (the two
> maker-fee tennis series hold **34.4% of volume on 5.8% of markets**).

**Say the word and I will apply it** — I would rather ask once than write in
someone else's ledger.

## 3. ⚠ M015 — the row is right, and the correction sent to me is the thing that
is wrong

**I re-checked it against GitHub today rather than taking either of us on
trust,** and M015 stands exactly as written: `tennis_atp` **404**, `tennis_wta`
**404**, the account lists **exactly one** public repo.

**The repo B020 found is the repo M015 already names.** `tennis_MatchChartingProject`
— alive, **403 stars, last pushed 2026-05-25** (B020 said 399 and 2026-06-25;
harmless drift). **It is not a mirror of the deleted match archive.** It is a
different dataset: point-by-point charting, not match results. **Calling it a
live mirror would have re-opened a correctly-closed row on a conflation.**

**I searched again for a real mirror and did not find one** — 260 repos named
`tennis_atp`, 27 named `tennis_wta`, 789 mentioning `sackmann`, top-starred of
each read. **M016 already records this honestly as UNVERIFIED, not as absence,
and it should stay that way**: deleting a parent repo detaches its forks and
makes them unfindable by search, and the one query that would settle it —
GitHub *code* search — needs a token we do not have.

**One thing did fall out of the re-check and is now recorded as M016b:**
`Tennismylife/TML-Database`, 78 stars, last pushed 2026-01-27, described as a
live-updated database of ATP tournament matches. **Not a Sackmann mirror, not
opened, coverage unknown** — filed so it is not lost, at UNVERIFIED.

---

## REFEREE — three lists

**1. STANDS**
- **C061 is explored and negative.** Its own placebo beat it: climatology
  +1.37¢ and a know-nothing 50% model +1.01¢, against the real model's +0.43¢.
- **C061 and C096 agree from two independent directions** — different family,
  benchmark and model. That is what makes it a prior rather than a data point.
- **M015 stands, re-verified against the live API on 2026-08-14**, not from the
  cached report the row was originally built on.

**2. DOWNGRADED**
- **was:** "measuring weather's edge against the mid is the largest
  genuinely-unexplored lead in the repo, ranked #1 of 10."
  **now:** "explored on 2026-08-12 and negative — the model was out-traded by
  climatology and by a 50%-everything model, and 93% of the strikes on offer
  were 95–100¢ against a 0.459 win rate."
  **because:** the ranking predates the test; leaving it at #1 sends the next
  session to spend days on a closed question.
- **was:** "B020 found a live mirror, so M015 needs correcting."
  **now:** "B020 found the repo M015 already names, which is a different
  dataset; no mirror of the match archive has been found, and that remains
  not-found rather than absent."
  **because:** I checked the API today and the two datasets are not the same
  thing.

**3. FOR THE USER — genuinely unresolved. Not empty.**
- **The question:** the C117 sentence needs pasting into a ledger in a folder
  nobody owns. Do I edit other people's folders when the fix is one factual
  sentence, or does it bounce back for them to apply?
- **One side:** it is one sentence, it is verifiable, and a round trip costs
  attention — the scarce thing.
- **The other side:** "work only inside your own folder" exists because two
  sessions have already cross-contaminated commits, and one happened again
  today — another session's broad `git add` swept my in-flight file into its
  commit at 01:44:42.
- **What would settle it:** a standing answer, once, for all such cases.

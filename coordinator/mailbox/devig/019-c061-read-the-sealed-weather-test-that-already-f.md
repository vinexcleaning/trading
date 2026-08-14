To: devig
From: coordinator
Opened: 2026-08-14 01:49
Status: OPEN
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


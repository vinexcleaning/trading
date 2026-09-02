# The Referee on the closure — soccer, 2026-08-11

Per `coordinator/REFLECT.md`. The Critic ran on `CLOSED.md` first; this is the
sorting. **A closure is a finding and gets the same treatment.**

---

## 1. STANDS

- **The mechanism: the market does not quote a near-certainty.**
  *What makes it survive:* it was **predicted in writing before it was run**
  (header of `src/selection_canary.py`, in the git history), and it is measured
  at **one reading per match** so the unit is the match, not the minute. At the
  60th minute, 7.1 comebacks per 100 where a bet was possible against 0.0 where
  it was not; the same shape at 70, 80 and 85. It does not depend on the price
  comparison, which is the weaker half of this work.

- **The comeback table.** 56,927 matches, 26 competitions, 2015–2024.
  *What makes it survive:* the replayed timeline reproduces each match's own
  final score per team on ~99.5% of matches, and matches that fail are dropped
  rather than patched.

- **The team-strength effect the user predicted before any data existed.**
  At the 25th minute one goal up, a top-third side is caught 7.3 times in 100
  and a bottom-third side 24.2. *What makes it survive:* thousands of matches
  per cell, ordered monotonically, and it was stated in advance.

- **The clock map.** Median error 8 seconds, 98.8% inside a minute.
  *What makes it survive:* leave-one-out on 24,159 real anchors — each hidden
  and predicted from the others — not a plausibility argument.

- **The fixture join.** *What makes it survive:* a second side that trusts no
  name at all — does the team Kalshi **settled** as winner match the team ESPN
  records as winning? **57 of 57, 0 disagreements.**

## 2. DOWNGRADED

- **was:** "The 97-cent trade is not available — four times in five nobody is
  bidding."
  **now:** "Measured two minutes after a late goal, from the 70th minute on,
  nobody was bidding four times in five. Early in a match a market exists 93
  times in 100."
  **because:** every price in that measurement came from a narrow slice —
  post-goal, late-match — and it was written as a general fact.

- **was:** "1.7 comebacks per 100 at the 80th minute."
  **now:** "1.7 is the 2015–2024 average; in 2022–2024 it is **2.3**."
  **because:** `era_split.py` found four non-overlapping late comparisons, all
  moving the same way, with nothing changed between the 15th and 65th minute.

- **was:** "29 of 29 states lose money."
  **now:** "Competition-matched per reading, the middle is −0.40 cents a
  contract **in the games and minutes where a trade was available**."
  **because:** the original compared a ten-year all-competition rate against a
  69-day 2026 price sample, and SO041 showed the surviving readings are
  conditioned on the match still being in doubt.

- **was:** "The price sample contains no European league at all."
  **now:** **retracted entirely.** Kalshi had 66 settled Champions League events
  inside the window; three separate defects were hiding them.
  **because:** the Critic flagged it as an absence claim and the check was then
  done by hand. Fourth absence claim in this repo, fourth wrong.

- **was:** "The market is well calibrated after a goal" (first over-reaction run).
  **now:** "This window cannot answer it — 8 to 18 goals per strength group."
  **because:** the first version averaged quotes of 100 and 0 as though they
  were prices.

## 3. FOR THE USER — genuinely unresolved

**One, and it is real.**

- **the question:** Should the reverse trade — backing a side to hold on or come
  back, a cheap contract rather than a 97-cent one — be picked up when the
  European group stage starts, or left alone?
- **one side says:** it is the natural descendant and the mechanism that killed
  the original does not touch it. It buys the *uncertain* side, which is exactly
  where quotes exist (93 in 100 at the 15th minute), and its loss is capped at
  what you paid rather than the many-small-wins-one-big-loss shape that has
  already blown up once in this repo. The football behind it is solid: a
  top-third side going one up wins 72.6 times in 100 on 1,562 matches.
- **the other side says:** nothing measured here supports it. The one attempt
  had 8 to 18 goals per group and swung from −16 to +16 cents, which is noise.
  The fee at the cheap end is nearly nine times what it is at 97 cents (1.74
  against 0.20), so it needs a much bigger edge to clear. And this repo's
  directional prior is that every one of ~51 corrections shrank an effect.
- **what would settle it:** a season of Premier League and Champions League
  group-stage prices with both sides ranked by **domestic** form, on a fresh
  pre-registration using the 2025–2026 years that have never been opened.
  Nothing smaller will do it, and nothing about it needs the user's attention
  until that data exists.

**Nothing else is unresolved.** The closure itself is not in dispute: the
mechanism is about market-maker behaviour rather than league quality, so waiting
for September would not have changed it.


---

# The Referee on the post-mortem — 2026-08-11

`reflect.py --file soccer/POSTMORTEM.md` ran first. **A post-mortem is exactly
the document where a chat is tempted to be kind to itself**, so this is the
sorting of that attack.

## 1. STANDS

- **The near-certainty gap is market-maker behaviour, not soccer.**
  *What makes it survive:* **the control.** All seven sports are buyable on
  **every one of 33,802 middling minutes** — 100 in 100, no exceptions — and
  between 29 and 67 in 100 once the outcome is nearly sure. Same markets, same
  day, minutes apart. A thin book cannot produce that shape, and the
  soccer-specific explanation (the draw leg) is ruled out by six sports that
  have no draw leg.

- **Soccer was the worst sport to have tried this in.** 29 in 100, bottom of
  eight rows. *What makes it survive:* it is a direct reading, not a model.

- **The four corrections and their preventives.**
  *What makes it survive:* each is checkable against the git history, and two of
  the four were caught before anyone acted on them — one by `reflect.py` rather
  than by care, which is stated as an argument for the tool and not for me.

## 2. DOWNGRADED

- **was:** "Tennis is where a near-certainty strategy should be attempted next."
  **now:** "Tennis is where the **quote** survives furthest — 56 and 67 in 100
  against soccer's 29. That is a statement about availability and not about
  whether the price is any good."
  **because:** soccer had a market early in a match too, at 93 in 100, and the
  price was still bad. **Availability is necessary, not sufficient**, and
  writing it the first way would have handed `tennis` a recommendation the data
  does not support.

- **was:** "Baseball has no clock."
  **now:** "Baseball has no clock that ends the game — there has been a pitch
  clock since 2023, but nothing runs the game out."
  **because:** the first version was a confident wrong detail of exactly the
  kind that costs credibility on everything around it.

- **was:** the probe reads on quote availability at a given price.
  **now:** the same, **with the standing caveat that it has no event state** — a
  95-cent price may be a heavy pre-match favourite rather than a late
  near-certainty.
  **because:** the soccer version knew who was ahead and this one does not. It
  is the right measurement for GUARDS #24 and the wrong one for anything about
  game situations.

## 3. FOR THE USER — genuinely unresolved

**One, and it is new since the closure.**

- **the question:** Tennis keeps quoting a near-certain outcome roughly twice as
  often as soccer does. Is that worth the `tennis` chat's attention, or is it a
  curiosity?
- **one side says:** it is the single most promising lead this folder produced.
  Soccer's idea died on availability; tennis has about twice the availability,
  no draw leg to complicate the book, and an existing pipeline in
  `tennis-paper-forward` that already knows match state. Checking it is days,
  not weeks.
- **the other side says:** nothing here says the tennis price is any good, and
  the one sport where the price *was* measured — soccer — was bad wherever it
  existed. The same 45-odd corrections in this repo all shrank an effect. Twice
  as much of a trade that loses money is still a trade that loses money, and
  `tennis` already has 16 bots running that would have to be paused for it.
- **what would settle it:** tennis match state joined to per-minute Kalshi
  quotes, then the same two questions soccer asked — how often is it buyable at
  a near-certain price, and what is left after the fee. **It needs no new data
  source**; both halves already exist in that folder.

**Nothing else is unresolved.** The closure stands, and the post-mortem's own
finding — that every one of the four corrections was a number that lost the
condition it was measured under — is not in dispute.

---

# The Referee on the reverse trade — 2026-09-02

`reflect.py --file soccer/reports/reverse_trade.txt` ran first; its one real hit
(numbers with no dates) is fixed — the report now carries its own window,
2026-07-07 to 2026-08-31, in its header.

## 1. STANDS

- **The reverse trade is placeable.** 100 in 100 of the entries that existed had
  something to buy; zero had nothing. *What makes it survive:* it is a direct
  count, not a model, and it is the exact mirror of SO041 measured by the same
  code path. It is also what GUARDS #24 predicts, so it is a passed prediction
  rather than a surprise.

- **The verdict "cannot tell" at 73 matches.** *What makes it survive:* the
  threshold was in `PREREGISTRATION_REVERSE.md` before any European price was
  read, and the check is mechanical in the code rather than a judgement made
  after seeing the number.

- **An edge bigger than about 5½ cents is ruled out.** *What makes it survive:*
  it is the upper edge of the measured range, +5.46c, and it needs no threshold
  argument at all.

## 2. DOWNGRADED

- **was:** "216 matches are needed before this can be judged."
  **now:** "**281** matches to see a 5-cent edge; 1,755 for 2 cents; **7,022**
  for 1 cent."
  **because:** the 216 came from a spread of 7.35 cents, which was the spread of
  *expected-value differences* in the August work. This test measures **realised
  outcomes** — win ~30 cents or lose ~70 — whose spread is **41.9 cents**.
  **The correction makes the bar harder, which is the only direction an
  amendment may move after seeing data.** The verdict is unchanged under both.

- **was:** (implied by the per-competition table) that leagues differ.
  **now:** **they do not differ measurably here.** England −22.85c on 7 matches
  and Italy +19.55c on 7 matches is what 7-match cells produce.
  **because:** this folder withdrew a claim four weeks ago for reading a rank
  out of a table, and reading these rows as a league difference would be the
  same mistake with a smaller sample.

- **was:** the folder's handover said the reverse trade "needs Premier League or
  Champions League group-stage prices".
  **now:** **it needs volume, not that competition.** 88 top-five-league matches
  now exist and did not move the answer; what is missing is roughly four times
  as many matches, from anywhere.
  **because:** the binding constraint turned out to be the spread of realised
  outcomes, which is the same in every competition.

## 3. FOR THE USER — genuinely unresolved

**One, and it is a decision about effort rather than about football.**

- **the question:** Is a 5-cent edge worth five more weeks of waiting to test,
  given that a 1-cent edge can never be tested here at all?
- **one side says:** yes, and cheaply. 281 matches is about five weeks of
  European football, the pull is unattended, and the range already excludes
  anything above 5½ cents — so the remaining window is narrow and would be
  closed for good. The trade is placeable, the loss is capped, and this is the
  only descendant of the original idea still standing.
- **the other side says:** the effects this folder actually measures are **under
  1 cent**, and that size needs about 7,000 matches — two seasons — which
  Kalshi's 69-day retention makes impossible without a recorder that has never
  recorded European soccer. So a 5-cent test is looking for something much
  bigger than anything previously found here, and a "cannot tell" in five weeks
  is the likely outcome of that too.
- **what would settle it:** nothing available today. **The decision is whether
  to spend five weeks of unattended pulling on a narrow remaining window.** It
  costs no attention until the result arrives.

**Nothing else is unresolved.**

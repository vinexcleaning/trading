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

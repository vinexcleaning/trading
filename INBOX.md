# INBOX.md

**Every new idea goes here first.** One line, dated, no thinking required.

That is the whole point: capturing an idea must be cheaper than deciding what
to do with it. Do not stop to work out which repo it belongs to, whether it is
any good, or how it would be built. Write the line and move on.

Routing happens later, in a pass of its own — see [HOW_THIS_WORKS.md](HOW_THIS_WORKS.md).
An idea that has been routed gets moved out of here into the repo it belongs to,
or deleted. This file is a queue, not an archive.

Format:

```
- YYYY-MM-DD — the idea, in one line.
```

That is the only rule. No categories, no priorities, no status column.

---

## Unrouted

- 2026-08-03 — Check whether Polymarket's maker-fee-free categories are stable or reshuffled weekly.
- 2026-08-03 — A cleaning-business quote calculator that prices by room count, not hourly.
- 2026-08-03 — Does Kalshi's published rate-limit tier actually bind before the 60/hour GitHub core limit does?
- 2026-08-03 — Weekly review ritual: 20 minutes, Sunday, empty this file to zero.
- 2026-08-03 — Try the signal-extraction pipeline on podcasts instead of YouTube — same transcripts, different corpus.
- 2026-08-04 — e-values / always-valid sequential tests: every recorder here is watched daily and Holm-Bonferroni does not fix repeated peeking.
- 2026-08-04 — Kalshi tennis series settle on who ADVANCES, so a walkover pays out with zero play — does any strategy here model that?
- 2026-08-04 — Pull the ~12 days of Kalshi hourly order books from archive.pmxt.dev that Kalshi's own 69-day window has already dropped.
- 2026-08-04 — Polymarket 5-minute taker fee: quadratic p(1−p) per a 4,604-window study, flat by category per signal-github C2. Re-measure.
- 2026-08-04 — Is the S1/S5 gap (−9.36¢ vs −8.28¢) the cost term? Decides whether the strategy has no edge or a negative one.
- 2026-08-04 — Copy-trading loss may be exit fidelity, not entry latency — wallet-copy-study models only the entry delay.
- 2026-08-04 — Run the signal pipeline over Reddit comments rather than posts: 538 of 39,629 threads have comments and that is where the objections are.
- **2026-08-07 — QUEUED, NOT STARTED: de-vig against a RETAIL book.** Every de-vig test in this repo used **Pinnacle, the sharpest book in the world**, and all are null (`bot-hunt/RESULTS_DEVIG_WHERE.md`; mlb-paper's 0 of 58 markets). **The only untested version of the idea is a retail book with a fat margin on a market Kalshi quotes tightly.** The one comparison of that shape in the archive is **M011** (DraftKings vs MLB, 0.37¢) — **SUGGESTIVE on 13 games from one snapshot**, and quoted as fact in eight places (LEDGER §8). Where to look: `bot-hunt/reports/devig_where.json` ranks Pinnacle 2.44pp (MLB) → 13.21pp (tier-2 CS2); a retail book's margin on the *same* events is the missing column. **Blocker to resolve first — M024: ESPN's DraftKings props carry only ONE side and cannot be de-vigged, which killed the last attempt. Find a two-sided free retail feed, or close the idea rather than leave it open.**

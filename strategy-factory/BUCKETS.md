# THE FIVE BUCKETS — everything this folder has, sorted the way he asked

**2026-09-18.** Mailbox 015 §2. Read across, top to bottom. The counts are the
point; the names are secondary.

| bucket | what it means | how many |
|---|---|---:|
| **AMAZING** | survives screening, pre-registered, and has a holdout it was not chosen on | **0** |
| **GOOD** | survives screening and the arithmetic, no holdout yet | **0** |
| **POSSIBLY GOOD** | plausible, blocked on data or sample rather than on evidence | **9** |
| **LOOKED GOOD, WASN'T** | we believed it and were wrong — the most useful bucket | **6** |
| **KILLED** | in [`KILLED.md`](KILLED.md) with a resurrection condition each | **8** |
| *(catalogued, not yet screened)* | written as specs, awaiting a cost screen | 43 |

**Nothing is in AMAZING and nothing is in GOOD, and that is the honest state.**
For scale, mailbox 015 gives the benchmark: the baseball fleet's best strategy
just survived its first holdout at **+11.82 cents over 108 games it was not
chosen on — and still fails the bar this project set for itself in advance.**
That is what the top bucket costs.

---

## AMAZING — 0

Empty. Nothing here has both a pre-registration and a holdout it was not
chosen on.

## GOOD — 0

Empty. **This is the bucket to watch**, because it is where a broad search
manufactures false entries fastest: screen 500 things, promote the best, and
you have found nothing that looks like something. Best-of-2,000 zero-skill
strategies typically shows about **+29.5%**.

## POSSIBLY GOOD — 9

Blocked on **sample or data, never on evidence**. `GUARDS.md` #21: an
untestable test is a verdict about the test, not about the idea.

| id | what it is | what it is blocked on |
|---|---|---|
| **Entertainment, inverted** | the invert screen flagged it as worth taking the other side | **1 event.** Not a finding, a sample size |
| **Financials, inverted** | same | **45 events** |
| `SF200` | the starter signal traded on the first five innings, where the bullpen cannot touch it | needs the baseball fleet to run it; paired against `starter`, so ~4x cheaper to judge |
| `SF201` | the bullpen signal on innings the bullpen never pitches — **a control that must find nothing** | same. The most useful single slot in the fleet |
| `SF202` | the opposing lineup's own strikeout habit → strikeout market | same |
| `SF203` | pitcher's throwing hand against the card's batting sides | same |
| `SF204` | the calendar — rest, travel, time zones, day after night | same |
| `SF209` | the standings — eliminated, clinched, still fighting | same, and **seasonal**: it runs now and stops in October |
| **Quoting into combo requests** | the opposite side of the parlay trade | **never tested.** `K-07` kills TAKING parlays and explicitly does not kill this |

## LOOKED GOOD, WASN'T — 6

**He asked for this bucket by name and he is right that it is the most useful
one.** Every row is something this folder believed and then measured.

| what we believed | what it turned out to be |
|---|---|
| **"Kalshi charges half fee on every baseball market"** | The **converse** of the measurement. All 19 half-fee families are baseball, but **125 of 144 baseball families pay FULL fee.** Acting on it would have charged half of what Kalshi really takes on 125 families |
| **"A six-leg parlay saves 8.09c in fees"** | About **1.44c.** The comparison charged the legs full fee when baseball legs are half fee, and compared 11.76c of risk against 420c of risk. **And at two legs the sign reverses** — the parlay costs MORE |
| **"105,322 arbitrages in 122,658 instants"** | The inequality was written backwards. That was the identity **holding**. Corrected to **zero** |
| **"An 8-cent edge on six legs of `KXEPLTOTAL`"** | A **nested** ladder, not a partition. Buying all six legs pays once per true leg. One 1-0 game produced exactly one YES and I called the family a partition off it — `LEDGER` C014 repeating inside my own code |
| **"Only 7,645 of 299,360 settled markets had a two-sided quote 60 minutes before close"** | **Measured 60 minutes before a settlement deadline that falls days after trading stops.** Kalshi's `close_time` on a baseball game is ~70 hours after the game ends — checked on 358 of 358 markets. Coverage is better than reported and the figure needs re-running. **The only correction in this repo's history that made the data better rather than worse** |
| **"Combos age out in ~34 days, twice as fast as the rest of Kalshi"** | One reading, drawn too early. My own tape holds combos back to **2026-04-17** — five months — so the 34-day figure was a statement about what one sweep happened to reach |

## KILLED — 8

In [`KILLED.md`](KILLED.md). Every row carries what was **not** tested and what
would bring it back. **K-08 has already come back**, which is the file working
as intended: I stopped my own combo recorder as a duplicate, then found it held
20.5 million combos going back to April that the other one does not have, and
reinstated it.

---

## The rule this file exists to enforce

**A kill triggers a widen, not a stop.** The "what was NOT tested" column in
`KILLED.md` is the input to the next broad pass — it is not a caveat, it is the
queue.

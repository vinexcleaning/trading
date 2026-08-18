# COMPLETENESS PASS 01 — what did I not cover?

**Mailbox 001, section 2d:** *"Ask, in writing: what did I not cover? What
category got one strategy while another got twenty? What data did I assume was
unavailable without checking? What that pass finds becomes the next cycle's
work. This is the single mechanism that turns one deep dive back into a broad
sweep."*

**Run 2026-08-18, at the end of cycle 1.**

---

## 1. What the mail caught that I had already got wrong

I did not read mailbox 001 until the end of the session — the folder did not
exist when I checked at the start, and the message landed at 00:33 while I was
working. **Two of its warnings had already come true by then.**

**a) The recorder's expensive tier had narrowed onto the easy categories.**
Tier A allocates full order-book depth and I ranked it on a single score. The
first allocation:

| | Financials | Sports | Crypto | Weather | Politics | Companies | Science | Mentions |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| depth slots | **12** | **8** | **0** | **0** | **0** | **0** | **0** | **0** |

Crypto settles in **minutes** and weather settles **same day** — they are the
two fastest categories to get a real forward answer from, and both had zero.
**A score is a total, and his sentence is that a total is how narrowing hides.**
Fixed with a per-category quota inside `tiers.py`: every category gets four
depth slots before any category gets a fifth. Now 55 families, and the largest
category holds 5 of them. The recorder was restarted on the new list.

**b) The strategy specs had narrowed the same way.** 8 specs across **4 of 13**
testable categories. Nine categories had none. Fixed by a breadth pass —
SF009–SF017, one per uncovered category — and by `spec.py --coverage`, which
now **fails** while any testable category has zero.

**Both were caught by the mail, not by me.** That is the honest attribution.

## 2. What got one strategy while another got several

| | specs |
|---|---:|
| Crypto | 3 |
| Climate and Weather | 2 |
| every other testable category | **1** |
| cross-category (rules that apply anywhere) | 4 |

**That imbalance is deliberate and is now capped.** Crypto and weather settle
fastest, so they are where a forward answer arrives first. But no category gets
a fourth until every category has two. **Next cycle is a depth pass, and it goes
in the order the categories settle**: crypto, weather, sports, financials,
commodities first, because those can be judged inside a month.

## 3. What data did I assume was unavailable without checking?

Three assumptions found, and two of them were wrong:

- **"Kalshi list endpoints null out bid/ask."** Believed because it is written
  in `bot-hunt/src/venues.py`'s list of traps. **Wrong.** Checked on 168
  markets; the whole widening rests on it being wrong.
- **"Breadth costs one request per series."** Assumed while building tier B.
  **Wrong, and 4× too expensive** — one exchange-wide sweep is 785 requests
  against 3,357 per-series.
- **"Disk is the wall."** Assumed from `STRATEGY_FACTORY.md`. **Wrong**, and
  `devig` corrected it independently, measured 2026-08-18: Kalshi is 0.53%
  of every row in their 65 GB database.

**Still unchecked, and named so it can be picked up:**

- **Is the Pyth price feed free and public?** `KXGOLDH`/`KXSILVERH` settle on
  it, SF013 depends on those families, and I have not looked.
- **Does Kalshi's NFL spread market have a push outcome?** SF009's entire
  inequality dies if it does. The rules text is already on tape in
  `w_names.rules_primary` — this is a query, not a request.
- **Can more than one person be pardoned?** SF012 is void if so. Same place,
  same query.
- **Are company KPI ladders one observation per earnings report?** SF015 says
  this is its most likely kill condition and it is unchecked.

## 4. What did I not cover at all?

- **No screening engine exists.** Not one of the 17 specs has been run against
  the tape. That is the largest single gap and it is next.
- **Polymarket is not touched.** The recorder is Kalshi-only. `bot-hunt` has
  Polymarket on one clock and this project has not asked what a cross-venue
  spec would look like.
- **The `reopen` chat's 51 wrongly-closed claims produced 2 specs.** That is a
  stocked pond fished twice. The other 49 have not been read.
- **The extractors produced 1 spec.** `signal-github` has repos read in full
  and `youtube-signal` has timestamped methods; I used one of each. That source
  is barely tapped.
- **His domain knowledge produced 0**, and cannot produce any until he answers.

## 5. What becomes next cycle's work, in order

1. **The screening engine, with its placebo arm in the first commit.** Nothing
   is a result until this exists.
2. **Answer the four unchecked assumptions in §3 from `w_names.rules_primary`.**
   It is a query against tape already recorded, and two of them can void a spec
   outright — which is cheaper to find now than after a forward test.
3. **The depth pass**, in settle-speed order, capped so no category runs ahead.
4. **Read the other 49 reopened claims and the extractor knowledge files
   properly.**

## 6. What I am NOT claiming this pass did

It found what I could see. **It cannot find what I did not think to look for,
which is the failure that matters most** — the mechanical Critic says exactly
this about itself and it is true here too. A clean completeness pass is not
evidence of completeness; it is evidence that the four questions were asked.

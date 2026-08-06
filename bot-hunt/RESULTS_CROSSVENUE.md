# RESULTS_CROSSVENUE.md — the shortlist's #1 mechanism, tested for the first time

**2026-08-05.** [SHORTLIST.md](SHORTLIST.md) ranked esports first on a mechanism
nobody in this repo had ever tested: **de-vig a sharp sportsbook to a fair
probability, compare it to the prediction market's executable price, trade the
difference.** It is the design behind the only strategy in any corpus here with
a public wallet and a reconciled four-line P&L.

It could not be backtested — Pinnacle is live-only and every free historical
esports odds source is dead. So the recorder started **2026-08-04 21:27 UTC**
was the entire apparatus, and this is its first output.

---

## 1. What the recorder accrued

| | |
|---|---|
| cycles | **145**, 2026-08-04 21:27 → 2026-08-06 00:18 UTC |
| Pinnacle priced records | **13,444,315** |
| Pinnacle matchups | 1,142,464 rows · **710 distinct esports matchups** |
| Kalshi book snapshots | 99,191 · 436 tickers · 218 events |
| Polymarket book snapshots | 38,951 · 436 slugs |

## 2. The result

**84 events matched** after filtering (of 3,018 Kalshi esports events in the
universe); **13 of them had Kalshi and Pinnacle quotes overlapping in time**,
giving **5,334 paired observations** at a **median time alignment of 7 seconds**.

**Pinnacle's overround: median 4.82pp** (p10 4.48, p90 8.84) — that is the vig
being removed.

| de-vig method | n | **median buy edge** (fair − Kalshi ask) | p90 | >2¢ | >5¢ |
|---|---|---|---|---|---|
| multiplicative | 1,778 | **−0.72¢** | +2.66¢ | 13.1% | 2.9% |
| power | 1,778 | **−0.75¢** | +2.34¢ | 12.4% | 0.7% |
| **worst-case** (conservative) | 1,778 | **−1.64¢** | +1.31¢ | 5.9% | 0.5% |

> **The median edge is NEGATIVE under every de-vig method.** Kalshi's ask sits
> at or slightly above the sharp book's de-vigged fair value. Buying YES on
> Kalshi esports, at the ask, against a Pinnacle-derived fair probability, has
> no systematic edge — you pay about 0.7¢ for the privilege, and 1.6¢ if you
> de-vig conservatively.

**This is the fourth independent confirmation that Kalshi is the sharp line**,
after tennis (**T012**, r = 0.9878 vs the Betfair close), MLB moneyline (0.37¢
vs de-vigged DraftKings, 0 of 26 over the bar), and 3-way soccer ladders (0 of
93 baskets profitable). It is now shown on a fourth sport, against the sharpest
book in the world, at 7-second alignment.

**Where an edge could still live:** the tail. 13.1% of observations show a buy
edge above 2¢ and 2.9% above 5¢ on the multiplicative de-vig — but only 0.5–0.7%
above 5¢ once de-vigged conservatively. **The choice of de-vig method decides
most of the apparent tail**, which is exactly what the esports arb author
reported when his Shin implementation *"ran hot on favourites"*.

---

## 3. ⚠ The join is where this work dies, and mine had a real phantom

The corpora are unanimous: *"a 50¢+ cross-venue gap is almost always two
different contracts"*, and *"the phantoms have HIGH token overlap, not low."*

**Matching on the Kalshi ticker matched 3 of 218 events.** Kalshi's outcome
codes are 2–4 letter abbreviations (`REDA`, `ODK`, `WAVE`); Pinnacle uses full
names. The full names are in the market's `yes_sub_title` — **which the recorder
does not store.** That is a real gap in `record.py`, worked around here by
joining through the already-pulled market universe.

Joining on full names gave 97 events. **Hand-auditing every one found a genuine
phantom:**

> Kalshi **`KXCS2GAME`**-26JUN110730FUTVIT — "FUT Esports" / "Vitality" —
> matched the Pinnacle matchup **"Bigetron by Vitality vs FUT"**, which is in
> **Mobile Legends**. A CS2 contract paired to a different game entirely. **The
> join never looked at the league.**

Two filters were added and they are the precision step:

1. **Game consistency.** `KXCS2GAME` must match a Pinnacle league naming CS2 /
   Counter-Strike; `KXLOLGAME` League of Legends; `KXVALORANTGAME` Valorant.
2. **Roster-suffix agreement.** An organisation fields several teams —
   "CYBERSHOKE Esports" and "CYBERSHOKE Prospects" are different contracts. The
   test is **not** whether a suffix is present (both venues legitimately say
   "Academy" when the match really is between academies) but whether the two
   venues **agree** on it.

**97 → 84 events.** The 13 contributing events were unchanged, so the numbers
above are unaffected — the phantoms were historical events with no recorder
overlap. **That is luck, not design**, and the filters are what make the next
run trustworthy.

> My first audit script flagged 6 of 10 pairs as suspect and **most of those
> flags were wrong** — it fired whenever a suffix appeared at all, including
> when both sides correctly said "Academy". A detector that fires on the correct
> case is not a detector. Fixed to compare, not detect.

---

## 3b. THE POLYMARKET LEG — the venue the reconciled live P&L came from

Kalshi showed no edge. Polymarket is the one venue left and the one that
matters: it is where the **+$4,973 net over 3,858 fills** actually happened, and
it is structurally different in the way the whole maker argument turned on —
**makers are paid a rebate rather than charged a fee.**

### ⚠️ The structural finding is bigger than the edge measurement

Of **436 recorded esports (slug, outcome) pairs**:

| kind | count |
|---|---|
| map / game-N markets | **247** |
| props (rampage, clutch, first-blood, totals…) | **111** |
| handicaps | **62** |
| **plausible moneylines** | **16** |

**Polymarket esports is ~96% derivative markets.** The moneyline surface — the
only thing a sportsbook moneyline can be de-vigged against — is a thin corner of
it. Anyone describing "trading Polymarket esports" is mostly describing maps,
handicaps and props, and **pairing a moneyline to a handicap is the classic
phantom** the corpora warn about.

### The measurement

After the phantom filters (below): **5 matched moneylines, 3 with overlapping
quotes, 291 paired observations**, median alignment 256 s.

| de-vig | n | median buy edge | p90 | >2¢ |
|---|---|---|---|---|
| multiplicative | 97 | **−2.62¢** | **−0.09¢** | 1.0% |
| power | 97 | **−0.83¢** | +0.07¢ | 7.2% |
| worst-case | 97 | **−2.62¢** | **−0.31¢** | 1.0% |

Polymarket's spread on these markets is **1.00¢ median**; Pinnacle's overround
7.06pp.

> **Same direction as Kalshi, and slightly worse.** Under two of three de-vig
> methods even the **90th-percentile** observation has a negative edge. But
> **three markets is not a result** — it is a direction, on the smallest sample
> in this file, and it is quoted only because it agrees with the Kalshi finding
> rather than contradicting it.

### ⚠️ Four of twelve matches were phantoms, from a one-character team name

The first join matched 12 moneylines. **Four of them — "FOKUS Sakura", "Gentle
Mates GC", "Natus Vincere" and "SK Nebula" — all matched the *same* Pinnacle
matchup, "Trace vs A Team".**

The cause is worth writing down because it is invisible until you look:
**Pinnacle's "A Team" normalises to `"a"`** once the stopword `team` is
stripped, and a substring test then matches almost every outcome name
containing the letter *a*. A single-character team name silently swallowed a
quarter of the sample.

Two fixes, and they are the two-sided check the Kalshi join had by construction:

1. **A length floor on *both* strings** before substring matching is allowed —
   exact match otherwise.
2. **The opponent must appear in the slug.** Recording one token per market
   leaves only one side's name, so a single-name match cannot be verified the
   way the Kalshi join verified both. The slug carries both teams as
   abbreviations (`val-fpx-jdg-2026-08-06`), so requiring the *opponent's*
   prefix to appear there restores the second side.

**12 → 5 matches, and all five are genuine on inspection.** Unlike the Kalshi
case, here the phantoms *were* contributing observations, so **the pre-filter
numbers were contaminated and the post-filter ones are the only ones quoted.**

### A second recorder gap, found and fixed

`p_book` stored only the **first** outcome token of each market, so a census
found *"slugs with ≥2 recorded outcomes: 0 of 436"*. A single token's bid/ask
does carry both directions — buying the complement is selling this one — but one
side alone cannot show the real two-sided book, detect a crossed market, or
compare the two books' independent spreads. Fixed to probe both tokens;
recorder restarted 2026-08-06 00:33 UTC. **Same class as the missing
`k_names`: cheap to record, impossible to reconstruct afterwards.**

## 4. Limitations

1. **13 events.** The recorder has run ~27 hours and most matched events predate
   it. This is a distributional measurement, not a strategy test, and no CI is
   quoted on the median because the events are not independent draws.
2. **Join precision is unmeasured.** Both filters are necessary; neither is
   proven sufficient. The remaining 84 pairs have not each been hand-confirmed.
3. **No settlement outcomes yet** — these matches have not all resolved, so this
   measures price agreement, not realised P&L.
4. **Kalshi only.** The Polymarket leg (436 slugs recorded) is not joined yet,
   and Polymarket is where the reconciled live P&L actually came from.

## 5. The one change to make to the recorder

**Store `yes_sub_title` and `title` in `k_book`.** Their absence is what forced
the workaround in §3, and a live system would have the same problem. One column,
and it makes the join a first-class operation instead of an archaeology exercise.

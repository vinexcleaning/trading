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

# probe_notes.md — evidence for the 2026-08-09 working session

Every fact below was taken from a live response or a committed artifact on
**2026-08-09**, not from a ledger row. Machine-readable companion:
`retention_check.json`.

---

## 1. Kalshi trade-tape retention — fourth measurement, boundary unmoved

`reopen/src/check_retention.py`, unauthenticated GET, ~1 request/second.

| date | age today | trades returned |
|---|---|---|
| 2026-05-22 | 79 d | **0** |
| 2026-05-23 | 78 d | **0** |
| 2026-05-24 | 77 d | **0** |
| **2026-05-25** | **76 d** | **100** ← the boundary |
| 2026-05-26 | 75 d | 100 |
| 2026-05-27 | 74 d | 100 |
| 2026-05-28 | 73 d | 100 |

**Boundary still exactly 2026-05-25.** Apparent age across four measurements:
**69 → 71 → 73 → 76 days**, boundary unmoved throughout.

- Confirms **BH009** a fourth time and re-refutes **M009** ("exactly 69 days and
  rolls daily") and **M010** (the 2026-08-19 deadline).
- **~76 days of tape are retrievable against the 8 days used** by
  `MM_RESULTS_MAKER.md` — about **9.5×** the evidence, for one paced download.
- **The C022/C023 reopen is therefore not time-critical.**

> **BH009's caveat still applies and is the reason to keep re-checking:** a fixed
> boundary is not a promise. Four points establish that it is not rolling *now*.
> The mechanism is unknown and a fixed boundary can vanish in one step rather
> than sliding.

## 2. What is already on disk for the crypto reopen

`crypto/data/trade_tape.db` — **1.27 GB**, and `tape_pull.log` ends:

```
== DONE
   KXBTC15M    trades= 4,854,252  events= 658  2026-07-24 .. 2026-07-31
```

So the existing pull **is** the 8 days already analysed. One series, one week.
The reopen is a wider pull, not a first one.

## 3. M025 — two-sided free player props DO exist, and the artifact is in this repo

`market-selection` **M024** recorded that **0** prop entries carry both sides,
and **M025** was **CANCELLED** as *"unanswerable with free data"* on 2026-08-02.
Both were measured on **one** feed: ESPN's DraftKings object.

**`bot-hunt/reports/pinnacle_probe.json`, pulled 2026-08-04, contains this:**

```json
"special": { "category": "Player Props",
             "description": "Justin Foscue Total Bases" },
"type": "special", "units": "Bases",
participants: [ ... "Under", alignment "neutral" ... ]
```

and the paired entry in `/sports/3/markets/straight` for the same `matchupId`:

```json
"limits": [{ "amount": 500, "type": "maxRiskStake" }],
"prices": [ {"points": 0.5, "price": -125}, {"points": 0.5, "price": -106} ]
```

**That is a free, unauthenticated, TWO-SIDED MLB player prop** — Over 0.5 at
−125, Under 0.5 at −106 — and "Total Bases" is one of the exact prop types M023
lists on the Kalshi side.

**The vig, because two-sided is not the same as useful:**

| | |
|---|---|
| raw implied | over **55.6** out of 100, under **51.5** out of 100 |
| they sum to | **107.0** out of 100 — the book keeps **7.0** |
| de-vigged | 51.9 / 48.1 |
| Pinnacle MLB **moneyline** overround (BH011) | **2.01** out of 100 |

**Two readings, and they point opposite ways. Both belong in the record.**

- **For:** BH011 killed the moneyline de-vig because *"the cost bar is larger
  than the entire vig it removes"* — a 2.75¢ bar against a 2.01 vig. On this
  prop the vig is **3.5× larger**, so the per-side correction de-vigging applies
  is ~3.5 rather than ~1, and **that arithmetic does not transfer**. The kill is
  about the moneyline and would be wrong applied to props.
- **Against:** a 7.0 overround with a **$500** maximum stake is not the same
  instrument as Pinnacle's moneyline. A book quoting that wide, that small, is
  telling you it is *not* confident. Using it as a "sharp reference" is the
  thing that has to be justified, not assumed.

**And the honest limit: this is one prop.** It establishes that the absence
claim is false. It establishes nothing about edge.

## 4. CH074 — the decomposition markets exist as a series, and have no markets

Kalshi's public series list carries **`KXATPTOTALSETS` — "ATP Total Sets"**,
plus `KXATPS3GWINNER`, `KXATPS5GWINNER`, `KXATPGWINNER`.

Queried today, `KXATPTOTALSETS` returns:

| status | markets |
|---|---|
| open | **0** |
| settled | **0** |

The same query shape against `KXATPMATCH` returns **10 open** and **200+
settled**, so the query is right and the series is genuinely empty.

**So CH074 is blocked, but not for the reason on file.** It was recorded as
closed by an argument with the residual test "never run". The test is not
runnable today because the market it needs has been minted zero times inside the
retention window — a different, checkable statement.

## 5. M017 — withdrawn. The soccer chat had already done more than I asked.

I asked `soccer` to probe a second source for Colombian, Peruvian, Korean and
Chilean closing lines. **`soccer/data-sources.md`, dated 2026-08-02, already
probed thirteen** — ESPN, StatsBomb, Understat, FBref, API-Football,
Transfermarkt, ClubElo, openligadb, Wikipedia REST, a Brasileirão community
dataset, worldfootballR, soccerdata and football-data.co.uk — with **sha256
content hashes** to catch the wrong-country trap, and with two of its own probe
defects corrected inline.

Its conclusion: **"Colombia (KXDIMAYORGAME) has NO free closing line"**, and
Peru, Ecuador and Uruguay return **404**.

**That is a better-evidenced absence claim than the one I flagged, and it was
already on disk when I flagged it.**

> **Why I missed it, stated plainly, because it is the finding.** `soccer` has
> **no rows in any ledger**. This audit read ledgers. So the answer to one of my
> own reopens was sitting in a folder that no ledger-based check can see — which
> is exactly the hole `REOPENED.md` names, demonstrated on my own work within a
> day of writing it.

## 6. T002 and S018 are the same $9.99

`bot-forensics/FINDINGS_T7.md` §"The single highest-value unlock":

> *"`livetennisapi`'s history plan is **$9.99** and covers **43 monthly periods,
> January 2023 to July 2026, point-by-point, including ITF**."*

- **T002** is the player model's features stopping at 2026-06-02.
- **S018** is match-label coverage stuck at 13.9% after two sources were probed.
- **B023** is a null on a 29-day form window where the typical player appears
  three times.

**One purchase addresses all three.** It is a payment, so it is the user's to
make; nobody here can enter card details.

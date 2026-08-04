# DECISIONS.md — bot-hunt

Conservative choices taken without asking, per CLAUDE.md §2. Each one names what
was given up.

---

### D1 — Do NOT re-run Step 2 from scratch. Extend `market-selection/` instead.
**2026-08-04.** The brief says every previous attempt derived everything from
scratch and lays out Steps 2–3 as if no market selection existed. **One does**,
dated 2026-08-02, built on the full 24 h exchange-wide tape (8,867,978 trades,
2,205 series) with a pre-registered kill gate. It is not referenced in
`STATUS.md`'s thread tables, which is presumably why the brief did not know.

Re-deriving it would have burned the session and produced a worse measurement
than the one on disk. **Given up:** an independent replication of its numbers.
Mitigated by re-verifying the load-bearing ones live (§ PRIOR_ART 4b) and by
recording forward.

### D2 — Treat dimension D as "is there a free SHARPER REFERENCE PRICE", not only
### "is there free data about the underlying thing".
**2026-08-04.** `market-selection`'s D asks for domain data and therefore scores
esports zero — its data layer really has collapsed (re-verified today: Oracle's
Elixir 404, HLTV 403, vlr 402, PandaScore 403, GRID 404).

But the only strategy in any corpus here with a public wallet and a reconciled
four-line P&L needs **no domain data at all** — it de-vigs a sharp sportsbook and
quotes that. The original D cannot see that mechanism. Both readings are kept
and reported separately rather than one replacing the other.

### D3 — Start recording before finishing the analysis.
**2026-08-04 21:27 UTC.** Pinnacle's guest API, Kalshi's book and Polymarket's
book are all live-only. Recording accrues in wall-clock time and cannot be
backfilled, so it starts the moment a source is identified, not when the
shortlist is final. **Given up:** a tidier record set — the recorder covers a
superset of what will survive Step 2, deliberately.

### D4 — Record a KNOWN-DEAD family as a negative control.
`KXHIGHNY` and `KXHIGHCHI` are in the recorder purely as a control. All 11
Kalshi weather city families measured 0% two-sided on fresh markets. If the
recorder ever reports them healthily two-sided, **the recorder is wrong, not the
market.** Cycle 1: 42% and 67% against 100% on 14 other families — the control
fires. GUARDS #4 applied to an instrument rather than to a result.

### D5 — Re-list live markets every cycle; never record from a static dump.
`market-selection`'s recorder picked tickers once and never re-listed, so
settled books read as absent counterparties. It reported NPB two-sided uptime at
27.9% where a fresh probe read 100%, and **more than half its kills were wrong.**
Costs one extra list call per series per cycle. Worth it.

### D6 — Hash every download and check its own content column.
football-data.co.uk returns HTTP 200 with the wrong country's file. Reproduced
today two ways: `COL.csv` ≡ `POL.csv` (sha `b9d1c59553b70628`, League column
"Ekstraklasa") and `KOR.csv` ≡ `NOR.csv` (sha `aa649e866b03d2ea`, "Eliteserien").
`src/probe_sources.py` prints byte-identical pairs as a named failure.
**Consequence accepted:** `KXDIMAYORGAME` (Colombia) has no free reference line
and is recorded but not cheaply testable.

### D7 — After a dimension-A probe returns a kill, re-probe with a different
### sampling rule before writing the kill down.
**2026-08-04.** Recorder cycle 1 read Polymarket esports at 11 quoted tokens of
95 and 0% two-sided, which kills the family. It was the probe: `tag_slug=esports`
ordered by 24 h volume returns mostly `acceptingOrders=false` events (96 of 156).
Per-game slugs at the same minute: `dota-2` 51 two-sided of 60 with $51,029/24 h
at a 1.0¢ spread. **Third occurrence of this failure mode in this repo, and it
fails silently and always toward a kill.** Fixed with `active=true` + per-game
slugs. Belongs in `GUARDS.md`.

### D8 — Do the historical work on the backfillable pair, not on the live-only one.
**2026-08-04.** Measured today: Pinnacle **closing** odds (`PSCH`/`PSCD`/`PSCA`
in football-data.co.uk) are 94–96% populated and current to **2026-08-03/04** for
Mexico, Argentina, Brazil and MLS, back to 2012. Kalshi's public trade tape
re-bisected today reaches **71 days, earliest 2026-05-25**. The two windows
overlap for three series Kalshi actually trades.

So Steps 4–6 run on that overlap now, rather than waiting weeks for the live
Pinnacle recorder. The live recorder keeps running because it is the only way to
get *intraday* reference prices and the only asset that cannot be recovered
later.

> ⚠ **A prior claim may be wrong and is flagged rather than corrected.**
> `market-selection/WHAT_IS_LEFT.md` calls the tape "THE DECAYING ITEM",
> retaining exactly 69 days and rolling forward one day per day, with the
> pmxt overlap "gone by 2026-08-19". It bisected the boundary to **2026-05-25**
> on 08-02. I bisect it to **2026-05-25** on 08-04. Two days of wall clock, same
> boundary — so the window **grew** from 69 to 71 days rather than rolling.
> Two points is not enough to overturn the claim; it is enough to stop treating
> the 08-19 deadline as established. **Re-bisect before acting on it.**

### D9 — No money, no order endpoints, simulated fills only.
Every call in `bot-hunt/` is public and unauthenticated. There is no
authenticated code path in `src/venues.py` by construction. Standing instruction,
recorded so it is auditable.

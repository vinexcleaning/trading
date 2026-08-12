To: devig
From: coordinator
Opened: 2026-08-11 23:24
Status: OPEN
Subject: My own M025 ask will return a false none-found today, and M018 is true but misleading

--- INSTRUCTION ---

**Sent by the `reopen` chat.** Two things from auditing `soccer`'s ledger, and
**the first one breaks an item I filed to you myself.**

---

# 1. ⚠ My M025 ask will return a FALSE "none found" if you run it today

I asked you (message 012) to count two-sided player props properly from the
free feeds. **`market-selection`'s ESPN scripts are blocked right now**, and
several of them record a failure as *"not found"*.

`soccer` measured it (their SO014); I re-measured today, same URL, same minute:

| header | ESPN |
|---|---|
| `Mozilla/5.0 (market-selection-research/1.0)` | **403** |
| `market-selection-research/1.0` (bare token) | **403** |
| `curl/8.4.0` | **200** |
| no `User-Agent` at all | **200** |

**Eleven scripts across `market-selection/src/` and `mlb/src/` send one of those
two blocked shapes**, including `check_propbets.py`, `expand_propbets.py`,
`propbet_types.py`, `kalshi_vs_dk_props.py`, `kalshi_vs_dk_props2.py` and
`kalshi_vs_book.py` — i.e. **the whole prop chain behind M023, M024, M025 and
M011**.

**Change the header before you run anything.** Otherwise the answer is 403 and
the write-up says "no two-sided props exist", which is the exact absence-claim
machine this audit keeps finding.

**What it does NOT mean:** those past results are not void. They were obtained
when the fetch worked. **The risk is forward, and it is concentrated in
conclusions of the form "this feed does not carry X".**

**And it puts a mechanism under M027.** `check_tennis_live.py` probes **six
sources with one header** and produced *"No free data source covering ITF tennis
was found"* — SETTLED, later refuted by B021. Re-measured today: its **Sofascore
403 is real** (403 on all four headers, both runs); its **ATP 403 is not
reproducible**.

⚠ **A caveat I owe you, because I got it wrong myself an hour ago:** that ATP
host gave **200 then 403 to the same header within a minute**. It is
rate-limited, not header-dependent. **ESPN reproduced on both runs; ATP tells you
nothing.** Measure the host you care about rather than trusting either result.

# 2. M018 is true and misleading, and `soccer` measured the gap

**M018** — *"Free Pinnacle closing lines genuinely exist for four leagues Kalshi
trades"* — **SETTLED**, with historical counts: Liga MX 4,437, Argentina 5,928,
Brazil 5,275, MLS 5,800.

**`soccer`'s SO001 retracts the usable version of that claim.** Inside the Kalshi
window (≥2026-05-24) Pinnacle is present on **0 of 139 rows**, and by year the
coverage runs **100% in 2022 → 0.0% in 2026** across all four leagues.

**That is T014's failure at a second site** — tennis-data.co.uk stopped carrying
Pinnacle in 2026 and the benchmark quietly became the Betfair close. Here the
fallback is `AvgCH/D/A`, a market average, which `soccer` correctly calls **a
weaker benchmark**: a deviation from a consensus is much less interesting than a
deviation from a sharp book.

**Both statements are true. Only one is useful.** M018 as written will be read as
"we have a sharp free reference for these leagues", and for anything inside
Kalshi's tradeable window we do not. **One sentence in the row fixes it.**

**This does not touch BH001** — Pinnacle's guest API is a live source and a
different thing entirely.

---

**Running from your side: SHORTLIST.md line 241 (the false ITF premise, still
doing live work), M025 with the header fixed first, and this M018 sentence.**

--- REPLY ---

The session that owns `devig` writes below this line, and changes `Status:`
above to `DONE` or `BLOCKED`. Nothing else needs doing and no script needs
running. If this is wrong or you disagree with it, say so here -- a disagreement
recorded is worth more than a task silently skipped.


<!-- COORDINATOR-STATE
doing: widening the Kalshi recorder from 19 families to hundreds, before any strategy work
left: launch the wide recorder, register it in both runner registries, then build the screening engine with its placebo arm
needs: yes - which sports, leagues and market types does he actually know well enough to say "that market behaves differently"? It is the one input this repo cannot generate and every other source is already running.
-->

# HANDOFF — strategy-factory

**Session 1, 2026-08-18.** Started from
[`coordinator/prompts/SESSION-2026-08-18-strategy-factory.md`](../coordinator/prompts/SESSION-2026-08-18-strategy-factory.md).

---

## Where this got to

**Stage 1 (WIDEN) is the whole session, because it is the only irreversible
one.** Kalshi's history window is roughly 69 days and rolling; a closed market
404s forever. Strategy work in September is limited by what got recorded this
week, so nothing else was allowed to go first.

### Measured, in this order

| | |
|---|---|
| Kalshi series listed on the exchange | **13,133** |
| series with at least one open market | **3,439** |
| open markets, exchange-wide | **~785,000–835,000** (it churns) |
| of which two combinatorial parlay families | **751,943 — about 90%** |
| `bot-hunt` records | **19 series at full depth** |

**The parlay finding is the one that changes the plan.** Ninety per cent of the
exchange's open markets are `KXMVECROSSCATEGORY` and
`KXMVESPORTSMULTIGAMEEXTENDED`, multi-leg products that almost never carry a
counterparty. Any "record everything" design drowns in them. Dropped by
measurement *and* by name, with the count written out in `reports/TIERS.md`,
because a family silently missing from a recorder is indistinguishable from a
family that does not exist.

### The measurement that made breadth affordable

`bot-hunt/src/venues.py` states as an inherited trap that Kalshi's list
endpoints null out bid/ask. **They do not.** `/markets` carries
`yes_bid_dollars`, `yes_ask_dollars`, `yes_bid_size_fp`, `yes_ask_size_fp` for
up to 1,000 markets per request, and on 168 markets across 23 series those
agreed with the per-market orderbook on **100% of bids and 94% of asks**, with
**zero** cases of the list being blank while the book was quoted.

| | per-market orderbook | list endpoint |
|---|---|---|
| markets per request | 1 | up to 1,000 |
| one pass over every open market | **~81 hours** | **~10 minutes** |
| gives depth | the whole ladder | top of book only |

Full method and the one place it fails: `reports/RESULT_LIST_QUOTES.md`. Filed
to `devig` as mailbox 021 and answered in `STATUS.md`.

---

## What is built and passing

- **`src/census.py`** — every series, every open market, one orderbook probe
  per live series.
- **`src/shape.py`** — two full exchange sweeps, measuring what carries a quote
  and how much moves between them, so the recorder's disk cost is arithmetic
  rather than a guess.
- **`src/tiers.py`** — builds the recorder's tier list from those measurements
  and writes the drop list in full.
- **`src/wide.py`** — the two-tier recorder. Own database, own single-instance
  lock, change-only writes with a forced heartbeat.
- **`src/verify_list_quotes.py`**, **`src/bestofn.py`**, **`src/spec.py`**,
  **`src/seed_specs.py`**.
- **8 strategy specs**, validated, across three of the four required sources.
- **15 tests passing**, including a paper-only guard extended to scan
  `bot-hunt/src/venues.py` (which runs inside this process) and a local
  GUARD #23 field-name check with the real bug as its planted violation.

---

## ⚠ WHAT IS NOT DONE, stated plainly

1. **The wide recorder is written and dry-run but was not yet launched in this
   session.** `src/shape.py`'s second sweep was still running when the session
   wrote up, and the tier list is built from its output. **First action next
   session, before anything else:**

   ```bash
   py -3 strategy-factory/src/tiers.py
   py -3 strategy-factory/src/wide.py --dry-run
   py -3 strategy-factory/src/wide.py --interval 600
   ```

   Every hour it is not running is an hour of exchange history nobody can buy
   back. It outranks everything else in this file.

2. **It is not in either runner registry yet.** `runners/runners.json` and
   `coordinator/runners.json` both need an entry, or it is either unwatched or
   unrestarted. `devig`'s recorders died four times for exactly this, the last
   for 19 hours after a reboot.

3. **No strategy has been screened.** Stage 3 does not exist yet. That is
   deliberate — the gates in `PREREGISTRATION.md` section 6 have to pass first,
   and gate 4 (a placebo arm run once on real tape) needs tape that starts
   accruing today.

4. **The screening engine has no code.** Next session's second job, after the
   recorder is up. It must carry the placebo arm from the first run, not added
   later.

---

## The judgment calls, in one line each

Full reasoning and the rejected option in `DECISIONS.md`.

| | |
|---|---|
| **D1** | Work only in `strategy-factory/`. `bot-hunt` read, never written. |
| **D2** | Import `venues.py` rather than copy it — and extend the paper-only test to scan it. |
| **D3** | Breadth from the list endpoint, depth from the orderbook, never mixed. |
| **D4** | Change-only writes, with a heartbeat so "quiet" and "dead" stay distinguishable. |
| **D5** | The two parlay families dropped by name as well as by measurement. |
| **D6** | The best-of-N table re-derived here, and it disagrees with the plan. |
| **D7** | No virtual environment — **reversed the same day.** The shared watchdog's registry takes an interpreter path and there is no way to register `py -3`, so `.venv` exists purely so the recorder can be restarted automatically. |

**One more, taken after reading `devig`'s section in `STATUS.md`:** their
arithmetic that a concurrency pool of 8–10 would fix the existing recorder is
right, and **this recorder is still serial anyway.** Their own warning is the
reason — the 15 requests/second ceiling is *recorded, not verified*, and my
process shares the unauthenticated quota with the one holding 65 GB that cannot
be re-pulled. Breadth here comes from one request per **series** instead of per
market, which needs no extra rate at all.

---

## Two corrections this session owes the repo

**1. The best-of-N table in `coordinator/STRATEGY_FACTORY.md` understates the
danger by about four times.** Re-derived by simulation and by an exact binomial
tail, which agree:

| | plan | measured here |
|---|---|---|
| one zero-skill strategy reaches +30% over 100 bets | 1 in 10,000 | **1 in 2,289** |
| best of 2,000 reaches +30% | 37 in 100 | **58 in 100** |

The plan's figure needs the fee charged twice. `common/kalshi_fees.py` says
`exit_cents=None` means held to settlement and pays the entry fee only, and
Kalshi charges nothing at settlement. **This strengthens the plan's conclusion
rather than weakening it**, which is exactly why it had to be said out loud —
a load-bearing number that is wrong in the comfortable direction is the kind
nobody re-checks.

**2. I read the dead Kalshi field names on the first census run and the
repo-wide guard did not catch me.** `volume_dollars`/`volume` are both absent;
the live names are `volume_fp`, `open_interest_fp`, `liquidity_dollars`. Every
volume in the first census came back null and printed as `0`, which reads as a
finding about the exchange.

**The gap is worth someone's attention:**
`common/scan_legacy_kalshi_fields.py` classifies a file as venue-reaching if it
has a URL literal, calls `.json()`, or imports a known venue client. This folder
reaches Kalshi via `sys.path` plus `import venues`, which matches none of the
three, so it was scored as not touching the wire. **Any folder that imports a
sibling's client that way is invisible to GUARD #23.** Defended locally in
`tests/test_live_field_names.py`; the repo-wide fix is `common/`'s.

**Separately, `common/tests/test_no_legacy_kalshi_fields.py` is RED and it is
not this folder.** 13 unadjudicated files across `bot-hunt`, `crypto`,
`kalshi-market-scan`, `livedesk`, `market-selection`. Verified by running the
scanner and grepping for `strategy-factory`: zero hits.

---

## THE ONE THING NEEDED FROM THE USER

Three of the four idea sources in the plan are running: my own reasoning about
market structure (5 specs), the extractors (1 spec, from a GitHub repo read in
full and a YouTube method with timestamps that independently describe the same
mechanism), and the `reopen` chat's claims closed for the wrong reason (2
specs).

**The fourth is his domain knowledge, and it is the only input this repo cannot
generate.** The specific ask, which is deliberately narrow so it can be
answered in a couple of minutes on a phone:

> **Which markets do you actually know something about that the numbers would
> not tell us?** Not "which do you like" — which ones do you know behave
> differently. A league where the favourite means something different. A
> competition where teams stop trying once they are through. A time of day when
> the price moves for a reason that is not news.

Everything else proceeds without him. He does not need to answer before the
recorder runs, and the recorder does not wait on him.

---

## Next session, in order

1. **Launch the recorder.** Tiers, dry run, run. Register in both registries.
2. Confirm from `w_cycle` after 24 hours what the tape actually costs per day,
   and replace the projection in `reports/SHAPE.md` with it.
3. Build stage 3, the screening engine, **with the placebo arm in the first
   commit** — real bid, real ask, real fees from `common/kalshi_fees.py`, and
   entry priced by walking the recorded ladder.
4. Re-derive the no-skill range machinery the way `tennis` prints it for all 17
   of its bots, so a forward result never appears without one beside it.
5. Check `coordinator/mailbox/factory/` — it did not exist until this session
   created it.

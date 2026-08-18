# strategy-factory

**A machine for inventing Kalshi strategies, killing most of them cheaply, and
forward paper-trading the survivors. No money and no keys, enforced by a test.**

The plan it implements is [`coordinator/STRATEGY_FACTORY.md`](../coordinator/STRATEGY_FACTORY.md).
The rule that makes it worth anything is one sentence:

> **The backtest chooses. Only the forward test counts.**

A backtest number from this folder is never reported as money, never sized on,
and never called a result. It selects candidates. Every report says how many
strategies were screened to produce the one being shown, because without that
number a return is uninterpretable — the best of 2,000 zero-skill strategies
reaches +30% **58 times in 100** (measured here: `src/bestofn.py`).

---

## The six stages

```
  [1] WIDEN      record more of Kalshi, every day, forever   <- the urgent one
  [2] GENERATE   specs in a fixed format, before any data
  [3] SCREEN     cheap backtest on tape. Kills most. Reports nothing.
  [4] REGISTER   survivors sealed BEFORE going forward
  [5] FORWARD    paper trade on unseen markets. THIS is the result.
  [6] PROMOTE    only a forward survivor is discussed as real
```

Stage 1 is urgent and irreversible: Kalshi's history window is about 69 days
and rolling, and a closed market 404s forever. **Every day a family is not
recorded is a day of its history that no amount of money will ever buy back.**

## What is here

| | |
|---|---|
| `PREREGISTRATION.md` | the question, the drop rules, the sample sizes — written before any strategy was screened |
| `DECISIONS.md` | every judgment call taken instead of asking, with the option rejected |
| `HANDOFF.md` | where it got to, and the one thing needed from the user |
| `specs/SF*.json` | one strategy per file, validated |
| `reports/` | measurements, including the ones that contradict this repo |

### The scripts, in the order they are run

```bash
py -3 strategy-factory/src/census.py            # every series, every open market
py -3 strategy-factory/src/shape.py             # what carries a quote, and what it costs
py -3 strategy-factory/src/tiers.py             # build the recorder's tier list
py -3 strategy-factory/src/wide.py --dry-run    # one cycle, writes nothing
py -3 strategy-factory/src/wide.py              # the recorder
```

Supporting:

```bash
py -3 strategy-factory/src/verify_list_quotes.py   # does the list endpoint quote?
py -3 strategy-factory/src/bestofn.py              # the best-of-N null, re-derived
py -3 strategy-factory/src/spec.py --validate      # every spec, checked
py -3 strategy-factory/src/spec.py --list
py -3 -m pytest strategy-factory/tests -q
```

**`python` on PATH is a Microsoft Store stub.** `py -3` works for everything
here, and `.venv\Scripts\python.exe` also exists — not because anything needs
it, but because `runners/runners.json` takes an interpreter path and the shared
watchdog is what stops a recorder dying unnoticed for 19 hours. It was created
with `--system-site-packages`, so it downloads nothing. `DECISIONS.md` D7 and
its reversal.

## The recorder, in one paragraph

Two tiers, because the two endpoints cost wildly different amounts. **Tier B**
reads the top of book from Kalshi's list endpoint, which returns up to 1,000
quotes in one request, and writes a row **only when the quote changed** — so
breadth is nearly free. **Tier A** walks the full orderbook ladder on a narrow
set of families, at one request per market, because depth is the only way to
answer *"what would it actually cost to put $500 into this thin market"*. Every
row records which endpoint it came from, so the two can never be silently
mixed.

It writes `data/wide.db` and **touches nothing in `bot-hunt/`**, whose 62 GB
recorder is the best asset in this repo and is not this project's to risk.

## Two things this folder found that contradict the repo

1. **Kalshi's list endpoint carries a real quote.** `bot-hunt/src/venues.py`
   says it does not. Measured on 168 markets across 23 series: 100% of bids and
   94% of asks agree with the orderbook within one tick, and not once was the
   list blank while the book was quoted. `reports/RESULT_LIST_QUOTES.md`.
2. **The best-of-N table in the plan understates the danger about fourfold.**
   One zero-skill strategy reaching +30% over 100 bets is 1 in 2,289, not 1 in
   10,000; the plan's figure needs the fee charged twice, and Kalshi charges
   nothing at settlement. `DECISIONS.md` D6.

Both were checked by two methods before being written down, and both are
reported where the claim they contradict lives.

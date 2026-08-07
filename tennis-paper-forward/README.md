# tennis-paper-forward

**Sixteen bots trade the same Kalshi tennis matches on paper. No money, no
keys, no order endpoint — by construction, not by configuration.**

- Put it on the laptop: **[deploy/LAPTOP_SETUP.md](deploy/LAPTOP_SETUP.md)**
- What it must clear, written before it ran: **[PREREGISTRATION.md](PREREGISTRATION.md)**
- Judgment calls taken without asking: **[DECISIONS.md](DECISIONS.md)**
- Where it got to: **[HANDOFF.md](HANDOFF.md)**

---

## The one command

```bash
deploy\check.bat
```

Prints every python process on the machine first — so the two recorders are the
first thing you see — then how the test is doing and how many days remain.

## The other three

```bash
.venv\Scripts\python.exe -m src.forward --once
```
```bash
.venv\Scripts\python.exe -m src.analyse
```
```bash
.venv\Scripts\python.exe -m pytest tests -q
```

---

## What it is

| | |
|---|---|
| **five mentalities** | favourite (80c+) · underdog (5–35c) · brief-led · momentum · unconstrained |
| **× three exit modes** | hold to settle · exit once · exit and re-enter freely |
| **+ one control** | logs intended trades, takes none |
| **= 16 bots** | all in one Benjamini–Hochberg denominator |

All sixteen see the **same match pool** on the same tick. None is forced to
enter anything. A mentality is a disposition, not a rule: each owns several
tactics and decides for itself which apply, including deciding that none do.
Every bot also chooses **how much** to stake from its own confidence, inside a
fixed $500 paper bankroll, so selection skill and sizing skill can be scored
apart afterwards.

**Every decision is written to disk, with its full reasoning, before the result
exists.** That is the point of the whole exercise.

## It cannot trade

| layer | what it does |
|---|---|
| `src/safety.py` | the only network call in the package. GET only, against a host+path allowlist with no order path on it |
| same | refuses to start if any Kalshi credential is in the process environment |
| `tests/test_paper_only.py` | greps every source file for order-shaped tokens; **plants a violation and asserts the detector still bites** |

There is no signing code, no private key, and no `TRADING_DISABLED` switch —
because there is nothing to switch off.

## Where the data comes from, all free

| source | what | checked |
|---|---|---|
| Kalshi public API | 7 singles tennis series, ~250 markets / ~123 matches live | 2026-08-06 |
| `Aneeshers/tennis-sackmann-archive` | ATP + WTA + Challenger + ITF match history, rankings | 200, pushed 2026-06-25 |
| `JeffSackmann/tennis_MatchChartingProject` | real point-by-point, ~13k charted matches | 200, 399★, pushed 2026-05-25 |
| `JeffSackmann/tennis_atp` · `_wta` · `_slam_pointbypoint` | **404 — dead**, the mirror above replaces them | 2026-08-06 |
| SofaScore live scores | **not used.** `robots.txt` is 403 → UNDECIDABLE, GUARDS #14. See DECISIONS.md D3 | 2026-08-06 |

## Two things worth knowing before you read any number

**The archive stops on 2026-06-01.** Anything the brief calls "recent form" is
form as of then. `staleness_days` carries the figure into every brief so a bot
can reason about it.

**Fifty matches cannot decide whether any of this makes money.** Under BH across
sixteen bots, fifty matches detects a **22.8c** edge against a **3.6c** cost
bar. Resolving an edge the size of the cost bar needs about **2,000 settled
matches per bot**. The P&L endpoint is pre-registered as UNTESTABLE at this
sample size and `analyse.py` says so at the top of its own output.

What fifty matches *can* decide: whether the machinery survives a week, what the
brief actually covers, **what it costs to trade this market**, whether the five
mentalities are genuinely different instruments, and how much execution takes
out. Those are the primary endpoints.

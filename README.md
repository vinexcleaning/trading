# trading

Consolidated research archive for five prediction-market projects on Kalshi and
Polymarket. Code, method documents and result artifacts. **No recorded data** —
every dataset stays local (see `.gitignore`).

The headline result is negative: across four independent studies, **no tradeable
edge survived correction**. The durable output is the set of checks that killed
each candidate.

## Start here

| File | What it is |
|---|---|
| **[STATUS.md](STATUS.md)** | Threads alive vs closed, what's running, what must not be touched. Read first. |
| **[LEDGER.md](LEDGER.md)** | Every claim ever made — 216 rows, 41 retractions — with the artifact behind it or `NONE`. |
| **[GUARDS.md](GUARDS.md)** | The 12 canaries and controls, and which projects have them. **The reusable part.** |

## Projects

| Directory | Study | Verdict |
|---|---|---|
| [`set1_overshoot/`](set1_overshoot/) | Does the Kalshi tennis market overshoot after a first-set upset? | Real **under**shoot, −2.42pp — uncollectable against a 3.61pp cost bar |
| [`crypto/`](crypto/) | Can any model beat the mid on BTC/ETH/SOL/XRP hourly ladders? | **No.** 250 events, two models tie, two lose |
| [`wallet-copy-study/`](wallet-copy-study/) | Is copying profitable Polymarket wallets viable? | Skill persists, but the copyable part is smaller than the spread |
| [`kalshi-tennis/`](kalshi-tennis/) | Stage 0–5 pre-match tennis player model | Model **loses** to the bookmakers, +0.019 Brier |
| [`kalshi-chat-audit/`](kalshi-chat-audit/) | Claims audit over the source conversation archive | 129 claims, 20 retractions |

## Method

Every study pre-registers its hypotheses, applies Benjamini-Hochberg across the
whole project ledger rather than per family, reports the minimum detectable
effect beside every null, and runs a synthetic null **and** a planted-effect
positive control so that a null result is a measurement rather than a failure to
look. Fees are exact-decimal and resolved from each venue's own data rather than
its documentation. P&L is marked at actual settlement and filled at the ask.

Two of these studies were voided mid-flight by their own guards. That is what
the guards are for.

# STATUS.md

Repo-root status board. **Append your session's entry; do not overwrite others.**

No `STATUS.md` existed at any of `crypto/`, `~/`, or `kalshi/` when this session
looked (2026-08-01 ~07:00 UTC), so this file is created here. If another session
has one elsewhere, merge rather than replace.

---

## Session: crypto market-making feasibility — 2026-08-01, laptop (`C:\Users\gianf\crypto`)

**Verdict: market making on Kalshi crypto is NOT viable. It loses −1.86¢ per
contract at every latency tested, including 0 ms.**

| item | value |
|---|---|
| Scope | Kalshi `KXBTCD` (BTC hourly above/below), 58 markets / 20 events, 25 May – 1 Aug 2026 |
| Headline | NET **−1.86¢/contract**, 95% CI [−2.73, −1.53] (bootstrap over markets, n=58) |
| Spread captured | +0.557¢ |
| Adverse selection | **−2.16¢** — ~4× the spread |
| Latency curve | **flat** 0→1000 ms; latency is not the binding constraint |
| Maker fee | **0¢ — verified**, corrects earlier 0.25×-taker assumption |
| Retractions this session | 3 (see `HANDOFF.md` §3) |

**Cumulative across all crypto phases: 20 hypotheses, ~105 tests, 0 tradeable
edges surviving, 6 withdrawn positives.**

Key artifacts: `HANDOFF.md`, `MM_RESULTS.md`, `MORNING_REPORT.md`,
`WHAT_WE_ACTUALLY_TESTED.md`, `HYPOTHESIS_LEDGER.md`, `docs/venue_spec.md`.

**Cross-session correction:** Kalshi's maker fee is **zero on crypto**
(`fee_type: quadratic` = taker-only; only 130 of 12,368 series carry maker
fees, none crypto). Any sibling session assuming 0.25× taker on crypto is wrong.

---

## Session: exchange-wide market-making scan — 2026-08-01 ~07:30 UTC, same repo

**Verdict: market making is closed EXCHANGE-WIDE, not just in crypto. Crypto was
the BEST of four categories tested, not the worst.**

| series | category | algo score | net ¢/ct | 95% CI (n markets) |
|---|---|---|---|---|
| KXBTCD | Crypto | 0.380 | **−1.84** | [−2.08, −0.48] (5) |
| KXATPSETWINNER | Sports | 0.389 | −3.74 | [−14.05, +2.76] (14) |
| KXNPBGAME | Sports | 0.431 | −4.81 | [−11.78, −1.37] (14) |
| KXUFCFIGHT | Sports | 0.505 | −4.63 | [−11.73, −3.08] (14) |

**0 of 4 profitable.** corr(counterparty algo-score, adverse selection) =
**−0.076** — no relationship. The "retail flow is less toxic" mechanism is
**not supported**. Weather (`KXHIGHLAX`, `KXRAIN`) and Elections
(`KXPRESNOMD`) were unmakeable — no fills or no settled markets.

Census: 12,368 series; Crypto is 271 series (2.2%) but **59% of exchange trade
flow** in the sampled window.

---

## Session: path-dependence + streak tests — 2026-08-01 ~09:00 UTC, same repo

**Verdict: both ideas closed. Buy-cheap-sell-the-spike loses −2¢ to −7¢/contract
in every cell; the streak idea is directionally backwards (reversal, not
momentum).**

| test | n + unit | result |
|---|---|---|
| Touch/expectancy matrix | 89,819 mkt-min / 1,968 mkts / **250 events**, 25 May–30 Jul 26 | every CI-excluding-zero cell **negative**, −2.18¢ to −7.25¢ |
| Spikes are real | same | 10¢ contract touches 15¢ **43.8%** of the time, median 7 min — and still loses |
| Streak: 8/10 ups → buy up | 190 windows of 6,429, 25 May–1 Aug 26 | **46.32%** vs a **51.75%** break-even bar |
| Strongest streak effect | 1,513 windows | 2 consecutive ups → next up **45.87%**, p=0.0014 — **REVERSAL** |
| Autocorrelation of settlement sign | 6,429 windows | lag1 **−0.0273**, lag2 **−0.0287**, both CI-excluding-zero; lags 3–20 null |
| Unconditional up rate | 6,429 windows | **49.23%** (p=0.22) — confirms the 49.29% figure |

**Retracted:** my own synthetic control's first version reported **+9.46¢** of
expectancy on structureless data (clipped random walk broke the martingale).
Fixed to `p_t = Φ(W_t/√(T−t))` before any real number was reported.

**Cumulative: ~30 hypotheses, ~160 tests, 0 tradeable edges, 7 withdrawn
positives.**

---

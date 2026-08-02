# PATH_STREAK_RESULTS.md

Written for a non-specialist. 2026-08-01. All data already on disk; no money,
no orders, simulated fills only.

---

## 1. The touch matrix — "buy at 10¢, sell the spike"

**Data:** 89,819 market-minutes, 1,968 markets, **250 events**, KXBTCD,
25 May – 30 Jul 2026. Entry at the real **ask**, exit at the real **bid**, two
taker fees for a round trip, one fee if it never touches and settles. CIs
bootstrap **events**.

| entry | target | opportunities | P(bid touches) | median min | net ¢/contract | 95% CI |
|---|---|---|---|---|---|---|
| 5¢ | +5¢ | 11,749 | 29.28% | 8 | **−2.18** | [−2.53, −1.81] |
| 5¢ | +10¢ | 11,749 | 22.44% | 12 | **−1.76** | [−2.29, −1.19] |
| 5¢ | +50¢ | 11,749 | 10.58% | 22 | +0.87 | [−0.91, +2.82] |
| 10¢ | +5¢ | 5,773 | 43.76% | 7 | **−4.32** | [−4.95, −3.73] |
| 10¢ | +10¢ | 5,773 | 37.40% | 9 | **−3.32** | [−4.23, −2.43] |
| 10¢ | +50¢ | 5,773 | 16.49% | 21 | −0.09 | [−2.60, +2.34] |
| 15¢ | +5¢ | 4,049 | 56.79% | 5 | **−4.91** | [−5.74, −4.09] |
| 20¢ | +5¢ | 3,288 | 63.41% | 4 | **−6.03** | [−6.99, −5.10] |
| 25¢ | +5¢ | 2,933 | 66.74% | 4 | **−7.25** | [−8.38, −6.19] |

**The spikes are real. A 10¢ contract touches 15¢ within a median of 7 minutes,
43.8% of the time. And it still loses money.** Every cell with a confidence
interval that excludes zero is **negative**. The four cells with positive point
estimates (the +50¢ targets) all have intervals straddling zero — they are
noise, not edge, and they rest on the rarest events (10–28% touch rates).

Why: the 56% of the time it *doesn't* touch, you are holding a contract that
usually settles worthless. The winners are exactly offset by the losers, which
is what it means for the price to be fair — and then fees and the spread take
the difference.

## 2. Does volatility help or hurt? — one sentence

**Volatile contracts are priced for their volatility, so the swings you would
trade are the reason the contract is cheap, not a flaw in its price.** Measured:
per-minute mid movement rises from **1.74¢** at a 5¢ entry to **7.75¢** at 50¢
and falls symmetrically to **3.69¢** at 90¢ — and net expectancy is *worst*
(−7.25¢) exactly where volatility and fees are highest.

## 3. The streak table — "8 of 10 went up, buy up"

**Data:** 6,429 settled `KXBTC15M` windows, 25 May – 1 Aug 2026. Unit = window.
Unconditional up rate **49.23%** (p=0.22 vs 50%) — this confirms the 49.29%
figure carried into this session.

**Break-even bar at a 50¢ entry, hold-to-settlement, one fee: 51.75%.**

| condition | n | next-up % | by chance | binom p | clears 51.75%? |
|---|---|---|---|---|---|
| 8/10 ups (the actual proposal) | 190 | **46.32%** | 4.39% | 0.346 | ❌ no |
| 7/10 ups | 688 | **45.64%** | 11.72% | 0.024 | ❌ no |
| 5/5 ups | 154 | 46.10% | 3.12% | 0.376 | ❌ no |
| **2 consecutive ups** | **1,513** | **45.87%** | — | **0.0014** | ❌ no |
| 4 consecutive ups | 334 | 46.11% | — | 0.171 | ❌ no |
| 6 consecutive ups | 71 | 43.66% | — | 0.343 | ❌ no |
| 5 consecutive **downs** | 167 | **56.29%** | — | 0.121 | ✅ yes |
| 4 consecutive **downs** | 372 | **55.11%** | — | 0.055 | ✅ yes |

**The streak idea is exactly backwards.** After a run of ups the next window is
*less* likely to be up, not more. Every up-streak condition lands **below** 50%,
and the proposal's own cell (8/10 ups) gives **46.32%** — you would be buying at
a 51.75% bar something that happens 46.32% of the time.

Note the chance column: 8-of-10 occurs 4.39% of the time by pure luck, and there
are 96 windows a day, so that pattern appears about **four times daily in data
with no structure at all**.

## 4. Autocorrelation — reversal, not momentum

n=6,429 windows. Lag 1: **−0.0273** [−0.0518, −0.0029]. Lag 2: **−0.0287**
[−0.0532, −0.0043]. Lags 3–20: indistinguishable from zero.

Significant **reversal** at lags 1–2, and nothing beyond. This reproduces the
mean-reversion direction carried into this session and refutes the momentum
premise.

## 5. Controls

**Synthetic control — FAILED, was fixed, then passed.** First version reported
**+4.05¢ to +9.46¢ expectancy on data built to contain none.** Cause: I built
the fake price as a random walk **clipped** to [0.02, 0.98]. Clipping destroys
the martingale property — at 5¢ the lower boundary pushes the path up more often
than down — which fabricated real drift at low entries. Rebuilt as an exact
martingale, `p_t = Φ(W_t/√(T−t))` with `y = 1{W_T>0}`: **every cell is now
negative**, matching the real data closely (real 5¢/5¢ −2.18 vs control −2.56).

Residual caveat: control gross expectancy is not exactly zero, so **absolute**
levels carry ~1–3¢ of bias. Only the real-vs-control comparison is trustworthy,
and on that comparison real and synthetic are indistinguishable.

**Selection audit** (n=1,968 markets, outcome base rate 0.5132):

| field | distinct | corr | z | verdict |
|---|---|---|---|---|
| n_minutes | 59 | −0.005 | −0.22 | clean |
| mean_spread | 855 | +0.026 | +1.14 | clean |
| mean_vol | 1,967 | +0.010 | +0.42 | clean |
| mean_oi | 1,968 | −0.054 | −2.37 | watch |
| **first_ask** | 98 | +0.661 | **+29.3** | **is the forecast** |
| **last_bid** | 66 | +0.982 | **+43.6** | **is the answer** |

`last_bid` at corr 0.982 is the same shape as the sibling session's `last_price`
leak. It is **not** used as a feature here — it appears only as an exit price at
times strictly after entry — but it must never become one.

## 6. Two-period consistency

Unconditional up rate: first half **48.16%** (n=3,214, p=0.039), second half
**50.30%** (n=3,215, p=0.751). **The down-tilt is not stable across periods** —
it exists in the first half and vanishes in the second. Any strategy resting on
the unconditional rate is resting on a regime, not a constant.

## 7. Retracted

- **My own synthetic control**, first version — reported up to +9.46¢ of
  expectancy on structureless data. Generator bug (clipping broke the
  martingale). Fixed and re-run before any real number was reported.
- **Prompt premise "if 8 of the last 10 went up, buy up"** — measured at
  **46.32%** against a 51.75% bar. The direction is wrong.

## 8. Plain-English verdict

**Idea 1 — buy cheap, sell the spike.** The spikes are real: a 10¢ contract
reaches 15¢ within seven minutes, four times out of nine. But you lose money
doing it, in every entry-and-target combination we measured, by roughly 2¢ to
7¢ per contract. The reason is simple: the times it spikes are exactly balanced
by the times it quietly expires worthless, and that balance is *what the 10¢
price means*. The price already contains the spike. You then pay a fee going in,
a fee coming out, and the gap between the buy and sell price — and that is your
whole result. Volatility does not rescue this, because the most volatile
contracts had the worst outcomes.

**Idea 2 — ride the streak.** This is backwards. After Bitcoin's 15-minute
window goes up twice in a row, the next window goes up only **45.9%** of the
time, measured over 1,513 occurrences — that is one of the strongest effects in
the whole dataset. A run of *ups* makes the next up **less** likely. The
proposal's own example, eight ups in ten, gives 46.3%, and you would need 51.75%
just to cover the fee. Worth knowing: eight-in-ten happens by pure chance about
four times a day, so seeing it means nothing on its own. The one genuinely
interesting cell is the mirror image — after four or five consecutive *downs*
the next window is up 55–56% — but that sits on 167–372 observations, does not
survive multiple-testing correction, and, critically, **we could not check the
price you would actually pay**, which is where any such effect normally goes to
die.

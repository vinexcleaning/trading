# Kalshi Live-Tennis Bot — v3 Parameter Spec

Supersedes v2. Integrates the Claude Code diagnostic session (Apify quota, staleness bug, feed alternatives, Kalshi score availability).

**Guiding principle:** the score feed is for **discovery and calibration only**. Entry timing, regime detection, and all exits derive from Kalshi price data, which is free and unlimited. This decouples the strategy from data cost.

---

## BUILD ORDER

Hand these to Claude Code in this sequence. Do not skip ahead — each step validates the next.

| Step | Task | Cost | Section |
|---|---|---|---|
| 1 | Reconcile P&L to a single source of truth | free | §1 |
| 2 | Verify staleness guard actually rejects | free | §2 |
| 3 | Build price-only structural classifier, run in shadow mode | free | §5 |
| 4 | Add Kalshi candlestick opening-price favorite | free | §6 |
| 5 | Add ESPN as a **calibration** source for ATP/WTA | free | §7 |
| 6 | Go live with Trade B only | — | §9 |
| 7 | Paper-trade Trade A for 30 signals | free | §10 |
| 8 | Re-evaluate Apify subscription with evidence | $49/mo | §7 |

---

## 1. P&L reconciliation (do this first)

Three conflicting figures exist for the 27 Jul session:

| Source | Figure |
|---|---|
| Kalshi history display (cost vs payout) | +$0.60 net |
| Raw fills | +$2.51 gross |
| App P&L tracker | −$3.55 |

**Arithmetic bound:** Kalshi's taker fee peaks at 1.75c/contract (at P=0.50) and decays toward both price extremes. 91 contracts round-trip = **$3.19 absolute maximum fee**, realistically ~$2.30 given the fill prices. Therefore true net lies between **−$0.68 and +$2.51**. The −$3.55 figure cannot be correct for this session.

**Task:** compute session P&L exclusively from the fills endpoint, including the actual `taker_fee` field returned by Kalshi on each fill. Print gross, fees, and net separately. Delete or fix whatever produces −$3.55. Every subsequent parameter decision depends on this number being right.

---

## 2. Staleness guard (verify, do not assume)

**Bug found:** `score_from_item` stamped `fetched_at = time.time()` at cache-read time rather than fetch time. `score_age_sec` always read ~0. `max_score_age_sec = 30` never rejected a single trade.

**Consequence:** every trade placed to date was entered on score data of unknown age by a bot that believed it was fresh. The 4-for-10 result is **not a valid test of the entry logic.** Treat all historical performance as provisional.

**Required:**
- Stamp `fetched_at` at genuine fetch time, propagate through cache
- Cache TTL must stay strictly below `max_score_age_sec` (currently 25s vs 30s — correct)
- Startup assertion: 45s-old score rejects, 5s-old score passes. Fail loudly on startup if this doesn't hold.
- Log `score_age_sec` on every fill so it can be correlated with outcome

---

## 3. Regime detection

Classify every tracked match on every tick. Derive from **price** primarily; score is confirmation only.

### ACT I — Drift band (mean reversion; tradeable, experimental)
- Trailing 5-minute realized price range **< 20c**
- No structural event (§5) in the last 3 minutes

### ACT II — Volatility explosion (**NO NEW ENTRIES**)
Enter if **any** of:
- Trailing 5-minute realized price range **> 30c**
- Two or more structural events in the last 6 minutes
- Score feed confirms tiebreak in progress (when available)

All six losses on 27 Jul occurred in Act II. Existing positions may be held under the structural stop; no new entries.

### ACT III — Terminal ramp (trend; tradeable, primary)
- Price has made an upward structural step (§5) **and** held above the post-step level for 2+ minutes without retracing more than 8c
- Price in the 55–78c band
- Score confirms "up a break in deciding set" or "set and a break ahead" (when available)

---

## 4. Global entry filters

| Filter | Value | Rationale |
|---|---|---|
| Max entry price | **75c** | 80c+ bucket went 1/4, lost $2.14. Target caps near 99c so reward shrinks as entry rises. **Flagged as fit to only 4 trades — see §12.** |
| Min entry price | **30c** | Below this, spread and settlement risk dominate |
| Order type | **Resting limit, 1c inside the bid** | Maker fee is 25% of taker. Cancel/re-price if unfilled after 60s. Saves ~1.1c/share vs market. |
| Max spread | **3c** | Above this, spread + fees exceed 40% of a 15c move |
| Min 24h volume | **$150,000** | Thin books make exits expensive |
| Staleness gate | **Reject if score_age > 30s**, when score is in use | Must be verified working per §2 |
| Act gate | **No new entries in ACT II** | |
| **Minimum edge test** | **Gross target ≥ 4× round-trip fee** | At 2.3c fees, minimum viable target is ~10c. Below that the trade cannot pay for itself. |

---

## 5. Price-only structural classifier (core component)

Replaces reliance on the score feed for break detection. Runs on Kalshi price data alone — free, unlimited, zero lag, works on ITF and Challenger where no free score source exists.

```
delta = price_now - price_45s_ago

if abs(delta) >= 12c:
    -> STRUCTURAL EVENT (break of serve, or equivalent)
    -> direction = sign(delta)

elif abs(delta) >= 20c over any 5-minute window:
    -> SET-LEVEL EVENT

elif abs(delta) < 12c over 90+ seconds:
    -> NOISE — take no action
```

**Thresholds are provisional.** Observed step sizes from the 27 Jul charts:
- routine hold: 3–8c
- break of serve: 15–30c
- set won: 20–35c
- deciding-tiebreak point: 10–25c

**Validation task (§7):** run this classifier against ESPN ground truth on ATP/WTA matches and measure precision/recall on break detection. Tune the 12c threshold from that data, then apply the tuned value to ITF.

**Known limitation:** cannot distinguish a break from a medical timeout, retirement scare, or a single large order. Score data resolves this; price data cannot. Accept a false-positive rate and size accordingly.

---

## 6. Kalshi candlestick opening price (free favorite detection)

Kalshi's candlestick history exposes the opening price. First candle `open` = the market's pre-match favorite, with no external feed and no cost.

**Uses:**
- Establish the pre-match baseline for measuring dislocation ("price has moved Xc from open")
- Skip matches where the open was above 85c or below 15c — no room for the strategy
- Store `open_price` on every candidate for post-hoc analysis of whether favorites or dogs produced the edge

---

## 7. Data sources — roles and decision

| Source | Status | Role |
|---|---|---|
| **Kalshi prices** | free, unlimited | **Primary.** All entries, exits, regime detection, structural classification |
| **Kalshi candlesticks** | free | Pre-match favorite, dislocation baseline |
| **ESPN** | free, no key, ATP/WTA + qualifying only | **Calibration set.** Ground truth for tuning the price classifier. Secondary trading feed on liquid markets. |
| **Apify → SofaScore** | $49/mo, quota-limited | Optional. ITF/Challenger score coverage. |
| SofaScore direct | 403 Cloudflare | dead |
| Flashscore direct | 401 | dead |
| TheSportsDB | free key works, 0 tennis events, live scores paid | useless |
| Kalshi score API | does not exist | confirmed absent — Kalshi sources from ITF/Flashscore/Fox/ESPN themselves |

### Apify decision

**Do not subscribe until steps 1–5 of the build order are complete.** The reason is not that the edge is unproven — it's that the price-only classifier may make the subscription unnecessary. Buying data before testing whether you need it is the wrong order.

If you do subscribe:
- Scan interval 20s ≈ $20.74/mo of usage against $49 included — comfortable headroom
- **Do not restore 20s until §2 is verified.** A 20s scan with a broken freshness stamp is the exact configuration that produced the current results.
- Quota alert at 80% consumption
- Cache TTL must remain below `max_score_age_sec`

Context for the decision: $49/mo against a $127 account requires ~38% monthly return to cover data cost alone. That ratio improves fast as the account grows; at $500+ it's negligible.

---

## 8. Exit logic

### Structural stop (replaces fixed-cent stop)

**Rationale:** a fixed-cent stop inside a mean-reverting band systematically sells local lows. Confirmed 6/6 on 27 Jul, with an average **+30c bounce** after each stop against a 15c stop distance.

Exit ladder, in priority order:

1. **Structural exit** — a structural event (§5) against the position, not reversed within 3 minutes
2. **Disaster floor** — −24c, unconditional circuit breaker; should fire rarely
3. **Time exit** — no progress within the time stop
4. **Target** — resting limit, always live on the exchange

### Order types
- Targets: **resting limit** (already correct — these filled server-side during the 27 Jul blackout)
- Stops: **limit 2c through the bid**, never market. Observed market-exit slippage was 2.2c, ~15% of the risk budget.

---

## 9. TRADE B — Terminal ramp (**PRIMARY — go live**)

| Parameter | Value |
|---|---|
| Regime | ACT III only |
| Trigger | Confirmed upward structural step, held 2+ min, no retrace > 8c |
| Entry band | 55–75c |
| Order | Resting limit, 1c inside bid |
| **Scale-out** | **Sell 50% at +15c, move stop on remainder to breakeven** |
| Final target | **95c** resting limit (not 99c — the last 4c costs disproportionate time and risk) |
| Stop | Structural (§8), disaster floor −24c |
| Time stop | None — let winners run |

**Economics:** entry ~65c, target 95c, fees ~2.0c → net win +28c, net loss −24c. **Breakeven hit rate 46%.** A player up a break in the deciding set converts at roughly 75–80% at this level. This is the trade with genuine margin.

Evidence: Paun (+$2.65) and Poljicak (+$1.18), the two clean non-lucky winners on 27 Jul, were both this setup.

---

## 10. TRADE A — Mean-reversion scalp (**PAPER ONLY — 30 signals**)

Mechanizes your own read: *"one point difference yet a sixty percent difference."*

| Parameter | Value |
|---|---|
| Regime | ACT I only |
| Trigger | Price moved **≥ 12c against a player in 90s** with **no structural event** in that window |
| Entry band | 30–70c |
| Target | **+15c** resting limit |
| Stop | Structural (§8), disaster floor −24c |
| Time stop | **12 minutes or 2 completed games** |

**Why paper-only:** entry ~50c, target +15c, stop −20c, fees ~2.6c (fee peaks near 50c) → net win +12.4c, net loss −22.6c. **Breakeven hit rate 65%.** Achievable but with almost no margin for error, and the historical evidence for it is contaminated by the staleness bug.

Run it in shadow mode alongside Trade B. It costs nothing and generates the sample you need. Promote to live only if it clears 65% across 30 logged signals.

---

## 11. Sizing and slot management

### Sizing — constant risk, not constant notional
Risk per trade on 27 Jul ranged $1.05 to $2.52 (2.4× variation) with no rationale.

```
shares = risk_budget_dollars / stop_distance_in_cents
```

| Tier | Risk per trade | When |
|---|---|---|
| Base | **1.5% of bankroll** | Trade B, live |
| Maximum | **2.5%** | Not to exceed until 50 logged trades under a working staleness guard |

On the 25%-of-capital idea: at the currently observed hit rate, that has a meaningful probability of ruin in a single session. Revisit after 50 clean trades, and cap at 5% even then.

### Slots
| Rule | Value |
|---|---|
| Cap type | **Risk budget** — total open risk ≤ 6% of bankroll (replaces flat cap of 5) |
| Stale eviction | Position > 25 min old and not in profit → force-close to free capacity |
| Blocked-candidate logging | Log every rejected candidate **and its subsequent 30-min price path** |

---

## 12. Re-entry rule

On 27 Jul the bot watched Compagnucci recover 51 → 60 → 69 → 71 → 100 and was locked out of every point of it by the position cap.

| Rule | Value |
|---|---|
| Trigger | **Structural event in the position's favor** since the stop-out (§5), or score confirmation of a break-back |
| Never trigger on | Price recovery alone. Backtest: 2 wins, 4 losses. Guarducci recovered 63 → **91c** and still settled at zero. |
| Limit | One re-entry per name per match |
| Slot priority | **Re-entries bypass the position cap** |
| Cooldown | Minimum 3 minutes after stop-out |

---

## 13. Required logging

Log per fill and per rejected candidate:

- `score_age_sec` at decision time, and the feed source
- Regime state (ACT I / II / III) and which signal triggered classification
- Structural classifier output: delta, window, classification
- Best bid, best ask, spread at decision
- Kalshi opening price for the market
- Order type, and whether it filled maker or taker
- **Actual `taker_fee` from the Kalshi fill object** — not an estimate
- Full price path for 30 minutes post-exit, including for rejected candidates
- Exit reason (target / scale-out / structural / disaster / time / eviction)

---

## 14. Open questions to resolve with data

1. **The 75c entry cap is fit to four trades.** It would have blocked three losers (−$3.32) and one winner (+$1.18). Net positive on this sample, but the sample is tiny. Log every rejected candidate above 75c with its outcome and revisit at trade 50.
2. **The 12c structural threshold is eyeballed from charts.** Calibrate against ESPN ground truth before trusting it on ITF.
3. **Does liquidity or dislocation dominate?** ATP/WTA has tighter spreads (lower cost) but more efficient pricing (less edge). ITF is the reverse. Run both and compare net edge per trade, not gross.
4. **Trade A viability.** 65% breakeven is a demanding bar. 30 paper signals will settle it.

---

## 15. Fee reference

Taker: `round_up(0.07 × C × P × (1−P))` · Maker: `round_up(0.0175 × C × P × (1−P))`

Peaks at **1.75c/contract at 50c**, decaying toward both extremes (0.63c at 90c or 10c). Note the implication: the scalping band of 40–60c is the **most expensive** part of the board to trade. Trade B's 55–75c entry and 95c exit sit in cheaper territory than Trade A's 30–70c band — another reason Trade B goes first.

Verify the current schedule at `kalshi.com/fee-schedule` before hard-coding; Kalshi revises it periodically.

---

## 16. Honest caveats

- The retrofit of these rules onto the 27 Jul trades produces roughly +$7 instead of +$0.60. **This is a six-trade fit on the data that generated the rules.** It indicates direction, not expectancy.
- All historical results were produced with a non-functional staleness guard. Treat them as provisional.
- The first 50 trades under a verified configuration are the actual test. Do not increase size before then.

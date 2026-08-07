# RESULTS — the weather gate is CLOSED. No edge, and the controls are why.

**2026-08-07.** Runs the design fixed in
[PREREGISTRATION_WEATHER_VS_MID.md](PREREGISTRATION_WEATHER_VS_MID.md),
committed at `9db1a5a` before any model score, edge or settled outcome touched a
price. Code `scripts/weather_vs_ask.py`; raw `reports/weather_vs_ask.json`.

**This was ranked the #1 open question in the programme** — the only family
clearing both the power bar (512 settlements vs 481) and the capacity bar, with a
model that genuinely beats climatology (**K002**), and with `GO_NO_GO.md` saying
of the deciding comparison: *"Edge vs the mid: still unmeasured."*

**It is now measured. There is no edge, the negative control says so before the
result does, and the reason is worth more than the null.**

---

## 1. The verdict in one table

| | persist_hod *(the real model)* | **N1 climatology** | **N3 always-50** |
|---|---|---|---|
| mean net at 1.0¢ slippage | **+0.43¢** | **+1.37¢** | **+1.01¢** |
| 95% CI (bootstrapped over settlement hours) | [−2.01, +4.30] | [−1.64, +5.24] | [−2.07, +5.24] |
| settlement hours trading | 67 | 72 | 68 |
| **median qualifying ask** | **1.0¢** | **1.0¢** | **1.0¢** |

> **N1 fires, and §3.1 of the pre-registration says exactly what that means:**
> *"If climatology trades as well as the real model, the 'edge' is the cost gate
> selecting cheap asks, not the forecast. **N1 positive ⇒ nothing is
> reportable.**"*
>
> Climatology does not merely trade as well — **it trades better**, +1.37¢
> against +0.43¢. And **N3, a model that assigns 50% to everything and knows
> nothing at all, also clears the gate at +1.01¢.**

**N2, the permutation null: two-sided p = 0.9200.** The real result sits exactly
at its own null's 90th percentile (null mean −2.00¢, sd 1.28¢, p90 **+0.43¢** —
the observed value to two decimals).

**Every cell's CI crosses zero, at every slippage, for every model.** Nothing
qualified to face the holdout. **The holdout — 132 settlement hours — is sealed
and untouched**, written to `reports/weather_holdout_hours.json`.

---

## 2. ⚠ The finding that outlives the null: at open, this market has no price

The gate selected 1-cent tickets in **every** cell. That is not a coincidence,
and the ask distribution at the market's open explains the whole result:

| ask at open | markets | market's implied probability | **actual win rate** |
|---|---|---|---|
| 0–2¢ | 127 | 0.010 | **0.008** ✅ calibrated |
| 2–5¢ | 1 | 0.020 | 0.000 |
| 5–20¢ | 1 | 0.100 | 0.000 |
| 20–50¢ | 5 | 0.430 | 0.400 |
| 50–80¢ | 42 | 0.614 | 0.143 |
| 80–95¢ | 1 | 0.900 | 1.000 |
| **95–100¢** | **2,286 (93%)** | **0.983** | **0.459** |

**Ninety-three per cent of strikes are offered at about 98¢ against a 46% actual
win rate, with no bid underneath.** That is not a mispricing. **It is a
placeholder offer on a market that has not opened an opinion yet** — the same
object as B024/B027 on tennis, where every apparent edge turned out to be
monotonic in book width and absent wherever the book was tradeable.

Three consequences:

1. **The only genuinely priced corner is the cheap tail**, and it is *correctly*
   priced: 0–2¢ asks imply 1.0% and win 0.8%. There is nothing there either.
2. **This is why the naive benchmark is catastrophic.** Buying every quotable
   market is **−59.46¢ per contract** [−63.10, −55.72] — you are lifting 98¢
   offers on coin flips.
3. **`K004`'s capacity bar was not measured at this moment.** It reports 2,972
   contracts of depth on `KXTEMPDCH`; at the open there is **no bid on any of
   2,463 markets**. Both can be true — the book forms *during* the hour, as the
   temperature becomes knowable — but **the depth a strategy could actually use
   at decision time is not the depth that was counted.** Same shape as
   RESULTS.md §3's esports cost bar, measured at the busiest moment of the
   busiest market.

---

## 3. What this does and does not overturn

**K002 stands untouched.** The model really does beat climatology as a *forecast*
— 812 independent settlements, clustered CIs excluding zero, positive control
present. Nothing here contradicts it.

> **And that is precisely the point worth carrying away.** The model is the
> better forecaster and the *worse trader*: climatology out-traded it, and a
> model that knows nothing out-traded it too. **Forecast quality and tradeable
> edge are different quantities**, and this is the cleanest demonstration of it
> anywhere in the programme, because the same model wins on one and loses on the
> other on the same 440 settlement hours.

**What is retired:** the phrase *"edge vs the mid"*. There is no mid to compare
to — **0 of 2,463 markets are two-sided at open** — and constructing one would be
**T008**, the retraction that turned +24.6% ROI into −30.9% by pricing at a mid
nobody trades at. The gate was tested against the **ask**, which is strictly
harder and is the only executable price that exists.

**What is now closed:** weather was the last untested corner this programme had
identified. `GO_NO_GO.md`'s *"the closest thing to a live candidate"* has been
run to a number.

## 4. Limitations, stated rather than buried

1. **One family, one city.** `KXTEMPDCH` only. The three other hourly families
   are a **replication arm** under §3.3 and were not run, because the
   pre-registration says they run only if `KXTEMPDCH` survives. It did not.
2. **A candle is not a book.** `yes_ask_open` is the offer at the start of the
   hour; **depth is unknown** and a qualifying 1¢ offer may be for one contract.
   §2.5 of the pre-registration flagged this in advance and it is unresolved.
3. **440 settlement hours, 308 in train.** The MDE on a per-hour mean at this
   dispersion is roughly ±2.5¢, so a sub-2¢ true edge is not excluded — it is
   unevidenced, and it would have to survive controls that a null model passes.
4. **This is a 22-day window** (2026-07-08 → 07-30), which is all the retention
   window holds for this family.

## 5. Reproduce

```bash
C:/Users/vinig/trading/kalshi-market-scan/.venv/Scripts/python.exe scripts/weather_vs_ask.py
```

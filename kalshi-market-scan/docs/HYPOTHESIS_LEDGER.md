# Hypothesis ledger

> **This file counts hypotheses. It does not track claim status.**
> For that, this project now has rows in the repo-wide ledger:
> **[`LEDGER.md` — Section 6, K001–K016](../../LEDGER.md)**, added 2026-08-03.
>
> Until then this project had **no rows there at all**, which is why three
> retracted results and one overstatement survived in the shorter, more
> quotable `GO_NO_GO.md` and `shortlist.md`. Anything asserting a status —
> SETTLED, RETRACTED, UNVERIFIED — belongs in the repo-wide ledger so it is
> visible to the same cross-check as every other project.

Every distinct model/parameter/market combination evaluated tonight. FDR control is
applied **across this whole ledger**, not per family.

## Total: 116 hypotheses evaluated

(Plus two measurement exercises that are not hypothesis tests: the live microstructure
profile in `reports/btc15m_microstructure.csv` and the weather depth measurement. Both
describe the market rather than test a claim about it, so neither enters FDR.)

| # | Block | Hypotheses | Where | FDR-corrected within block | Survivors |
|---|---|---|---|---|---|
| 1 | Synthetic control — negative (3 cases x 6 models) | 18 | `reports/synthetic_control.csv` | yes | **0** (required) |
| 2 | Synthetic control — positive (1 case x 6 models) | 6 | same | yes | 3 (required >0) |
| 3 | BTC fair value (5 decision offsets x 7 models) | 35 | `reports/btc15m_fair_value.csv` | yes | 25 vs coinflip only |
| 4 | BTC seasonal-sigma vs flat sigma (5 offsets) | 5 | `reports/btc15m_seasonal_sigma.csv` | paired CI | **0** |
| 5 | BTC direction: sign persistence (4 horizons) | 4 | `reports/btc_analysis.json` | reported raw | 3 significant, **0 above cost bar** |
| 6 | BTC direction: ETH lead-lag (21 lags, tested jointly) | 1 | same | — | **0** |
| 7 | Copy trading: persistence, raw and price-matched | 2 | `reports/copytrade_tests_v2.json` | — | 2 |
| 8 | Copy trading: skill-vs-luck across 2,579 wallets | 1 | `reports/copytrade_skill_v2.csv` | BH across wallets | 274/2,579 |
| 9 | Copy trading: favourite-longshot naive strategy (4 price bands) | 4 | inline | — | 4 |
| 10 | Weather models (4 cities x 4 models) | 16 | `reports/weather_model.csv` | yes, across all 4 cities jointly | 10 beat climatology; **0 established edge vs market** |
| 11 | Kalshi sports calibration (v3, buckets x 3 horizons) | 30 | `reports/kalshi_longshot_v3.json` | binomial per bucket | **0** (underpowered: CIs +/-11-29pp) |
| 12 | Kalshi flow following (5 imbalance buckets + 2 correlations) | 7 | `reports/flow_predicts_outcome.json` | — | **0** |
| 13 | KXBTC15M vs mid (7 offsets, market-clustered) | 7 | `reports/vs_mid_clustered.csv` | market bootstrap | **0** |
| | **TOTAL** | **116** | | | |

Note on #8: it is one *hypothesis* in this ledger ("do any wallets have skill?") but it
internally tests 2,579 wallets, and BH is applied across all of them. 516 were
significant at raw p<0.05 against ~129 expected by chance; 274 survive FDR.

## Deviations from pre-registration, logged as new hypotheses

- **#4 was added mid-run.** The intra-window vol decay was discovered while analysing
  seasonality (not pre-registered), so testing whether it improves the forecast is a
  new hypothesis. It was pre-specified before being run, evaluated on a strict 60/40
  time split with the seasonal fit on train only, and **it failed.** Counted.
- **#10 was added mid-run.** Testing the weather model became possible once I realised
  `expiration_value` on settled markets reconstructs the temperature series, which was
  not anticipated when the recorders were designed. Counted.
- **#11-13 were added after the exchange reopened**, once live books and a large trade
  tape existed. All three are the decisive versions of tests the brief asked for, and all
  three returned nulls. Counted.
- **#9 was added mid-run** after the price-bucket table revealed the favourite-longshot
  pattern. Counted, and it is the finding that reframes the whole copy-trading block.
- **The v1 copy-trading run is excluded from the ledger** because it was invalid, not
  merely unsuccessful: it treated non-independent fills as independent observations.
  It is documented in `scripts/copytrade_tests_v2.py` and the morning report as a
  methodological error rather than counted as a tested hypothesis.

## Deflated Sharpe

Not computed, deliberately. A deflated Sharpe ratio requires a P&L time series from a
strategy sweep, and **no Phase 7 strategy sweep was run** — nothing cleared Phase 1 and
Phase 4 with a mechanism plus fillable liquidity, so there was no candidate to sweep.
Computing a deflated Sharpe on the null result would be theatre. `evaluate.py` ships
`deflated_sharpe_ratio()` ready for when a candidate exists.

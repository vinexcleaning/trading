# README_DEFECTS.md — known defects and traps in this project

Written 2026-07-31. Read this before trusting any file in `reports\` or `data\`.

All research in this folder was produced in a single session on **2026-07-29, 12:22–15:13**.
The defects below were found afterwards, during an audit of the chat history. Nothing here has
been re-run since 2026-07-29.

---

## 1. `data\kalshi\kalshi_prematch_prices.parquet.INVALID_LOOKAHEAD_LEAK` — do not use

**Status: renamed, not deleted.** Original name was `kalshi_prematch_prices.parquet`.
Superseded by `data\kalshi\kalshi_prices_multianchor.parquet`, read at the **−6h** anchor.

**What's wrong.** These "pre-match" prices were anchored on the market's `occurrence_datetime`
field. For many Kalshi tennis markets that field is **at or after the match end** — it equals
`expected_expiration_time`. Kalshi publishes no match-start field, so taking the last candlestick
at or before `occurrence_datetime` returns a **post-settlement price**.

**Measured signature in this exact file** (4,968 markets):

| Check | Value |
|---|---|
| Rows anchored **< 1 hour** before `occurrence_datetime` | 4,194 of 4,968 — **84.5%** |
| Rows anchored **< 6 hours** before | 4,891 of 4,968 — **98.6%** |
| Mid prices outside 2c–98c | 212 — **4.3%** |

That 4.3% matches the 4.1% recorded in `anchor_leak_test.txt`, where those extreme quotes were
found to be **100% correct**. A genuine pre-match market is rarely that confident, and when it is,
it is right about 95% of the time — not 100%.

**What it contaminated.** This file fed the Kalshi benchmark in `stage4_model.txt` and
`stage4_kalshi_liquid.txt`, and the P&L in `stage5_selective.txt`. It also produced a
now-retracted headline finding that **"Kalshi beats the Betfair Exchange closing line by 0.022
Brier"** — impossible for a real market, and the thing that led to the leak being found.

It did **not** touch the bookmaker benchmark in `stage4_model.txt` (Benchmark 1), which contains no
Kalshi data. That result — the model losing to the books by +0.019 Brier, n=2,645 — is unaffected
and remains valid.

**What to use instead.** `data\kalshi\kalshi_prices_multianchor.parquet`, which carries
`bid_h{0,1,2,6,24}` / `ask_h*` / `mid_h*` columns. Use the **h6** set. `anchor_leak_test.txt` shows
why: at −6h the extreme-quote rate falls to 0.1%, correlation with the books rises to 0.978, and the
Kalshi−Betfair difference sits at +0.0012 instead of −0.0176.

**Why it was kept.** It is the only record of what the leaking pull contained, and it is the
evidence behind the retraction. Deleting it would make the correction unauditable. It must never be
loaded by a script.

> **If you re-run this pipeline:** Kalshi has no published match-start field, so the safe anchor
> must be re-validated empirically each time — do not assume −6h transfers to a new pull, a new
> sport, or a new market family. Re-run the anchor sweep in `src\anchor_leak_test.py`.

---

## 2. `pinnacle_vs_kalshi.txt` / `src\pinnacle_vs_kalshi.py` — the benchmark is **Betfair**, not Pinnacle

**Status: misleading name, correct contents.** The analysis is sound; only the naming is wrong.

tennis-data.co.uk **stopped publishing Pinnacle odds in 2026** — coverage collapsed to **5.1%** of
rows. The report says so explicitly in its own header block:

```
with a real Pinnacle price    0   (why Pinnacle is not the benchmark)
```

The sharp benchmark actually used is the **Betfair Exchange closing price** (93.6% coverage in
2026), with the book average as a control. For tennis that is at least as sharp as Pinnacle, so the
substitution is defensible — but the filenames were never updated.

**Where this misleads:**

- The script and report are both still named `pinnacle_vs_kalshi`.
- `stage4_model.txt` still prints a row labelled **"Pinnacle closing: 1,774 matches"** under
  BENCHMARK 1. That row uses tennis-data's `PSW`/`PSL` columns where present, so it is a genuine
  Pinnacle subset — but it sits next to the Betfair-based analysis under a shared name, and the two
  are easy to conflate.
- Any summary quoting "we tested against Pinnacle" is describing the Betfair result.

**Fix if you touch this:** rename to `betfair_vs_kalshi.*` and relabel. Do not re-run to "get
Pinnacle back" — the data does not exist for 2026.

---

## 3. `stage2_chosen_k.csv` — **not a defect. Previously reported as empty; that was wrong.**

An earlier inventory of this project recorded `data\cache\stage2_chosen_k.csv` as **0 bytes** and
flagged it as a missing pipeline output. **That was an error in the inventory, not in the file.**
The size had been displayed in megabytes rounded to three decimals, so 307 bytes rendered as
`0.000` and was misread as empty.

The file is **307 bytes and fully populated** — all 16 statistic × bucket shrinkage constants:

```
serve_pts_won|all,100    first_won|all,50     df|all,100      rtn_pts_won|all,400
serve_pts_won|surf,200   first_won|surf,100   df|surf,100     rtn_pts_won|surf,400
first_in|all,100         ace|all,50           hold|all,25     break|all,10
first_in|surf,100        ace|surf,50          hold|surf,25    break|surf,10
```

These match the `k` column in `stage2_shrinkage.txt` exactly. Stage 2 completed correctly and
nothing downstream is missing an input.

**Recorded here so the non-defect does not get re-raised** — and as a reminder that a rounded
display is not a measurement.

---

## Cross-reference

| File | Status |
|---|---|
| `stage0_coverage.txt` | Valid — this is the **corrected** run, after the ITF series omission was fixed (ITF ≈ 76% of Kalshi's tennis book had been excluded by a hand-written title regex; coverage fell from 74.5% to 36.9%). |
| `stage2_shrinkage.txt` | Valid. |
| `stage3_traits.txt` | Valid. |
| `stage4_model.txt` | Benchmark 1 (bookmakers) **valid**. Benchmark 2 (Kalshi) **contaminated** by defect 1. See §2 on the "Pinnacle" label. |
| `stage4_kalshi_liquid.txt` | Contaminated by defect 1 — but its *conclusion* (market beats model once wide quotes are excluded) is directionally reinforced, not reversed, by removing the leak. |
| `stage5_selective.txt` | Contaminated by defect 1. Note its own separate and still-valid finding: **mid-price fills show +14% to +25% ROI; executable ask/bid fills show −24% to −31%.** A result that only survives at mid-fill is not a result. |
| `anchor_leak_test.txt` | Valid — this is the diagnostic that found defect 1. |
| `pinnacle_vs_kalshi.txt` | Valid, at the −6h anchor. See §2 on the name. |

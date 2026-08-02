# DECISIONS.md

Ambiguities resolved without asking, per operating mode. Conservative reading
taken each time.

| # | ambiguity | conservative reading taken | why |
|---|---|---|---|
| 1 | "every asset with adequate ladder history" — which series? | `KXETHD`, `KXSOLD`, `KXXRPD` (the `greater` above/below ladders) | Direct analogues of `KXBTCD`, which produced the BTC result. Comparing like with like. `KXDOGED` excluded — no strike on any of 83,030 rows. |
| 2 | Panel size for non-BTC assets | 150 events × 6 strikes (vs BTC's 250 × 8) | API is shared with other sessions; three series at BTC's density would take ~3 h and risk 429s. 150 events still clears the 200-event floor when pooled and is stated as a limitation rather than hidden. |
| 3 | Effective-n for a single asset | report nominal n; effective-n applies only to CROSS-asset claims | Within one asset, windows are the unit and are not obviously correlated; the 1.81 figure is about agreement BETWEEN assets. |
| 4 | Task 6 costing with <200 windows | do not run; report accrual status only | "Never substitute an assumed entry price" and three bars have already been wrong-shaped. Underpowered costing would be a fourth. |
| 5 | `no_bid_size` / `no_ask_size` null in recorder rows | keep, do not treat as defect | Kalshi does not return NO-side sizes; YES sizes are present and the NO price is what the fade needs. Logged so a future session does not chase it. |
| 6 | Which "hourly" BTC series is the ladder | `KXBTCD` (above/below) not `KXBTC` (bucket) | Already established: `KXBTC` has 3× the spread but 1/29 the flow. |
| 7 | Whether to re-pull settled data that has grown | no | Audited clean this session; the window 2026-05-25 → 2026-08-01 is fixed for every test so far, and changing it mid-session would break comparability. |

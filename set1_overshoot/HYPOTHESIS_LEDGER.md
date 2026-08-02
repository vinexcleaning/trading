# HYPOTHESIS_LEDGER.md

Every hypothesis evaluated in this study, in the order it was evaluated.
Benjamini-Hochberg FDR is applied across **this entire table**, not per phase.

- **Total hypotheses evaluated: 97**
- Tests with a computable p-value: 80
- BH is applied to **two-sided** p-values, because an undershoot is a finding here and a one-sided overshoot test would hide it.
- BH threshold at q=0.1: p <= 0.03740
- **Surviving FDR: 30**

| # | phase | factor | level | n | mis pp | 95% CI | p (2-sided) | net c | BH | note |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 2 | headline | deep:12 (pre-committed primary) | 5390 | -0.84 | [-2.10, +0.42] | 0.2058 | -4.792 | no | nan |
| 2 | 2 | headline | deep:30@38 (best-targeted) | 3436 | -2.42 | [-3.90, -0.93] | 0.0019 | -6.114 | **yes** | nan |
| 3 | 2 | headline | label-verified subsample | 223 | -5.94 | [-11.66, -0.23] | 0.0664 | -9.548 | no | nan |
| 4 | 2-grid | entry definition | deep:8+0 | 5542 | -0.91 | [-2.17, +0.32] | 0.1585 | -4.847 | no | nan |
| 5 | 2-grid | entry definition | deep:12+0 | 5390 | -0.84 | [-2.12, +0.40] | 0.2021 | -4.792 | no | nan |
| 6 | 2-grid | entry definition | deep:16+0 | 4973 | -1.55 | [-2.87, -0.21] | 0.0242 | -5.483 | **yes** | nan |
| 7 | 2-grid | entry definition | deep:20+0 | 4551 | -1.84 | [-3.23, -0.43] | 0.0098 | -5.741 | **yes** | nan |
| 8 | 2-grid | entry definition | deep:25+0 | 4052 | -2.52 | [-4.01, -1.08] | 0.0008 | -6.361 | **yes** | nan |
| 9 | 2-grid | entry definition | deep:30+0 | 3611 | -2.40 | [-3.90, -0.93] | 0.0022 | -6.170 | **yes** | nan |
| 10 | 2-grid | entry definition | deep:12@38+0 | 4827 | -1.37 | [-2.69, -0.05] | 0.0469 | -5.239 | no | nan |
| 11 | 2-grid | entry definition | deep:20@38+0 | 4188 | -2.19 | [-3.52, -0.77] | 0.0031 | -6.008 | **yes** | nan |
| 12 | 2-grid | entry definition | deep:30@38+0 | 3436 | -2.42 | [-3.91, -0.89] | 0.0019 | -6.114 | **yes** | nan |
| 13 | 2-grid | entry definition | deep:12+5 | 4781 | -1.52 | [-2.86, -0.20] | 0.0291 | -5.398 | **yes** | nan |
| 14 | 2-grid | entry definition | deep:12+10 | 4358 | -1.93 | [-3.28, -0.56] | 0.0079 | -5.752 | **yes** | nan |
| 15 | 2-grid | entry definition | cp+0 | 3524 | +0.14 | [-1.28, +1.62] | 0.8612 | -3.483 | no | nan |
| 16 | 2-grid | entry definition | cp+5 | 3285 | +0.24 | [-1.19, +1.67] | 0.7833 | -3.361 | no | nan |
| 17 | 2-grid | entry definition | cp+10 | 3115 | -0.07 | [-1.59, +1.48] | 0.9490 | -3.679 | no | nan |
| 18 | 2-grid | entry definition | cp+15 | 2934 | +0.20 | [-1.36, +1.70] | 0.8196 | -3.330 | no | nan |
| 19 | 2-grid | entry definition | cp+20 | 2733 | -0.06 | [-1.66, +1.49] | 0.9642 | -3.613 | no | nan |
| 20 | 2-grid | entry definition | causal:5+0 | 3846 | -1.34 | [-2.79, +0.19] | 0.0814 | -5.246 | no | nan |
| 21 | 2-grid | entry definition | causal:8+0 | 3940 | -1.41 | [-2.91, +0.04] | 0.0640 | -5.316 | no | nan |
| 22 | 2-grid | entry definition | causal:12+0 | 3866 | -1.97 | [-3.41, -0.50] | 0.0114 | -5.819 | **yes** | nan |
| 23 | 2-grid | entry definition | causal:16+0 | 3434 | -1.99 | [-3.59, -0.39] | 0.0142 | -5.801 | **yes** | nan |
| 24 | 2-grid | entry definition | fixed+25 | 3094 | -1.81 | [-3.44, -0.15] | 0.0330 | -5.846 | **yes** | nan |
| 25 | 2-grid | entry definition | fixed+30 | 3296 | -1.16 | [-2.74, +0.43] | 0.1580 | -5.121 | no | nan |
| 26 | 2-grid | entry definition | fixed+35 | 3326 | -1.16 | [-2.69, +0.45] | 0.1609 | -5.059 | no | nan |
| 27 | 2-grid | entry definition | fixed+40 | 3341 | -2.09 | [-3.66, -0.52] | 0.0108 | -5.982 | **yes** | nan |
| 28 | 2-grid | entry definition | fixed+45 | 3335 | -1.59 | [-3.19, -0.02] | 0.0516 | -5.461 | no | nan |
| 29 | 2-grid | entry definition | fixed+50 | 3316 | -1.69 | [-3.26, -0.12] | 0.0396 | -5.577 | no | nan |
| 30 | 2-grid | entry definition | fixed+60 | 3381 | -1.33 | [-2.87, +0.25] | 0.0960 | -5.092 | no | nan |
| 31 | 2-grid | entry definition | fixed+75 | 3279 | -1.65 | [-3.13, -0.06] | 0.0374 | -5.309 | **yes** | nan |
| 32 | 2-grid | entry definition | cpleak-10 | 4390 | +6.96 | [+5.59, +8.22] | 0.0000 | +2.990 | **yes** | DELIBERATE LEAK, diagnostic only |
| 33 | 2-grid | entry definition | cpleak+0 | 3898 | -2.67 | [-4.02, -1.31] | 0.0003 | -6.401 | **yes** | DELIBERATE LEAK, diagnostic only |
| 34 | 4-holdout | top config | f_strength=90+ | 153 | +3.72 | [-2.72, +9.79] | 0.3180 | +0.268 | no | holdout, run once |
| 35 | 4-holdout | top config | f_drop=30c+ | 283 | +2.09 | [-3.25, +7.46] | 0.4782 | -1.490 | no | holdout, run once |
| 36 | 4-holdout | top config | f_drop=5-10c | 333 | +1.50 | [-3.39, +6.38] | 0.5846 | -2.225 | no | holdout, run once |
| 37 | 4-holdout | undershoot, deep:30@38 | all | 3436 | -2.42 | [-3.93, -0.89] | 0.0018 | -1.195 | **yes** | fade side; p is one-sided for UNDERSHOOT |
| 38 | 4-holdout | undershoot, deep:30@38 | train (oldest 60%) | 2062 | -2.51 | [-4.45, -0.54] | 0.0116 | -1.200 | **yes** | fade side; p is one-sided for UNDERSHOOT |
| 39 | 4-holdout | undershoot, deep:30@38 | holdout (newest 40%) | 1374 | -2.27 | [-4.67, +0.17] | 0.0620 | -1.188 | no | fade side; p is one-sided for UNDERSHOOT |
| 40 | 5-1b | maker fill | improve/5min | 2437 | +nan | - | - | -0.949 | no | fill 0.709; per-opportunity, 1/4 fee |
| 41 | 5-1b | maker fill | improve/10min | 2738 | +nan | - | - | -0.871 | no | fill 0.797; per-opportunity, 1/4 fee |
| 42 | 5-1b | maker fill | improve/20min | 2897 | +nan | - | - | -0.831 | no | fill 0.843; per-opportunity, 1/4 fee |
| 43 | 5-1b | maker fill | improve/30min | 2971 | +nan | - | - | -0.905 | no | fill 0.865; per-opportunity, 1/4 fee |
| 44 | 5-1b | maker fill | improve/endmin | 3029 | +nan | - | - | -1.220 | no | fill 0.882; per-opportunity, 1/4 fee |
| 45 | 5-1b | maker fill | join_ask/5min | 2167 | +nan | - | - | -0.205 | no | fill 0.631; per-opportunity, 1/4 fee |
| 46 | 5-1b | maker fill | join_ask/10min | 2528 | +nan | - | - | -0.304 | no | fill 0.736; per-opportunity, 1/4 fee |
| 47 | 5-1b | maker fill | join_ask/20min | 2749 | +nan | - | - | -0.456 | no | fill 0.800; per-opportunity, 1/4 fee |
| 48 | 5-1b | maker fill | join_ask/30min | 2849 | +nan | - | - | -0.592 | no | fill 0.829; per-opportunity, 1/4 fee |
| 49 | 5-1b | maker fill | join_ask/endmin | 2940 | +nan | - | - | -0.871 | no | fill 0.856; per-opportunity, 1/4 fee |
| 50 | 5-1b | maker fill | passive/5min | 1889 | +nan | - | - | -0.314 | no | fill 0.550; per-opportunity, 1/4 fee |
| 51 | 5-1b | maker fill | passive/10min | 2312 | +nan | - | - | -0.421 | no | fill 0.673; per-opportunity, 1/4 fee |
| 52 | 5-1b | maker fill | passive/20min | 2593 | +nan | - | - | -0.585 | no | fill 0.755; per-opportunity, 1/4 fee |
| 53 | 5-1b | maker fill | passive/30min | 2725 | +nan | - | - | -0.654 | no | fill 0.793; per-opportunity, 1/4 fee |
| 54 | 5-1b | maker fill | passive/endmin | 2844 | +nan | - | - | -0.976 | no | fill 0.828; per-opportunity, 1/4 fee |
| 55 | 2 | headline | deep:12 (pre-committed primary) | 1609 | -0.59 | [-2.92, +1.71] | 0.6377 | -3.790 | no | nan |
| 56 | 2 | headline | deep:30@38 (best-targeted) | 846 | -2.07 | [-5.13, +0.97] | 0.2003 | -5.191 | no | nan |
| 57 | 2 | headline | deep:12 (pre-committed primary) | 1632 | +4.04 | [+1.80, +6.25] | 0.0003 | +0.847 | **yes** | nan |
| 58 | 2 | headline | deep:30@38 (best-targeted) | 873 | +3.37 | [+0.31, +6.42] | 0.0302 | +0.263 | **yes** | nan |
| 59 | 5-seg | pooled | ALL | 3436 | +2.42 | [-2.67, +0.32] | 0.0019 | -1.195 | **yes** | bar +3.61pp; MDE 2.15c |
| 60 | 5-seg | T1 hour UTC | 00:00–04:00 UTC | 195 | +4.11 | [-5.28, +6.96] | 0.2475 | +0.806 | no | bar +3.30pp; MDE 9.03c |
| 61 | 5-seg | T1 hour UTC | 04:00–08:00 UTC | 221 | +4.63 | [-4.51, +7.12] | 0.1628 | +1.140 | no | bar +3.49pp; MDE 8.48c |
| 62 | 5-seg | T1 hour UTC | 08:00–12:00 UTC | 1161 | +2.93 | [-3.54, +1.64] | 0.0338 | -0.923 | **yes** | bar +3.85pp; MDE 3.70c |
| 63 | 5-seg | T1 hour UTC | 12:00–16:00 UTC | 988 | +1.15 | [-5.33, +0.36] | 0.4611 | -2.442 | no | bar +3.59pp; MDE 4.01c |
| 64 | 5-seg | T1 hour UTC | 16:00–20:00 UTC | 671 | +2.67 | [-4.09, +2.54] | 0.1415 | -0.745 | no | bar +3.41pp; MDE 4.87c |
| 65 | 5-seg | T1 hour UTC | 20:00–24:00 UTC | 200 | +0.73 | [-8.53, +3.32] | 0.8794 | -2.655 | no | bar +3.38pp; MDE 8.91c |
| 66 | 5-seg | T2 hour ET | 00:00–04:00 ET | 221 | +4.63 | [-4.99, +6.80] | 0.1588 | +1.140 | no | bar +3.49pp; MDE 8.48c |
| 67 | 5-seg | T2 hour ET | 04:00–08:00 ET | 1161 | +2.93 | [-3.45, +1.71] | 0.0332 | -0.923 | **yes** | bar +3.85pp; MDE 3.70c |
| 68 | 5-seg | T2 hour ET | 08:00–12:00 ET | 988 | +1.15 | [-5.28, +0.35] | 0.4575 | -2.442 | no | bar +3.59pp; MDE 4.01c |
| 69 | 5-seg | T2 hour ET | 12:00–16:00 ET | 671 | +2.67 | [-4.23, +2.67] | 0.1396 | -0.745 | no | bar +3.41pp; MDE 4.87c |
| 70 | 5-seg | T2 hour ET | 16:00–20:00 ET | 200 | +0.73 | [-9.03, +3.25] | 0.8959 | -2.655 | no | bar +3.38pp; MDE 8.91c |
| 71 | 5-seg | T2 hour ET | 20:00–24:00 ET | 195 | +4.11 | [-5.59, +6.93] | 0.2524 | +0.806 | no | bar +3.30pp; MDE 9.03c |
| 72 | 5-seg | T3 tier | ATP | 192 | +7.97 | [-1.44, +10.63] | 0.0175 | +4.795 | **yes** | bar +3.18pp; MDE 9.10c |
| 73 | 5-seg | T3 tier | CHALL | 556 | +1.87 | [-5.13, +2.28] | 0.3574 | -1.533 | no | bar +3.40pp; MDE 5.35c |
| 74 | 5-seg | T3 tier | ITF-M | 1275 | +1.80 | [-4.44, +0.63] | 0.1765 | -1.914 | no | bar +3.72pp; MDE 3.53c |
| 75 | 5-seg | T3 tier | ITF-W | 1204 | +2.52 | [-3.59, +1.22] | 0.0605 | -1.216 | no | bar +3.74pp; MDE 3.63c |
| 76 | 5-seg | T3 tier | WTA | 209 | +1.89 | [-7.49, +4.65] | 0.6058 | -1.293 | no | bar +3.19pp; MDE 8.72c |
| 77 | 5-seg | T4 hour x tier | CHALL @ 04:00–08:00 ET | 162 | +3.83 | [-6.41, +7.23] | 0.3239 | +0.387 | no | bar +3.44pp; MDE 9.91c |
| 78 | 5-seg | T4 hour x tier | CHALL @ 08:00–12:00 ET | 179 | +3.40 | [-6.90, +6.40] | 0.3615 | -0.064 | no | bar +3.47pp; MDE 9.42c |
| 79 | 5-seg | T4 hour x tier | ITF-M @ 04:00–08:00 ET | 453 | +0.59 | [-7.65, +0.68] | 0.8208 | -3.403 | no | bar +3.99pp; MDE 5.92c |
| 80 | 5-seg | T4 hour x tier | ITF-M @ 08:00–12:00 ET | 357 | +0.48 | [-8.04, +1.61] | 0.8874 | -3.252 | no | bar +3.73pp; MDE 6.67c |
| 81 | 5-seg | T4 hour x tier | ITF-M @ 12:00–16:00 ET | 205 | +1.05 | [-8.86, +3.78] | 0.8063 | -2.429 | no | bar +3.48pp; MDE 8.81c |
| 82 | 5-seg | T4 hour x tier | ITF-W @ 04:00–08:00 ET | 450 | +3.46 | [-4.61, +3.48] | 0.1198 | -0.527 | no | bar +3.99pp; MDE 5.94c |
| 83 | 5-seg | T4 hour x tier | ITF-W @ 08:00–12:00 ET | 285 | -0.70 | [-10.01, +0.95] | 0.8481 | -4.432 | no | bar +3.73pp; MDE 7.47c |
| 84 | 5-seg | T4 hour x tier | ITF-W @ 12:00–16:00 ET | 217 | +7.35 | [-1.81, +9.55] | 0.0237 | +3.791 | **yes** | bar +3.56pp; MDE 8.56c |
| 85 | 6-margin | reference | all label-verified | 479 | +5.75 | [-1.89, +6.05] | 0.0067 | +2.141 | **yes** | bar +3.61pp MDE 5.71c |
| 86 | 6-margin | set-1 margin | 6-0 / 6-1 | 36 | +nan | - | - | +nan | no | skipped n<40 |
| 87 | 6-margin | set-1 margin | 6-2 / 6-3 | 160 | +8.15 | [-2.03, +11.12] | 0.0316 | +4.564 | **yes** | bar +3.58pp MDE 9.47c |
| 88 | 6-margin | set-1 margin | 6-4 / 7-5 | 190 | +4.12 | [-6.39, +7.00] | 0.2552 | +0.466 | no | bar +3.66pp MDE 9.51c |
| 89 | 6-margin | set-1 margin | 7-6 tiebreak | 93 | +1.84 | [-10.95, +7.22] | 0.7889 | -1.632 | no | bar +3.47pp MDE 13.15c |
| 90 | 6-margin | tiebreak | set 1 went to a tiebreak | 93 | +1.84 | [-11.04, +7.29] | 0.7952 | -1.632 | no | bar +3.47pp MDE 13.15c |
| 91 | 6-margin | tiebreak | set 1 did not | 386 | +6.69 | [-1.43, +7.45] | 0.0054 | +3.050 | **yes** | bar +3.64pp MDE 6.33c |
| 92 | 6-margin | games in set 1 | 6–8 games (blowout) | 99 | +10.86 | [-1.18, +14.79] | 0.0202 | +7.196 | **yes** | bar +3.66pp MDE 11.31c |
| 93 | 6-margin | games in set 1 | 9–10 games | 223 | +5.58 | [-3.95, +7.95] | 0.0868 | +1.992 | no | bar +3.58pp MDE 8.46c |
| 94 | 6-margin | games in set 1 | 11+ games (long set) | 157 | +2.77 | [-8.18, +6.25] | 0.5142 | -0.835 | no | bar +3.60pp MDE 10.33c |
| 95 | 6-margin | best-of | best-of-5 (Slam men's main draw) | 73 | +6.22 | [-7.28, +13.02] | 0.3123 | +3.033 | no | bar +3.19pp MDE 14.75c |
| 96 | 6-margin | best-of | best-of-3 (everything else) | 406 | +5.66 | [-2.31, +6.34] | 0.0144 | +1.981 | **yes** | bar +3.68pp MDE 6.19c |
| 97 | 6-margin | join canary | labelled join | 3436 | +nan | - | - | +nan | no | UNTESTABLE |
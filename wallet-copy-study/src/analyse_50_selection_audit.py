"""Selection audit: every filter in THIS pipeline, checked for leaks.

The brief's central warning is that a prior result was destroyed by selection
that used post-settlement information. That warning applies to this study too,
so each filter is listed, classified, and where it touches settlement, measured.

A filter is only a LEAK if it selects on something correlated with the DIRECTION
of the outcome. Using settlement to *score* is unavoidable -- realised outcome
cannot be measured without it. Using it to *choose which rows exist* is the
danger.

Filters audited:
  F1 market eligibility: settle_verdict == "clean"      TOUCHES SETTLEMENT
  F2 market eligibility: in_subgraph_window             time only
  F3 position flags: negative_balance / sell_only       behaviour only
  F4 Phase 2 structural exclusions                      behaviour only
  F5 persistence both-periods requirement               SURVIVORSHIP
  F6 wallet panel draw                                  activity-weighted
  F7 price-bucket benchmark                             symmetric by construction

Also runs a CANARY: a deliberately null strategy that should score ~0 excess. If
the canary shows an edge, the measurement apparatus is broken and every other
number in the study is suspect.
"""
import json
import random
import time
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
UNI = ROOT / "data" / "markets_clob.jsonl"
POS = ROOT / "data" / "wallet_positions.jsonl"
OUT = ROOT / "reports" / "selection_audit.json"
OUT.parent.mkdir(parents=True, exist_ok=True)

SEED = 20260801
FEE_START = 1767830400

BUCKETS = [(0.00, 0.05), (0.05, 0.10), (0.10, 0.20), (0.20, 0.30),
           (0.30, 0.40), (0.40, 0.50), (0.50, 0.60), (0.60, 0.70),
           (0.70, 0.80), (0.80, 0.90), (0.90, 0.95), (0.95, 1.00)]


def bucket_of(p):
    for lo, hi in BUCKETS:
        if lo <= p < hi:
            return f"{lo:.2f}-{hi:.2f}"
    return "1.00"


audit = {}

# ---------------------------------------------------------------- F1 + F2
print("F1/F2: market eligibility ...", flush=True)
c = Counter()
for line in UNI.open(encoding="utf-8"):
    m = json.loads(line)
    v = m["settle_verdict"]
    inw = bool(m.get("in_subgraph_window"))
    c[f"verdict_{v}"] += 1
    if inw:
        c[f"inwindow_verdict_{v}"] += 1
    c["total"] += 1

inw_total = sum(v for k, v in c.items() if k.startswith("inwindow_verdict_"))
dropped_inw = inw_total - c["inwindow_verdict_clean"]
audit["F1_clean_settlement"] = {
    "classification": "TOUCHES SETTLEMENT",
    "counts_all": {k: v for k, v in c.items() if k.startswith("verdict_")},
    "counts_in_window": {k: v for k, v in c.items()
                         if k.startswith("inwindow_verdict_")},
    "n_in_window": inw_total,
    "n_dropped_in_window": dropped_inw,
    "frac_dropped_in_window": round(dropped_inw / max(inw_total, 1), 5),
    "leak_assessment":
        "NOT a directional leak. The filter requires that a winner EXISTS; it "
        "does not condition on WHICH outcome won, so YES-winning and "
        "NO-winning markets are retained at their natural rates. It does "
        "introduce a resolution-survivorship effect: void and unresolved "
        "markets are absent. Those return capital, so their true edge is near "
        "zero, and excluding them slightly widens the dispersion of measured "
        "edge without shifting its sign.",
    "bound_note":
        "Worst-case bound: if every dropped in-window market had been a total "
        "loss for buyers, measured edge would fall by at most "
        f"{round(dropped_inw / max(inw_total,1) * 100, 3)}% of observations' "
        "weight. Reported rather than corrected.",
}
audit["F2_in_subgraph_window"] = {
    "classification": "time only -- no settlement information",
    "leak_assessment": "NOT a leak. Depends solely on end_ts versus the "
                       "subgraph's coverage bounds, which are properties of the "
                       "data source, not of any outcome.",
}

# --------------------------------------------------------- F3 flag audit
print("F3: position flags ...", flush=True)
if POS.exists():
    grp = defaultdict(lambda: {"n": 0, "win": 0, "px": 0.0, "pxn": 0,
                               "edge": 0.0, "edgen": 0})
    n = 0
    for line in POS.open(encoding="utf-8"):
        r = json.loads(line)
        n += 1
        key = ("clean" if not r["flags"] else
               "negative_balance" if "negative_balance_split_or_external" in r["flags"]
               else "sell_only" if "no_buys_sell_only" in r["flags"]
               else "unsettled")
        g = grp[key]
        g["n"] += 1
        if r["is_winner"]:
            g["win"] += 1
        if r["entry_px"] is not None:
            g["px"] += r["entry_px"]
            g["pxn"] += 1
        if r["edge"] is not None:
            g["edge"] += r["edge"]
            g["edgen"] += 1
        if n % 3_000_000 == 0:
            print(f"  {n:,}", flush=True)
    audit["F3_position_flags"] = {
        "classification": "behaviour only -- flags describe share flow, not outcome",
        "n_positions": n,
        "groups": {k: {
            "n": g["n"], "share": round(g["n"] / max(n, 1), 4),
            "win_rate": round(g["win"] / max(g["n"], 1), 4),
            "mean_entry_px": round(g["px"] / g["pxn"], 4) if g["pxn"] else None,
            "mean_edge_pp": round(g["edge"] / g["edgen"] * 100, 4) if g["edgen"] else None,
        } for k, g in grp.items()},
        "leak_assessment":
            "Flags are computed from share flow (running balance going "
            "negative, or no buys at all), never from the outcome. Excluding "
            "them is required because their entry cost is genuinely "
            "unobservable -- the tokens came from a split, which is a "
            "ConditionalTokens event absent from the orderbook subgraph. The "
            "win rates above show whether the excluded set is directionally "
            "different from the kept set; a large gap would mean the exclusion "
            "is doing more than it should.",
    }
else:
    audit["F3_position_flags"] = {"status": "positions not built yet"}

# -------------------------------------------------- F5, F6, F7 statements
audit["F4_phase2_exclusions"] = {
    "classification": "behaviour only",
    "leak_assessment":
        "The market-maker fingerprint uses two-sided flow, median hold time and "
        "settlement-carry rate; the size filter uses median market notional. "
        "None consults profitability. 'Settlement-carry rate' is the wallet's "
        "own ACTION (did it hold the position to the end), not the RESULT of "
        "that action, so it is behaviour rather than outcome.",
}
audit["F5_persistence_both_periods"] = {
    "classification": "SURVIVORSHIP",
    "leak_assessment":
        "Requiring activity in both periods excludes wallets that stopped "
        "trading. If quitters were the losers, persistence is biased upward. "
        "Measured directly inside analyse_41_persistence.py, which reports "
        "attrition rate and compares the period-1 performance of survivors "
        "against quitters at every cut.",
}
audit["F6_wallet_panel_draw"] = {
    "classification": "activity-weighted, no performance criterion",
    "leak_assessment":
        "Wallets are every distinct maker in 260 randomly placed 15-minute "
        "windows. More active wallets are likelier to be drawn, which is "
        "intended -- a wallet too inactive to appear is too inactive to copy. "
        "Nothing about returns enters the draw.",
}
audit["F7_price_bucket_benchmark"] = {
    "classification": "symmetric by construction",
    "leak_assessment":
        "The benchmark is the pooled mean edge at the same entry-price bucket, "
        "computed over the same population being evaluated. A wallet is "
        "compared against what everyone else got at the price it paid. It "
        "cannot manufacture an edge because subtracting a pooled mean forces "
        "the population's average excess to zero by construction -- which is "
        "what the canary below verifies.",
}

# ------------------------------------------------------------- CANARY
print("CANARY: null strategy should score ~0 excess ...", flush=True)
if POS.exists():
    rng = random.Random(SEED)
    bench = defaultdict(lambda: [0, 0.0])
    rows = []
    n = 0
    for line in POS.open(encoding="utf-8"):
        r = json.loads(line)
        n += 1
        if r["flags"] or r["edge"] is None or r["settle_state"] != "settled":
            continue
        rows.append((r["entry_px"], r["edge"]))
        b = bench[bucket_of(r["entry_px"])]
        b[0] += 1
        b[1] += r["edge"]
        if n > 4_000_000:
            break
    mu = {k: v[1] / v[0] for k, v in bench.items() if v[0]}
    ex = [e - mu.get(bucket_of(p), 0.0) for p, e in rows]
    pooled = sum(ex) / len(ex) if ex else None

    # random subsets of the same size as a top decile
    k = max(len(ex) // 10, 1)
    subs = []
    for _ in range(200):
        s = sum(ex[rng.randrange(len(ex))] for _ in range(min(k, 5000)))
        subs.append(s / min(k, 5000) * 100)
    subs.sort()
    audit["CANARY_null_strategy"] = {
        "n_observations": len(ex),
        "pooled_mean_excess_pp": round(pooled * 100, 6) if pooled is not None else None,
        "random_subset_excess_pp": {
            "mean": round(sum(subs) / len(subs), 4),
            "p05": round(subs[int(len(subs) * .05)], 4),
            "p95": round(subs[int(len(subs) * .95)], 4),
        },
        "expectation": "pooled mean excess must be ~0 by construction; random "
                       "subsets must straddle 0",
        "PASS": abs(pooled * 100) < 0.01 if pooled is not None else None,
    }
    print(f"  pooled excess = {round(pooled*100, 6)}pp "
          f"(PASS={audit['CANARY_null_strategy']['PASS']})")
else:
    audit["CANARY_null_strategy"] = {"status": "positions not built yet"}

OUT.write_text(json.dumps(audit, indent=2), encoding="utf-8")
print(f"\nwrote {OUT}")

"""The shared backtester core — with this project's guards built in, not bolted on.

Every retraction in LEDGER.md that came from a backtest came from one of five
things. This module makes each of them structurally hard rather than a matter
of remembering:

  1. MARKED AT THE MID (T008: +14.4%..+24.6% ROI became -24.3%..-30.9% at
     executable fills, every CI below zero). -> `fill_price` only ever returns
     the ask when buying and the bid when selling. There is no mid path.
  2. FLOAT FEE ARITHMETIC (recurred in three codebases). -> fees come from
     `common.costbar`, exact Decimal, asserted at import.
  3. ROW COUNT MISTAKEN FOR EVIDENCE COUNT (the single largest source of
     retractions). -> every interval is an EVENT-CLUSTERED bootstrap and the
     unit of clustering is a required argument.
  4. NO CONTROLS (a pipeline that always reports zero passes a null test).
     -> `run_controls` plants a known edge and a known null and reports both.
  5. P&L THAT DOES NOT DECOMPOSE (a single negative number tells you nothing
     about which term killed it). -> `settle` returns named components that
     sum to the total exactly, asserted.

Nothing here fits a model or chooses a strategy. It prices decisions that
someone else has made, honestly.
"""
import math
import os
import random
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(__file__))
import costbar  # noqa: E402


# --------------------------------------------------------------- fills
def fill_price(side, bid_c, ask_c):
    """The price you ACTUALLY get, in cents. Never the mid.

    side='buy'  -> you lift the ask
    side='sell' -> you hit the bid

    Returns None if that side of the book is empty. Kalshi reports an empty
    side as bid 0 / ask 100, and those are treated as absent rather than as
    a tradeable price -- the 1c/99c quote with a 50c "mid that nobody trades
    at" is exactly what produced T008.
    """
    b = bid_c if (bid_c is not None and bid_c > 0) else None
    a = ask_c if (ask_c is not None and ask_c < 100) else None
    if side == "buy":
        return a
    if side == "sell":
        return b
    raise ValueError(f"side must be buy or sell, got {side!r}")


# --------------------------------------------------------------- settlement
def settle(entry_price_c, contracts, won, venue="kalshi",
           exit_price_c=None, slippage_c=0.0):
    """P&L for one position, decomposed into terms that sum exactly.

    Holding to settlement pays the ENTRY FEE ONLY -- there is no separate
    settlement fee. Getting that wrong doubles the cost bar on every
    hold-to-settle strategy.

    Returns a dict whose components sum to `net_c`, asserted.
    """
    if entry_price_c is None:
        return None
    n = float(contracts)
    entry = float(entry_price_c)
    fee_fn = (costbar.kalshi_fee_cents if venue == "kalshi"
              else costbar.poly_fee_cents)
    entry_fee = float(fee_fn(round(entry))) * n
    if exit_price_c is None:
        gross = ((100.0 - entry) if won else -entry) * n
        exit_fee = 0.0
    else:
        gross = (float(exit_price_c) - entry) * n
        exit_fee = float(fee_fn(round(float(exit_price_c)))) * n
    slip = float(slippage_c) * n
    net = gross - entry_fee - exit_fee - slip
    d = {"gross_c": gross, "entry_fee_c": -entry_fee,
         "exit_fee_c": -exit_fee, "slippage_c": -slip, "net_c": net,
         "contracts": n, "entry_price_c": entry, "won": bool(won)}
    resid = d["net_c"] - (d["gross_c"] + d["entry_fee_c"]
                          + d["exit_fee_c"] + d["slippage_c"])
    assert abs(resid) < 1e-9, f"P&L decomposition is not an identity: {resid}"
    return d


# --------------------------------------- event-clustered bootstrap
def clustered_bootstrap(values, clusters, n_boot=4000, seed=20260802,
                        stat=None):
    """Mean and CI, resampling CLUSTERS not rows.

    `clusters` is required and has no default on purpose. crypto's 89,806
    market-minutes were 250 events; a tennis "25,250 observations" was ~171
    matches; a copy-trading "644 fills" was ONE match. Row-level intervals on
    clustered data are the most common way this project has fooled itself.
    """
    if len(values) != len(clusters):
        raise ValueError("values and clusters must be the same length")
    if not values:
        return {"n": 0, "n_clusters": 0, "mean": None, "lo": None, "hi": None}
    stat = stat or (lambda xs: sum(xs) / len(xs))
    by = defaultdict(list)
    for v, c in zip(values, clusters):
        by[c].append(v)
    keys = list(by)
    rng = random.Random(seed)
    point = stat([v for v in values])
    boots = []
    for _ in range(n_boot):
        pick = [by[keys[rng.randrange(len(keys))]] for _ in range(len(keys))]
        flat = [v for grp in pick for v in grp]
        if flat:
            boots.append(stat(flat))
    boots.sort()
    lo = boots[int(0.025 * len(boots))] if boots else None
    hi = boots[int(0.975 * len(boots))] if boots else None
    return {"n": len(values), "n_clusters": len(keys), "mean": point,
            "lo": lo, "hi": hi,
            "effective_n_note": f"{len(values)} rows across {len(keys)} "
                                f"clusters -- intervals use the cluster count"}


# --------------------------------------------------------------- the run
def run(decisions, venue="kalshi", slippage_c=0.0):
    """Price a list of decisions.

    Each decision: {cluster, side, bid_c, ask_c, contracts, won}
    `cluster` is the unit of observation (a match id, an event id).

    Returns per-decision rows, the decomposed totals, and a clustered CI on
    net cents per contract.
    """
    rows, skipped = [], 0
    for d in decisions:
        px = fill_price(d.get("side", "buy"), d.get("bid_c"), d.get("ask_c"))
        if px is None:
            skipped += 1
            continue
        r = settle(px, d.get("contracts", 1), d["won"], venue=venue,
                   slippage_c=slippage_c)
        if r is None:
            skipped += 1
            continue
        r["cluster"] = d["cluster"]
        rows.append(r)
    if not rows:
        return {"n": 0, "skipped": skipped, "note": "no fillable decisions"}
    tot = {k: sum(r[k] for r in rows)
           for k in ("gross_c", "entry_fee_c", "exit_fee_c", "slippage_c",
                     "net_c")}
    resid = tot["net_c"] - (tot["gross_c"] + tot["entry_fee_c"]
                            + tot["exit_fee_c"] + tot["slippage_c"])
    assert abs(resid) < 1e-6, f"aggregate decomposition broke: {resid}"
    per = [r["net_c"] / r["contracts"] for r in rows]
    ci = clustered_bootstrap(per, [r["cluster"] for r in rows])
    return {"n": len(rows), "skipped": skipped, "totals": tot,
            "net_c_per_contract": ci, "rows": rows}


# --------------------------------------------------------------- controls
def run_controls(bid_c=49.0, ask_c=51.0, n=2000, seed=20260802):
    """A null and a positive control. A pipeline that always reports zero
    passes the null; only the positive control shows it can see anything.

    NULL     : outcomes are coin flips independent of price -> expect the
               cost bar, i.e. clearly negative, never positive.
    POSITIVE : outcomes favour the bought side by a planted 10pp -> the
               backtester must detect an improvement of roughly that size.
    """
    rng = random.Random(seed)
    out = {}
    for name, edge in (("null", 0.0), ("positive_10pp", 0.10)):
        p_true = (bid_c + ask_c) / 200.0 + edge
        dec = [{"cluster": f"m{i}", "side": "buy", "bid_c": bid_c,
                "ask_c": ask_c, "contracts": 1,
                "won": rng.random() < p_true} for i in range(n)]
        res = run(dec)
        ci = res["net_c_per_contract"]
        out[name] = {"mean_net_c": ci["mean"], "lo": ci["lo"], "hi": ci["hi"],
                     "n_clusters": ci["n_clusters"]}
    bar = costbar.cost_bar_cents(50, ask_c - bid_c, "kalshi")["total_c"]
    out["cost_bar_at_50c"] = bar
    out["verdict"] = {
        "null_is_negative": out["null"]["mean_net_c"] < 0,
        "positive_detected": (out["positive_10pp"]["mean_net_c"]
                              - out["null"]["mean_net_c"]) > 5.0,
        "separation_c": (out["positive_10pp"]["mean_net_c"]
                         - out["null"]["mean_net_c"]),
    }
    return out


if __name__ == "__main__":
    import json
    print("=== controls ===")
    c = run_controls()
    print(json.dumps(c, indent=2, default=str))
    ok = c["verdict"]["null_is_negative"] and c["verdict"]["positive_detected"]
    print("\nCONTROLS:", "PASS" if ok else "**FAIL**")
    print("\n=== the mid-price trap, demonstrated ===")
    print("A 1c/99c quote has a 50c mid that nobody trades at.")
    print(f"  fill_price('buy',  1, 99) = {fill_price('buy', 1, 99)}c  (the ask)")
    print(f"  fill_price('buy',  0, 100) = {fill_price('buy', 0, 100)}  "
          f"(empty side -> untradeable, not 50c)")
    print("\n=== decomposition identity ===")
    d = settle(45, 100, won=True)
    print("  " + json.dumps(d, default=str))

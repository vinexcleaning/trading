r"""Position sizing sweep: the binding constraint turned out to be capital, not edge.

The 2% stake produced +294.9% / -60.1% / +184.7% across three windows, while the
SAME signals without a capital constraint gave +265.3% / +36.3% / +150.0%. The
difference is entirely cash scheduling: peak exposure hit $22,000 against a
$10,000 bankroll, and 172-257 signals were skipped because the money was already
committed. Which signals you can afford then decides the outcome, which is not a
property of the wallets at all.

So this sweeps the two knobs that control that -- stake fraction, and a cap on
total simultaneous exposure -- and asks a deliberately harsh question: **is there
a sizing that is positive in ALL THREE windows?** A configuration that wins on
average across windows but loses badly in one is not a configuration anyone
should run, because you do not get to pick which window you live through.

Stake is a fixed fraction of the STARTING bankroll throughout, so nothing here is
flattered by compounding into larger bets after a lucky run.
"""
import json
import sys
from bisect import bisect_left
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from spec_pipeline import (  # noqa: E402
    add_excess, fee, price_band_benchmark, rank_within_category,
)

ROOT = Path(__file__).resolve().parents[1]
PANEL = ROOT / "data" / "spec_panel.jsonl"
FLAGS = ROOT / "data" / "wallet_flags.json"
BOOKS = [ROOT / "data" / "spec_task5_fills.jsonl",
         ROOT / "data" / "exit_fills.jsonl", ROOT / "data" / "fills.jsonl"]
OUT = ROOT / "reports" / "spec_sizing_sweep.json"

CUTS = [("2025-01-01", 1735689600), ("2025-07-01", 1751328000),
        ("2026-01-08_fee_era", 1767830400)]
FILT = {"min_trades": 20, "min_events": 10, "recent_within_days": 30,
        "max_gap_days": 30}
MIN_RANKED, DELAY, MAX_LOOKAHEAD = 30, 60, 3600
BANKROLL = 10_000.0
COST_PP = 1.000   # CORRECTED: 10-level book gives 1.000pp at $200, not 0.675
CAT = "politics"

STAKE_FRACS = [0.005, 0.01, 0.02, 0.05]
EXPOSURE_CAPS = [0.25, 0.50, 1.00]        # fraction of bankroll at risk at once

MM = set(json.loads(FLAGS.read_text(encoding="utf-8"))["excluded"])

print("loading books...", flush=True)
bts, bpx = defaultdict(list), defaultdict(list)
for p in BOOKS:
    if not p.exists():
        continue
    for line in p.open(encoding="utf-8"):
        try:
            f = json.loads(line)
        except Exception:  # noqa: BLE001
            continue
        t = f.get("token")
        if t is None:
            continue
        bts[t].append(f["ts"])
        bpx[t].append(f["price"])
for t in bts:
    z = sorted(zip(bts[t], bpx[t]))
    bts[t] = [a for a, _ in z]
    bpx[t] = [b for _, b in z]
print(f"  {len(bts):,} tokens")


def px_at(tok, when):
    ts = bts.get(tok)
    if not ts:
        return None
    i = bisect_left(ts, when)
    if i >= len(ts) or ts[i] - when > MAX_LOOKAHEAD:
        return None
    return bpx[tok][i]


rows = [json.loads(l) for l in PANEL.open(encoding="utf-8")]

# precompute the signal stream per cut once
streams = {}
for cut_label, cut in CUTS:
    sel = [r for r in rows if r["ts"] < cut]
    mea = [r for r in rows if r["ts"] >= cut]
    add_excess(sel, price_band_benchmark(sel))
    f2 = dict(FILT)
    f2["exclude"] = MM
    scores, _ = rank_within_category(sel, CAT, f2, None)
    if len(scores) < MIN_RANKED:
        continue
    order = sorted(scores, key=lambda w: -scores[w])
    top = set(order[:max(len(order) // 10, 1)])
    sig = []
    for r in sorted((x for x in mea if x["cat"] == CAT and x["w"] in top),
                    key=lambda x: x["ts"]):
        p = px_at(r["tok"], r["ts"] + DELAY)
        if p is None:
            continue
        eff = p + COST_PP / 100.0
        if not 0 < eff < 1:
            continue
        sig.append((r["ts"], eff, r["outcome"],
                    r.get("end_ts") or r["ts"] + 86400 * 30))
    streams[cut_label] = sig
    print(f"  {cut_label}: {len(sig):,} priceable signals")


def run(sig, stake, cap):
    cash = BANKROLL
    open_pos = []
    committed = 0.0
    taken = skipped = 0
    eq_min = BANKROLL
    peak_eq = BANKROLL
    maxdd = 0.0
    for ts, eff, outcome, res_ts in sig:
        keep = []
        for rts, payout, amt in open_pos:
            if rts <= ts:
                cash += payout
                committed -= amt
            else:
                keep.append((rts, payout, amt))
        open_pos = keep
        eq = cash + sum(p for _, p, _ in open_pos)
        peak_eq = max(peak_eq, eq)
        maxdd = max(maxdd, (peak_eq - eq) / peak_eq if peak_eq > 0 else 0)
        eq_min = min(eq_min, eq)
        if cash < stake or committed + stake > cap * BANKROLL:
            skipped += 1
            continue
        shares = stake / eff
        payout = shares * outcome - fee(eff) * shares
        cash -= stake
        committed += stake
        open_pos.append((res_ts, payout, stake))
        taken += 1
    for _, payout, _ in open_pos:
        cash += payout
    return {"final": cash, "pnl": cash - BANKROLL,
            "ret_pct": (cash - BANKROLL) / BANKROLL * 100,
            "taken": taken, "skipped": skipped,
            "max_dd_pct": maxdd * 100}


report = {"meta": {"bankroll": BANKROLL, "cost_pp": COST_PP, "delay_s": DELAY,
                   "stake_fracs": STAKE_FRACS, "exposure_caps": EXPOSURE_CAPS,
                   "criterion": "positive in ALL THREE windows"},
          "grid": []}

print(f"\n{'stake':>7} {'cap':>6} " +
      " ".join(f"{c[0][:12]:>13}" for c in CUTS) +
      f" {'worst':>9} {'all+':>5} {'maxDD':>7} {'taken':>7}")
best = None
for sf in STAKE_FRACS:
    for cap in EXPOSURE_CAPS:
        stake = BANKROLL * sf
        res = {}
        for cl, _ in CUTS:
            if cl in streams:
                res[cl] = run(streams[cl], stake, cap)
        if len(res) < len(CUTS):
            continue
        rets = [res[cl]["ret_pct"] for cl, _ in CUTS]
        worst = min(rets)
        allpos = all(r > 0 for r in rets)
        dd = max(res[cl]["max_dd_pct"] for cl, _ in CUTS)
        tk = sum(res[cl]["taken"] for cl, _ in CUTS)
        row = {"stake_frac": sf, "stake": stake, "exposure_cap": cap,
               "returns_pct": {cl: round(res[cl]["ret_pct"], 2) for cl, _ in CUTS},
               "worst_window_pct": round(worst, 2),
               "positive_in_all_windows": allpos,
               "max_drawdown_pct": round(dd, 2),
               "total_taken": tk,
               "total_skipped": sum(res[cl]["skipped"] for cl, _ in CUTS)}
        report["grid"].append(row)
        if allpos and (best is None or worst > best["worst_window_pct"]):
            best = row
        print(f"{sf:>7.3f} {cap:>6.2f} " +
              " ".join(f"{res[cl]['ret_pct']:>12.1f}%" for cl, _ in CUTS) +
              f" {worst:>8.1f}% {str(allpos):>5} {dd:>6.1f}% {tk:>7,}")

report["best_all_positive"] = best
print("\n=== BEST CONFIG POSITIVE IN ALL THREE WINDOWS ===")
if best:
    print(f"  stake {best['stake_frac']:.1%} (${best['stake']:,.0f}), "
          f"exposure cap {best['exposure_cap']:.0%} of bankroll")
    print(f"  returns {best['returns_pct']}")
    print(f"  worst window {best['worst_window_pct']:+.1f}%, "
          f"max drawdown {best['max_drawdown_pct']:.1f}%, "
          f"{best['total_taken']:,} trades taken")
else:
    print("  NONE. No sizing in the grid is positive in all three windows.")

OUT.write_text(json.dumps(report, indent=2), encoding="utf-8")
print(f"\nwrote {OUT}")

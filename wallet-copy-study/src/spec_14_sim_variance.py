r"""How lucky was +295%? Bootstrap the bankroll simulation.

The simulation returned +294.9%, -60.1% and +184.7% on three windows of the same
strategy. Point estimates that unstable are not results, they are draws. This
resamples EVENTS with replacement and re-runs the P&L, which answers the only
question that matters about them: what is the distribution those three came from,
and how much of it is below zero?

Resampling is at the EVENT level, not the trade level, for the usual reason --
several positions in one market are one bet. Resampling trades would shrink the
interval by pretending they were independent, which is precisely the error that
made a coinflip look like a "+95pp genius".

Also reports concentration directly: the share of total profit contributed by the
top 1, 5 and 10 events, and how many events it takes to reach half the profit. A
strategy whose profit is one event is a lottery ticket regardless of its mean.
"""
import json
import sys
from bisect import bisect_left
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from spec_pipeline import (  # noqa: E402
    add_excess, fee, price_band_benchmark, rank_within_category,
)

ROOT = Path(__file__).resolve().parents[1]
PANEL = ROOT / "data" / "spec_panel.jsonl"
FLAGS = ROOT / "data" / "wallet_flags.json"
BOOKS = [ROOT / "data" / "spec_task5_fills.jsonl",
         ROOT / "data" / "exit_fills.jsonl", ROOT / "data" / "fills.jsonl"]
OUT = ROOT / "reports" / "spec_sim_variance.json"

CUTS = [("2025-01-01", 1735689600), ("2025-07-01", 1751328000),
        ("2026-01-08_fee_era", 1767830400)]
FILT = {"min_trades": 20, "min_events": 10, "recent_within_days": 30,
        "max_gap_days": 30}
MIN_RANKED, DELAY, MAX_LOOKAHEAD = 30, 60, 3600
BANKROLL, STAKE = 10_000.0, 200.0
COST_PP = 0.675
CAT = "politics"
N_BOOT = 5000
SEED = 20260801

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
report = {"meta": {"bankroll": BANKROLL, "stake": STAKE, "cost_pp": COST_PP,
                   "n_boot": N_BOOT, "resample_unit": "event",
                   "delay_s": DELAY}, "runs": {}}

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

    # per-event P&L, no capital constraint (so the distribution is about the
    # EDGE, not about cash scheduling, which was covered in spec_13)
    ev_pnl = defaultdict(float)
    n_taken = 0
    for r in mea:
        if r["cat"] != CAT or r["w"] not in top:
            continue
        p = px_at(r["tok"], r["ts"] + DELAY)
        if p is None:
            continue
        eff = p + COST_PP / 100.0
        if not 0 < eff < 1:
            continue
        shares = STAKE / eff
        pnl = shares * r["outcome"] - fee(eff) * shares - STAKE
        ev_pnl[r["ev"]] += pnl
        n_taken += 1
    if len(ev_pnl) < 20:
        continue

    vals = np.array(list(ev_pnl.values()), dtype=np.float64)
    tot = float(vals.sum())
    srt = np.sort(vals)[::-1]
    pos = srt[srt > 0]
    cum = np.cumsum(pos)
    half_n = int(np.searchsorted(cum, pos.sum() / 2.0) + 1) if pos.size else None

    gen = np.random.default_rng(SEED)
    K = vals.size
    idx = gen.integers(0, K, size=(N_BOOT, K))
    draws = np.sort(vals[idx].sum(axis=1))

    run = {
        "n_taken_positions": n_taken, "n_events": int(K),
        "actual_total_pnl": round(tot, 2),
        "actual_return_on_bankroll_pct": round(tot / BANKROLL * 100, 2),
        "concentration": {
            "top1_share_of_gross_profit": round(float(srt[0] / pos.sum()), 4)
            if pos.size else None,
            "top5_share": round(float(srt[:5][srt[:5] > 0].sum() / pos.sum()), 4)
            if pos.size else None,
            "top10_share": round(float(srt[:10][srt[:10] > 0].sum() / pos.sum()), 4)
            if pos.size else None,
            "events_for_half_the_profit": half_n,
            "n_profitable_events": int((vals > 0).sum()),
            "n_losing_events": int((vals < 0).sum()),
        },
        "bootstrap_pnl": {
            "p05": round(float(draws[int(N_BOOT * .05)]), 2),
            "p25": round(float(draws[int(N_BOOT * .25)]), 2),
            "median": round(float(draws[int(N_BOOT * .5)]), 2),
            "p75": round(float(draws[int(N_BOOT * .75)]), 2),
            "p95": round(float(draws[int(N_BOOT * .95)]), 2),
            "prob_loss": round(float((draws < 0).mean()), 4),
            "prob_lose_half_bankroll": round(
                float((draws < -BANKROLL / 2).mean()), 4),
        },
    }
    report["runs"][cut_label] = run
    b = run["bootstrap_pnl"]
    c = run["concentration"]
    print(f"\n=== {cut_label} ===")
    print(f"  {n_taken:,} positions over {K:,} events; actual P&L "
          f"${tot:+,.0f} ({tot/BANKROLL*100:+.1f}% of bankroll)")
    print(f"  bootstrap P&L: p05 ${b['p05']:+,.0f}  median ${b['median']:+,.0f}  "
          f"p95 ${b['p95']:+,.0f}")
    print(f"  P(lose money) = {b['prob_loss']:.1%}   "
          f"P(lose half the bankroll) = {b['prob_lose_half_bankroll']:.1%}")
    print(f"  concentration: top event {c['top1_share_of_gross_profit']:.1%} of "
          f"gross profit, top 5 {c['top5_share']:.1%}; "
          f"{c['events_for_half_the_profit']} events = half the profit "
          f"({c['n_profitable_events']:,} winners / {c['n_losing_events']:,} losers)")

OUT.write_text(json.dumps(report, indent=2), encoding="utf-8")
print(f"\nwrote {OUT}")

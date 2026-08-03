r"""What would actually copying politics specialists have done to a bankroll?

Every number so far is a per-position average. That is the right way to test
whether an edge exists, and the wrong way to decide whether to trade it. This
runs the thing itself: a fixed bankroll, a fixed stake per signal, a realistic
entry delay, the MEASURED spread rather than an assumed one, and capital that is
locked up until each market resolves.

Rules, fixed in advance:
  - selection on period 1 only, politics only, market makers excluded;
  - entry at the traded price 60 SECONDS after the wallet's fill, taken from the
    recorded book where coverage exists -- never at the wallet's own price,
    which 55.5% of the time is their trade and not something you could buy;
  - entry cost = measured politics effective cost for the stake size, on top of
    the Polymarket fee 0.10*min(p,1-p);
  - stake is a fixed fraction of the STARTING bankroll, so results are not
    flattered by compounding into a bigger position after a lucky run;
  - a position ties up cash until the market resolves, and a signal arriving
    with no free cash is SKIPPED and counted. That constraint is the whole point
    -- per-position averages quietly assume infinite capital.

Reported with the skipped-signal count, peak concurrent exposure and worst
drawdown, because a strategy that only works with unlimited capital is not a
strategy.
"""
import json
import sys
from bisect import bisect_left
from collections import Counter, defaultdict
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
OUT = ROOT / "reports" / "spec_simulation.json"

CUTS = [("2025-01-01", 1735689600), ("2025-07-01", 1751328000),
        ("2026-01-08_fee_era", 1767830400)]
FILT = {"min_trades": 20, "min_events": 10, "recent_within_days": 30,
        "max_gap_days": 30}
MIN_RANKED = 30
DELAY = 60
MAX_LOOKAHEAD = 3600
BANKROLL = 10_000.0
STAKE_FRAC = 0.02              # 2% of starting bankroll per signal
# measured medians from rec_02_spread (politics), pp above mid
COST_BY_STAKE = {200: 1.000, 500: 1.163, 1000: 1.573}  # CORRECTED from 10-level book
CAT = "politics"

MM = set(json.loads(FLAGS.read_text(encoding="utf-8"))["excluded"])

print("loading books...", flush=True)
bts, bpx = defaultdict(list), defaultdict(list)
n = 0
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
        n += 1
for t in bts:
    z = sorted(zip(bts[t], bpx[t]))
    bts[t] = [a for a, _ in z]
    bpx[t] = [b for _, b in z]
print(f"  {n:,} fills over {len(bts):,} tokens")


def px_at(tok, when):
    ts = bts.get(tok)
    if not ts:
        return None
    i = bisect_left(ts, when)
    if i >= len(ts) or ts[i] - when > MAX_LOOKAHEAD:
        return None
    return bpx[tok][i]


print("loading panel...", flush=True)
rows = [json.loads(l) for l in PANEL.open(encoding="utf-8")]

stake = BANKROLL * STAKE_FRAC
cost_pp = COST_BY_STAKE.get(int(stake), 0.675)
print(f"  bankroll ${BANKROLL:,.0f}, stake ${stake:,.0f} "
      f"({STAKE_FRAC:.0%}), measured politics cost {cost_pp}pp\n")

report = {"meta": {"bankroll": BANKROLL, "stake": stake,
                   "stake_frac": STAKE_FRAC, "delay_s": DELAY,
                   "measured_cost_pp": cost_pp, "category": CAT,
                   "filters": FILT,
                   "rules": "entry at +60s traded price from recorded books; "
                            "fixed stake off STARTING bankroll; capital locked "
                            "until resolution; signals with no free cash are "
                            "skipped and counted"},
          "runs": {}}

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
    k = max(len(order) // 10, 1)
    top = set(order[:k])

    sigs = sorted((r for r in mea if r["cat"] == CAT and r["w"] in top),
                  key=lambda r: r["ts"])
    cash = BANKROLL
    open_pos = []          # (resolve_ts, payout_fn_inputs)
    taken, skipped_cash, skipped_book = 0, 0, 0
    pnl_events = []
    equity = [BANKROLL]
    peak_exposure = 0.0
    wins = 0

    for r in sigs:
        # settle anything that resolved before this signal
        still = []
        for res_ts, payout in open_pos:
            if res_ts <= r["ts"]:
                cash += payout
            else:
                still.append((res_ts, payout))
        open_pos = still
        equity.append(cash + sum(p for _, p in open_pos))

        p_entry = px_at(r["tok"], r["ts"] + DELAY)
        if p_entry is None:
            skipped_book += 1
            continue
        if cash < stake:
            skipped_cash += 1
            continue
        eff_px = p_entry + cost_pp / 100.0
        if not 0 < eff_px < 1:
            skipped_book += 1
            continue
        shares = stake / eff_px
        f = fee(eff_px) * shares
        cash -= stake
        payout = shares * r["outcome"] - f
        res_ts = r.get("end_ts") or (r["ts"] + 86400 * 30)
        open_pos.append((res_ts, payout))
        taken += 1
        pnl_events.append((r["ev"], payout - stake))
        if r["outcome"] > 0:
            wins += 1
        peak_exposure = max(peak_exposure, sum(1 for _ in open_pos) * stake)

    for _, payout in open_pos:
        cash += payout
    final = cash
    eq = equity + [final]
    peak = eq[0]
    maxdd = 0.0
    for v in eq:
        peak = max(peak, v)
        maxdd = max(maxdd, (peak - v) / peak if peak > 0 else 0)

    by_ev = defaultdict(float)
    for ev, pl in pnl_events:
        by_ev[ev] += pl
    tot_pl = final - BANKROLL

    run = {
        "n_signals": len(sigs), "n_taken": taken,
        "skipped_no_book": skipped_book, "skipped_no_cash": skipped_cash,
        "n_distinct_events": len(by_ev),
        "final_bankroll": round(final, 2),
        "pnl": round(tot_pl, 2),
        "return_on_bankroll_pct": round(tot_pl / BANKROLL * 100, 3),
        "capital_deployed": round(taken * stake, 2),
        "return_on_deployed_pct": round(
            tot_pl / max(taken * stake, 1) * 100, 3),
        "win_rate": round(wins / max(taken, 1), 4),
        "peak_concurrent_exposure": round(peak_exposure, 2),
        "max_drawdown_pct": round(maxdd * 100, 3),
        "mean_pnl_per_trade": round(tot_pl / max(taken, 1), 3),
        "best_event_pnl": round(max(by_ev.values()), 2) if by_ev else None,
        "worst_event_pnl": round(min(by_ev.values()), 2) if by_ev else None,
        "top_event_share_of_pnl": (
            round(max(by_ev.values()) / tot_pl, 3)
            if by_ev and tot_pl > 0 else None),
    }
    report["runs"][cut_label] = run
    print(f"=== {cut_label} ===")
    print(f"  signals {len(sigs):,}  taken {taken:,}  "
          f"skipped(no book) {skipped_book:,}  skipped(no cash) {skipped_cash:,}")
    print(f"  final bankroll ${final:,.2f}  P&L ${tot_pl:+,.2f}  "
          f"({tot_pl/BANKROLL*100:+.2f}% on bankroll, "
          f"{tot_pl/max(taken*stake,1)*100:+.2f}% on deployed)")
    print(f"  win rate {wins/max(taken,1):.1%}  peak exposure "
          f"${peak_exposure:,.0f}  max drawdown {maxdd*100:.1f}%")
    print(f"  events {len(by_ev):,}  top event = "
          f"{run['top_event_share_of_pnl']} of P&L\n")

OUT.write_text(json.dumps(report, indent=2), encoding="utf-8")
print(f"wrote {OUT}")

"""Seven sizing arms over the SAME picks. Paper replay, no new data.

Pre-registered in `PREREGISTRATION_SIZING.md`, which was written and committed
BEFORE this file existed. Read §1 there first: **sizing cannot create an edge
and cannot change the average result.** It changes the chance of going broke.
This test exists to make that visible on his own picks, not to discover it.

    python src/sizing.py                 # the table
    python src/sizing.py --runs 2000     # orderings per arm (default 2000)
    python src/sizing.py --json out.json

Every arm replays the identical settled positions at their identical recorded
entry prices. Only the stake rule differs.
"""
from __future__ import annotations

import argparse
import json
import math
import random
import statistics
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
TRADING_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(TRADING_ROOT))

import engine as E                              # noqa: E402
from common.kalshi_fees import fee_order_cents  # noqa: E402

START_BALANCE = 250.00
BUST_FLOOR = 50.00          # "went below $50", pre-registered in section 4
RUNS = 2000
SEED = 20260812


def _kelly(price_c, believed_win):
    """Optimal fraction for a binary contract bought at `price_c`.

    b = (100 - p) / p is the payoff per unit risked. f* = (b*q - (1-q)) / b.
    Clamped to [0, 1]; a negative Kelly means "do not bet", which for this test
    means stake nothing rather than bet the other side.
    """
    p = max(1, min(99, price_c)) / 100.0
    b = (1.0 - p) / p
    q = max(0.0, min(1.0, believed_win))
    f = (b * q - (1 - q)) / b if b > 0 else 0.0
    return max(0.0, min(1.0, f))


ARMS = {
    "flat-5":       lambda bal, st, pc, bw: 0.05 * START_BALANCE,
    "flat-5-comp":  lambda bal, st, pc, bw: 0.05 * bal,
    "flat-20":      lambda bal, st, pc, bw: 0.20 * bal,
    "half":         lambda bal, st, pc, bw: 0.50 * bal,
    "all-in":       lambda bal, st, pc, bw: 1.00 * bal,
    "kelly":        lambda bal, st, pc, bw: _kelly(pc, bw) * bal,
    "kelly-half":   lambda bal, st, pc, bw: 0.5 * _kelly(pc, bw) * bal,
}


def load_picks(con, bots=("starter__hold", "early__hold")):
    """Every settled position, as (entry_price_c, settle_value_c, believed).

    `believed` is the win probability the bot itself claimed, used ONLY by the
    two Kelly arms -- they are defined as "the optimal fraction for the edge it
    believes it has", so the belief has to come from the bot rather than from
    the outcome. `stated_prob_c` is written at decision time, before the game.
    """
    rows = []
    for b in bots:
        for r in con.execute(
                "SELECT p.entry_price_c, p.settle_value_c, p.game_key, "
                "       d.stated_prob_c, p.bot "
                "FROM positions p LEFT JOIN decisions d ON d.id = p.decision_id "
                "WHERE p.bot=? AND p.status='settled' "
                "  AND p.settle_value_c IS NOT NULL "
                "ORDER BY p.opened_utc", (b,)).fetchall():
            believed = r["stated_prob_c"]
            rows.append({
                "bot": r["bot"], "game": r["game_key"],
                "price_c": r["entry_price_c"],
                "settle_c": r["settle_value_c"],
                "believed": (believed / 100.0) if believed is not None
                            else r["entry_price_c"] / 100.0,
            })
    return rows


def run_once(picks, arm_fn, order):
    """One pass. Returns (final, min_balance, max_drawdown, worst_game, bust)."""
    bal = START_BALANCE
    peak = bal
    max_dd = 0.0
    worst = 0.0
    low = bal
    for i in order:
        p = picks[i]
        stake = arm_fn(bal, START_BALANCE, p["price_c"], p["believed"])
        stake = min(stake, bal)
        if stake <= 0:
            continue
        n = int(stake / (p["price_c"] / 100.0))
        if n < 1:
            # cannot afford a single contract -> BUST, and it stops.
            break
        cost = n * p["price_c"] / 100.0
        fee = float(fee_order_cents(p["price_c"], n)) / 100.0
        if cost + fee > bal:
            n = int((bal * 100.0) / (p["price_c"] + 2.0))
            if n < 1:
                break
            cost = n * p["price_c"] / 100.0
            fee = float(fee_order_cents(p["price_c"], n)) / 100.0
            if cost + fee > bal:
                break
        # the stake leaves the balance BEFORE the outcome is known
        bal -= cost + fee
        bal += n * p["settle_c"] / 100.0
        delta = (p["settle_c"] - p["price_c"]) * n / 100.0 - fee
        worst = min(worst, delta)
        peak = max(peak, bal)
        max_dd = max(max_dd, peak - bal)
        low = min(low, bal)
        if bal < 0.01:
            bal = 0.0
            break
    return bal, low, max_dd, worst, bal < 0.01


def evaluate(picks, runs=RUNS, seed=SEED):
    rnd = random.Random(seed)
    idx = list(range(len(picks)))
    orders = [idx[:]]                       # the real ordering, first
    for _ in range(runs - 1):
        o = idx[:]
        rnd.shuffle(o)
        orders.append(o)

    out = {}
    for name, fn in ARMS.items():
        finals, lows, dds, worsts, busts, below = [], [], [], [], 0, 0
        real = None
        for k, o in enumerate(orders):
            f, lo, dd, w, bust = run_once(picks, fn, o)
            if k == 0:
                real = f
            finals.append(f)
            lows.append(lo)
            dds.append(dd)
            worsts.append(w)
            busts += bust
            below += (lo < BUST_FLOOR)
        finals_s = sorted(finals)
        out[name] = {
            "real_ordering_final": round(real, 2),
            "median_final": round(statistics.median(finals), 2),
            "worst_5pct": round(finals_s[int(0.05 * len(finals_s))], 2),
            "best_5pct": round(finals_s[int(0.95 * len(finals_s))], 2),
            "runs_below_50": below,
            "runs_below_50_pct": round(100.0 * below / len(orders), 1),
            "runs_to_zero": busts,
            "runs_to_zero_pct": round(100.0 * busts / len(orders), 1),
            "median_max_drawdown": round(statistics.median(dds), 2),
            "worst_single_game": round(min(worsts), 2),
        }
        # the pre-registered three-condition rule, section 5
        gain = out[name]["median_final"] - START_BALANCE
        out[name]["passes_rule"] = bool(
            gain > 0 and below == 0
            and out[name]["median_max_drawdown"] < gain)
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", type=int, default=RUNS)
    ap.add_argument("--json")
    a = ap.parse_args()
    con = E.connect()
    picks = load_picks(con)
    con.close()
    if not picks:
        print("no settled positions to replay")
        sys.exit(0)

    wins = sum(1 for p in picks if p["settle_c"] > p["price_c"])
    avg_price = statistics.mean(p["price_c"] for p in picks)
    print(f"replaying {len(picks)} settled picks from starter+early, "
          f"{wins} won ({100*wins/len(picks):.0f} out of 100), "
          f"average buy price {avg_price:.1f}c")
    print(f"{a.runs} orderings per arm, starting balance ${START_BALANCE:.0f}")
    print()
    print("SIZING CANNOT CREATE AN EDGE. It cannot change the average result.")
    print("It changes the chance of going broke. See PREREGISTRATION_SIZING "
          "section 1.")
    print()
    res = evaluate(picks, runs=a.runs)
    print(f"{'arm':<14} {'median $':>9} {'real $':>8} {'worst5% $':>10} "
          f"{'best5% $':>9} {'<$50':>7} {'zero':>7} {'maxdrop $':>10} "
          f"{'rule':>6}")
    for name in ARMS:
        r = res[name]
        print(f"{name:<14} {r['median_final']:>9.2f} "
              f"{r['real_ordering_final']:>8.2f} {r['worst_5pct']:>10.2f} "
              f"{r['best_5pct']:>9.2f} {r['runs_below_50_pct']:>6.1f}% "
              f"{r['runs_to_zero_pct']:>6.1f}% {r['median_max_drawdown']:>10.2f} "
              f"{'PASS' if r['passes_rule'] else 'fail':>6}")
    print()
    print("'rule' is the PRE-REGISTERED three-condition test (section 5): ahead "
          "on the median,\nNEVER below $50 in any ordering, and the biggest "
          "fall smaller than the final gain.")
    print("Winning on final balance alone does NOT count. That was fixed "
          "before any number existed.")
    if a.json:
        Path(a.json).write_text(json.dumps(
            {"picks": len(picks), "runs": a.runs, "arms": res}, indent=2))
        print(f"\nwrote {a.json}")

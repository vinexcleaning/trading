"""His take-profit / stop-loss sweep. Mailbox 019, job 2.

    "is there a version of this exact same bot that instead of holding, has
     take profit and stop loss... at a bunch of different percentages, and see
     which ones make the most money"

Pre-registered in PREREGISTRATION_EXITGRID.md BEFORE any result existed. The
grid is 81 cells and that number was fixed in writing first, because the whole
danger here is that the best of 81 looks good even when nothing works.

⚠ FEES. A position held to settlement pays ONE fee. Every exit pays TWO. That
is not bookkeeping detail -- it is the reason `hold` starts ahead, and an exit
grid that forgets it will manufacture a winner.

    python src/exitgrid.py
"""
from __future__ import annotations

import random
import sqlite3
import statistics
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent.parent))
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

import engine as E                                    # noqa: E402
from common.kalshi_fees import fee_order_cents        # noqa: E402

TRUTH = HERE.parent / "data" / "kalshi_truth.db"
LEVELS = [4, 6, 8, 10, 12, 15, 20, 25, None]          # None = never
NEVER = "never"


def paths(tcon, positions):
    """Minute-by-minute exit price for each position, entry -> settlement.

    We are LONG, so leaving means hitting the BID. Never the mid.
    """
    out = {}
    for p in positions:
        t0 = int(datetime.fromisoformat(p["opened_utc"]).timestamp())
        rows = tcon.execute(
            "SELECT end_ts, yes_bid_close_c FROM candle WHERE ticker=? AND "
            "end_ts >= ? AND yes_bid_close_c IS NOT NULL ORDER BY end_ts",
            (p["ticker"], t0)).fetchall()
        if rows:
            out[p["id"]] = [r["yes_bid_close_c"] for r in rows]
    return out


def run_cell(positions, pth, tp, sl, rng=None, random_rate=None):
    """One cell of the grid. `random_rate` runs the PLACEBO instead.

    The placebo exits at a uniformly random minute with probability
    `random_rate` per position -- the same rate the real cell exits -- so a
    threshold that only wins by exiting rarely is caught.
    """
    money = 0.0
    fired = 0
    for p in positions:
        n = p["contracts"]
        paid = n * p["entry_price_c"] / 100.0 + (p["entry_fee_c"] or 0) / 100.0
        path = pth.get(p["id"])
        exit_c = None
        if path:
            if random_rate is not None:
                if rng.random() < random_rate:
                    exit_c = path[rng.randrange(len(path))]
            else:
                for bid in path:
                    move = bid - p["entry_price_c"]
                    if (tp is not None and move >= tp) or \
                       (sl is not None and move <= -sl):
                        exit_c = bid
                        break
        if exit_c is not None:
            fired += 1
            got = n * exit_c / 100.0 - float(fee_order_cents(exit_c, n)) / 100.0
        else:
            # settled: 100 or 0, and NO second fee
            won = (p["pnl_c"] or 0) > 0
            got = n * 1.0 if won else 0.0
        money += got - paid
    return money, fired


if __name__ == "__main__":
    con = E.connect()
    tcon = sqlite3.connect(f"file:{TRUTH}?mode=ro", uri=True)
    tcon.row_factory = sqlite3.Row
    pos = [dict(r) for r in con.execute(
        "SELECT * FROM positions WHERE bot='starter__hold' AND "
        "status IN ('settled','closed') ORDER BY opened_utc")]
    pth = paths(tcon, pos)
    print(f"{len(pos)} settled games; minute tape found for {len(pth)} of them")
    print(f"grid = {len(LEVELS)}x{len(LEVELS)} = {len(LEVELS)**2} cells, "
          f"fixed in the pre-registration before looking\n")

    base, _ = run_cell(pos, pth, None, None)
    print(f"HOLD to settlement (the benchmark): ${base:.2f}\n")

    print("money by cell -- rows are take-profit, columns are stop-loss")
    hdr = "".join(f"{(NEVER if s is None else s):>8}" for s in LEVELS)
    TPSL = "TP/SL"
    print(f"{TPSL:<7}{hdr}")
    grid = {}
    for tp in LEVELS:
        line = f"{(NEVER if tp is None else tp):<7}"
        for sl in LEVELS:
            m, f = run_cell(pos, pth, tp, sl)
            grid[(tp, sl)] = (m, f)
            line += f"{m:>8.2f}"
        print(line)

    best = max(grid.items(), key=lambda kv: kv[1][0])
    (btp, bsl), (bm, bf) = best
    print(f"\nBEST CELL: take-profit {btp}, stop-loss {bsl} -> ${bm:.2f} "
          f"(fired on {bf} of {len(pos)})")
    print(f"  beats holding by ${bm - base:.2f}")
    print(f"  ⚠ it is the best of {len(LEVELS)**2} cells. That is what makes it "
          f"look good.\n")

    # is the surface smooth or spiky? a real effect does not switch off
    # between one level and the next.
    ti, si = LEVELS.index(btp), LEVELS.index(bsl)
    nb = []
    for dt in (-1, 0, 1):
        for ds in (-1, 0, 1):
            if dt == ds == 0:
                continue
            a, b = ti + dt, si + ds
            if 0 <= a < len(LEVELS) and 0 <= b < len(LEVELS):
                nb.append(grid[(LEVELS[a], LEVELS[b])][0])
    print(f"SMOOTH OR SPIKY -- the winner's {len(nb)} neighbours:")
    print(f"  best ${bm:.2f} | neighbours middle ${statistics.median(nb):.2f}, "
          f"worst ${min(nb):.2f}, best ${max(nb):.2f}")
    print(f"  a real effect does not switch off between one level and the next.")

    rng = random.Random(20260820)
    rate = bf / max(1, len(pos))
    pl = [run_cell(pos, pth, None, None, rng=rng, random_rate=rate)[0]
          for _ in range(200)]
    pl.sort()
    print(f"\nPLACEBO -- exit at a RANDOM minute, same rate ({rate:.0%}), 200 runs:")
    print(f"  middle ${statistics.median(pl):.2f}, "
          f"range ${pl[5]:.2f} to ${pl[-6]:.2f}")
    print(f"  the best cell: ${bm:.2f}")
    inside = pl[5] <= bm <= pl[-6]
    print(f"  -> the best of 81 cells is {'INSIDE' if inside else 'OUTSIDE'} "
          f"what random exiting produces")
    con.close()
    tcon.close()

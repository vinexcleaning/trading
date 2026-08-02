"""Phase 0e -- verify the mirror relationship before trusting the dedupe.

Kalshi lists two markets per match, one per player. If they are near-perfect
inverses then keeping one side loses nothing and keeping both would double-count
every observation -- the pseudo-replication that has fired four times in this
project. This checks the claim rather than assuming it, on 400 randomly chosen
opposite sides fetched alongside the main pull.

Two different things are measured, and they are not the same:
  mid(A) + mid(B) == 100     -- do the two markets agree on the probability?
  ask(A) + bid(B) == 100     -- is trading NO on A the same as YES on B?
The second is the one the study depends on, because the favourite is traded as
the NO side of the kept market whenever the kept player is the underdog.
"""
import pathlib

import numpy as np
import pandas as pd

import p1_state as ps

ROOT = pathlib.Path(__file__).resolve().parents[1]
DATA = ROOT / "data"


def main():
    cd = ps.load_candles("candles")
    uni = pd.read_parquet(DATA / "universe.parquet")
    sides = pd.read_parquet(DATA / "sides.parquet")

    kept = set(uni["ticker"])
    have = set(cd["ticker"].unique())
    mirror = sides[(~sides["ticker"].isin(kept)) & sides["ticker"].isin(have)]
    ev2tick = dict(zip(uni["event_ticker"], uni["ticker"]))
    pairs = [(ev2tick[e], t) for e, t in
             zip(mirror["event_ticker"], mirror["ticker"])
             if ev2tick.get(e) in have]
    print(f"mirror pairs with candles on both sides: {len(pairs):,}")
    if not pairs:
        return

    g = {k: v for k, v in cd.groupby("ticker")}
    mid_diff, exec_diff, n_min = [], [], 0
    for a, b in pairs:
        da, db = g[a], g[b]
        m = da.merge(db, on="ts", suffixes=("_a", "_b"))
        ok = ((m["bid_a"] >= 0) & (m["ask_a"] >= 0) & (m["bid_b"] >= 0)
              & (m["ask_b"] >= 0)
              & (m["ask_a"] - m["bid_a"] <= ps.MAX_SPREAD)
              & (m["ask_b"] - m["bid_b"] <= ps.MAX_SPREAD))
        m = m[ok]
        if len(m) < 20:
            continue
        n_min += len(m)
        mida = (m["bid_a"] + m["ask_a"]) / 2
        midb = (m["bid_b"] + m["ask_b"]) / 2
        mid_diff.append((mida + midb - 100).values)
        # cost of the favourite via NO on A  vs  via YES on B
        exec_diff.append(((100 - m["bid_a"]) - m["ask_b"]).values)

    md = np.concatenate(mid_diff)
    xd = np.concatenate(exec_diff)
    lines = []

    def w(s=""):
        print(s, flush=True)
        lines.append(s)

    w("MIRROR VERIFICATION")
    w("=" * 60)
    w(f"pairs used            {len(mid_diff):,}")
    w(f"aligned minutes       {n_min:,}")
    w("")
    w("mid(A) + mid(B) - 100, in cents:")
    w(f"  median {np.median(md):+.3f}   mean {md.mean():+.3f}   "
      f"sd {md.std():.3f}")
    w(f"  |diff| <= 0.5c: {(np.abs(md) <= 0.5).mean():.4f}   "
      f"<= 1c: {(np.abs(md) <= 1).mean():.4f}   "
      f"<= 2c: {(np.abs(md) <= 2).mean():.4f}")
    w("")
    w("cost of the favourite: (100 - bid_A)  minus  ask_B, in cents")
    w("  positive means the NO side of the kept market is the dearer route")
    w(f"  median {np.median(xd):+.3f}   mean {xd.mean():+.3f}   "
      f"sd {xd.std():.3f}")
    w(f"  |diff| <= 1c: {(np.abs(xd) <= 1).mean():.4f}   "
      f"<= 2c: {(np.abs(xd) <= 2).mean():.4f}")
    w("")
    if np.abs(np.median(md)) <= 0.5:
        w("VERDICT: the two sides are inverses to within half a cent at the "
          "median.")
        w("Keeping one side per match loses no information and keeping both "
          "would")
        w("double-count every match. Dedupe is correct.")
    else:
        w("VERDICT: the sides are NOT clean inverses. Investigate before "
          "trusting the dedupe.")
    if np.median(xd) > 0.5:
        w("")
        w(f"NOTE: buying the favourite as NO on the kept market costs "
          f"{np.median(xd):+.2f}c more at the")
        w("median than buying YES on the sibling market. The study prices the "
          "kept-market")
        w("route, so its cost assumption is the conservative one.")
    (ROOT / "reports" / "p0_mirror.txt").write_text("\n".join(lines),
                                                    encoding="utf-8")


if __name__ == "__main__":
    main()

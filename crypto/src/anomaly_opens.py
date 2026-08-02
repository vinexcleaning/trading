"""THE BLOCKER: why do KXBTC15M contracts open anywhere from 18c to 70c?

A contract minted at the previous window's 60-second average should open at
~50c, because at the instant the window starts spot IS (approximately) the
strike. Observed first-capture no_ask spans 18c-70c with sd 12.6c. Until this
is explained no break-even bar is trustworthy, so the fade test is blocked.

Hypotheses, each with a distinct signature in the data:

  H1  BOOK NOT YET POPULATED. The first capture lands microseconds after open
      and the maker quotes are not up. Signature: extreme prices coincide with
      TINY or ZERO sizes, and/or very wide spreads, and the price CONVERGES
      toward 50c over the next few seconds.
  H2  STALE CARRYOVER from the previous market. Signature: opening price
      resembles the PREVIOUS window's closing price rather than 50c, and
      volume/OI are already non-zero at age ~0.
  H3  GENUINE MONEYNESS. The strike really is far from spot at open. Signature:
      prices are dispersed but STABLE — no convergence — and sizes are normal.
  H4  MIS-ALIGNED WINDOW. `open_time` is not the window start, so we are
      sampling a market that has been live for a while. Signature: volume/OI
      already large at age ~0, and price dispersion matches a market that has
      been trading.

These make different predictions, so the data can separate them.
"""
import glob
import json
import os
from collections import defaultdict

import numpy as np

ROOT = r"C:\Users\gianf\crypto\data\btc15m_opens"


def fv(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def main():
    rows = []
    for p in sorted(glob.glob(os.path.join(ROOT, "*.jsonl"))):
        with open(p, encoding="utf-8") as f:
            for line in f:
                try:
                    rows.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
    by_win = defaultdict(list)
    for r in rows:
        by_win[r.get("ticker")].append(r)
    for k in by_win:
        by_win[k].sort(key=lambda r: r.get("age_since_open_s") or 0)
    print(f"{len(rows)} captures across {len(by_win)} windows\n")

    print("=" * 110)
    print("PER-WINDOW TRAJECTORY — first capture vs where it settles down")
    print("=" * 110)
    print(f"  {'window':<30} {'age':>6} {'yes_bid':>8} {'yes_ask':>8} "
          f"{'bidsz':>9} {'asksz':>9} {'vol':>10} {'OI':>10} "
          f"{'spread':>7} {'->60s ask':>10}")
    firsts, lasts, conv = [], [], []
    for k in sorted(by_win, key=lambda x: by_win[x][0].get("open_ts_ns") or 0):
        seq = by_win[k]
        f0 = seq[0]
        fl = seq[-1]
        a0 = fv(f0.get("yes_ask"))
        b0 = fv(f0.get("yes_bid"))
        a1 = fv(fl.get("yes_ask"))
        if a0 is None or b0 is None:
            continue
        firsts.append(a0)
        lasts.append(a1)
        conv.append(abs(a1 - 0.5) - abs(a0 - 0.5))
        print(f"  {k[:30]:<30} {f0.get('age_since_open_s',0):>6.1f} "
              f"{b0:>8.4f} {a0:>8.4f} "
              f"{str(f0.get('yes_bid_size'))[:9]:>9} "
              f"{str(f0.get('yes_ask_size'))[:9]:>9} "
              f"{str(f0.get('volume'))[:10]:>10} "
              f"{str(f0.get('open_interest'))[:10]:>10} "
              f"{(a0-b0)*100:>6.2f}c {a1:>10.4f}")

    fa = np.array(firsts)
    la = np.array([x for x in lasts if x is not None])
    print(f"\n  first-capture yes_ask : n={len(fa)} "
          f"median={np.median(fa)*100:.1f}c sd={fa.std()*100:.1f}c "
          f"range {fa.min()*100:.0f}-{fa.max()*100:.0f}c")
    print(f"  last-capture  yes_ask : n={len(la)} "
          f"median={np.median(la)*100:.1f}c sd={la.std()*100:.1f}c")

    print("\n" + "=" * 110)
    print("H1 TEST — do EXTREME opens have tiny size / wide spreads, and do "
          "they converge to 50c?")
    print("=" * 110)
    ext, mid = [], []
    for k, seq in by_win.items():
        f0 = seq[0]
        a0, b0 = fv(f0.get("yes_ask")), fv(f0.get("yes_bid"))
        if a0 is None or b0 is None:
            continue
        bs = fv(f0.get("yes_bid_size")) or 0
        as_ = fv(f0.get("yes_ask_size")) or 0
        rec = {"ask": a0, "spread": a0 - b0, "minsz": min(bs, as_),
               "vol": fv(f0.get("volume")) or 0,
               "oi": fv(f0.get("open_interest")) or 0,
               "drift": (fv(seq[-1].get("yes_ask")) or a0) - a0}
        (ext if abs(a0 - 0.5) > 0.15 else mid).append(rec)
    for nm, g in (("EXTREME (|ask-50c|>15c)", ext), ("NEAR 50c", mid)):
        if not g:
            continue
        print(f"  {nm:<26} n={len(g):>3}  "
              f"med spread={np.median([x['spread'] for x in g])*100:5.2f}c  "
              f"med min-size={np.median([x['minsz'] for x in g]):9.1f}  "
              f"med vol={np.median([x['vol'] for x in g]):10.1f}  "
              f"med OI={np.median([x['oi'] for x in g]):10.1f}")
        d = np.array([x["drift"] for x in g])
        print(f"  {'':<26} drift over 60s: median "
              f"{np.median(d)*100:+.2f}c, |drift| median "
              f"{np.median(np.abs(d))*100:.2f}c")

    print("\n" + "=" * 110)
    print("H2/H4 TEST — is volume/OI already non-zero at the FIRST capture?")
    print("=" * 110)
    v0 = np.array([fv(by_win[k][0].get("volume")) or 0 for k in by_win])
    o0 = np.array([fv(by_win[k][0].get("open_interest")) or 0 for k in by_win])
    ages = np.array([by_win[k][0].get("age_since_open_s") or 0
                     for k in by_win])
    print(f"  first-capture age : median {np.median(ages):.1f}s "
          f"(min {ages.min():.1f}, max {ages.max():.1f})")
    print(f"  volume at first capture : {int((v0>0).sum())}/{len(v0)} "
          f"non-zero, median {np.median(v0):.1f}")
    print(f"  OI at first capture     : {int((o0>0).sum())}/{len(o0)} "
          f"non-zero, median {np.median(o0):.1f}")
    print("\n  A market that has genuinely JUST opened should have volume and")
    print("  open interest of ~0. Large values mean it has been trading, which")
    print("  would point at H2/H4 (stale carryover or mis-aligned window).")

    print("\n" + "=" * 110)
    print("VERDICT INPUTS")
    print("=" * 110)
    corr_ask_oi = (float(np.corrcoef(
        [abs(fv(by_win[k][0].get("yes_ask")) - 0.5) for k in by_win
         if fv(by_win[k][0].get("yes_ask")) is not None],
        [fv(by_win[k][0].get("open_interest")) or 0 for k in by_win
         if fv(by_win[k][0].get("yes_ask")) is not None])[0, 1]))
    print(f"  corr(|open ask - 50c|, open interest at first capture) = "
          f"{corr_ask_oi:+.4f}")
    print("  positive => the further from 50c, the more the market had already")
    print("  traded, i.e. we are NOT catching it at birth.")


if __name__ == "__main__":
    main()

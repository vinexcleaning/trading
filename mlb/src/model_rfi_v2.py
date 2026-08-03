"""THE GATE, v2: base features + Statcast pitch quality vs Kalshi's price.

Same test as model_rfi.py, same discipline, one change: the pitcher and batter
features are now measured on hundreds of pitches (expected wOBA on contact,
hard-hit rate, K rate, BB rate) instead of a binary run/no-run outcome over a
dozen starts.

THE DIAGNOSTIC TO WATCH is not the Brier alone. It is the SPREAD of the
model's probabilities. v1 varied by 1.9pp while Kalshi varied by ~6.5pp -- the
model could not tell games apart. If better data does not widen that, the
market's extra information is not pitch quality and no amount of Statcast will
close it.
"""
import json
import os
import random
import re
import sys
from collections import Counter
from datetime import datetime, timedelta, timezone

import numpy as np

HERE = os.path.dirname(__file__)
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "..", "market-selection", "src"))
sys.path.insert(0, os.path.join(HERE, "..", "..", "common"))
import model_rfi as V1  # noqa: E402

ROOT = os.path.join(HERE, "..")
DATA, REP = os.path.join(ROOT, "data"), os.path.join(ROOT, "reports")

SC_NUM = ["home_sp_xwoba", "home_sp_hard", "home_sp_k", "home_sp_bb",
          "home_bat_xwoba", "home_bat_hard", "home_bat_k",
          "away_sp_xwoba", "away_sp_hard", "away_sp_k", "away_sp_bb",
          "away_bat_xwoba", "away_bat_hard", "away_bat_k"]


def main():
    rows = V1.load_games()
    feat = V1.build(rows)
    print(f"{len(feat):,} base feature rows")

    sc = {}
    p = os.path.join(DATA, "sc_features.jsonl")
    if os.path.exists(p):
        with open(p, encoding="utf-8") as fh:
            for line in fh:
                try:
                    r = json.loads(line)
                except ValueError:
                    continue
                sc[r["game_pk"]] = r["feats"]
    print(f"{len(sc):,} games with Statcast features")

    merged = 0
    for r in feat:
        s = sc.get(r["game_pk"])
        if s:
            r["feats"].update(s)
            merged += 1
    print(f"merged onto {merged:,} games "
          f"({100*merged/max(len(feat),1):.1f}%)")
    for k in SC_NUM[:4]:
        n = sum(1 for r in feat if r["feats"].get(k) is not None)
        print(f"  {k:18s} {100*n/max(len(feat),1):5.1f}%")

    # league means for the unknown-flag fill
    means = {}
    for k in SC_NUM:
        v = [r["feats"][k] for r in feat if r["feats"].get(k) is not None]
        means[k] = float(np.mean(v)) if v else 0.0

    def design2(rs):
        X = []
        for r in rs:
            f = r["feats"]
            lg = f.get("league_rate", 0.506)
            v, m = [], []
            for k in V1.NUM:
                x = f.get(k)
                m.append(1.0 if x is None else 0.0)
                v.append(lg if x is None else x)
            for k in SC_NUM:
                x = f.get(k)
                m.append(1.0 if x is None else 0.0)
                v.append(means[k] if x is None else x)
            v += [f.get("is_night", 0.0),
                  np.log1p(f.get("home_sp_n", 0) or 0),
                  np.log1p(f.get("away_sp_n", 0) or 0)]
            X.append(v + m)
        return np.array(X, float)

    tr = [r for r in feat if r["season"] and int(r["season"]) <= 2024]
    te = [r for r in feat if r["season"] and int(r["season"]) >= 2025]
    print(f"\ntrain <=2024 {len(tr):,}   test 2025+ {len(te):,}")

    from sklearn.linear_model import LogisticRegression
    from sklearn.preprocessing import StandardScaler
    Xtr, ytr = design2(tr), np.array([r["yrfi"] for r in tr], float)
    Xte, yte = design2(te), np.array([r["yrfi"] for r in te], float)
    sc_ = StandardScaler().fit(Xtr)
    clf = LogisticRegression(max_iter=4000, C=0.3).fit(sc_.transform(Xtr), ytr)
    pte = clf.predict_proba(sc_.transform(Xte))[:, 1]
    base = float(ytr.mean())

    print("\n" + "=" * 66)
    print("TEST 1 -- vs the base rate, held out")
    print("=" * 66)
    bb = V1.brier(np.full_like(yte, base), yte)
    bm = V1.brier(pte, yte)
    print(f"  n={len(yte):,}  base {bb:.5f}  model {bm:.5f}  "
          f"improvement {bb-bm:+.5f}")
    print(f"  MODEL PROBABILITY SPREAD: sd {pte.std()*100:.2f}pp   "
          f"range {pte.min()*100:.1f}-{pte.max()*100:.1f}c")
    print(f"  (v1 was sd 1.89pp; Kalshi is ~6.5pp)")

    print("\n" + "=" * 66)
    print("TEST 2 -- calibration")
    print("=" * 66)
    for lo in np.arange(0.30, 0.75, 0.05):
        m = (pte >= lo) & (pte < lo + 0.05)
        if m.sum() >= 30:
            print(f"  {lo:.2f}-{lo+0.05:.2f}: n={m.sum():5d}  "
                  f"pred {pte[m].mean():.3f}  actual {yte[m].mean():.3f}")

    print("\n" + "=" * 66)
    print("TEST 3 -- THE GATE vs Kalshi's price")
    print("=" * 66)
    mk = json.load(open(os.path.join(REP, "rfi_calibration.json"),
                        encoding="utf-8"))
    by_key = {(r["dt"].date().isoformat(),
               frozenset((r["home_key"], r["away_key"]))): r for r in feat}
    pm = {r["game_pk"]: p for r, p in zip(te, pte)}
    joined = []
    for m in mk:
        mm = re.match(r"KXMLBRFI-(\d\d)([A-Z]{3})(\d\d)(\d{4})([A-Z]+)$",
                      m["ticker"])
        if not mm:
            continue
        yy, mon, dd, hhmm, codes = mm.groups()
        fp = datetime(2000 + int(yy), V1.MON[mon], int(dd), int(hhmm[:2]),
                      int(hhmm[2:]), tzinfo=timezone.utc) + timedelta(hours=4)
        pair = None
        for i in range(2, len(codes) - 1):
            a, b = codes[:i], codes[i:]
            if a in V1.CITY and b in V1.CITY:
                pair = frozenset((a, b))
                break
        if pair is None:
            continue
        hit = None
        for off in (0, -1, 1):
            k = ((fp + timedelta(days=off)).date().isoformat(), pair)
            if k in by_key:
                hit = by_key[k]
                break
        if hit is None or hit["game_pk"] not in pm:
            continue
        joined.append((m, hit, pm[hit["game_pk"]]))

    print(f"  joined {len(joined)} markets")
    if len(joined) < 100:
        print("  UNTESTABLE")
        return
    y = np.array([j[1]["yrfi"] for j in joined], float)
    pmar = np.array([j[0]["mid"] / 100 for j in joined])
    pmod = np.array([j[2] for j in joined])
    bmar, bmod = V1.brier(pmar, y), V1.brier(pmod, y)
    d = (pmod - y) ** 2 - (pmar - y) ** 2
    rng = random.Random(20260803)
    bs = sorted(float(np.mean(d[[rng.randrange(len(d)) for _ in range(len(d))]]))
                for _ in range(4000))
    lo, hi = bs[100], bs[3900]
    print(f"  n={len(joined)}  outcome {y.mean():.4f}")
    print(f"  KALSHI {bmar:.5f}   MODEL {bmod:.5f}")
    print(f"  model - market {bmod-bmar:+.5f}  [{lo:+.5f}, {hi:+.5f}]  "
          f"(positive = worse)")
    print(f"  VERDICT: model {'BEATS' if hi < 0 else 'DOES NOT BEAT'} Kalshi")
    print(f"  v1 was +0.00237 [-0.00072, +0.00553]")
    dis = np.abs(pmod - pmar) * 100
    print(f"\n  |model - market|: median {np.median(dis):.2f}c  "
          f"p90 {np.percentile(dis,90):.2f}c")
    print(f"  disagreements beyond the 2.25c cost bar: "
          f"{(dis>2.25).sum()} of {len(dis)}")

    print("\n" + "=" * 66)
    print("CONTROLS")
    print("=" * 66)
    ysh = y.copy()
    random.Random(3).shuffle(ysh)
    print(f"  NULL   model {V1.brier(pmod, ysh):.5f}  market "
          f"{V1.brier(pmar, ysh):.5f}")
    peek = np.clip(y * 0.96 + 0.02, 0.02, 0.98)
    print(f"  PEEK   {V1.brier(peek, y):.5f}  vs market {bmar:.5f}  "
          f"diff {V1.brier(peek,y)-bmar:+.5f}")

    json.dump({"n": len(joined), "market": bmar, "model": bmod,
               "diff": bmod - bmar, "ci": [lo, hi], "beats": bool(hi < 0),
               "model_sd_pp": float(pte.std() * 100),
               "test1_base": bb, "test1_model": bm},
              open(os.path.join(REP, "model_rfi_v2.json"), "w"), indent=1)
    print("\nwrote reports/model_rfi_v2.json")


if __name__ == "__main__":
    main()

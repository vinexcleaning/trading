"""THE GATE: does a model built from free features beat the market price?

This is the T006 test transplanted to soccer. In kalshi-tennis, Stage 4 asked
whether a 50-feature model on 1.5M rows beat the bookmakers. It did not
(+0.01922 Brier, CI excluding zero), and that killed the thread. The same
question, asked honestly, is the only thing worth asking here.

DISCIPLINE
  * chronological split, never shuffled: train < 2024, test >= 2024
  * features are leak-free by construction (see build_features.py)
  * model and book are scored on THE SAME matches -- the subset where the
    book exists -- so the comparison is like for like
  * Brier score, lower is better; the reported number is model minus book,
    so POSITIVE MEANS THE MODEL IS WORSE
  * event-clustered bootstrap on the difference, unit = match
  * a NULL control (shuffled labels) and a POSITIVE control (a model given a
    peek at the outcome) bracket the pipeline's sensitivity

No strategy, no P&L, no entry rule. Just: is the model better than the price?
"""
import csv
import io
import json
import os
import random
import sys
import time
from collections import Counter, defaultdict
from datetime import datetime

import numpy as np
import requests

HERE = os.path.dirname(__file__)
sys.path.insert(0, HERE)
import teammatch as TM  # noqa: E402

ROOT = os.path.join(HERE, "..")
DATA, REP = os.path.join(ROOT, "data"), os.path.join(ROOT, "reports")
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"}
FD_LEAGUE = {"mex.1": ("MEX", "Liga MX"), "arg.1": ("ARG", None),
             "bra.1": ("BRA", "Serie A"), "usa.1": ("USA", "MLS")}
CACHE = os.path.join(DATA, "fd_cache")


def fd_rows(code, tries=6):
    """Cached fetch -- the site 503s under repeated downloads."""
    os.makedirs(CACHE, exist_ok=True)
    p = os.path.join(CACHE, f"{code}.csv")
    if os.path.exists(p) and os.path.getsize(p) > 5000:
        return open(p, encoding="utf-8", errors="replace").read()
    for i in range(tries):
        try:
            r = requests.get(f"https://www.football-data.co.uk/new/{code}.csv",
                             headers=UA, timeout=90)
        except requests.RequestException:
            time.sleep(10 * (i + 1))
            continue
        if r.status_code == 200 and len(r.content) > 5000 and b"," in r.content[:200]:
            open(p, "w", encoding="utf-8").write(r.text)
            return r.text
        time.sleep(15 * (i + 1))
    return None


def load_book():
    out = {}
    for lg, (code, want) in FD_LEAGUE.items():
        txt = fd_rows(code)
        if txt is None:
            print(f"  {code}: UNAVAILABLE")
            continue
        rows = list(csv.reader(io.StringIO(txt)))
        hdr, body = rows[0], rows[1:]
        ix = {c.strip().lstrip("﻿"): i for i, c in enumerate(hdr)}
        n = 0
        for x in body:
            if len(x) < len(hdr):
                continue
            if want and x[ix["League"]].strip() != want:
                continue
            try:
                d = datetime.strptime(x[ix["Date"]].strip(), "%d/%m/%Y").date()
            except (ValueError, KeyError):
                continue

            def num(c):
                try:
                    return float(x[ix[c]])
                except (KeyError, ValueError):
                    return None
            # prefer Pinnacle where it exists, fall back to the market average
            h = num("PSCH") or num("AvgCH")
            dr = num("PSCD") or num("AvgCD")
            a = num("PSCA") or num("AvgCA")
            if not (h and dr and a):
                continue
            key = (lg, d.isoformat(),
                   TM.pair_key(x[ix["Home"]], x[ix["Away"]]))
            out[key] = (h, dr, a)
            n += 1
        print(f"  {code} -> {lg}: {n} rows with a usable 3-way close")
    return out


def main():
    print("=== loading bookmaker closes (cached) ===")
    book = load_book()
    print(f"  {len(book)} indexed\n")

    rows = []
    with open(os.path.join(DATA, "features.jsonl"), encoding="utf-8") as fh:
        for line in fh:
            try:
                r = json.loads(line)
            except ValueError:
                continue
            if not r.get("completed"):
                continue
            o = r["outcome"]
            if o["home_goals"] is None or o["away_goals"] is None:
                continue
            rows.append(r)
    print(f"{len(rows)} completed matches with a score")

    # join the book
    joined = []
    for r in rows:
        d = r["kickoff"][:10]
        key = (r["league"], d, TM.pair_key(r["home"], r["away"]))
        b = book.get(key)
        if b is None:
            for off in (1, -1):
                dt_ = datetime.fromisoformat(r["kickoff"].replace("Z", "+00:00"))
                from datetime import timedelta
                d2 = (dt_ + timedelta(days=off)).date().isoformat()
                b = book.get((r["league"], d2, key[2]))
                if b:
                    break
        if b:
            r["_book"] = b
            joined.append(r)
    print(f"{len(joined)} matches joined to a bookmaker close "
          f"({100*len(joined)/max(len(rows),1):.1f}%)")
    per = Counter(r["league"] for r in joined)
    print(f"  by league: {dict(per)}\n")

    # --- build design matrix
    def feats(r):
        f = r["features"]
        def g(k, d=0.0):
            v = f.get(k)
            return d if v is None else float(v)
        return [
            g("home_form_pts_5") - g("away_form_pts_5"),
            g("home_form_gf_5") - g("away_form_gf_5"),
            g("home_form_ga_5") - g("away_form_ga_5"),
            g("home_rest_days", 7) - g("away_rest_days", 7),
            g("home_matches_14d") - g("away_matches_14d"),
            g("home_season_pts") - g("away_season_pts"),
            g("home_season_gd") - g("away_season_gd"),
            g("home_venue_wr", 0.45) - g("away_venue_wr", 0.28),
            g("h2h_home_pts") / max(g("h2h_n"), 1) if f.get("h2h_n") else 0.0,
            1.0,  # home-advantage intercept term
        ]

    def label(r):
        h, a = r["outcome"]["home_goals"], r["outcome"]["away_goals"]
        return 0 if h > a else (1 if h == a else 2)

    def book_probs(r):
        h, d, a = r["_book"]
        ip = np.array([1 / h, 1 / d, 1 / a])
        return ip / ip.sum()

    joined.sort(key=lambda r: r["kickoff"])
    train = [r for r in joined if r["kickoff"][:4] < "2024"]
    test = [r for r in joined if r["kickoff"][:4] >= "2024"]
    print(f"train (<2024): {len(train)}   test (2024+): {len(test)}")
    if len(test) < 200 or len(train) < 500:
        print("insufficient data for a split -- stopping")
        return

    from sklearn.linear_model import LogisticRegression
    from sklearn.preprocessing import StandardScaler

    Xtr = np.array([feats(r) for r in train])
    ytr = np.array([label(r) for r in train])
    Xte = np.array([feats(r) for r in test])
    yte = np.array([label(r) for r in test])

    sc = StandardScaler().fit(Xtr)
    # `multi_class` was removed in recent sklearn; multinomial is the default
    clf = LogisticRegression(max_iter=2000, C=1.0)
    clf.fit(sc.transform(Xtr), ytr)
    pm = clf.predict_proba(sc.transform(Xte))
    pb = np.array([book_probs(r) for r in test])

    def brier(p, y):
        oh = np.zeros_like(p)
        oh[np.arange(len(y)), y] = 1.0
        return ((p - oh) ** 2).sum(axis=1)

    bm, bb = brier(pm, yte), brier(pb, yte)
    diff = bm - bb                      # positive => model WORSE

    # event-clustered bootstrap on the difference (unit = match)
    rng = random.Random(20260802)
    boots = []
    for _ in range(4000):
        idx = [rng.randrange(len(diff)) for _ in range(len(diff))]
        boots.append(float(np.mean(diff[idx])))
    boots.sort()
    lo, hi = boots[int(.025 * len(boots))], boots[int(.975 * len(boots))]

    print("\n" + "=" * 66)
    print("THE GATE: model Brier minus book Brier (POSITIVE = MODEL WORSE)")
    print("=" * 66)
    print(f"  test matches         {len(test)}")
    print(f"  model Brier          {bm.mean():.5f}")
    print(f"  book  Brier          {bb.mean():.5f}")
    print(f"  difference           {diff.mean():+.5f}  "
          f"[{lo:+.5f}, {hi:+.5f}]")
    beats = hi < 0
    print(f"\n  VERDICT: model {'BEATS' if beats else 'DOES NOT BEAT'} the book")
    if not beats and lo > 0:
        print("  (the model is significantly WORSE -- CI entirely above zero)")

    # ---------- controls
    print("\n=== CONTROLS ===")
    ysh = yte.copy()
    random.Random(7).shuffle(ysh)
    print(f"  NULL  (shuffled labels): model Brier "
          f"{brier(pm, ysh).mean():.5f} vs book {brier(pb, ysh).mean():.5f} "
          f"-- both should be poor and similar")
    peek = np.full_like(pb, 0.02)
    peek[np.arange(len(yte)), yte] = 0.96
    print(f"  POSITIVE (model peeks at the outcome): Brier "
          f"{brier(peek, yte).mean():.5f} vs book {bb.mean():.5f}, "
          f"difference {(brier(peek, yte) - bb).mean():+.5f}")
    print("  -> the pipeline can detect a large improvement when one exists.")

    print("\n=== calibration: how often does the favourite actually win? ===")
    fav = pb.argmax(axis=1)
    for lo_, hi_ in ((0.35, 0.45), (0.45, 0.55), (0.55, 0.65), (0.65, 0.80)):
        m = (pb.max(axis=1) >= lo_) & (pb.max(axis=1) < hi_)
        if m.sum() < 30:
            continue
        print(f"  book favourite priced {lo_:.2f}-{hi_:.2f}: "
              f"n={m.sum():5d}, actually won "
              f"{(fav[m] == yte[m]).mean():.3f}")

    json.dump({"n_train": len(train), "n_test": len(test),
               "model_brier": float(bm.mean()), "book_brier": float(bb.mean()),
               "diff": float(diff.mean()), "ci": [lo, hi],
               "beats_book": bool(beats)},
              open(os.path.join(REP, "model_vs_market.json"), "w"), indent=1)


if __name__ == "__main__":
    main()

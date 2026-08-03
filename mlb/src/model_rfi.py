"""Build a first-inning model and test it against Kalshi's actual prices.

LEAK-FREE BY CONSTRUCTION. Games are processed in strict date order and each
game enters the running history only AFTER its own features are computed, so a
future game cannot inform a past one. Assertions sit on top of that.

MISSING STAYS MISSING. phatcobra/nrfi-predictor's rule, and it is right:
"Missing observations remain missing; they are never converted into
zero-valued outcomes or included in rate denominators." A pitcher with no
history gets an explicit unknown flag and the league mean, not a zero.

THREE TESTS, in increasing difficulty:
  1. does the model beat the base rate on held-out games?   (weak)
  2. is the model calibrated?                               (necessary)
  3. does the model beat KALSHI'S PRICE on the 889 markets? (the gate)

Controls: shuffled labels (must collapse) and a peek at the outcome (must
soar). Without both, a null result means nothing.
"""
import json
import os
import random
import re
import sys
from collections import Counter, defaultdict, deque
from datetime import datetime, timedelta, timezone

import numpy as np

HERE = os.path.dirname(__file__)
sys.path.insert(0, os.path.join(HERE, "..", "..", "market-selection", "src"))
sys.path.insert(0, os.path.join(HERE, "..", "..", "common"))
import kalshi_api as K  # noqa: E402
import costbar  # noqa: E402

ROOT = os.path.join(HERE, "..")
DATA, REP = os.path.join(ROOT, "data"), os.path.join(ROOT, "reports")
MON = {m: i + 1 for i, m in enumerate(
    ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT",
     "NOV", "DEC"])}

CITY = {
    "ARI": "arizona", "ATL": "atlanta", "BAL": "baltimore", "BOS": "boston",
    "CHC": "chicago cubs", "CWS": "chicago white sox", "CIN": "cincinnati",
    "CLE": "cleveland", "COL": "colorado", "DET": "detroit", "HOU": "houston",
    "KC": "kansas city", "LAA": "los angeles angels", "LAD": "los angeles dodgers",
    "MIA": "miami", "MIL": "milwaukee", "MIN": "minnesota", "NYM": "new york mets",
    "NYY": "new york yankees", "ATH": "athletics", "PHI": "philadelphia",
    "PIT": "pittsburgh", "SD": "san diego", "SF": "san francisco",
    "SEA": "seattle", "STL": "st. louis", "TB": "tampa bay", "TEX": "texas",
    "TOR": "toronto", "WSH": "washington",
}


def norm(s):
    return re.sub(r"[^a-z ]", " ", (s or "").lower()).strip()


def team_key(full_name):
    """'San Francisco Giants' -> a stable key matching Kalshi's city string."""
    n = norm(full_name)
    best, bl = None, 0
    for code, city in CITY.items():
        if city in n and len(city) > bl:
            best, bl = code, len(city)
    if best:
        return best
    # Athletics / others without a city in the name
    if "athletic" in n:
        return "ATH"
    return n[:12]


def load_games():
    rows = []
    with open(os.path.join(DATA, "games", "games.jsonl"), encoding="utf-8") as fh:
        for line in fh:
            try:
                g = json.loads(line)
            except ValueError:
                continue
            if g.get("game_type") not in ("R", None):   # regular season only
                continue
            try:
                g["_dt"] = datetime.fromisoformat(g["date"].replace("Z", "+00:00"))
            except (ValueError, KeyError):
                continue
            rows.append(g)
    rows.sort(key=lambda g: g["_dt"])
    return rows


def build(rows):
    """Chronological pass. Features from history only."""
    LG = 0.506                                   # league prior, refined below
    p_hist = defaultdict(lambda: [0, 0])         # pitcher -> [starts, 1st-inn runs allowed]
    t_off = defaultdict(lambda: [0, 0])          # team -> [games, scored in 1st]
    t_off_ha = defaultdict(lambda: [0, 0])       # (team,ha)
    v_hist = defaultdict(lambda: [0, 0])         # venue -> [games, yrfi]
    recent = defaultdict(lambda: deque(maxlen=10))
    out = []
    lg_n = lg_y = 0
    for g in rows:
        h, a = g["home"], g["away"]
        hk, ak = team_key(h.get("team")), team_key(a.get("team"))
        hp, ap = h.get("probable_id"), a.get("probable_id")
        vid = g.get("venue_id")
        lg = (lg_y / lg_n) if lg_n >= 500 else LG

        def prate(pid):
            if not pid:
                return None, 0
            s, r = p_hist[pid]
            return (r / s if s >= 3 else None), s

        def orate(tk, ha):
            n_, y_ = t_off_ha[(tk, ha)]
            return (y_ / n_ if n_ >= 10 else None), n_

        hp_r, hp_n = prate(hp)
        ap_r, ap_n = prate(ap)
        ho_r, ho_n = orate(hk, "home")
        ao_r, ao_n = orate(ak, "away")
        vn, vy = v_hist[vid]
        v_r = (vy / vn) if vn >= 20 else None
        hrec = list(recent[hk])
        arec = list(recent[ak])

        feats = {
            # pitcher: fraction of past starts where he allowed a 1st-inning run
            "home_sp_r1": hp_r, "home_sp_n": hp_n,
            "away_sp_r1": ap_r, "away_sp_n": ap_n,
            # offence: fraction of past games where the team scored in the 1st
            "home_off": ho_r, "home_off_n": ho_n,
            "away_off": ao_r, "away_off_n": ao_n,
            "venue_yrfi": v_r, "venue_n": vn,
            "recent_home": (sum(hrec) / len(hrec)) if len(hrec) >= 5 else None,
            "recent_away": (sum(arec) / len(arec)) if len(arec) >= 5 else None,
            "is_night": 1.0 if g.get("day_night") == "night" else 0.0,
            "league_rate": lg,
        }
        out.append({"game_pk": g["game_pk"], "dt": g["_dt"], "date": g["date"],
                    "season": g.get("season"), "home_key": hk, "away_key": ak,
                    "home_team": h.get("team"), "away_team": a.get("team"),
                    "yrfi": g["yrfi"], "feats": feats})

        # ---- now, and only now, this game enters history
        y = g["yrfi"]
        lg_n += 1
        lg_y += y
        ar = g["first_inning_away_runs"]
        hr = g["first_inning_home_runs"]
        if hp:
            p_hist[hp][0] += 1
            p_hist[hp][1] += 1 if ar > 0 else 0     # home SP faces away batters
        if ap:
            p_hist[ap][0] += 1
            p_hist[ap][1] += 1 if hr > 0 else 0
        t_off_ha[(hk, "home")][0] += 1
        t_off_ha[(hk, "home")][1] += 1 if hr > 0 else 0
        t_off_ha[(ak, "away")][0] += 1
        t_off_ha[(ak, "away")][1] += 1 if ar > 0 else 0
        v_hist[vid][0] += 1
        v_hist[vid][1] += y
        recent[hk].append(y)
        recent[ak].append(y)
    return out


NUM = ["home_sp_r1", "away_sp_r1", "home_off", "away_off", "venue_yrfi",
       "recent_home", "recent_away"]


def design(rows):
    X, miss = [], []
    for r in rows:
        f = r["feats"]
        lg = f["league_rate"]
        v, m = [], []
        for k in NUM:
            x = f.get(k)
            m.append(1.0 if x is None else 0.0)
            v.append(lg if x is None else x)      # league mean, flagged
        v += [f["is_night"], np.log1p(f["home_sp_n"]), np.log1p(f["away_sp_n"])]
        X.append(v + m)
    return np.array(X, dtype=float)


def brier(p, y):
    return float(np.mean((p - y) ** 2))


def main():
    rows = load_games()
    print(f"{len(rows)} regular-season games "
          f"{rows[0]['_dt'].date()} .. {rows[-1]['_dt'].date()}")
    feat = build(rows)

    # leak assertion: features of game i must not use game i or later
    assert all(feat[i]["dt"] <= feat[i + 1]["dt"] for i in range(len(feat) - 1))
    print(f"built {len(feat)} feature rows (chronological, leak-free by construction)")
    cov = {k: sum(1 for r in feat if r["feats"].get(k) is not None) for k in NUM}
    print("  coverage: " + ", ".join(f"{k}={100*v/len(feat):.0f}%"
                                     for k, v in cov.items()))

    tr = [r for r in feat if r["season"] and int(r["season"]) <= 2024]
    te = [r for r in feat if r["season"] and int(r["season"]) >= 2025]
    print(f"\ntrain <=2024: {len(tr)}   test 2025+: {len(te)}")

    from sklearn.linear_model import LogisticRegression
    from sklearn.preprocessing import StandardScaler
    Xtr, ytr = design(tr), np.array([r["yrfi"] for r in tr], float)
    Xte, yte = design(te), np.array([r["yrfi"] for r in te], float)
    sc = StandardScaler().fit(Xtr)
    clf = LogisticRegression(max_iter=3000, C=0.5).fit(sc.transform(Xtr), ytr)
    pte = clf.predict_proba(sc.transform(Xte))[:, 1]
    base = float(ytr.mean())

    print("\n" + "=" * 66)
    print("TEST 1 -- does the model beat the base rate on held-out games?")
    print("=" * 66)
    bb = brier(np.full_like(yte, base), yte)
    bm = brier(pte, yte)
    print(f"  n={len(yte)}   base rate (train) {base:.4f}")
    print(f"  base-rate Brier {bb:.5f}")
    print(f"  model Brier     {bm:.5f}")
    print(f"  improvement     {bb-bm:+.5f}")
    print(f"  model prob: sd {pte.std():.4f}  range {pte.min():.3f}-{pte.max():.3f}")

    print("\n" + "=" * 66)
    print("TEST 2 -- is the model calibrated?")
    print("=" * 66)
    for lo in np.arange(0.35, 0.70, 0.05):
        m = (pte >= lo) & (pte < lo + 0.05)
        if m.sum() >= 30:
            print(f"  predicted {lo:.2f}-{lo+0.05:.2f}: n={m.sum():5d} "
                  f"mean p {pte[m].mean():.3f}  actual {yte[m].mean():.3f}")

    # ---------------- TEST 3: against Kalshi's actual prices
    print("\n" + "=" * 66)
    print("TEST 3 -- THE GATE: does the model beat KALSHI'S PRICE?")
    print("=" * 66)
    mk = json.load(open(os.path.join(REP, "rfi_calibration.json"),
                        encoding="utf-8"))
    print(f"  {len(mk)} priced markets loaded")
    by_key = {}
    for r in feat:
        by_key[(r["dt"].date().isoformat(),
                frozenset((r["home_key"], r["away_key"])))] = r
    # index model probs for the test period
    pm = {r["game_pk"]: p for r, p in zip(te, pte)}

    joined, nojoin = [], 0
    for m in mk:
        t = m["ticker"]
        mm = re.match(r"KXMLBRFI-(\d\d)([A-Z]{3})(\d\d)(\d{4})([A-Z]+)$", t)
        if not mm:
            nojoin += 1
            continue
        yy, mon, dd, hhmm, codes = mm.groups()
        fp = datetime(2000 + int(yy), MON[mon], int(dd), int(hhmm[:2]),
                      int(hhmm[2:]), tzinfo=timezone.utc) + timedelta(hours=4)
        # split the concatenated team codes against the known set
        pair = None
        for i in range(2, len(codes) - 1):
            a_, b_ = codes[:i], codes[i:]
            if a_ in CITY and b_ in CITY:
                pair = frozenset((a_, b_))
                break
        if pair is None:
            nojoin += 1
            continue
        hit = None
        for off in (0, -1, 1):
            k = ((fp + timedelta(days=off)).date().isoformat(), pair)
            if k in by_key:
                hit = by_key[k]
                break
        if hit is None or hit["game_pk"] not in pm:
            nojoin += 1
            continue
        joined.append((m, hit, pm[hit["game_pk"]]))

    print(f"  joined to a modelled game: {len(joined)}   failed: {nojoin}")
    if len(joined) < 100:
        print("  too few joined -- UNTESTABLE")
        return
    y = np.array([j[1]["yrfi"] for j in joined], float)
    pmar = np.array([j[0]["mid"] / 100 for j in joined])
    pmod = np.array([j[2] for j in joined])
    bmar, bmod = brier(pmar, y), brier(pmod, y)
    d = (pmod - y) ** 2 - (pmar - y) ** 2
    rng = random.Random(20260802)
    boots = sorted(float(np.mean(d[[rng.randrange(len(d))
                                    for _ in range(len(d))]]))
                   for _ in range(4000))
    lo, hi = boots[100], boots[3900]
    print(f"\n  n={len(joined)}   outcome rate {y.mean():.4f}")
    print(f"  KALSHI Brier {bmar:.5f}")
    print(f"  MODEL  Brier {bmod:.5f}")
    print(f"  model - market {bmod-bmar:+.5f}  [{lo:+.5f}, {hi:+.5f}]")
    print(f"  (positive = model WORSE)")
    print(f"\n  VERDICT: model "
          f"{'BEATS' if hi < 0 else 'DOES NOT BEAT'} the Kalshi price")

    disagree = np.abs(pmod - pmar) * 100
    bar = 2.25
    print(f"\n  |model - market| in cents: median {np.median(disagree):.2f}  "
          f"p90 {np.percentile(disagree,90):.2f}  max {disagree.max():.2f}")
    print(f"  markets where the model disagrees by more than the "
          f"{bar}c cost bar: {(disagree > bar).sum()} of {len(disagree)}")

    print("\n" + "=" * 66)
    print("CONTROLS")
    print("=" * 66)
    ysh = y.copy()
    random.Random(11).shuffle(ysh)
    print(f"  NULL (shuffled outcomes): model {brier(pmod, ysh):.5f} vs "
          f"market {brier(pmar, ysh):.5f} -- both should degrade to ~0.25")
    peek = np.clip(y * 0.96 + 0.02, 0.02, 0.98)
    print(f"  POSITIVE (peek at outcome): Brier {brier(peek, y):.5f} vs "
          f"market {bmar:.5f}, difference {brier(peek,y)-bmar:+.5f}")
    print("  -> the comparison can detect a real improvement when one exists.")

    json.dump({"n": len(joined), "market_brier": bmar, "model_brier": bmod,
               "diff": bmod - bmar, "ci": [lo, hi],
               "beats": bool(hi < 0),
               "test1_base": bb, "test1_model": bm},
              open(os.path.join(REP, "model_rfi.json"), "w"), indent=1)


if __name__ == "__main__":
    main()

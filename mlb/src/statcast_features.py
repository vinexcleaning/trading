"""Pitcher and batter quality features from first-inning Statcast.

WHY THE OLD MODEL WAS WEAK. Its pitcher feature was "what fraction of his past
starts allowed a first-inning run" -- a binary outcome on a dozen games, which
is mostly noise. That is why the model's probabilities varied by only 1.9pp
while Kalshi's varied by ~6.5pp: it could not tell pitchers apart.

Statcast measures the underlying quality on hundreds of pitches instead:
expected wOBA on contact, hard-hit rate, strikeout rate, walk rate. Same idea
for the three batters due up.

NO EXTRA LINEUP FETCH NEEDED. Statcast records who actually batted, and the
first three at-bats of a game ARE the top of the order. Substitutions happen
later, so for the first inning "who batted" is the announced lineup.

LEAK-FREE BY CONSTRUCTION. Games are processed in date order; a game's pitches
enter the rolling stats only AFTER that game's features are written.

MISSING STAYS MISSING (phatcobra's rule). A pitcher with too little history
gets an explicit unknown flag and the league mean, never a zero.
"""
import csv
import glob
import json
import os
import sys
from collections import Counter, defaultdict, deque
from datetime import datetime

ROOT = os.path.join(os.path.dirname(__file__), "..")
SC = os.path.join(ROOT, "data", "statcast")
OUT = os.path.join(ROOT, "data", "sc_features.jsonl")

MIN_PITCH = 60          # minimum pitches before a rate is trusted
WIN = 400               # rolling window, pitches


def load():
    """All first-inning pitches, grouped by game, in date order."""
    games = defaultdict(list)
    files = sorted(glob.glob(os.path.join(SC, "first_*.csv")))
    print(f"{len(files)} statcast chunks")
    for f in files:
        with open(f, encoding="utf-8") as fh:
            rd = csv.DictReader(fh)
            for r in rd:
                if r.get("inning") != "1":
                    continue
                pk = r.get("game_pk")
                if not pk:
                    continue
                games[pk].append(r)
    print(f"  {len(games):,} games, "
          f"{sum(len(v) for v in games.values()):,} first-inning pitches")
    return games


def fnum(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


class Roll:
    """Rolling first-inning quality for one player."""

    __slots__ = ("xwoba", "hard", "k", "bb", "pa", "pitches")

    def __init__(self):
        self.xwoba = deque(maxlen=WIN)
        self.hard = deque(maxlen=WIN)
        self.k = deque(maxlen=200)
        self.bb = deque(maxlen=200)
        self.pa = 0
        self.pitches = 0

    def stats(self):
        if self.pitches < MIN_PITCH:
            return None
        return {
            "xwoba": (sum(self.xwoba) / len(self.xwoba)) if self.xwoba else None,
            "hard": (sum(self.hard) / len(self.hard)) if self.hard else None,
            "k": (sum(self.k) / len(self.k)) if self.k else None,
            "bb": (sum(self.bb) / len(self.bb)) if self.bb else None,
            "n": self.pitches,
        }

    def add(self, rows):
        for r in rows:
            self.pitches += 1
            xw = fnum(r.get("estimated_woba_using_speedangle"))
            if xw is not None:
                self.xwoba.append(xw)
            ls = fnum(r.get("launch_speed"))
            if ls is not None:
                self.hard.append(1.0 if ls >= 95 else 0.0)
            ev = (r.get("events") or "").strip()
            if ev:
                self.pa += 1
                self.k.append(1.0 if "strikeout" in ev else 0.0)
                self.bb.append(1.0 if ev in ("walk", "hit_by_pitch") else 0.0)


def main():
    games = load()
    order = sorted(games, key=lambda pk: (games[pk][0].get("game_date") or "",
                                          pk))
    pit = defaultdict(Roll)
    bat = defaultdict(Roll)
    out = []
    for pk in order:
        rows = games[pk]
        date_ = rows[0].get("game_date")
        # split the inning into halves; away bats first (top)
        top = [r for r in rows if (r.get("inning_topbot") or "").lower().startswith("t")]
        bot = [r for r in rows if (r.get("inning_topbot") or "").lower().startswith("b")]
        if not top or not bot:
            # fall back on at_bat_number ordering if topbot is absent
            rows2 = sorted(rows, key=lambda r: (int(r.get("at_bat_number") or 0),
                                                int(r.get("pitch_number") or 0)))
            half = len(rows2) // 2
            top, bot = rows2[:half], rows2[half:]

        def side(half_rows):
            if not half_rows:
                return None, []
            pids = Counter(r.get("pitcher") for r in half_rows)
            p = pids.most_common(1)[0][0]
            seen, bs = set(), []
            for r in sorted(half_rows,
                            key=lambda r: int(r.get("at_bat_number") or 0)):
                b = r.get("batter")
                if b and b not in seen:
                    seen.add(b)
                    bs.append(b)
            return p, bs[:3]

        home_p, away_bs = side(top)      # home pitcher faces away batters
        away_p, home_bs = side(bot)

        def pack(pref, pid, bids):
            d = {}
            ps = pit[pid].stats() if pid else None
            d[f"{pref}_sp_xwoba"] = ps["xwoba"] if ps else None
            d[f"{pref}_sp_hard"] = ps["hard"] if ps else None
            d[f"{pref}_sp_k"] = ps["k"] if ps else None
            d[f"{pref}_sp_bb"] = ps["bb"] if ps else None
            d[f"{pref}_sp_n"] = ps["n"] if ps else 0
            xs = [bat[b].stats() for b in bids]
            xs = [x for x in xs if x]
            for key in ("xwoba", "hard", "k", "bb"):
                vals = [x[key] for x in xs if x.get(key) is not None]
                d[f"{pref}_bat_{key}"] = (sum(vals) / len(vals)) if vals else None
            d[f"{pref}_bat_known"] = len(xs)
            return d

        feats = {}
        feats.update(pack("home", home_p, away_bs))   # home SP vs away bats
        feats.update(pack("away", away_p, home_bs))
        out.append({"game_pk": int(pk), "date": date_, "feats": feats})

        # ---- only now do this game's pitches enter the rolling stats
        if home_p:
            pit[home_p].add(top)
        if away_p:
            pit[away_p].add(bot)
        bybat = defaultdict(list)
        for r in rows:
            bybat[r.get("batter")].append(r)
        for b, rs in bybat.items():
            if b:
                bat[b].add(rs)

    with open(OUT, "w", encoding="utf-8") as fh:
        for r in out:
            fh.write(json.dumps(r) + "\n")
    print(f"\nwrote {len(out):,} games to {OUT}")
    keys = ["home_sp_xwoba", "home_sp_k", "home_bat_xwoba", "away_sp_xwoba",
            "away_bat_xwoba"]
    for k in keys:
        n = sum(1 for r in out if r["feats"].get(k) is not None)
        print(f"  {k:20s} present on {n:>6,} ({100*n/max(len(out),1):5.1f}%)")
    print(f"  distinct pitchers tracked: {len(pit):,}   batters: {len(bat):,}")


if __name__ == "__main__":
    main()

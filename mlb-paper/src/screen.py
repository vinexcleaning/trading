"""Screen candidate ENTRY strategies offline before any of them takes a slot.

Mailbox 028. The 10 duplicate slots are already being paid for in the joint
denominator, so filling them is close to free -- but only if what goes in is
genuinely different from the current five and from each other.

⚠ THIS IS A SCREEN, NOT A RESULT. Every candidate is measured on the SAME 863
archive games. The best of N candidates on one sample looks good whether or not
anything works, and the number of candidates screened is printed at the top of
the output for exactly that reason. **Nothing here is evidence.** The screen
decides only which ideas are worth a pre-registration and a slot; the forward
test is what decides whether they work.

Costs use the corrected half rate (see fees.py). Prices are the real ask.

    python src/screen.py
"""
from __future__ import annotations

import collections
import statistics
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

import features as FT                                  # noqa: E402
import fees as FEE                                     # noqa: E402
import replay as R                                     # noqa: E402

TRUTH = HERE.parent / "data" / "kalshi_truth.db"
BAR_C = 1.0
HOURS_BEFORE = 6


# --------------------------------------------------------- the candidates
# Each returns "home", "away" or None: which side this idea would back.
# None means "no view on this game" and is NOT a bet.

def c_rested(f, g):
    """Back the better-rested team. Fatigue is the oldest baseball story
    there is and none of the current five touch it."""
    a, h = f["away"]["rest_days"], f["home"]["rest_days"]
    if a is None or h is None or a == h:
        return None
    return "home" if h > a else "away"


def c_travel(f, g):
    """Fade the team that has just flown a long way."""
    a = f["away"]["travel_miles"] or 0
    h = f["home"]["travel_miles"] or 0
    if max(a, h) < 1200 or abs(a - h) < 600:
        return None
    return "home" if a > h else "away"


def c_night_to_day(f, g):
    """Fade a team playing a day game after a night game."""
    a, h = f["away"]["night_to_day"], f["home"]["night_to_day"]
    if a == h:
        return None
    return "home" if a else "away"


def c_doubleheader(f, g):
    """Fade the team in a doubleheader (both are, usually -- so this mostly
    fires on the rare split-squad/makeup case)."""
    if not f["away"]["doubleheader"] and not f["home"]["doubleheader"]:
        return None
    return "home"          # home team sleeps at home between games


def c_home_late_series(f, g):
    """Back the home team from game 3 of a series on -- the visitor is deepest
    into the trip."""
    sg = f["home"]["series_game"]
    if not sg or sg < 3:
        return None
    return "home"


def c_road_favourite_fade(f, g):
    """Fade the road side when it is the market favourite. A structural
    price-shape idea rather than a fatigue one, kept for contrast."""
    return "home"


CANDIDATES = {
    "rested": c_rested,
    "travel": c_travel,
    "night-to-day": c_night_to_day,
    "doubleheader": c_doubleheader,
    "home-late-series": c_home_late_series,
    "always-home": c_road_favourite_fade,          # the naive benchmark
}


def run():
    cache = R.cache()
    feats = FT.build(cache)
    tcon = sqlite3.connect(f"file:{TRUTH}?mode=ro", uri=True)
    tcon.row_factory = sqlite3.Row
    tape = collections.defaultdict(dict)
    for r in tcon.execute("SELECT ticker, game_date, away, home, suffix "
                          "FROM market WHERE series='KXMLBGAME'"):
        tape[(r["game_date"], r["away"], r["home"])][r["suffix"]] = r["ticker"]

    from datetime import timedelta
    rows = cache.execute(
        "SELECT * FROM game WHERE status='Final' AND away_runs IS NOT NULL "
        "AND json_extract(raw,'$.gameType')='R' ORDER BY starts_utc").fetchall()
    res = {k: [] for k in CANDIDATES}
    seen = 0
    for g in rows:
        f = feats.get(g["game_pk"])
        if not f:
            continue
        tk = None
        for off in (0, 1, -1):
            d2 = (datetime.fromisoformat(g["game_date"])
                  + timedelta(days=off)).date().isoformat()
            tk = tape.get((d2, g["away_code"], g["home_code"]))
            if tk:
                break
        if not tk or len(tk) < 2:
            continue
        st = int(datetime.fromisoformat(
            g["starts_utc"].replace("Z", "+00:00")).timestamp())
        at = st - HOURS_BEFORE * 3600
        q = {s: R.quote(tcon, tk.get(g[f"{s}_code"]), at)
             for s in ("away", "home")}
        if not q["away"] or not q["home"]:
            continue
        seen += 1
        home_won = g["home_runs"] > g["away_runs"]
        for name, fn in CANDIDATES.items():
            side = fn(f, g)
            if side is None:
                continue
            price = q[side]["ask"]
            fee = FEE.edge_fee_c(price, "KXMLBGAME")
            won = home_won if side == "home" else not home_won
            pnl = (100.0 if won else 0.0) - price - fee
            res[name].append((pnl / 100.0, price / 100.0, won))
    tcon.close()
    cache.close()
    return res, seen


if __name__ == "__main__":
    res, seen = run()
    print(f"⚠ SCREEN ONLY -- {len(CANDIDATES)} candidates on the SAME {seen} "
          f"archive games.")
    print("   The best of six on one sample looks good whether or not anything")
    print("   works. Nothing below is evidence; it decides only what earns a")
    print("   pre-registration and a slot.\n")
    print(f"{'candidate':<20}{'games':>7}{'won':>7}{'return':>10}{'money':>10}")
    for name, v in sorted(res.items(), key=lambda kv: -len(kv[1])):
        if not v:
            print(f"{name:<20}      0")
            continue
        P = sum(x[0] for x in v)
        S = sum(x[1] for x in v)
        w = sum(1 for x in v if x[2])
        print(f"{name:<20}{len(v):>7}{100*w/len(v):>6.0f}%"
              f"{100*P/S:>9.1f}%{P:>10.2f}")
    print("\n  'always-home' is the naive benchmark: back the home team every")
    print("  time. Any candidate that cannot beat it is not an idea.")

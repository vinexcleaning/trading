r"""
t9_upcoming.py - the practical sheet: what is coming up, and what the ranking
gap says about it.

READ THIS BEFORE READING THE SHEET
    This is NOT a set of picks and there is no validated edge behind it.

    `t7_sweep.py` tested 2,008 pre-registered cells of player features against
    Kalshi's opening price and found a clean null - fewer discoveries than its
    own permutation null. `t8_calibration.py` then showed that on tradeable
    books (spread <= 2c) the opening price is calibrated across the entire range
    from 1c to 99c: 0 of 10 price bands deviate, pooled residual +0.03pp.

    Ranking is the single most public piece of information in tennis. If
    computed recent form adds nothing to the price, ranking almost certainly
    adds less. **The ranking-implied probability column below is a DESCRIPTION,
    not a signal.** Where it disagrees with a market price, the base rate in this
    repo says the market is right and the model is wrong.

WHAT IT IS GOOD FOR
    Knowing what is on, on what surface, at what level, and who is nominally
    stronger - without opening ten browser tabs.

BUDGET
    The free key is 100 calls/day (the site advertises 1,000 - it is wrong, see
    ledger B022). Everything is cached to ../data/, so a re-run costs 0 calls
    unless you pass --refresh.
"""
from __future__ import annotations
import os, sys, json, time, argparse, math

import requests
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.abspath(os.path.join(HERE, "..", "data"))
OUT = os.path.abspath(os.path.join(HERE, "..", "out"))
os.makedirs(DATA, exist_ok=True)

BASE = "https://api.livetennisapi.com/api/public/v1"
PLAYER_PAGES = 10           # 10 x 200 = the 2,000 best-ranked players


def client():
    key = os.environ.get("LIVETENNIS_API_KEY", "").strip()
    if not key:
        sys.exit("LIVETENNIS_API_KEY is not set. See ../ITF_CHECK.md")
    return {"User-Agent": "bot-forensics/1.0", "Authorization": f"bearer {key}"}


def paged(path, headers, pages, params=None, sleep=2.2):
    """Fetch `pages` pages of 200. Retries a 502 once - the API throws
    transient gateway errors that are NOT auth failures."""
    recs = []
    for i in range(pages):
        p = dict(params or {}, limit=200, offset=i * 200)
        for attempt in range(2):
            r = requests.get(BASE + path, headers=headers, params=p, timeout=30)
            if r.status_code == 200:
                break
            time.sleep(3)
        if r.status_code != 200:
            print(f"  {path} offset {i*200} -> {r.status_code}, stopping")
            break
        d = r.json()
        recs += d.get("data", [])
        if not d.get("meta", {}).get("has_more"):
            break
        time.sleep(sleep)
    return recs


def cached(name, fetch, refresh):
    path = os.path.join(DATA, name)
    if os.path.exists(path) and not refresh:
        with open(path, encoding="utf-8") as f:
            print(f"  {name}: from cache (0 API calls)")
            return json.load(f)
    recs = fetch()
    with open(path, "w", encoding="utf-8") as f:
        json.dump(recs, f)
    print(f"  {name}: fetched {len(recs)}")
    return recs


def elo_ish(r1, r2):
    """A crude ranking-gap -> probability map. NOT fitted, NOT validated.

    Log-ranking difference through a logistic, scale 0.9. It is here to make
    the gap readable, not to price anything.

    Measured anchor points, so nobody has to guess what the scale means:
        rank   1 vs  10  ->  88.8%      rank  10 vs  50  ->  81.0%
        rank   1 vs 100  ->  98.4%      rank  50 vs 100  ->  65.1%
        rank 100 vs 200  ->  65.1%      rank  13 vs  27  ->  65.9%

    Note it is scale-free in the ratio: 50-vs-100 and 100-vs-200 give the same
    number. That is almost certainly wrong as tennis, and is one more reason
    not to read this column as a price. **98.4% for rank 1 vs 100 is far too
    confident** - a real model would not go there on ranking alone.
    """
    if not r1 or not r2:
        return float("nan")
    d = math.log(r2) - math.log(r1)
    return 1.0 / (1.0 + math.exp(-d * 0.9))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--refresh", action="store_true")
    ap.add_argument("--tour", default=None, help="atp / wta / challenger / itf")
    a = ap.parse_args()

    H = client()
    print("fetching (cached where possible):")
    players = cached("lta_players.json",
                     lambda: paged("/players", H, PLAYER_PAGES), a.refresh)
    fixtures = cached("lta_fixtures_all.json",
                      lambda: paged("/fixtures", H, 3), a.refresh)

    P = {p["id"]: p for p in players}
    print(f"\nplayers cached: {len(P)}   fixtures: {len(fixtures)}")

    rows = []
    for f in fixtures:
        p1, p2 = P.get(f.get("player1_id")), P.get(f.get("player2_id"))
        r1 = (p1 or {}).get("ranking")
        r2 = (p2 or {}).get("ranking")
        rows.append(dict(
            date=f.get("event_date"), start=(f.get("start_time") or "")[11:16],
            tour=(f.get("tour") or "").upper(),
            tournament=f.get("tournament"), surface=f.get("surface"),
            round=f.get("round_code"),
            p1=f.get("player1_name"), r1=r1,
            p2=f.get("player2_name"), r2=r2,
            gap=(r2 - r1) if (r1 and r2) else None,
            p1_win_rank=elo_ish(r1, r2)))
    df = pd.DataFrame(rows)
    if a.tour:
        df = df[df.tour == a.tour.upper()]

    df = df.sort_values(["date", "start"], na_position="last")
    df.to_csv(os.path.join(OUT, "t9_upcoming.csv"), index=False)

    pd.set_option("display.width", 250)
    pd.set_option("display.max_rows", 200)

    print(f"\n{'='*100}")
    print("UPCOMING MATCHES  -  DESCRIPTIVE ONLY, NOT PICKS")
    print(f"{'='*100}")
    print(f"total fixtures: {len(df)}")
    print("\nby tour:", df.tour.value_counts().to_dict())
    print("by surface:", df.surface.value_counts(dropna=False).to_dict())

    both = df[df.r1.notna() & df.r2.notna()]
    print(f"\nfixtures where BOTH players are inside the top "
          f"{PLAYER_PAGES*200} by ranking: {len(both)} of {len(df)}")
    print("(the rest are lower-ranked ITF/Challenger players not in the cache;")
    print(" pull more pages with --refresh after raising PLAYER_PAGES)")

    if len(both):
        show = both.nsmallest(40, "gap", keep="all") if False else \
            both.reindex(both.gap.abs().sort_values().index)
        print("\n--- the 25 CLOSEST matchups by ranking (most uncertain)")
        print(show.head(25)[["date", "start", "tour", "tournament", "surface",
                             "round", "p1", "r1", "p2", "r2",
                             "p1_win_rank"]].to_string(
            index=False, float_format=lambda x: f"{x:.2f}"))

        print("\n--- the 25 most LOPSIDED by ranking")
        print(show.tail(25)[["date", "start", "tour", "tournament", "surface",
                             "round", "p1", "r1", "p2", "r2",
                             "p1_win_rank"]].to_string(
            index=False, float_format=lambda x: f"{x:.2f}"))

    print(f"\nwritten: out/t9_upcoming.csv")
    print("\n" + "!" * 100)
    print("`p1_win_rank` IS NOT A PRICE AND NOT A PICK. It is an unfitted")
    print("function of the ranking gap, shown to make the gap readable.")
    print("This repo has measured that Kalshi's price already contains")
    print("everything a ranking or a form model knows (ledger B023, B027):")
    print("on tradeable books, 0 of 10 price bands deviate from calibration.")
    print("Where this column disagrees with a market, bet on the market.")
    print("!" * 100)


if __name__ == "__main__":
    main()

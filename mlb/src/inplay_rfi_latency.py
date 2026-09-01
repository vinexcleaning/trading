"""THE IN-PLAY TEST: when a run scores in the 1st, when does the price move?

The cleanest event available anywhere in this project. A first-inning run
resolves KXMLBRFI to YES outright, so the price must travel from roughly 50c
to roughly 99c at a precisely known instant. Nothing about it is ambiguous.

WHAT IS BEING MEASURED, and why it is the whole question:

    t_feed   = MLB StatsAPI's timestamp for the scoring play
    t_market = the first trade that prints at a clearly-moved price

    lag = t_market - t_feed

  lag strongly POSITIVE -> the feed knows first. There is a window, and its
                           size and the volume inside it are the opportunity.
  lag NEGATIVE or ~zero -> the market moves at or before the feed. We would
                           always be last. The idea is dead, and no amount of
                           modelling fixes it.

This is a latency question, not a prediction question, so no model is fitted
and nothing is forecast.

HONEST LIMITS, stated before the numbers:
  * `startTime` is when MLB's system recorded the play, not when the ball was
    hit. The lag measured is feed-to-market, which is what a trader using that
    feed would face -- but it is not "physics to market".
  * Trade prints show when someone DID trade, not when they COULD have. A gap
    with no prints is ambiguous.
  * Kalshi's tape has millisecond stamps; that part is not the constraint.
"""
import glob
import json
import os
import re
import statistics as st
import sys
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone

ROOT = os.path.join(os.path.dirname(__file__), "..")
TAPE = os.path.join(ROOT, "..", "market-selection", "data", "tape_pmxt_window")
DATA, REP = os.path.join(ROOT, "data"), os.path.join(ROOT, "reports")

CODES = {
    "ARI": "arizona", "ATL": "atlanta", "BAL": "baltimore", "BOS": "boston",
    "CHC": "chicago cubs", "CWS": "chicago white sox", "CIN": "cincinnati",
    "CLE": "cleveland", "COL": "colorado", "DET": "detroit", "HOU": "houston",
    "KC": "kansas city", "LAA": "los angeles angels", "LAD": "los angeles dodgers",
    "MIA": "miami", "MIL": "milwaukee", "MIN": "minnesota",
    "NYM": "new york mets", "NYY": "new york yankees", "ATH": "athletics",
    "PHI": "philadelphia", "PIT": "pittsburgh", "SD": "san diego",
    "SF": "san francisco", "SEA": "seattle", "STL": "st. louis",
    "TB": "tampa bay", "TEX": "texas", "TOR": "toronto", "WSH": "washington",
}
MON = {m: i + 1 for i, m in enumerate(
    ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT",
     "NOV", "DEC"])}


def tkey(name):
    n = (name or "").lower()
    best, bl = None, 0
    for c, city in CODES.items():
        if city in n and len(city) > bl:
            best, bl = c, len(city)
    if best:
        return best
    return "ATH" if "athletic" in n else None


def parse_ticker(t):
    m = re.match(r"KXMLBRFI-(\d\d)([A-Z]{3})(\d\d)(\d{4})([A-Z]+)$", t)
    if not m:
        return None
    yy, mon, dd, hhmm, codes = m.groups()
    pair = None
    for i in range(2, len(codes) - 1):
        a, b = codes[:i], codes[i:]
        if a in CODES and b in CODES:
            pair = frozenset((a, b))
            break
    if pair is None:
        return None
    return (f"20{yy}-{MON[mon]:02d}-{int(dd):02d}", pair)


def main():
    # ---------- events: first-inning scoring plays
    games = []
    with open(os.path.join(DATA, "window_plays.jsonl"), encoding="utf-8") as fh:
        for line in fh:
            try:
                games.append(json.loads(line))
            except ValueError:
                pass
    ev = {}
    for g in games:
        hk, ak = tkey(g.get("home")), tkey(g.get("away"))
        if not hk or not ak:
            continue
        first = [p for p in g.get("scoring_plays", []) if p.get("inning") == 1]
        if not first:
            continue
        first.sort(key=lambda p: p["start"])
        p0 = first[0]                      # the FIRST run of the game
        d = (g["date"] or "")[:10]
        ev[(d, frozenset((hk, ak)))] = {
            "game_pk": g["pk"], "t_feed": p0["start"], "end": p0.get("end"),
            "desc": p0["desc"], "event": p0["event"], "half": p0["half"],
            "date": d,
        }
        # a run can also arrive on the previous UTC day for late games
        d2 = (datetime.fromisoformat(g["date"].replace("Z", "+00:00"))
              - timedelta(days=1)).date().isoformat()
        ev.setdefault((d2, frozenset((hk, ak))), ev[(d, frozenset((hk, ak)))])
    print(f"{len(games)} games, "
          f"{len({v['game_pk'] for v in ev.values()})} with a 1st-inning run")

    # ---------- tape: KXMLBRFI trades only
    trades = defaultdict(list)
    files = sorted(glob.glob(os.path.join(TAPE, "trades_*.jsonl")))
    print(f"scanning {len(files)} tape files for KXMLBRFI ...", flush=True)
    for f in files:
        n = 0
        with open(f, encoding="utf-8") as fh:
            for line in fh:
                if "KXMLBRFI" not in line:
                    continue
                try:
                    t = json.loads(line)
                except ValueError:
                    continue
                tk = t.get("ticker") or ""
                if not tk.startswith("KXMLBRFI"):
                    continue
                try:
                    ts = datetime.fromisoformat(
                        t["created_time"].replace("Z", "+00:00"))
                    px = float(t["yes_price_dollars"]) * 100
                    cnt = float(t.get("count_fp") or 0)
                except (KeyError, ValueError, TypeError):
                    continue
                trades[tk].append((ts, px, cnt, t.get("taker_outcome_side")))
                n += 1
        print(f"  {os.path.basename(f)[7:17]}: {n:>6,}", flush=True)
    print(f"  {sum(len(v) for v in trades.values()):,} RFI trades across "
          f"{len(trades)} markets")

    # ---------- join and measure
    rows = []
    nojoin = 0
    for tk, tr in trades.items():
        k = parse_ticker(tk)
        if k is None or k not in ev:
            nojoin += 1
            continue
        e = ev[k]
        tf = datetime.fromisoformat(e["t_feed"].replace("Z", "+00:00"))
        tr.sort()
        pre = [x for x in tr if x[0] < tf]
        post = [x for x in tr if x[0] >= tf]
        if len(pre) < 3 or not post:
            continue
        base = st.median([x[1] for x in pre[-10:]])
        if base > 85:                      # already resolved-ish; not an event
            continue
        # first trade at a clearly-moved price: >= base + 15c, or >= 80c.
        #
        # ⚠ The comment said 90c until 2026-09-01 while the code said
        # 80.0. THE CODE IS AUTHORITATIVE: it is what produced the published
        # result, and editing the number to match a comment would silently
        # change a number already reported. The comment was the error.
        #
        # The 80 is a FLOOR and only binds when `base` is under 65 (the guard
        # above already drops anything over 85). Whether the verdict is
        # sensitive to 80 vs 90 has NOT been re-tested.
        thr = max(base + 15.0, 80.0)
        first_moved = next((x for x in post if x[1] >= thr), None)
        # also: the last trade still at (near) the pre-event price
        last_stale = None
        for x in post:
            if x[1] <= base + 5.0:
                last_stale = x
            if first_moved and x[0] > first_moved[0]:
                break
        rows.append({
            "ticker": tk, "game_pk": e["game_pk"], "desc": e["desc"],
            "t_feed": e["t_feed"], "base_px": base,
            "lag_s": ((first_moved[0] - tf).total_seconds()
                      if first_moved else None),
            "moved_px": first_moved[1] if first_moved else None,
            "stale_lag_s": ((last_stale[0] - tf).total_seconds()
                            if last_stale else None),
            "stale_px": last_stale[1] if last_stale else None,
            "stale_size": last_stale[2] if last_stale else None,
            "n_pre": len(pre), "n_post": len(post),
        })

    json.dump(rows, open(os.path.join(REP, "inplay_rfi_latency.json"), "w"),
              indent=1, default=str)
    got = [r for r in rows if r["lag_s"] is not None]
    print(f"\njoined events: {len(rows)}   with a detectable move: {len(got)}"
          f"   tickers not joined: {nojoin}")
    if len(got) < 20:
        print("too few to conclude -- UNTESTABLE")
        return

    lags = sorted(r["lag_s"] for r in got)
    n = len(lags)
    print("\n" + "=" * 66)
    print("LAG: feed timestamp -> first trade at a clearly-moved price")
    print("=" * 66)
    print(f"  n={n}")
    print(f"  median {st.median(lags):+.1f}s   mean {st.mean(lags):+.1f}s")
    for q in (0.05, 0.10, 0.25, 0.75, 0.90, 0.95):
        print(f"  p{int(q*100):<3d}  {lags[min(int(n*q), n-1)]:+.1f}s")
    print(f"  min {lags[0]:+.1f}s   max {lags[-1]:+.1f}s")
    neg = sum(1 for x in lags if x < 0)
    print(f"\n  events where the MARKET MOVED BEFORE THE FEED: {neg} of {n} "
          f"({100*neg/n:.0f}%)")
    within = {s: sum(1 for x in lags if 0 <= x <= s) for s in (1, 2, 5, 10, 30, 60)}
    print(f"  market moved within N seconds of the feed: {within}")

    print("\n" + "=" * 66)
    print("WAS THE OLD PRICE STILL AVAILABLE AFTER THE FEED?")
    print("=" * 66)
    stale = [r for r in got if r["stale_lag_s"] is not None
             and r["stale_lag_s"] > 0]
    print(f"  events with a trade at (near) the pre-event price AFTER the "
          f"feed stamp: {len(stale)} of {n}")
    if stale:
        sl = sorted(r["stale_lag_s"] for r in stale)
        sz = sorted(r["stale_size"] or 0 for r in stale)
        print(f"    that window lasted: median {st.median(sl):.1f}s  "
              f"p90 {sl[int(len(sl)*.9)]:.1f}s  max {max(sl):.1f}s")
        print(f"    size traded in it: median {st.median(sz):.0f} contracts  "
              f"max {max(sz):.0f}")

    print("\n" + "=" * 66)
    print("VERDICT")
    print("=" * 66)
    med = st.median(lags)
    if med <= 0:
        print("  The market moves AT OR BEFORE the feed timestamp. Anyone")
        print("  trading off this feed is last in the queue. DEAD.")
    elif med < 2:
        print(f"  Median lag {med:+.1f}s. The market reacts essentially")
        print("  instantly. A retail order cannot be placed inside that.")
    else:
        print(f"  Median lag {med:+.1f}s -- a real window exists. Size it")
        print("  against the depth available before concluding anything.")


if __name__ == "__main__":
    main()

"""Day-one arm for TOTALS: does the sharp book disagree with Kalshi on run totals?

Mailbox 021. `KXMLBTOTAL` is **the largest family on the recorder — 2,280
tickers, 96,336 snapshots since 2026-08-04** — and no strategy has ever been
written against it.

**No settled game is used**, so nothing here can be a result-dependent choice.
Same discipline that killed the retail-book idea in an hour.

WHY THIS COMPARISON IS UNUSUALLY CLEAN
---------------------------------------
Kalshi publishes `floor_strike = 8.5` with `strike_type = "greater"` -- an
explicit number, no title parsing. Pinnacle prices the same half-integer lines,
both sides. So:

    Kalshi "Over 8.5 runs scored"  ==  Pinnacle "over 8.5"

is the **same event**, exactly. No interpolation, and no push, because a total of
8.5 cannot be tied. Whole-number lines (Pinnacle also quotes 8.0 and 9.0) ARE
DISCARDED and counted: those carry a push that Kalshi's market does not have.

⚠ AND THE FEE POINT THAT DID NOT MATTER ON WHO-WINS-THE-GAME
-------------------------------------------------------------
A totals ladder runs from "over 2.5" to "over 13.5" on the same game, so its
outer rungs sit at extreme prices where **the Kalshi fee is near its MINIMUM --
about 0.20c at 97c, not the 3.6-4.8c this repo habitually quotes.** The bar is
therefore computed per rung from the price that rung actually trades at, and the
distribution of bars is printed rather than a single number.
"""
from __future__ import annotations

import json
import math
import re
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(ROOT.parent))
import venues as V  # noqa: E402
from props_n3 import a2p, devig, norm  # noqa: E402
from common.kalshi_fees import fee_rate_cents  # noqa: E402
from costbar_local import bar_cents as _bar  # noqa: E402

# ⚠ ADDED 2026-08-21 AFTER THIS COST US THE ONE CAPTURE WE HAD WAITED THREE DAYS
# FOR. Launched by hand these scripts inherit PYTHONIOENCODING=utf-8; launched by
# the watchdog they inherit the Windows cp1252 console default, and the first
# print containing a warning glyph raises UnicodeEncodeError and kills the run.
# It died AFTER fetching 32 sharp props and 225 Kalshi rungs -- the data was in
# memory and was lost to a print statement. Fixed at the source rather than by
# setting an environment variable in one launcher, because the next launcher
# would not have it either.
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:  # noqa: BLE001 - a non-reconfigurable stream is not fatal
    pass

REP = ROOT / "reports"
PIN = "https://guest.api.arcadia.pinnacle.com/0.1/sports/3"

CLUB = {
    "ATH": "athletics", "ATL": "braves", "AZ": "diamondbacks", "BAL": "orioles",
    "BOS": "sox_red", "CHC": "cubs", "CIN": "reds", "CLE": "guardians",
    "COL": "rockies", "CWS": "sox_white", "DET": "tigers", "HOU": "astros",
    "KC": "royals", "LAA": "angels", "LAD": "dodgers", "MIA": "marlins",
    "MIL": "brewers", "MIN": "twins", "NYM": "mets", "NYY": "yankees",
    "PHI": "phillies", "PIT": "pirates", "SD": "padres", "SEA": "mariners",
    "SF": "giants", "STL": "cardinals", "TB": "rays", "TEX": "rangers",
    "TOR": "blue jays", "WSH": "nationals",
}


def nick(text: str):
    low = (text or "").lower()
    if "red sox" in low:
        return "sox_red"
    if "white sox" in low:
        return "sox_white"
    hits = {v for v in CLUB.values() if v not in ("sox_red", "sox_white") and v in low}
    return next(iter(hits)) if len(hits) == 1 else None


def split_pair(suffix: str):
    """'WSHTEX' -> ('WSH','TEX'). Ambiguity is an error, not a guess."""
    ok = [(suffix[:i], suffix[i:]) for i in range(2, len(suffix) - 1)
          if suffix[:i] in CLUB and suffix[i:] in CLUB]
    return ok[0] if len(ok) == 1 else None


def fetch_kalshi_totals():
    """{frozenset(two club keys): {strike: {ticker,bid,ask,size}}}"""
    out = defaultdict(dict)
    bad = defaultdict(int)
    for m in V.k_paginate("/markets", {"series_ticker": "KXMLBTOTAL",
                                       "status": "open", "limit": 200},
                          "markets", max_pages=15):
        strike = V.fnum(m.get("floor_strike"))
        if strike is None or m.get("strike_type") != "greater":
            bad["no_greater_than_strike"] += 1
            continue
        ev = m.get("event_ticker") or ""
        mm = re.match(r"^KXMLBTOTAL-\d{2}[A-Z]{3}\d{6}([A-Z]+)$", ev)
        if not mm:
            bad["event_ticker_unparseable"] += 1
            continue
        pair = split_pair(mm.group(1))
        if not pair:
            bad["club_pair_ambiguous"] += 1
            continue
        key = frozenset((CLUB[pair[0]], CLUB[pair[1]]))
        if len(key) != 2:
            bad["same_club_twice"] += 1
            continue
        ylv, nlv = V.k_orderbook(m["ticker"])
        yb, ya, bs, asz = V.k_touch(ylv, nlv)
        out[key][strike] = {"ticker": m["ticker"], "bid": yb, "ask": ya,
                            "ask_size": asz}
    return dict(out), dict(bad)


def fetch_pinnacle_totals():
    """{frozenset(two club keys): {line: (over_am, under_am)}}"""
    mus = V.get(f"{PIN}/matchups", pace=0.3, tries=2, timeout=30)
    mk = V.get(f"{PIN}/markets/straight", pace=0.3, tries=2, timeout=30)
    ts = datetime.now(timezone.utc)
    if mus is None or mus.status_code != 200 or len(mus.content) < 100_000:
        return None, ts          # GUARDS #27 -- no access, not an empty board
    meta = {}
    for m in mus.json():
        lg = m.get("league") or {}
        if (lg.get("name") if isinstance(lg, dict) else None) != "MLB":
            continue
        if m.get("parentId") or m.get("isLive"):
            continue
        ns = [nick(p.get("name")) for p in (m.get("participants") or [])]
        ns = [n for n in ns if n]
        if len(set(ns)) == 2:
            meta[m["id"]] = frozenset(ns)
    out = defaultdict(dict)
    for m in (mk.json() if mk is not None and mk.status_code == 200 else []):
        mid = m.get("matchupId")
        if mid not in meta or m.get("type") != "total" or m.get("period") != 0:
            continue
        sides = {}
        for p in (m.get("prices") or []):
            if p.get("price") is None or p.get("points") is None:
                continue
            d = (p.get("designation") or "").lower()
            if d in ("over", "under"):
                sides[d] = (float(p["points"]), float(p["price"]))
        if len(sides) == 2 and sides["over"][0] == sides["under"][0]:
            out[meta[mid]][sides["over"][0]] = (sides["over"][1], sides["under"][1])
    return dict(out), ts


def main() -> None:
    REP.mkdir(parents=True, exist_ok=True)
    print("=" * 78)
    print("TOTALS DAY-ONE ARM — sharp book vs Kalshi on RUN TOTALS")
    print("=" * 78)
    print("No settled game is used. Half-integer lines only, so Kalshi's")
    print("'Over 8.5 runs' and Pinnacle's 'over 8.5' are the SAME event.\n")

    pin, t_p = fetch_pinnacle_totals()
    if pin is None:
        print("   ⚠ NO ACCESS to the sharp feed. Apparatus, not a finding.")
        return
    kal, bad = fetch_kalshi_totals()
    t_k = datetime.now(timezone.utc)
    print(f"   Pinnacle games with two-sided totals : {len(pin)}")
    print(f"   Kalshi games with a totals ladder    : {len(kal)}")
    for k, v in sorted(bad.items(), key=lambda x: -x[1]):
        print(f"      kalshi dropped, {k:32} {v}")
    print(f"   ⚠ both feeds pulled within {abs((t_k-t_p).total_seconds()):.0f} seconds")

    both = sorted(set(pin) & set(kal), key=lambda k: sorted(k))
    print(f"\n   games joined: {len(both)}")
    if not both:
        print("   ⚠ NOTHING JOINS. Apparatus result, not a finding.")
        return

    rows, drops = [], defaultdict(int)
    for key in both:
        for line, (o_am, u_am) in sorted(pin[key].items()):
            if abs(line - math.floor(line) - 0.5) > 1e-9:
                drops["whole_number_line_has_a_push"] += 1
                continue
            if line not in kal[key]:
                drops["kalshi_has_no_rung_at_that_line"] += 1
                continue
            r = kal[key][line]
            if r["ask"] is None or r["bid"] is None:
                drops["rung_not_two_sided"] += 1
                continue
            fair = devig(a2p(o_am), a2p(u_am))
            if not fair:
                drops["devig_failed"] += 1
                continue
            over = {m: 100 * v[0] for m, v in fair.items()}
            ask, bid = r["ask"], r["bid"]
            # audit pass 4 item 3: fee + HALF-SPREAD, not fee alone.
            bar = _bar(ask, bid)
            no_ask = 100 - bid
            rows.append({
                "game": "/".join(sorted(key)), "line": line,
                "ticker": r["ticker"], "over_am": o_am, "under_am": u_am,
                "margin": 100 * (a2p(o_am) + a2p(u_am) - 1),
                "fair_over_c": over["power"], "ask_c": ask, "bid_c": bid,
                "edge_c": over["power"] - ask, "bar_c": bar,
                "qualifies": over["power"] - ask > bar,
                "edge_no_c": (100 - over["power"]) - no_ask,
                "bar_no_c": float(fee_rate_cents(no_ask)),
                "qualifies_no": (100 - over["power"]) - no_ask > float(fee_rate_cents(no_ask)),
                "by_method_c": {m: 100 * v[0] - ask for m, v in fair.items()},
                "ask_size": r["ask_size"]})

    for k, v in sorted(drops.items(), key=lambda x: -x[1]):
        print(f"      dropped, {k:36} {v}")
    print(f"   USABLE rungs: {len(rows)}")
    if not rows:
        print("   ⚠ Nothing usable. Apparatus result, not a finding.")
        return

    print("\n" + "-" * 78)
    print("PER RUNG — in cents")
    print("-" * 78)
    print(f"   {'game':24} {'line':>5} {'marg':>6} {'fair':>6} {'ask':>6} "
          f"{'edge':>7} {'bar':>5}  verdict")
    for r in sorted(rows, key=lambda x: -x["edge_c"])[:28]:
        v = "⚠ QUALIFIES" if r["qualifies"] else ("sell?" if r["qualifies_no"] else "no")
        print(f"   {r['game'][:24]:24} {r['line']:>5} {r['margin']:>6.2f} "
              f"{r['fair_over_c']:>6.2f} {r['ask_c']:>6.2f} {r['edge_c']:>+7.2f} "
              f"{r['bar_c']:>5.2f}  {v}")
    if len(rows) > 28:
        print(f"   … {len(rows)-28} more rungs, all in the json")

    e = np.array([r["edge_c"] for r in rows])
    bars = np.array([r["bar_c"] for r in rows])
    asks = np.array([r["ask_c"] for r in rows])
    marg = np.array([r["margin"] for r in rows])
    print("\n" + "=" * 78)
    print("THE ANSWER")
    print("=" * 78)
    print(f"   rungs compared                    : {len(e)}")
    print(f"   ⚠ GAMES, which is the real count  : {len({r['game'] for r in rows})}")
    print(f"      one game's whole ladder settles on ONE score. Rungs are NOT")
    print(f"      independent observations and are never counted as such.")
    print(f"   Pinnacle's margin, median         : {np.median(marg):.2f} out of 100")
    print(f"   |sharp fair − Kalshi ask| median  : {np.median(np.abs(e)):.2f}c")
    print(f"                             p90     : {np.percentile(np.abs(e),90):.2f}c")
    print(f"                             MAX     : {np.abs(e).max():.2f}c")
    print(f"   ⚠ cost bar AT THE PRICES THESE ACTUALLY TRADE AT:")
    print(f"        ask  median {np.median(asks):.1f}c  range {asks.min():.0f}-{asks.max():.0f}c")
    print(f"        fee  median {np.median(bars):.2f}c  range {bars.min():.2f}-{bars.max():.2f}c")
    nq = sum(r["qualifies"] for r in rows)
    nqn = sum(r["qualifies_no"] for r in rows)
    print(f"   BUY side clearing the bar         : {nq} of {len(rows)}")
    print(f"   SELL side clearing the bar        : {nqn} of {len(rows)}")
    if nq and nqn:
        print("   ⚠ N2 COHERENCE: both sides qualifying on one population is")
        print("     arithmetically impossible. Suspect the join or the cost model.")
    print("\n   Method disagreement — sign disagreement stops this (§6):")
    for m in ("proportional", "power", "shin"):
        v = np.array([r["by_method_c"][m] for r in rows])
        print(f"      {m:14} mean {v.mean():+6.2f}c  median {np.median(v):+6.2f}c  "
              f"share positive {100*np.mean(v>0):5.1f}%")

    (REP / "totals_n3.json").write_text(json.dumps(
        {"pulled_utc": t_p.strftime("%Y-%m-%dT%H:%M:%SZ"),
         "n_games_joined": len(both), "drops": dict(drops),
         "n_rungs": len(rows), "rows": rows}, indent=1), encoding="utf-8")
    print("\n   wrote reports/totals_n3.json")


if __name__ == "__main__":
    main()

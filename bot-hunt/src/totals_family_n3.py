"""The other two totals families nobody has joined: FIRST FIVE INNINGS and TEAM TOTALS.

`RESULTS_TOTALS_N3.md` §4 listed both as untested. This tests them, on the same
day, with the same machinery, so the list shrinks rather than sits there.

**No settled game is used.** Same structure as `totals_n3.py`: Kalshi publishes
`floor_strike` with `strike_type="greater"`, Pinnacle prices the same
half-integer line both sides, so the two are the SAME event and no interpolation
happens. Whole-number lines are discarded and counted -- they carry a push that
Kalshi's market does not have.

    KXMLBF5TOTAL    "First 5 innings: Over 6.5 runs"  <->  Pinnacle total,  period 1
    KXMLBTEAMTOTAL  "Will Washington score over 7.5?" <->  Pinnacle team_total, side

⚠ THE COUNT THAT MATTERS IS GAMES, NOT RUNGS. One game's whole ladder settles on
one final score. For team totals the unit is the TEAM-GAME, which is still not
independent of its opponent's -- the two share a game state -- so the game count
is printed beside it and is the conservative one.
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
from props_n3 import a2p, devig  # noqa: E402
from totals_n3 import CLUB, PIN, nick, split_pair  # noqa: E402
from common.kalshi_fees import fee_rate_cents  # noqa: E402

REP = ROOT / "reports"


def pinnacle_lines(kind: str):
    """kind='f5' -> total period 1 ; kind='team' -> team_total period 0."""
    mus = V.get(f"{PIN}/matchups", pace=0.3, tries=2, timeout=30)
    mk = V.get(f"{PIN}/markets/straight", pace=0.3, tries=2, timeout=30)
    ts = datetime.now(timezone.utc)
    if mus is None or mus.status_code != 200 or len(mus.content) < 100_000:
        return None, ts                      # GUARDS #27: no access, not empty
    meta = {}
    for m in mus.json():
        lg = m.get("league") or {}
        if (lg.get("name") if isinstance(lg, dict) else None) != "MLB":
            continue
        if m.get("parentId") or m.get("isLive"):
            continue
        sides = {}
        for p in (m.get("participants") or []):
            n = nick(p.get("name"))
            if n and p.get("alignment") in ("home", "away"):
                sides[p["alignment"]] = n
        if len(set(sides.values())) == 2:
            meta[m["id"]] = sides
    want_type, want_period = ("total", 1) if kind == "f5" else ("team_total", 0)
    out = defaultdict(dict)
    for m in (mk.json() if mk is not None and mk.status_code == 200 else []):
        mid = m.get("matchupId")
        if mid not in meta or m.get("type") != want_type or m.get("period") != want_period:
            continue
        px = {}
        for p in (m.get("prices") or []):
            d = (p.get("designation") or "").lower()
            if d in ("over", "under") and p.get("price") is not None \
                    and p.get("points") is not None:
                px[d] = (float(p["points"]), float(p["price"]))
        if len(px) != 2 or px["over"][0] != px["under"][0]:
            continue
        if kind == "f5":
            key = (frozenset(meta[mid].values()),)
        else:
            side = m.get("side")
            if side not in ("home", "away"):
                continue
            key = (frozenset(meta[mid].values()), meta[mid][side])
        out[key][px["over"][0]] = (px["over"][1], px["under"][1])
    return dict(out), ts


def kalshi_ladders(series: str, kind: str):
    out, bad = defaultdict(dict), defaultdict(int)
    for m in V.k_paginate("/markets", {"series_ticker": series, "status": "open",
                                       "limit": 200}, "markets", max_pages=15):
        strike = V.fnum(m.get("floor_strike"))
        if strike is None or m.get("strike_type") != "greater":
            bad["no_greater_than_strike"] += 1
            continue
        ev = m.get("event_ticker") or ""
        mm = re.match(rf"^{series}-\d{{2}}[A-Z]{{3}}\d{{6}}([A-Z]+)$", ev)
        if not mm:
            bad["event_ticker_unparseable"] += 1
            continue
        pair = split_pair(mm.group(1))
        if not pair:
            bad["club_pair_ambiguous"] += 1
            continue
        game = frozenset((CLUB[pair[0]], CLUB[pair[1]]))
        if len(game) != 2:
            bad["same_club_twice"] += 1
            continue
        if kind == "f5":
            key = (game,)
        else:
            # ticker tail is TEAMABBR + rung index, e.g. '...-WSH8'
            tail = (m.get("ticker") or "").rsplit("-", 1)[-1]
            ab = re.sub(r"\d+$", "", tail)
            if ab not in CLUB:
                bad["team_abbrev_unknown"] += 1
                continue
            key = (game, CLUB[ab])
        ylv, nlv = V.k_orderbook(m["ticker"])
        yb, ya, bs, asz = V.k_touch(ylv, nlv)
        out[key][strike] = {"ticker": m["ticker"], "bid": yb, "ask": ya,
                            "ask_size": asz}
    return dict(out), dict(bad)


def run(label: str, series: str, kind: str):
    print("\n" + "=" * 78)
    print(f"{label}  —  {series}")
    print("=" * 78)
    pin, t_p = pinnacle_lines(kind)
    if pin is None:
        print("   ⚠ NO ACCESS to the sharp feed. Apparatus, not a finding.")
        return None
    kal, bad = kalshi_ladders(series, kind)
    spread = abs((datetime.now(timezone.utc) - t_p).total_seconds())
    print(f"   Pinnacle units quoted : {len(pin)}")
    print(f"   Kalshi units quoted   : {len(kal)}")
    for k, v in sorted(bad.items(), key=lambda x: -x[1]):
        print(f"      kalshi dropped, {k:32} {v}")
    both = sorted(set(pin) & set(kal), key=lambda k: sorted(map(str, k[0])) + list(k[1:]))
    print(f"   joined                : {len(both)}   (feeds {spread:.0f}s apart)")
    if not both:
        print("   ⚠ NOTHING JOINS. Apparatus result, not a finding.")
        return None

    rows, drops = [], defaultdict(int)
    covered, uncovered = [], []
    for key in both:
        plines = set(pin[key])
        for strike, r in kal[key].items():
            if r["ask"] is not None:
                (covered if strike in plines else uncovered).append(r["ask"])
        for line, (o, u) in sorted(pin[key].items()):
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
            fair = devig(a2p(o), a2p(u))
            if not fair:
                drops["devig_failed"] += 1
                continue
            over = {m: 100 * v[0] for m, v in fair.items()}
            ask, bid = r["ask"], r["bid"]
            no_ask = 100 - bid
            rows.append({"unit": "/".join(sorted(key[0])) + (f" [{key[1]}]" if len(key) > 1 else ""),
                         "game": "/".join(sorted(key[0])), "line": line,
                         "ticker": r["ticker"],
                         "margin": 100 * (a2p(o) + a2p(u) - 1),
                         "fair_over_c": over["power"], "ask_c": ask, "bid_c": bid,
                         "edge_c": over["power"] - ask,
                         "bar_c": float(fee_rate_cents(ask)),
                         "qualifies": over["power"] - ask > float(fee_rate_cents(ask)),
                         "edge_no_c": (100 - over["power"]) - no_ask,
                         "qualifies_no": (100 - over["power"]) - no_ask > float(fee_rate_cents(no_ask)),
                         "by_method_c": {m: 100 * v[0] - ask for m, v in fair.items()}})
    for k, v in sorted(drops.items(), key=lambda x: -x[1]):
        print(f"      dropped, {k:36} {v}")
    if not rows:
        print("   ⚠ Nothing usable. Apparatus result, not a finding.")
        return None

    e = np.array([r["edge_c"] for r in rows])
    bars = np.array([r["bar_c"] for r in rows])
    asks = np.array([r["ask_c"] for r in rows])
    marg = np.array([r["margin"] for r in rows])
    games = {r["game"] for r in rows}
    print(f"\n   rungs compared                 : {len(e)}")
    print(f"   ⚠ GAMES, the conservative count: {len(games)}")
    if len(rows[0]["unit"]) != len(rows[0]["game"]):
        print(f"      team-games                  : {len({r['unit'] for r in rows})}"
              f"   (still not independent — the two share a game state)")
    print(f"   Pinnacle margin, median        : {np.median(marg):.2f} out of 100")
    print(f"   |sharp fair − ask| median      : {np.median(np.abs(e)):.2f}c")
    print(f"                      p90 / MAX   : {np.percentile(np.abs(e),90):.2f}c / {np.abs(e).max():.2f}c")
    print(f"   ask median {np.median(asks):.1f}c  fee median {np.median(bars):.2f}c "
          f"(range {bars.min():.2f}-{bars.max():.2f}c)")
    nq, nqn = sum(r["qualifies"] for r in rows), sum(r["qualifies_no"] for r in rows)
    print(f"   clearing the bar   BUY {nq} of {len(rows)}   SELL {nqn} of {len(rows)}")
    if nq and nqn:
        print("   ⚠ N2: both sides qualifying is arithmetically impossible — "
              "suspect the join or the cost model.")
    for m in ("proportional", "power", "shin"):
        v = np.array([r["by_method_c"][m] for r in rows])
        print(f"      {m:14} mean {v.mean():+6.2f}c  share positive {100*np.mean(v>0):5.1f}%")
    if covered or uncovered:
        c, u = np.array(covered or [0]), np.array(uncovered or [0])
        fc = np.array([float(fee_rate_cents(x)) for x in c])
        fu = np.array([float(fee_rate_cents(x)) for x in u])
        print(f"\n   ⚠ COVERAGE — which rungs a sharp book actually quotes:")
        print(f"      referenced   {len(covered):>4}  ask {c.min():.0f}-{c.max():.0f}c  "
              f"fee median {np.median(fc):.2f}c")
        print(f"      NOT          {len(uncovered):>4}  ask {u.min():.0f}-{u.max():.0f}c  "
              f"fee median {np.median(fu):.2f}c  min {fu.min():.2f}c")
    return {"label": label, "series": series, "n_rungs": len(rows),
            "n_games": len(games), "n_covered": len(covered),
            "n_uncovered": len(uncovered), "max_abs_edge_c": float(np.abs(e).max()),
            "median_abs_edge_c": float(np.median(np.abs(e))),
            "median_bar_c": float(np.median(bars)),
            "qualify_buy": int(nq), "qualify_sell": int(nqn), "rows": rows}


def main() -> None:
    REP.mkdir(parents=True, exist_ok=True)
    out = []
    for label, series, kind in (
            ("FIRST FIVE INNINGS totals", "KXMLBF5TOTAL", "f5"),
            ("TEAM totals", "KXMLBTEAMTOTAL", "team")):
        r = run(label, series, kind)
        if r:
            out.append(r)
    if out:
        (REP / "totals_family_n3.json").write_text(json.dumps(out, indent=1),
                                                   encoding="utf-8")
        print("\n   wrote reports/totals_family_n3.json")


if __name__ == "__main__":
    main()

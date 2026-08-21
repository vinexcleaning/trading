"""P1's day-one arm: does the SHARP book disagree with Kalshi on PLAYER PROPS?

`PREREGISTRATION_PROPS.md`, and the same shape that killed the retail-book idea
in an hour: **no settled game is used**, so nothing here can be a
result-dependent choice. It asks only whether the two venues disagree at all,
and whether the disagreement beats what it costs to act on.

⚠ ONE THING IS MUCH BETTER THAN THE PRE-REGISTRATION ASSUMED, AND IT REMOVES
THE SINGLE BIGGEST RISK IN IT.
-----------------------------------------------------------------------------
§3b worried that Kalshi quotes a LADDER ("6+ strikeouts?") while Pinnacle quotes
a LINE ("over 5.5"), so comparing them would need interpolation -- and
interpolation is the one step capable of manufacturing an edge out of nothing.

**When Pinnacle's line is a half-integer, no interpolation is needed at all.**
Strikeouts are a count, so:

    Pinnacle "over 5.5"  ==  P(X > 5.5)  ==  P(X >= 6)  ==  Kalshi "6+"

They are the *same event*, exactly, not an approximation of one. So this script
uses **only half-integer lines** and does no interpolation whatsoever. Whole-number
lines are DISCARDED and counted, because those carry a push (X == the line) that
Kalshi's market does not have, and pretending otherwise would be the error.

That means N4 -- the ladder-interpolation placebo -- **is not needed for the
half-integer set**, and §3b's "if the two interpolation methods disagree" drop
condition cannot fire because neither is used. The ladder is still checked for
monotonicity, because a ladder that contradicts itself marks a bad read.
"""
from __future__ import annotations

import json
import math
import re
import sys
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(ROOT.parent))
import venues as V  # noqa: E402
from common.kalshi_fees import fee_rate_cents  # noqa: E402

REP = ROOT / "reports"
PIN = "https://guest.api.arcadia.pinnacle.com/0.1/sports/3"
# Kalshi family  ->  the Pinnacle prop kind it corresponds to
FAMILIES = {"KXMLBKS": "Strikeouts", "KXMLBHR": "Home Runs"}


def norm(name: str) -> str:
    """Player-name key. Punctuation and suffixes differ between venues."""
    s = (name or "").lower()
    s = re.sub(r"\b(jr|sr|ii|iii|iv)\b", " ", s)
    return " ".join(re.sub(r"[^a-z ]+", " ", s).split())


def a2p(american) -> float:
    a = float(american)
    return (-a) / ((-a) + 100.0) if a < 0 else 100.0 / (a + 100.0)


def devig(p1: float, p2: float):
    """Three margin-removal methods. Returns {method: (side1, side2)}."""
    s = p1 + p2
    if s <= 0 or p1 <= 0 or p2 <= 0:
        return {}
    out = {"proportional": (p1 / s, p2 / s)}
    lo, hi = 0.2, 5.0
    for _ in range(80):
        k = (lo + hi) / 2
        if p1 ** k + p2 ** k > 1:
            lo = k
        else:
            hi = k
    k = (lo + hi) / 2
    t = p1 ** k + p2 ** k
    out["power"] = (p1 ** k / t, p2 ** k / t)

    def shin(z):
        f = lambda p: (math.sqrt(z * z + 4 * (1 - z) * p * p / s) - z) / (2 * (1 - z))
        return f(p1), f(p2)
    lo, hi = 1e-9, 0.4999
    for _ in range(80):
        z = (lo + hi) / 2
        if sum(shin(z)) > 1:
            lo = z
        else:
            hi = z
    out["shin"] = shin((lo + hi) / 2)
    return out


# ------------------------------------------------------------- Pinnacle ----

def fetch_pinnacle_props():
    """{(player_key, kind): {"line": L, "over": p_raw, "under": p_raw, ...}}"""
    mus = V.get(f"{PIN}/matchups", pace=0.3, tries=2, timeout=30)
    mk = V.get(f"{PIN}/markets/straight", pace=0.3, tries=2, timeout=30)
    ts = datetime.now(timezone.utc)
    # GUARDS #27: the control. A thin payload means no access, not no props.
    if mus is None or mus.status_code != 200 or len(mus.content) < 100_000:
        return None, ts, "NO ACCESS"
    meta = {}
    for m in mus.json():
        sp = m.get("special") or {}
        if (sp.get("category") or "") != "Player Props":
            continue
        mm = re.match(r"(.+?) Total (Strikeouts|Home Runs)", sp.get("description") or "")
        if not mm:
            continue
        units = {p.get("id"): (p.get("name") or "").lower()
                 for p in (m.get("participants") or [])}
        meta[m["id"]] = (norm(mm.group(1)), mm.group(2), units, mm.group(1).strip())
    if not meta:
        return {}, ts, "EMPTY BOARD"

    out = {}
    for m in (mk.json() if mk is not None and mk.status_code == 200 else []):
        mid = m.get("matchupId")
        if mid not in meta:
            continue
        key, kind, units, disp = meta[mid]
        sides = {}
        for p in (m.get("prices") or []):
            if p.get("price") is None or p.get("points") is None:
                continue
            # designation is the reliable field; participantId is the fallback
            lab = (p.get("designation") or units.get(p.get("participantId")) or "").lower()
            if lab in ("over", "under"):
                sides[lab] = (float(p["points"]), float(p["price"]))
        if len(sides) == 2 and sides["over"][0] == sides["under"][0]:
            out[(key, kind)] = {"line": sides["over"][0],
                                "over_am": sides["over"][1],
                                "under_am": sides["under"][1],
                                "display": disp}
    return out, ts, "PROPS"


# --------------------------------------------------------------- Kalshi ----

def fetch_kalshi_ladders():
    """{(player_key, kind): {threshold: {ticker, bid, ask}}}"""
    lad = defaultdict(dict)
    for series, kind in FAMILIES.items():
        for m in V.k_paginate("/markets", {"series_ticker": series,
                                           "status": "open", "limit": 200},
                              "markets", max_pages=10):
            t = m.get("title") or ""
            mm = re.match(r"([A-Za-z\.\'\- ]+):\s*(\d+)\+", t)
            if not mm:
                continue
            ylv, nlv = V.k_orderbook(m["ticker"])
            yb, ya, bs, asz = V.k_touch(ylv, nlv)
            lad[(norm(mm.group(1)), kind)][int(mm.group(2))] = {
                "ticker": m["ticker"], "bid": yb, "ask": ya, "ask_size": asz,
                "title": t}
    return dict(lad)


def main() -> None:
    REP.mkdir(parents=True, exist_ok=True)
    wait_min = 0
    if "--wait" in sys.argv:
        wait_min = int(sys.argv[sys.argv.index("--wait") + 1])
    print("=" * 78)
    print("P1 DAY-ONE ARM — sharp book vs Kalshi on PLAYER PROPS")
    print("=" * 78)
    print("No settled game is used. Half-integer lines only, so NO interpolation")
    print("is performed: Pinnacle 'over 5.5' and Kalshi '6+' are the same event.\n")

    # ⚠ ARMED MODE, and it is idempotent so the watchdog can restart it forever.
    # The prop board is INTERMITTENT in a way one day's data did not show (see
    # RESULTS_PROPS_WINDOW.md): live 15 hours on 2026-08-18, absent through
    # comparable windows on the 20th and 21st. So this now waits for days rather
    # than hours, fires the comparison the FIRST time the board opens, and then
    # refuses to run again -- otherwise a restart would overwrite the one capture
    # we waited days for.
    done = REP / "props_n3.json"
    if "--once-only" in sys.argv and done.exists():
        print(f"   already captured -> {done.name}. Exiting without re-running.")
        return
    deadline = time.time() + wait_min * 60
    while True:
        pin, t_p, state = fetch_pinnacle_props()
        print(f"   Pinnacle player props: {state}"
              f"  ({datetime.now(timezone.utc):%H:%M:%SZ})"
              f"  {len(pin) if pin else 0} priced", flush=True)
        if (pin and state == "PROPS") or time.time() >= deadline:
            break
        time.sleep(900)
    if not pin:
        print("\n   No props inside the wait window. ⚠ APPARATUS RESULT, NOT A")
        print("   FINDING — it says nothing about whether the venues disagree.")
        return

    kal = fetch_kalshi_ladders()
    t_k = datetime.now(timezone.utc)
    spread = abs((t_k - t_p).total_seconds())
    print(f"   Kalshi ladders: {len(kal)} player-families, "
          f"{sum(len(v) for v in kal.values())} rungs")
    print(f"   ⚠ both feeds pulled within {spread:.0f} seconds")

    both = sorted(set(pin) & set(kal))
    print(f"\n   joined on player name: {len(both)}")
    drops = defaultdict(int)
    rows = []
    for key in both:
        p, ladder = pin[key], kal[key]
        line = p["line"]
        # ⚠ HALF-INTEGER ONLY. A whole-number line carries a push that Kalshi's
        # market does not have, so the two are NOT the same event.
        if abs(line - math.floor(line) - 0.5) > 1e-9:
            drops["whole_number_line_has_a_push"] += 1
            continue
        thr = int(math.ceil(line))
        if thr not in ladder:
            drops["kalshi_has_no_rung_at_that_line"] += 1
            continue
        # a ladder that contradicts itself marks a bad read, not an opportunity
        ks = sorted(ladder)
        asks = [ladder[k]["ask"] for k in ks]
        if any(a is None for a in asks):
            drops["ladder_has_an_unquoted_rung"] += 1
            continue
        if any(asks[i] < asks[i + 1] - 1e-9 for i in range(len(asks) - 1)):
            drops["ladder_not_monotone"] += 1
            continue
        rung = ladder[thr]
        ask, bid = rung["ask"], rung["bid"]
        if ask is None or bid is None:
            drops["rung_not_two_sided"] += 1
            continue
        fair = devig(a2p(p["over_am"]), a2p(p["under_am"]))
        if not fair:
            drops["devig_failed"] += 1
            continue
        over = {m: 100 * v[0] for m, v in fair.items()}
        # buying YES on "thr+" is backing the OVER
        bar = float(fee_rate_cents(ask))
        edge = over["power"] - ask
        # and the sell side: buying NO backs the UNDER, paying 100 - bid
        no_ask = 100 - bid
        edge_no = (100 - over["power"]) - no_ask
        bar_no = float(fee_rate_cents(no_ask))
        rows.append({"player": p["display"], "kind": key[1], "line": line,
                     "threshold": thr, "ticker": rung["ticker"],
                     "pin_over_am": p["over_am"], "pin_under_am": p["under_am"],
                     "margin": 100 * (a2p(p["over_am"]) + a2p(p["under_am"]) - 1),
                     "fair_over_c": over["power"], "kalshi_ask_c": ask,
                     "kalshi_bid_c": bid, "edge_c": edge, "bar_c": bar,
                     "qualifies": edge > bar,
                     "edge_no_c": edge_no, "bar_no_c": bar_no,
                     "qualifies_no": edge_no > bar_no,
                     "by_method_c": {m: 100 * v[0] - ask for m, v in fair.items()},
                     "ask_size": rung["ask_size"]})

    for k, v in sorted(drops.items(), key=lambda x: -x[1]):
        print(f"      dropped, {k:36} {v}")
    print(f"   USABLE (half-integer line, live two-sided rung): {len(rows)}")
    if not rows:
        print("\n   Nothing usable. ⚠ APPARATUS RESULT, NOT A FINDING.")
        return

    print("\n" + "-" * 78)
    print("PER PROP — in cents. 'edge' is sharp-fair minus what Kalshi charges")
    print("-" * 78)
    print(f"   {'player':20} {'kind':10} {'line':>5} {'K':>4} {'marg':>6} "
          f"{'fair':>6} {'ask':>6} {'edge':>7} {'bar':>5}  verdict")
    for r in sorted(rows, key=lambda x: -x["edge_c"]):
        v = "⚠ QUALIFIES" if r["qualifies"] else ("sell?" if r["qualifies_no"] else "no")
        print(f"   {r['player'][:20]:20} {r['kind']:10} {r['line']:>5} "
              f"{r['threshold']:>4} {r['margin']:>6.2f} {r['fair_over_c']:>6.2f} "
              f"{r['kalshi_ask_c']:>6.2f} {r['edge_c']:>+7.2f} {r['bar_c']:>5.2f}  {v}")

    e = np.array([r["edge_c"] for r in rows])
    bars = np.array([r["bar_c"] for r in rows])
    marg = np.array([r["margin"] for r in rows])
    asks = np.array([r["kalshi_ask_c"] for r in rows])
    print("\n" + "=" * 78)
    print("THE ANSWER")
    print("=" * 78)
    print(f"   props compared                       : {len(e)}")
    print(f"   distinct players                     : {len({r['player'] for r in rows})}")
    print(f"   Pinnacle's margin on props, median   : {np.median(marg):.2f} out of 100")
    print(f"   |sharp fair − Kalshi ask|  median    : {np.median(np.abs(e)):.2f}c")
    print(f"                              p90       : {np.percentile(np.abs(e),90):.2f}c")
    print(f"                              MAX       : {np.abs(e).max():.2f}c")
    print(f"   ⚠ the cost bar AT THE PRICES THESE ACTUALLY TRADE AT:")
    print(f"        Kalshi ask   median {np.median(asks):.1f}c   range "
          f"{asks.min():.0f}-{asks.max():.0f}c")
    print(f"        fee          median {np.median(bars):.2f}c   range "
          f"{bars.min():.2f}-{bars.max():.2f}c   (NOT the habitual 3.6-4.8c)")
    nq = sum(r["qualifies"] for r in rows)
    nqn = sum(r["qualifies_no"] for r in rows)
    print(f"   BUY side clearing the bar            : {nq} of {len(rows)}")
    print(f"   SELL side clearing the bar           : {nqn} of {len(rows)}")
    if nq and nqn:
        print("   ⚠ BOTH SIDES QUALIFY SOMEWHERE — N2 coherence check: that is")
        print("     arithmetically impossible on one population and means the")
        print("     join or the cost model is wrong, not that there are two edges.")
    print("\n   Method disagreement — sign disagreement stops P1 (§6):")
    for m in ("proportional", "power", "shin"):
        v = np.array([r["by_method_c"][m] for r in rows])
        print(f"      {m:14} mean {v.mean():+6.2f}c  median {np.median(v):+6.2f}c  "
              f"share positive {100*np.mean(v>0):5.1f}%")

    out = {"pulled_utc": t_p.strftime("%Y-%m-%dT%H:%M:%SZ"),
           "feed_spread_seconds": spread, "n_joined": len(both),
           "drops": dict(drops), "n_usable": len(rows), "rows": rows}
    (REP / "props_n3.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    print("\n   wrote reports/props_n3.json")


if __name__ == "__main__":
    main()

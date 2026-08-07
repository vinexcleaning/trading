"""Which MLB market should the paper test target: moneyline, totals, or RFI?

SCOREBOARD.md flags 249 KXMLBTOTAL tickers and 71 KXMLBRFI tickers as recorded
and never examined, and asks whether they beat moneyline. This measures the
answer rather than asserting it.

Five axes, and the fifth decides:

  1. EFFECTIVE sample rate -- GAMES, not tickers. KXMLBTOTAL is a ladder of
     ~11 strikes per game, so 249 tickers is about 23 games, not 249.
  2. cost to enter (spread/2 + Kalshi taker fee), from market_census.py
  3. size at the touch
  4. does a free sharp reference exist, and how much vig does it carry
  5. how often the de-vigged reference disagrees with the executable Kalshi
     price by MORE than cost -- the feasibility statistic bot-hunt measured as
     q = 0 of 17 on moneyline, run here on totals for the first time.

No settlement outcome is joined anywhere in this file, so nothing in it can be
a claim about profit. It is a feasibility measurement.

### The join, and the error it exists to prevent

Baseball teams play each other on three consecutive days. Joining Kalshi to
Pinnacle on the club pair ALONE matches Tuesday's Kalshi price to Thursday's
Pinnacle price. The first version of this file did exactly that and reported
an 80% qualifying rate with a 57-cent best edge -- against bot-hunt's measured
q = 0 of 17 on the same market. The join now requires the START TIMES to agree
within a tolerance, and a MISMATCHED-PAIR PLACEBO deliberately joins each
Kalshi game to a different Pinnacle game and reports its qualifying rate. If
the placebo rate is not far below the real rate, the real rate is join error.
"""
from __future__ import annotations

import argparse
import json
import random
import re
import statistics
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(Path(r"C:\Users\vinig\trading")))

import pinnacle as PIN                          # noqa: E402
from common.kalshi_fees import fee_order_cents   # noqa: E402
from kalshi import markets as k_markets, cents, ticker_parts, CODE  # noqa: E402

OUT = HERE.parent / "reports"
SLIPPAGE_C = 1.0          # same convention as bot-hunt/PREREGISTRATION_DEVIG.md
START_TOL_MIN = 20        # Kalshi ticker minute vs Pinnacle startTime


def join_games(kalshi_events, pin_games, tol_min=START_TOL_MIN):
    """(kalshi event key) -> pinnacle game, on club pair AND start time."""
    out, rejected = {}, []
    for key, ke in kalshi_events.items():
        a_name = CODE.get(ke["away"])
        h_name = CODE.get(ke["home"])
        if not a_name or not h_name:
            rejected.append((key, "unknown club code"))
            continue
        cands = []
        for g in pin_games.values():
            names_ok = (a_name in (g["away"] or "") and h_name in (g["home"] or ""))
            if not names_ok:
                continue
            if not g["starts"] or not ke["starts"]:
                continue
            dt = abs((g["starts"] - ke["starts"]).total_seconds()) / 60.0
            cands.append((dt, g))
        if not cands:
            rejected.append((key, "no club-pair candidate"))
            continue
        cands.sort(key=lambda x: x[0])
        dt, g = cands[0]
        if dt > tol_min:
            rejected.append((key, f"club pair matched but start off by "
                                  f"{dt:.0f} min -- WRONG DAY OF THE SERIES"))
            continue
        out[key] = {"pin": g, "start_delta_min": round(dt, 1)}
    return out, rejected


def _edges(kalshi_ask, kalshi_bid, fair_yes_c):
    """Net edge in cents for buying YES at the ask and NO at (100-bid)."""
    fee_y = float(fee_order_cents(kalshi_ask, 1))
    e_yes = fair_yes_c - kalshi_ask - fee_y - SLIPPAGE_C
    no_ask = 100 - kalshi_bid
    fee_n = float(fee_order_cents(no_ask, 1))
    e_no = (100 - fair_yes_c) - no_ask - fee_n - SLIPPAGE_C
    return e_yes, e_no


def eval_moneyline(k_mkt, pin_game, pin_mkts, method, k_parts):
    """Fair probability for the team named in the Kalshi ticker suffix.

    Matched on Pinnacle's `designation` ("home"/"away"), NOT on participantId.
    The first version matched by participant name through
    `participant_names[participantId]`, and on games reached via a special's
    `parent` object those ids are all None -- the dict collapses to a single
    `{None: <one team>}` entry, the name lookup returns that team for BOTH
    prices, and the side is effectively chosen at random. Symptom: Toronto
    quoted 33.5c on Kalshi came back with a 66.65c "fair value" and a 29.65c
    "edge". Read the right way the two prices agree to 0.2c.
    """
    ml = PIN.markets_for(pin_game, pin_mkts).get("moneyline")
    if not ml:
        return None
    side = (k_mkt["ticker"].rsplit("-", 1)[-1] or "").upper()
    if side == k_parts["away"]:
        want = "away"
    elif side == k_parts["home"]:
        want = "home"
    else:
        return None
    tgt = next((p for p in ml["prices"]
                if str(p.get("designation", "")).lower() == want), None)
    oth = next((p for p in ml["prices"]
                if str(p.get("designation", "")).lower()
                == ("home" if want == "away" else "away")), None)
    if tgt is None or oth is None:
        return None
    pa = PIN.american_to_prob(tgt["price"])
    pb = PIN.american_to_prob(oth["price"])
    fa, _, vig = PIN.devig(pa, pb, method)
    return {"fair_yes_c": fa * 100.0, "vig_pp": vig * 100.0,
            "limit": ml["limit"], "line": None}


def eval_total(k_mkt, pin_game, pin_mkts, method):
    strike = k_mkt.get("floor_strike")
    if strike is None:
        return None
    for t in PIN.markets_for(pin_game, pin_mkts).get("totals", []):
        ou = PIN.over_under(t)
        if not ou:
            continue
        over_px, under_px, pts = ou
        if pts is None or abs(float(pts) - float(strike)) > 1e-6:
            continue
        pa = PIN.american_to_prob(over_px)     # Kalshi YES = "Over X.5 runs"
        pb = PIN.american_to_prob(under_px)
        fa, _, vig = PIN.devig(pa, pb, method)
        return {"fair_yes_c": fa * 100.0, "vig_pp": vig * 100.0,
                "limit": t["limit"], "line": pts,
                "is_alternate": t["is_alternate"]}
    return None


def run(series, kind, pin_games, pin_mkts, method, placebo=False, seed=7):
    mkts = k_markets(series)
    # index Kalshi markets by event, carrying the parsed start time
    events, rows = {}, []
    for m in mkts:
        p = ticker_parts(m["ticker"])
        if not p:
            continue
        events.setdefault(p["event_key"], dict(p, markets=[]))
        events[p["event_key"]]["markets"].append(m)

    joined, rejected = join_games(events, pin_games)

    if placebo:
        # deliberately wrong: rotate the pinnacle assignment by one
        keys = sorted(joined)
        vals = [joined[k]["pin"] for k in keys]
        rnd = random.Random(seed)
        rot = vals[1:] + vals[:1] if len(vals) > 1 else vals
        rnd.shuffle(rot)
        joined = {k: {"pin": rot[i], "start_delta_min": None}
                  for i, k in enumerate(keys)}

    now = datetime.now(timezone.utc)
    for key, j in joined.items():
        ev = events[key]
        if ev["starts"] and ev["starts"] <= now:
            continue                    # pre-match only; never price in-play
        for m in ev["markets"]:
            bid, ask = cents(m.get("yes_bid_dollars")), cents(m.get("yes_ask_dollars"))
            if not bid or not ask or ask >= 100 or bid <= 0:
                continue
            if kind == "moneyline":
                r = eval_moneyline(m, j["pin"], pin_mkts, method, ev)
            else:
                r = eval_total(m, j["pin"], pin_mkts, method)
            if not r:
                continue
            e_yes, e_no = _edges(ask, bid, r["fair_yes_c"])
            rows.append({
                "event": key, "ticker": m["ticker"], "kind": kind,
                "line": r["line"], "start_delta_min": j["start_delta_min"],
                "kalshi_bid": bid, "kalshi_ask": ask,
                "kalshi_mid": (bid + ask) / 2,
                "pin_fair_yes_c": round(r["fair_yes_c"], 2),
                "pin_vig_pp": round(r["vig_pp"], 3),
                "pin_limit_usd": r["limit"],
                "edge_yes_c": round(e_yes, 2), "edge_no_c": round(e_no, 2),
                "best_edge_c": round(max(e_yes, e_no), 2),
                "qualifies": bool(max(e_yes, e_no) > 0),
            })
    return rows, rejected, len(events), len(joined)


def summarise(rows, label):
    if not rows:
        print(f"\n=== {label} ===\n  NO JOINED ROWS")
        return {"label": label, "joined_markets": 0}
    vig = [r["pin_vig_pp"] for r in rows]
    best = [r["best_edge_c"] for r in rows]
    q = sum(1 for r in rows if r["qualifies"])
    games = len({r["event"] for r in rows})
    qg = len({r["event"] for r in rows if r["qualifies"]})
    s = {
        "label": label,
        "joined_markets": len(rows), "distinct_games": games,
        "vig_pp_median": round(statistics.median(vig), 3),
        "pin_limit_usd_median": statistics.median(
            [r["pin_limit_usd"] for r in rows]),
        "best_edge_c_median": round(statistics.median(best), 2),
        "best_edge_c_max": round(max(best), 2),
        "qualifying_markets": q,
        "qualifying_rate_markets": round(q / len(rows), 4),
        "qualifying_games": qg,
        "qualifying_rate_games": round(qg / max(1, games), 4),
    }
    print(f"\n=== {label} ===")
    for k, v in s.items():
        if k != "label":
            print(f"  {k:<26} {v}")
    for r in sorted(rows, key=lambda x: -x["best_edge_c"])[:4]:
        print(f"    {r['ticker']:<42} line={r['line']} mid={r['kalshi_mid']} "
              f"fair={r['pin_fair_yes_c']} edge={r['best_edge_c']}c "
              f"vig={r['pin_vig_pp']}pp dt={r['start_delta_min']}m")
    return s


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--method", default="multiplicative",
                    choices=["multiplicative", "additive", "power"])
    a = ap.parse_args()

    OUT.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
    print(f"measured_at_utc = {stamp}   devig = {a.method}   "
          f"slippage = {SLIPPAGE_C}c")

    pg = PIN.games()
    pm = PIN.straight_markets()
    print(f"pinnacle MLB games indexed = {len(pg)}, "
          f"with full-game markets = {sum(1 for g in pg.values() if PIN.markets_for(g, pm))}")

    out = {"measured_at_utc": stamp, "devig_method": a.method,
           "slippage_assumed_c": SLIPPAGE_C, "summary": [], "rows": {}}

    for series, kind in [("KXMLBGAME", "moneyline"), ("KXMLBTOTAL", "totals")]:
        rows, rej, nev, njo = run(series, kind, pg, pm, a.method)
        prows, _, _, _ = run(series, kind, pg, pm, a.method, placebo=True)
        print(f"\n{series}: kalshi events {nev}, joined {njo}, "
              f"rejected {len(rej)}")
        wrongday = [r for r in rej if "WRONG DAY" in r[1]]
        print(f"  rejected for wrong day of the series: {len(wrongday)}"
              + (f"   e.g. {wrongday[0][0]} -- {wrongday[0][1]}" if wrongday else ""))
        s = summarise(rows, f"{series} vs de-vigged Pinnacle ({kind})")
        ps = summarise(prows, f"{series} PLACEBO (mismatched pairs)")
        out["summary"] += [s, ps]
        out["rows"][series] = rows
        out["rows"][series + "_placebo"] = prows

    (OUT / f"target_choice_{a.method}.json").write_text(json.dumps(out, indent=2))
    print(f"\nwrote {OUT / f'target_choice_{a.method}.json'}")
    print("\nNo settlement outcome is joined anywhere in this file. "
          "These are feasibility statistics, not P&L.")

"""What does Kalshi actually charge to bet against the team that is behind?

The other half of the question. `build_comeback_table.py` says how often the
trailing team comes back; this says what you are paid for taking the other side,
and the two together are the whole bet.

THE ONE DESIGN DECISION THAT MATTERS. To read a price at "the 80th minute" you
need the real instant the 80th minute happened, and the displayed clock is 17.5
minutes away from that at the median (SO009, 362 events). Interpolating a
wallclock for an arbitrary minute would inherit exactly that error.

So no interpolation happens. **Prices are read at the wallclock of a goal**,
which ESPN publishes exactly. Every measurement here is of the form: *the score
became 2-1 at the 78th minute; two minutes later, Kalshi was charging this much
to bet against the side now behind.* The state, the displayed minute and the
instant are all known rather than derived, and +2 minutes is used because 91% of
a goal's price move is already in within one minute (SO007).

WHAT THIS IS NOT. It attaches no outcome and computes no profit. It is a
description of what the market charges. Pairing a price with a comeback rate is
the actual test and it gets pre-registered before it is run, on years this
session has not looked at.

WINDOW. Kalshi keeps about 69 days of candles, so this can only ever cover very
recent matches. That is a permanent limit, not a gap to fill.

Read-only. Unauthenticated. GET only. No orders.
"""
import json
import os
import sys
import time
from collections import Counter, defaultdict
from datetime import datetime, timezone

HERE = os.path.dirname(__file__)
ROOT = os.path.join(HERE, "..")
DATA, REP = os.path.join(ROOT, "data"), os.path.join(ROOT, "reports")
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, "..", "market-selection", "src"))
import kalshi_api as K      # noqa: E402
import teammatch as TM      # noqa: E402

GOALS = os.path.join(DATA, "goal_minutes.jsonl")
OUT = os.path.join(DATA, "price_at_state.json")

# Every per-match soccer series found on Kalshi 2026-08-08. See
# soccer/kalshi_soccer_series.md for how this list was established.
SERIES = {
    "KXEPLGAME": "eng.1", "KXUCLGAME": "uefa.champions",
    "KXUELGAME": "uefa.europa", "KXLALIGAGAME": "esp.1",
    "KXSERIEAGAME": "ita.1", "KXBUNDESLIGAGAME": "ger.1",
    "KXLIGUE1GAME": "fra.1", "KXWCGAME": "fifa.world",
    "KXCLUBWCGAME": "fifa.cwc", "KXMLSGAME": "usa.1",
    "KXLIGAMXGAME": "mex.1", "KXDIMAYORGAME": "col.1",
    "KXURYPDGAME": "uru.1", "KXPERLIGA1GAME": "per.1",
    "KXECULPGAME": "ecu.1", "KXCHLLDPGAME": "chi.1",
    "KXUSLGAME": "usa.usl.1", "KXNWSLGAME": "usa.nwsl",
    "KXCOPADOBRASILGAME": "bra.copa_do_brazil",
    "KXINTLFRIENDLYGAME": "fifa.friendly",
}

PACE = 1.0          # Kalshi rate-limited hard at 2,200 events unpaced on 08-08
OFFSET_MIN = 2      # read the price this long after the goal
CANDLE_SPAN = 86400 * 2   # the endpoint 400s on a 7-day request


def iso_to_ts(s):
    if not s:
        return None
    return int(datetime.fromisoformat(s.replace("Z", "+00:00")).timestamp())


def kalshi_events():
    """Every settled per-match soccer event still inside Kalshi's window."""
    out = []
    for series, league in SERIES.items():
        cursor = None
        for _ in range(10):
            p = {"series_ticker": series, "limit": 200, "status": "settled"}
            if cursor:
                p["cursor"] = cursor
            r = K.get("/events", p)
            time.sleep(PACE)
            if r is None or r.status_code != 200:
                break
            d = r.json()
            for e in d.get("events", []):
                out.append({"event_ticker": e.get("event_ticker"),
                            "title": e.get("title"), "series": series,
                            "league": league})
            cursor = d.get("cursor")
            if not cursor:
                break
        print(f"  {series:22s} {sum(1 for e in out if e['series']==series):4d}",
              flush=True)
    return out


def legs(event_ticker):
    """The three sides of a 3-way market -> {yes_sub_title: ticker}."""
    r = K.get("/markets", {"event_ticker": event_ticker, "limit": 20,
                           "status": "settled"})
    time.sleep(PACE)
    if r is None or r.status_code != 200:
        return {}
    return {m.get("yes_sub_title"): m.get("ticker")
            for m in r.json().get("markets", []) if m.get("ticker")}


def candles(series, ticker, t0, t1):
    """1-minute candles -> {minute_ts: (yes_bid_cents, yes_ask_cents)}.

    Kalshi rejects spans of about a week, so the request is chunked. Prices come
    back as dollar strings on `*_dollars` fields; the integer-cent fields are
    null on every market (GUARDS #12, and M006 measured it on 200 of 200).
    """
    out = {}
    a = t0
    while a < t1:
        b = min(a + CANDLE_SPAN, t1)
        r = K.get(f"/series/{series}/markets/{ticker}/candlesticks",
                  {"start_ts": a, "end_ts": b, "period_interval": 1})
        time.sleep(0.35)
        if r is not None and r.status_code == 200:
            for c in r.json().get("candlesticks", []):
                ts = c.get("end_period_ts")
                try:
                    bid = float((c.get("yes_bid") or {}).get("close_dollars"))
                    ask = float((c.get("yes_ask") or {}).get("close_dollars"))
                except (TypeError, ValueError):
                    continue
                out[ts] = (bid * 100, ask * 100)
        a = b
    return out


def nearest(cs, ts, tol=180):
    """The candle closest to ts, within tol seconds. None rather than a guess."""
    best, bestd = None, tol + 1
    for k in cs:
        d = abs(k - ts)
        if d < bestd:
            best, bestd = k, d
    return cs.get(best) if best is not None else None


def main():
    if not os.path.exists(GOALS):
        sys.exit("no goal timelines yet -- run fetch_goal_minutes.py first")

    # ESPN fixtures with a timeline, indexed by (date, canonical team pair).
    fixtures = {}
    with open(GOALS, encoding="utf-8") as fh:
        for line in fh:
            try:
                r = json.loads(line)
            except ValueError:
                continue
            if not r.get("kickoff_wallclock"):
                continue
            key = (r["date"][:10], TM.pair_key(r["home"], r["away"]))
            fixtures[key] = r
    print(f"{len(fixtures)} ESPN fixtures with a timeline and a kickoff instant")

    print("Kalshi settled soccer events:")
    evs = kalshi_events()
    print(f"  {len(evs)} total")

    rows, stats = [], Counter()
    for i, ev in enumerate(evs):
        tick = ev["event_ticker"] or ""
        parts = tick.split("-")
        if len(parts) < 2 or len(parts[1]) < 7:
            stats["unparseable ticker"] += 1
            continue
        try:
            d = datetime.strptime(parts[1][:7], "%y%b%d").replace(
                year=2000 + int(parts[1][:2]))
        except ValueError:
            stats["unparseable date"] += 1
            continue
        date = d.strftime("%Y-%m-%d")

        try:
            a, b = TM.teams_from_kalshi_title(ev["title"] or "")
        except (ValueError, TypeError):
            stats["unparseable title"] += 1
            continue
        if not a or not b:
            stats["unparseable title"] += 1
            continue

        key = (date, TM.pair_key(a, b))
        fx = fixtures.get(key)
        if fx is None:
            # Kalshi dates the event by local kickoff; ESPN stamps UTC, so a
            # late kickoff lands on the next UTC day. Try one day either side
            # rather than losing every evening match.
            for delta in (1, -1):
                alt = (d.toordinal() + delta)
                altdate = datetime.fromordinal(alt).strftime("%Y-%m-%d")
                fx = fixtures.get((altdate, key[1]))
                if fx:
                    stats["joined on a +/-1 day shift"] += 1
                    break
        if fx is None:
            stats["no ESPN fixture"] += 1
            continue

        L = legs(tick)
        if len(L) < 3:
            stats["fewer than 3 legs"] += 1
            continue

        goals = sorted((g for g in fx["events"]
                        if g["kind"] == "goal" and g["minute"] is not None
                        and g.get("wallclock") and g.get("side")),
                       key=lambda g: g["minute"])
        if not goals:
            stats["no goals"] += 1
            continue

        # Which Kalshi leg is the home side and which the away side. The two
        # ESPN names are a closed set of exactly two, so each Kalshi leg is
        # resolved against them -- `resolve_against_roster` returns None on a
        # tie rather than guessing, which is the behaviour wanted here: getting
        # this backwards would silently price the wrong team on every goal.
        subs = [s for s in L if s and s.lower() not in ("tie", "draw")]
        roster = [fx["home"], fx["away"]]
        assign = {}
        for s in subs:
            got, _, _ = TM.resolve_against_roster(s, roster)
            if got:
                assign[s] = got
        home_leg = away_leg = None
        for s, espn in assign.items():
            if espn == fx["home"]:
                home_leg = L[s]
            elif espn == fx["away"]:
                away_leg = L[s]
        if not home_leg or not away_leg or home_leg == away_leg:
            stats["could not tell the two legs apart"] += 1
            continue

        t0 = iso_to_ts(fx["kickoff_wallclock"])
        t1 = t0 + 3 * 3600
        ch = candles(ev["series"], home_leg, t0, t1)
        ca = candles(ev["series"], away_leg, t0, t1)
        if not ch or not ca:
            stats["no candles"] += 1
            continue

        h = a_ = 0
        for g in goals:
            if g["side"] == "home":
                h += 1
            else:
                a_ += 1
            if h == a_:
                continue
            ts = iso_to_ts(g["wallclock"])
            if ts is None:
                continue
            look = ts + OFFSET_MIN * 60
            trailing_is_home = h < a_
            cs = ch if trailing_is_home else ca
            q = nearest(cs, look)
            if q is None:
                stats["no candle at that instant"] += 1
                continue
            yes_bid, yes_ask = q
            # Buying NO on the trailing side means crossing to the NO ask,
            # which is 100 minus the YES bid. Using the mid here would flatter
            # the price by half the spread, and this whole bet lives inside a
            # few cents.
            no_cost = 100.0 - yes_bid
            rows.append({
                "event": tick, "league": ev["league"], "date": date,
                "minute": g["minute"],
                "lead": max(h, a_), "trail": min(h, a_),
                "no_cost_cents": round(no_cost, 2),
                "spread_cents": round(yes_ask - yes_bid, 2),
            })
            stats["priced states"] += 1

        if (i + 1) % 25 == 0:
            print(f"  {i+1}/{len(evs)} events | {len(rows)} priced states | "
                  f"{dict(stats)}", flush=True)

    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(rows, fh, indent=1)
    report(rows, stats)


def report(rows, stats):
    out = ["WHAT KALSHI CHARGES TO BET AGAINST THE TEAM THAT IS BEHIND", "=" * 78, ""]
    out.append("Read at the exact instant a goal was scored, plus two minutes.")
    out.append("No clock interpolation. Price is what you PAY to cross the")
    out.append("spread, not the middle of it.")
    out.append("")
    out.append(f"{len(rows)} priced moments")
    out.append("")
    for k in sorted(stats):
        out.append(f"    {k:38s} {stats[k]:6d}")
    out.append("")
    if rows:
        out.append(f"{'minute':>8s} {'score':>8s} {'moments':>9s} "
                   f"{'you pay (middle)':>18s} {'spread':>8s}")
        out.append("-" * 56)
        by = defaultdict(list)
        for r in rows:
            band = (r["minute"] // 10) * 10
            by[(band, r["lead"], r["trail"])].append(r)
        for key in sorted(by):
            band, lead, trail = key
            g = by[key]
            if len(g) < 5:
                continue
            costs = sorted(x["no_cost_cents"] for x in g)
            spr = sorted(x["spread_cents"] for x in g)
            out.append(f"{f'{band}-{band+9}':>8s} {f'{lead}-{trail}':>8s} "
                       f"{len(g):>9d} {costs[len(costs)//2]:>18.1f} "
                       f"{spr[len(spr)//2]:>8.1f}")
    txt = "\n".join(out)
    print("\n" + txt)
    os.makedirs(REP, exist_ok=True)
    with open(os.path.join(REP, "price_at_state.txt"), "w",
              encoding="utf-8") as fh:
        fh.write(txt + "\n")


if __name__ == "__main__":
    main()

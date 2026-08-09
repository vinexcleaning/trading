"""Kalshi's price at EVERY displayed minute, whether or not anything happened.

WHAT THIS FIXES. `price_at_state.py` could only read a price at the instant of a
goal, so every price this folder had was two minutes after somebody scored, and
only from the 70th minute on. The ordinary settled scoreline -- one-nil since the
20th, now the 60th, nothing since -- was unmeasured at every minute. That is
SO026-SO028's recorded limitation and it is what this removes.

HOW. `clock_map.py` places any displayed minute at a real instant by
interpolating between ESPN's timestamped events inside the same half. Its
leave-one-out error is a median of 0.13 minutes and 98.8% inside one minute, so
a one-minute candle read at that instant is reading the right minute.

WHAT IS STORED. Both sides' bid and ask at every minute, not just the trailing
side's. Storing the raw quotes means the over-reaction question -- does the
price move as far for a weak team's goal as a strong one's -- can be answered
off the same file without going back to the API for another hour.

**LIQUIDITY IS A FIRST-CLASS RESULT HERE, NOT A FOOTNOTE.** A yes_bid of zero
means nobody is bidding for that side at all, so there is no NO to buy at any
price below 100. Those minutes are recorded, not dropped -- "there was no market"
is the single most common answer this file produces and dropping it would turn a
dead idea into a live one.

WINDOW. Kalshi keeps about 69 days of candles. This can only ever cover recent
matches, and in this particular window that means very little Premier League and
almost no Champions League. That is a permanent limit of the venue, not a gap to
fill by trying harder.

Read-only. Unauthenticated. GET only. No orders.
"""
import json
import os
import sys
import time
from collections import Counter
from datetime import datetime

HERE = os.path.dirname(__file__)
ROOT = os.path.join(HERE, "..")
DATA, REP = os.path.join(ROOT, "data"), os.path.join(ROOT, "reports")
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, "..", "market-selection", "src"))
import kalshi_api as K       # noqa: E402
import teammatch as TM       # noqa: E402
import clock_map as CM       # noqa: E402

GOALS = os.path.join(DATA, "goal_minutes.jsonl")
ANCHORS = os.path.join(DATA, "clock_anchors.jsonl")
STRENGTH = os.path.join(DATA, "strength.json")
OUT = os.path.join(DATA, "price_by_minute.jsonl")
DONE = os.path.join(DATA, "price_by_minute_done.json")

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

PACE = 0.9
CANDLE_PACE = 0.35
CANDLE_TOL = 90          # a candle further than this from the instant is not it
MINUTES = range(1, 91)


def iso_to_ts(s):
    if not s:
        return None
    return int(datetime.fromisoformat(s.replace("Z", "+00:00")).timestamp())


def kalshi_events():
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
    return out


def legs(event_ticker):
    r = K.get("/markets", {"event_ticker": event_ticker, "limit": 20,
                           "status": "settled"})
    time.sleep(CANDLE_PACE)
    if r is None or r.status_code != 200:
        return {}
    return {m.get("yes_sub_title"): m.get("ticker")
            for m in r.json().get("markets", []) if m.get("ticker")}


def candles(series, ticker, t0, t1):
    """1-minute candles -> {ts: (yes_bid_cents, yes_ask_cents)}.

    The integer-cent fields are null on every market (GUARDS #12, measured on
    200 of 200 in M006); the dollar strings are the real ones.
    """
    out = {}
    r = K.get(f"/series/{series}/markets/{ticker}/candlesticks",
              {"start_ts": t0, "end_ts": t1, "period_interval": 1})
    time.sleep(CANDLE_PACE)
    if r is None or r.status_code != 200:
        return out
    for c in r.json().get("candlesticks", []):
        ts = c.get("end_period_ts")
        try:
            bid = float((c.get("yes_bid") or {}).get("close_dollars"))
            ask = float((c.get("yes_ask") or {}).get("close_dollars"))
        except (TypeError, ValueError):
            continue
        out[ts] = (round(bid * 100, 2), round(ask * 100, 2))
    return out


def nearest(cs, ts, tol=CANDLE_TOL):
    best, bestd = None, tol + 1
    for k in cs:
        d = abs(k - ts)
        if d < bestd:
            best, bestd = k, d
    return cs.get(best) if best is not None else None


def main():
    fixtures, anchors = {}, {}
    with open(GOALS, encoding="utf-8") as fh:
        for line in fh:
            try:
                r = json.loads(line)
            except ValueError:
                continue
            if not r.get("kickoff_wallclock"):
                continue
            fixtures[(r["date"][:10], TM.pair_key(r["home"], r["away"]))] = r
    with open(ANCHORS, encoding="utf-8") as fh:
        for line in fh:
            try:
                a = json.loads(line)
            except ValueError:
                continue
            anchors[a["espn_id"]] = a["anchors"]
    strength = {}
    if os.path.exists(STRENGTH):
        strength = json.load(open(STRENGTH, encoding="utf-8"))
    print(f"{len(fixtures)} fixtures, {len(anchors)} with clock anchors")

    done = set()
    if os.path.exists(DONE):
        try:
            done = set(json.load(open(DONE, encoding="utf-8")))
        except ValueError:
            done = set()

    print("listing Kalshi settled soccer events...", flush=True)
    evs = kalshi_events()
    print(f"  {len(evs)} events", flush=True)

    fh = open(OUT, "a", encoding="utf-8", buffering=1)
    stats = Counter()
    t0 = time.time()

    for i, ev in enumerate(evs):
        tick = ev["event_ticker"] or ""
        if tick in done:
            stats["already done"] += 1
            continue
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
            a = b = None
        if not a or not b:
            stats["unparseable title"] += 1
            continue

        key = (date, TM.pair_key(a, b))
        fx = fixtures.get(key)
        if fx is None:
            for delta in (1, -1):
                alt = datetime.fromordinal(d.toordinal() + delta)
                fx = fixtures.get((alt.strftime("%Y-%m-%d"), key[1]))
                if fx:
                    stats["joined on a +/-1 day shift"] += 1
                    break
        if fx is None:
            stats["no ESPN fixture"] += 1
            continue

        anc = anchors.get(fx["espn_id"])
        if not anc:
            stats["no clock anchors"] += 1
            continue
        cmap = CM.build(anc)
        if not cmap.get(1) and not cmap.get(2):
            stats["clock map empty"] += 1
            continue

        L = legs(tick)
        if len(L) < 3:
            stats["fewer than 3 legs"] += 1
            continue
        subs = [s for s in L if s and s.lower() not in ("tie", "draw")]
        roster = [fx["home"], fx["away"]]
        home_leg = away_leg = None
        for s in subs:
            got, _, _ = TM.resolve_against_roster(s, roster)
            if got == fx["home"]:
                home_leg = L[s]
            elif got == fx["away"]:
                away_leg = L[s]
        if not home_leg or not away_leg or home_leg == away_leg:
            stats["could not tell the two legs apart"] += 1
            continue

        kt = iso_to_ts(fx["kickoff_wallclock"])
        if kt is None:
            stats["no kickoff instant"] += 1
            continue
        ch = candles(ev["series"], home_leg, kt - 1800, kt + 4 * 3600)
        ca = candles(ev["series"], away_leg, kt - 1800, kt + 4 * 3600)
        if not ch or not ca:
            stats["no candles"] += 1
            done.add(tick)
            continue

        goals = sorted((g for g in fx["events"]
                        if g["kind"] == "goal" and g["minute"] is not None
                        and g.get("side")),
                       key=lambda g: (g["minute"], g.get("stoppage") or 0))
        st = strength.get(fx["espn_id"], {})

        rows_this = 0
        gi = h = a_ = 0
        for minute in MINUTES:
            while gi < len(goals) and goals[gi]["minute"] <= minute:
                if goals[gi]["side"] == "home":
                    h += 1
                else:
                    a_ += 1
                gi += 1
            # Minute 45 is read as the end of the first half; 46 and up as the
            # second. See clock_map.instant() -- the number alone is ambiguous.
            period = 1 if minute <= 45 else 2
            inst = CM.instant(cmap, minute, 0, period=period)
            if inst is None:
                stats["minute could not be placed on the clock"] += 1
                continue
            qh = nearest(ch, inst)
            qa = nearest(ca, inst)
            if qh is None or qa is None:
                stats["no candle at that minute"] += 1
                continue
            fh.write(json.dumps({
                "event": tick, "league": ev["league"], "date": date,
                "espn_id": fx["espn_id"], "minute": minute,
                "h": h, "a": a_,
                "home_bid": qh[0], "home_ask": qh[1],
                "away_bid": qa[0], "away_ask": qa[1],
                "home_tier": st.get("home_tier", "unknown"),
                "away_tier": st.get("away_tier", "unknown"),
            }) + "\n")
            rows_this += 1
            stats["minutes priced"] += 1
        if rows_this:
            stats["matches priced"] += 1
        done.add(tick)

        if (i + 1) % 20 == 0:
            json.dump(sorted(done), open(DONE, "w", encoding="utf-8"))
            el = time.time() - t0
            print(f"  {i+1}/{len(evs)} | {stats['matches priced']} matches | "
                  f"{stats['minutes priced']} minutes | {el/60:.1f} min | "
                  f"eta {(len(evs)-i-1)*el/max(i+1,1)/60:.0f} min", flush=True)

    fh.close()
    json.dump(sorted(done), open(DONE, "w", encoding="utf-8"))
    print(f"\nDONE in {(time.time()-t0)/60:.1f} min")
    for k in sorted(stats):
        print(f"    {k:44s} {stats[k]:7d}")


if __name__ == "__main__":
    main()

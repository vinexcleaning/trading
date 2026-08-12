"""Does the near-certainty gap exist outside soccer?

THE QUESTION THE USER ASKED. Soccer's answer was that Kalshi stops quoting the
losing side exactly when the match becomes near-certain, so the trade "buy the
thing that is 97% to happen" is absent rather than mispriced. **Is that a fact
about market makers, or a fact about soccer?**

Those two possibilities make opposite predictions, which is what makes this
worth measuring instead of arguing:

  * **If it is market-maker behaviour**, it should appear in every sport with
    in-play quoting — baseball, tennis, basketball, hockey, football.
  * **If it is something about soccer's three-way market** (the draw leg gives a
    market maker somewhere else to put its risk), it will not.

HOW IT IS MEASURED, AND WHY THIS NEEDS NO SPORT KNOWLEDGE. The soccer version
needed goal timelines to know who was ahead. This does not: **the price itself
says whether the outcome is near-certain.** For every one-minute candle in a
settled market:

  * "near-certain" = somebody is bidding **95 cents or more** for this side.
  * "could you buy it" = there is an ask **below 100** you could actually hit.

So the measurement is: *when the market itself says an outcome is nearly sure,
how often can you buy it?* That is exactly the soccer question with the
sport-specific machinery removed.

**A CONTROL, BECAUSE OTHERWISE THIS MEASURES NOTHING.** A sport whose book is
thin everywhere would show few quotes at 95+ and it would mean nothing about
near-certainty. So the same fraction is computed for **middling prices (40-70)**
in the same markets. The comparison between the two bands is the result; the
level on its own is not.

WHAT THIS CANNOT DO. It has no event state, so it cannot tell a 95-cent price
late in a blowout from a 95-cent price on a heavy pre-match favourite. It
measures **quote availability against price**, which is the thing the soccer
finding was about, and nothing else. Per-sport follow-up belongs to the chats
that own those folders.

Read-only. Unauthenticated. GET only. No orders.
"""
import json
import os
import sys
import time
from collections import Counter, defaultdict

HERE = os.path.dirname(__file__)
ROOT = os.path.join(HERE, "..")
DATA, REP = os.path.join(ROOT, "data"), os.path.join(ROOT, "reports")
sys.path.insert(0, os.path.join(ROOT, "..", "market-selection", "src"))
import kalshi_api as K       # noqa: E402

OUT = os.path.join(DATA, "other_sports_probe.json")

SPORTS = {
    "baseball": "KXMLBGAME",
    "tennis (men)": "KXATPMATCH",
    "tennis (women)": "KXWTAMATCH",
    "basketball": "KXNBAGAME",
    "basketball (women)": "KXWNBAGAME",
    "hockey": "KXNHLGAME",
    "american football": "KXNFLGAME",
    "soccer (reference)": "KXUCLGAME",
}
EVENTS_PER_SPORT = 22
PACE = 0.5
NEAR_CERTAIN = 95        # somebody bidding this much says the outcome is sure
MID_LO, MID_HI = 40, 70  # the control band


def candles(series, ticker, t0, t1):
    r = K.get(f"/series/{series}/markets/{ticker}/candlesticks",
              {"start_ts": t0, "end_ts": t1, "period_interval": 1})
    time.sleep(PACE)
    if r is None or r.status_code != 200:
        return []
    out = []
    for c in r.json().get("candlesticks", []):
        try:
            bid = float((c.get("yes_bid") or {}).get("close_dollars")) * 100
            ask = float((c.get("yes_ask") or {}).get("close_dollars")) * 100
        except (TypeError, ValueError):
            continue
        out.append((round(bid, 2), round(ask, 2)))
    return out


def main():
    results = {}
    for sport, series in SPORTS.items():
        r = K.get("/events", {"series_ticker": series, "limit": 60,
                              "status": "settled"})
        time.sleep(PACE)
        if r is None or r.status_code != 200:
            print(f"{sport:22s} could not list events")
            continue
        evs = r.json().get("events", [])[:EVENTS_PER_SPORT]

        near_total = near_ok = mid_total = mid_ok = 0
        n_markets = 0
        for e in evs:
            tick = e.get("event_ticker")
            mr = K.get("/markets", {"event_ticker": tick, "limit": 20,
                                    "status": "settled"})
            time.sleep(PACE)
            if mr is None or mr.status_code != 200:
                continue
            for m in mr.json().get("markets", []):
                ct = m.get("close_time")
                if not ct:
                    continue
                try:
                    from datetime import datetime
                    end = int(datetime.fromisoformat(
                        ct.replace("Z", "+00:00")).timestamp())
                except ValueError:
                    continue
                cs = candles(series, m["ticker"], end - 5 * 3600, end)
                if not cs:
                    continue
                n_markets += 1
                for bid, ask in cs:
                    if bid >= NEAR_CERTAIN:
                        near_total += 1
                        if 0 < ask < 100:
                            near_ok += 1
                    elif MID_LO <= bid <= MID_HI:
                        mid_total += 1
                        if 0 < ask < 100:
                            mid_ok += 1
        results[sport] = {
            "series": series, "markets": n_markets,
            "near_total": near_total, "near_ok": near_ok,
            "mid_total": mid_total, "mid_ok": mid_ok,
        }
        print(f"{sport:22s} markets {n_markets:4d} | near-certain minutes "
              f"{near_total:6d} buyable {near_ok:6d} | middling {mid_total:6d} "
              f"buyable {mid_ok:6d}", flush=True)

    os.makedirs(DATA, exist_ok=True)
    json.dump(results, open(OUT, "w", encoding="utf-8"), indent=1)

    out = []
    out.append("DOES THE NEAR-CERTAINTY GAP EXIST IN OTHER SPORTS?")
    out.append("=" * 78)
    out.append("")
    out.append("Soccer found that Kalshi stops quoting an outcome once it")
    out.append("becomes near-certain, so the bet 'buy the thing that is 97% to")
    out.append("happen' is absent rather than badly priced.")
    out.append("")
    out.append("This asks the same question of every sport Kalshi runs per-game,")
    out.append("using only the price -- no scores, no clocks, no sport knowledge.")
    out.append("")
    out.append(f"  near-certain = somebody bidding {NEAR_CERTAIN} cents or more")
    out.append(f"  middling     = somebody bidding {MID_LO} to {MID_HI} cents")
    out.append("  buyable      = there is an offer below 100 you could hit")
    out.append("")
    out.append("**The comparison between the two columns is the result.** A")
    out.append("thin book would show few offers everywhere and would mean")
    out.append("nothing about near-certainty.")
    out.append("")
    out.append(f"{'sport':22s} {'markets':>8s} {'buyable when NEARLY SURE':>26s} "
               f"{'buyable when IN DOUBT':>23s}")
    out.append("-" * 82)
    for sport, v in results.items():
        nt, nk = v["near_total"], v["near_ok"]
        mt, mk = v["mid_total"], v["mid_ok"]
        a = f"{nk/nt*100:.0f} in 100  ({nt} min)" if nt >= 50 else f"too few ({nt})"
        b = f"{mk/mt*100:.0f} in 100  ({mt} min)" if mt >= 50 else f"too few ({mt})"
        out.append(f"{sport:22s} {v['markets']:>8d} {a:>26s} {b:>23s}")
    out.append("")
    txt = "\n".join(out)
    print()
    print(txt)
    os.makedirs(REP, exist_ok=True)
    with open(os.path.join(REP, "other_sports_probe.txt"), "w",
              encoding="utf-8") as fh:
        fh.write(txt + "\n")
    print("\nwrote reports/other_sports_probe.txt")


if __name__ == "__main__":
    main()

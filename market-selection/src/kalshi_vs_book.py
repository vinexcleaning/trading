"""Does Kalshi already track the free bookmaker line? (MLB, live snapshot)

This is a MARKET PROPERTY measurement for selection, not a strategy test. The
question it answers is whether the shortlist's central mechanism is even
available: if Kalshi's price is already indistinguishable from the sharp line,
then "we would know something the counterparty does not" has to come from
somewhere other than a better pre-match estimate, and the family should be
ranked accordingly.

It is a deliberately small live version of LEDGER T012, which found Kalshi
indistinguishable from Betfair on tennis (r=0.9878, MAD 1.95c against a 2.44c
round-trip cost) and T013, which found that where the two disagreed Kalshi was
closer 49.1% of the time -- a coin flip measured precisely.

Reference line: DraftKings moneyline from ESPN's core API, free and unkeyed.
Vig is removed by normalising the two sides' implied probabilities to sum to 1.

CAVEATS, up front, because this is a snapshot:
  - one point in time, no closing line, so this is NOT T012. It cannot measure
    who is sharper, only whether they currently agree.
  - DraftKings is a retail-facing US book, not Pinnacle. Agreement with DK is
    weaker evidence of efficiency than agreement with Pinnacle would be.
  - n is one day's games.
"""
import json
import os
import re
import sys

import requests

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "common"))
import kalshi_api as K  # noqa: E402
import costbar  # noqa: E402
from cross_venue import TEAMS, franchises, MONTHS  # noqa: E402

UA = {"User-Agent": "Mozilla/5.0 (market-selection-research/1.0)"}
CORE = "https://sports.core.api.espn.com/v2/sports/baseball/leagues/mlb"
REP = os.path.join(os.path.dirname(__file__), "..", "reports")


def american_to_prob(ml):
    if ml is None:
        return None
    ml = float(ml)
    return (-ml) / ((-ml) + 100.0) if ml < 0 else 100.0 / (ml + 100.0)


def espn_lines(date_range="20260802-20260806"):
    """{(date, frozenset(pair)): {team: devigged_prob}} from DraftKings.

    The bare /events call returns only the current day (15 games) while Kalshi
    lists several days ahead, which held the first run to 4 matched games. A
    `dates=YYYYMMDD-YYYYMMDD` range plus paging raises it.
    """
    out = {}
    items = []
    for page in range(1, 5):
        r = requests.get(f"{CORE}/events",
                         params={"dates": date_range, "limit": 100, "page": page},
                         headers=UA, timeout=45)
        if r.status_code != 200:
            break
        d = r.json()
        batch = d.get("items", [])
        items.extend(batch)
        if len(items) >= (d.get("count") or 0) or not batch:
            break
    print(f"  ESPN events in {date_range}: {len(items)}")
    for it in items:
        ref = it["$ref"].split("?")[0]
        eid = ref.rstrip("/").split("/")[-1]
        try:
            ev = requests.get(ref, headers=UA, timeout=40).json()
        except requests.RequestException:
            continue
        date = (ev.get("date") or "")[:10]
        name = ev.get("name") or ""
        pair = franchises(name)
        if len(pair) != 2:
            continue
        try:
            od = requests.get(f"{ref}/competitions/{eid}/odds",
                              headers=UA, timeout=40).json()
        except requests.RequestException:
            continue
        for item in od.get("items", []):
            if (item.get("provider") or {}).get("name") != "DraftKings":
                continue
            a = (item.get("awayTeamOdds") or {})
            h = (item.get("homeTeamOdds") or {})
            pa, ph = american_to_prob(a.get("moneyLine")), american_to_prob(h.get("moneyLine"))
            if pa is None or ph is None:
                continue
            tot = pa + ph
            if not (1.0 < tot < 1.20):
                continue
            # which franchise is home / away
            at = franchises((a.get("team") or {}).get("abbreviation", "") or
                            (a.get("team") or {}).get("displayName", "") or "")
            ht = franchises((h.get("team") or {}).get("abbreviation", "") or
                            (h.get("team") or {}).get("displayName", "") or "")
            # ESPN's "X at Y" name is away-at-home
            if len(at) != 1 or len(ht) != 1:
                parts = re.split(r"\s+at\s+", name)
                if len(parts) == 2:
                    at, ht = franchises(parts[0]), franchises(parts[1])
            if len(at) != 1 or len(ht) != 1:
                continue
            out[(date, frozenset(pair))] = {
                next(iter(at)): pa / tot, next(iter(ht)): ph / tot,
                "_vig_pct": round((tot - 1) * 100, 2)}
            break
    return out


def main():
    lines = espn_lines()
    print(f"DraftKings lines from ESPN: {len(lines)} games")
    if not lines:
        print("no lines -- cannot run")
        return

    r = K.get("/markets", {"series_ticker": "KXMLBGAME", "status": "open",
                           "limit": 1000})
    rows = []
    for m in (r.json().get("markets", []) if r and r.status_code == 200 else []):
        tk = m["ticker"]
        mm = re.match(r"KXMLBGAME-(\d\d)([A-Z]{3})(\d\d)", tk)
        if not mm:
            continue
        yy, mon, dd = mm.groups()
        date = f"20{yy}-{MONTHS[mon]:02d}-{int(dd):02d}"
        pair, yes = franchises(m.get("title")), franchises(m.get("yes_sub_title"))
        if len(pair) != 2 or len(yes) != 1:
            continue
        L = lines.get((date, frozenset(pair)))
        if not L:
            continue
        team = next(iter(yes))
        if team not in L:
            continue
        yb_l, no_l = K.orderbook(tk)
        yb, ya, _, _ = K.touch(yb_l or [], no_l or [])
        if yb is None or ya is None:
            continue
        mid = (yb + ya) / 2
        dk = L[team] * 100.0
        px = int(min(max(round(mid), 1), 99))
        bar = costbar.cost_bar_cents(px, ya - yb, "kalshi")["total_c"]
        rows.append({"date": date, "game": "/".join(sorted(pair)), "team": team,
                     "k_bid": yb, "k_ask": ya, "k_mid": round(mid, 2),
                     "dk_prob_c": round(dk, 2),
                     "diff_c": round(mid - dk, 2),
                     "abs_diff_c": round(abs(mid - dk), 2),
                     "cost_bar_c": bar,
                     "exceeds_bar": abs(mid - dk) > bar,
                     "vig_pct": L["_vig_pct"]})

    rows.sort(key=lambda r: -r["abs_diff_c"])
    with open(os.path.join(REP, "kalshi_vs_dk_mlb.json"), "w",
              encoding="utf-8") as fh:
        json.dump(rows, fh, indent=1)
    if not rows:
        print("no matched games")
        return
    d = sorted(r["abs_diff_c"] for r in rows)
    n = len(d)
    ex = sum(r["exceeds_bar"] for r in rows)
    import statistics as st
    signed = [r["diff_c"] for r in rows]
    print(f"\nunit of observation: one MLB game side, n={n}")
    print(f"|Kalshi mid - DraftKings devigged|, cents:")
    print(f"  median {d[n//2]:.2f}   p75 {d[int(n*.75)]:.2f}   "
          f"p90 {d[min(int(n*.9),n-1)]:.2f}   max {d[-1]:.2f}")
    print(f"  mean signed difference {st.mean(signed):+.2f}c "
          f"(sd {st.pstdev(signed):.2f}) -- tests for a systematic lean")
    print(f"  median DraftKings vig {st.median(r['vig_pct'] for r in rows):.2f}%")
    print(f"\ngame sides where |difference| EXCEEDS the Kalshi cost bar: "
          f"{ex} of {n} ({100*ex/n:.0f}%)")
    print(f"\n{'date':11s} {'game':9s} {'yes':4s} {'k_bid':>6s} {'k_ask':>6s} "
          f"{'k_mid':>6s} {'DK':>6s} {'diff':>6s} {'bar':>5s} over?")
    for r in rows[:20]:
        print(f"{r['date']:11s} {r['game']:9s} {r['team']:4s} {r['k_bid']:6.1f} "
              f"{r['k_ask']:6.1f} {r['k_mid']:6.2f} {r['dk_prob_c']:6.2f} "
              f"{r['diff_c']:+6.2f} {r['cost_bar_c']:5.2f} "
              f"{'YES' if r['exceeds_bar'] else ''}")
    print("\nwrote reports/kalshi_vs_dk_mlb.json")


if __name__ == "__main__":
    main()

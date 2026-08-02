"""Kalshi props vs the free DraftKings line, DE-VIGGED properly.

The first attempt matched Kalshi's "N+" milestones to DraftKings' MILESTONE
entries. Those are one-sided: a single American price with no opposing side, so
the implied probability carries the book's margin and cannot be de-vigged. It
produced a mean signed gap of -3.52c and "79% exceed the cost bar", which is
almost exactly what a 4-7% margin looks like and is therefore not evidence of
disagreement at all. Reporting it would have been reporting the vig.

This version uses DraftKings' TWO-SIDED over/under entries, which carry both
`overOdds` and `underOdds` and can be normalised.

The mapping is exact, not approximate:
    Kalshi "N+"  ==  DK "Total X" with line (N - 0.5), OVER side
    "1+" is "over 0.5", "2+" is "over 1.5", and so on.

De-vig: p_over_fair = p_over_raw / (p_over_raw + p_under_raw).
"""
import json
import os
import re
import sys
from collections import defaultdict

import requests

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "common"))
import kalshi_api as K  # noqa: E402
import costbar  # noqa: E402

UA = {"User-Agent": "Mozilla/5.0 (market-selection-research/1.0)"}
CORE = "https://sports.core.api.espn.com/v2/sports/baseball/leagues/mlb"
REP = os.path.join(os.path.dirname(__file__), "..", "reports")

MAP = {
    "KXMLBKS": ["Total Strikeouts"],
    "KXMLBHIT": ["Total Hits"],
    "KXMLBTB": ["Total Bases"],
    "KXMLBHRR": ["Total Hits + Runs + RBIs"],
}


def am_to_prob(v):
    try:
        ml = float(str(v).replace("+", ""))
    except (TypeError, ValueError):
        return None
    return (-ml) / ((-ml) + 100.0) if ml < 0 else 100.0 / (ml + 100.0)


def norm(name):
    return " ".join(re.sub(r"[^a-z ]", " ", (name or "").lower()).split())


def dk_totals():
    """{(athlete, type, line): {'over':p,'under':p,'vig':x}} two-sided only."""
    raw = defaultdict(dict)
    ath = {}
    wanted = {t for v in MAP.values() for t in v}
    items = requests.get(f"{CORE}/events", headers=UA, timeout=45).json()["items"]
    for it0 in items:
        ref = it0["$ref"].split("?")[0]
        eid = ref.rstrip("/").split("/")[-1]
        url = f"{ref}/competitions/{eid}/odds/100/propBets"
        page, got = 1, 0
        while page <= 8:
            try:
                d = requests.get(url, params={"limit": 100, "page": page},
                                 headers=UA, timeout=45).json()
            except Exception:  # noqa: BLE001
                break
            its = d.get("items", [])
            if not its:
                break
            for x in its:
                t = (x.get("type") or {}).get("name")
                if t not in wanted:
                    continue
                aref = (x.get("athlete") or {}).get("$ref")
                if not aref:
                    continue
                if aref not in ath:
                    try:
                        ath[aref] = requests.get(aref, headers=UA,
                                                 timeout=30).json().get("displayName")
                    except Exception:  # noqa: BLE001
                        ath[aref] = None
                who = ath[aref]
                o = x.get("odds") or {}
                line = (o.get("total") or {}).get("value")
                if who is None or line is None:
                    continue
                key = (norm(who), t, str(float(line)))
                # two-sided fields live at the top of the entry
                po = am_to_prob(x.get("overOdds"))
                pu = am_to_prob(x.get("underOdds"))
                if po is None or pu is None:
                    # fall back: some entries put the priced side in odds.american
                    continue
                raw[key] = {"over": po, "under": pu, "vig": po + pu}
            got += len(its)
            if got >= (d.get("count") or 0):
                break
            page += 1
    out = {}
    for k, v in raw.items():
        if 1.0 < v["vig"] < 1.35:
            out[k] = {"fair_over": v["over"] / v["vig"], "vig_pct": (v["vig"] - 1) * 100}
    return out


def main():
    print("pulling two-sided DraftKings totals ...", flush=True)
    dk = dk_totals()
    print(f"  {len(dk)} de-viggable two-sided prop lines")
    if not dk:
        print("\nNo two-sided prop entries carried both overOdds and underOdds.")
        print("The free feed's player props are ONE-SIDED, so they cannot be")
        print("de-vigged, and the earlier -3.52c gap cannot be separated from")
        print("the book's margin. Reported as inconclusive, not as a finding.")
        json.dump({"result": "no two-sided prop entries"},
                  open(os.path.join(REP, "kalshi_vs_dk_props2.json"), "w"), indent=1)
        return

    rows = []
    for series, types in MAP.items():
        r = K.get("/markets", {"series_ticker": series, "status": "open",
                               "limit": 1000})
        ms = r.json().get("markets", []) if r and r.status_code == 200 else []
        for m in ms:
            mm = re.match(r"(.+?):\s*(\d+)\+", m.get("yes_sub_title") or "")
            if not mm:
                continue
            who, n = norm(mm.group(1)), int(mm.group(2))
            line = str(float(n) - 0.5)
            hit = None
            for t in types:
                hit = dk.get((who, t, line))
                if hit:
                    break
            if not hit:
                continue
            yes, no = K.orderbook(m["ticker"])
            yb, ya, _b, _a = K.touch(yes or [], no or [])
            if yb is None or ya is None:
                continue
            mid = (yb + ya) / 2
            dkc = hit["fair_over"] * 100
            px = int(min(max(round(mid), 1), 99))
            bar = costbar.cost_bar_cents(px, ya - yb, "kalshi")["total_c"]
            rows.append({"series": series, "who": who, "n": n,
                         "k_bid": yb, "k_ask": ya, "k_mid": round(mid, 2),
                         "dk_fair_c": round(dkc, 2),
                         "diff_c": round(mid - dkc, 2),
                         "abs_diff_c": round(abs(mid - dkc), 2),
                         "vig_pct": round(hit["vig_pct"], 2),
                         "cost_bar_c": bar,
                         "exceeds_bar": abs(mid - dkc) > bar})

    json.dump(rows, open(os.path.join(REP, "kalshi_vs_dk_props2.json"), "w"),
              indent=1)
    print(f"\nmatched (de-vigged): {len(rows)}")
    if not rows:
        print("no matches after de-vigging")
        return
    import statistics as st
    d = sorted(r["abs_diff_c"] for r in rows)
    n = len(d)
    ex = sum(r["exceeds_bar"] for r in rows)
    print(f"unit: one player-threshold prop, n={n}")
    print(f"median |gap| {d[n//2]:.2f}c  p90 {d[min(int(n*.9),n-1)]:.2f}c  "
          f"max {d[-1]:.2f}c")
    print(f"mean signed {st.mean(r['diff_c'] for r in rows):+.2f}c")
    print(f"median DK vig {st.median(r['vig_pct'] for r in rows):.2f}%")
    print(f"exceeding the cost bar: {ex} of {n} ({100*ex/n:.0f}%)")


if __name__ == "__main__":
    main()

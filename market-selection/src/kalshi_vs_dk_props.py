"""Do Kalshi's MLB player props agree with the free DraftKings prop line?

This is the measurement that decides whether the MLB prop families belong at
the top of the shortlist. It is a market-property measurement of the same kind
as the moneyline and cross-venue comparisons, not a strategy test: it asks
whether a free reference already prices what Kalshi prices, and if so how far
apart they sit relative to the cost bar.

MATCHING. Kalshi quotes milestones ("Cade Cavalli: 9+ strikeouts?"). DraftKings
publishes both an over/under ("Total Strikeouts", line 5.5, American odds) and
milestone entries ("Strikeouts Thrown Milestones", "6+"). The milestone form is
the directly comparable one: a "6+" milestone at American odds converts to an
implied probability that maps onto Kalshi's YES price for the same threshold.

De-vigging: milestone entries are one-sided (a YES price only), so there is no
two-sided pair to normalise against. The raw implied probability therefore
carries the book's margin and is BIASED HIGH relative to a fair probability.
That bias is reported rather than corrected, and it means a positive
Kalshi-minus-DK gap is the conservative direction.

Prices are executable on the Kalshi side: YES ask = 1 - best NO bid.
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

# Kalshi series -> the DraftKings prop type names that describe the same thing
MAP = {
    "KXMLBKS": ["Strikeouts Thrown Milestones"],
    "KXMLBHIT": ["Hits Milestones"],
    "KXMLBTB": ["Total Bases Milestones"],
    "KXMLBHR": ["Home Runs Milestones"],
    "KXMLBHRR": ["Hits + Runs + RBIs Milestones"],
}


def am_to_prob(v):
    try:
        ml = float(str(v).replace("+", ""))
    except (TypeError, ValueError):
        return None
    return (-ml) / ((-ml) + 100.0) if ml < 0 else 100.0 / (ml + 100.0)


def norm(name):
    n = re.sub(r"[^a-z ]", " ", (name or "").lower())
    return " ".join(n.split())


def dk_props():
    """{(normalised athlete, dk_type, threshold): implied_prob}"""
    out = {}
    ath_cache = {}
    items = requests.get(f"{CORE}/events", headers=UA, timeout=45).json()["items"]
    wanted = {t for v in MAP.values() for t in v}
    for it0 in items:
        ref = it0["$ref"].split("?")[0]
        eid = ref.rstrip("/").split("/")[-1]
        url = f"{ref}/competitions/{eid}/odds/100/propBets"
        page = 1
        got = 0
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
                tname = (x.get("type") or {}).get("name")
                if tname not in wanted:
                    continue
                aref = (x.get("athlete") or {}).get("$ref")
                if not aref:
                    continue
                if aref not in ath_cache:
                    try:
                        ath_cache[aref] = requests.get(
                            aref, headers=UA, timeout=30).json().get("displayName")
                    except Exception:  # noqa: BLE001
                        ath_cache[aref] = None
                who = ath_cache[aref]
                o = x.get("odds") or {}
                p = am_to_prob((o.get("american") or {}).get("value"))
                tgt = ((x.get("current") or {}).get("target") or {}).get("displayValue")
                if who and p is not None and tgt:
                    thr = re.sub(r"[^0-9]", "", str(tgt))
                    if thr:
                        out[(norm(who), tname, thr)] = p
            got += len(its)
            if got >= (d.get("count") or 0):
                break
            page += 1
    return out


def main():
    print("pulling free DraftKings milestone props ...", flush=True)
    dk = dk_props()
    print(f"  {len(dk)} priced milestone entries")
    if not dk:
        print("none -- cannot compare")
        return

    rows = []
    unmatched = defaultdict(int)
    for series, dk_types in MAP.items():
        r = K.get("/markets", {"series_ticker": series, "status": "open",
                               "limit": 1000})
        ms = r.json().get("markets", []) if r and r.status_code == 200 else []
        for m in ms:
            sub = m.get("yes_sub_title") or ""
            mm = re.match(r"(.+?):\s*(\d+)\+", sub)
            if not mm:
                unmatched[series] += 1
                continue
            who, thr = norm(mm.group(1)), mm.group(2)
            hit = None
            for t in dk_types:
                if (who, t, thr) in dk:
                    hit = dk[(who, t, thr)]
                    break
            if hit is None:
                unmatched[series] += 1
                continue
            yes, no = K.orderbook(m["ticker"])
            yb, ya, _bs, _as = K.touch(yes or [], no or [])
            if yb is None or ya is None:
                continue
            mid = (yb + ya) / 2
            dkc = hit * 100.0
            px = int(min(max(round(mid), 1), 99))
            bar = costbar.cost_bar_cents(px, ya - yb, "kalshi")["total_c"]
            rows.append({"series": series, "ticker": m["ticker"], "who": who,
                         "threshold": thr, "k_bid": yb, "k_ask": ya,
                         "k_mid": round(mid, 2), "dk_prob_c": round(dkc, 2),
                         "diff_c": round(mid - dkc, 2),
                         "abs_diff_c": round(abs(mid - dkc), 2),
                         "cost_bar_c": bar,
                         "exceeds_bar": abs(mid - dkc) > bar})

    with open(os.path.join(REP, "kalshi_vs_dk_props.json"), "w",
              encoding="utf-8") as fh:
        json.dump(rows, fh, indent=1)
    print(f"\nmatched: {len(rows)}   unmatched by series: {dict(unmatched)}")
    if not rows:
        print("no matched props")
        return
    import statistics as st
    d = sorted(r["abs_diff_c"] for r in rows)
    n = len(d)
    ex = sum(r["exceeds_bar"] for r in rows)
    sig = [r["diff_c"] for r in rows]
    print(f"\nunit of observation: one player-threshold prop, n={n}")
    print(f"|Kalshi mid - DK implied| cents:  median {d[n//2]:.2f}  "
          f"p75 {d[int(n*.75)]:.2f}  p90 {d[min(int(n*.9),n-1)]:.2f}  max {d[-1]:.2f}")
    print(f"mean SIGNED gap {st.mean(sig):+.2f}c (sd {st.pstdev(sig):.2f})")
    print("  NOTE: DK milestone entries are one-sided, so the implied "
          "probability carries the book's margin and is biased HIGH.")
    print("  A negative mean signed gap is therefore the EXPECTED direction "
          "and is not evidence of a Kalshi discount.")
    print(f"\nprops where |gap| exceeds the Kalshi cost bar: {ex} of {n} "
          f"({100*ex/n:.0f}%)")
    print(f"\n{'series':12s} {'who':22s} {'thr':>4s} {'k_mid':>6s} {'DK':>6s} "
          f"{'diff':>7s} {'bar':>5s}")
    for r in sorted(rows, key=lambda r: -r["abs_diff_c"])[:20]:
        print(f"{r['series']:12s} {r['who'][:22]:22s} {r['threshold']:>4s} "
              f"{r['k_mid']:6.2f} {r['dk_prob_c']:6.2f} {r['diff_c']:+7.2f} "
              f"{r['cost_bar_c']:5.2f}")


if __name__ == "__main__":
    main()

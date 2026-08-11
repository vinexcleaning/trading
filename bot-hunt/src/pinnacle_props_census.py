"""M025 — are Pinnacle's PLAYER PROPS two-sided, and how wide is the margin?

`market-selection` M024 says **0** prop entries carry both sides, and M025 was
**CANCELLED as "unanswerable with free data"** on 2026-08-02. Both were measured
on ONE feed — ESPN's DraftKings object.

The `reopen` chat found a counter-example sitting in **my own committed
artifact**, `bot-hunt/reports/pinnacle_probe.json` from 2026-08-04:

    "special": {"category": "Player Props",
                "description": "Justin Foscue Total Bases"}
    "prices":  [{"points": 0.5, "price": -125}, {"points": 0.5, "price": -106}]

A free, unauthenticated, **two-sided** MLB player prop. The absence claim is
false. But one prop from two saved entries is an existence proof, not a
measurement — so this counts them properly.

WHY IT MATTERS MORE THAN A CORRECTED ROW. BH011 killed the moneyline de-vig
because the two venues agree more tightly than it costs to trade. That is an
EMPIRICAL fact about Pinnacle's **moneyline**, which is the sharpest line in the
world. **It does not transfer to props**, and assuming it does would be exactly
the "only one version was tested" error this whole audit is about. The single
observed prop keeps **7.0 out of 100** against the moneyline's **2.01** — 3.5x
wider.

Cuts the other way too, and this is the honest half: a book quoting 7 out of 100
with a **$500** maximum stake is telling you it is not confident. Wide margin and
low limits are what a book looks like when it does not want the action.

Read-only, unauthenticated, one paced pull.
"""
from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
import venues as V  # noqa: E402

REP = ROOT / "reports"
SPORTS = {3: "baseball", 33: "tennis", 12: "esports", 29: "soccer"}


def a2p(a):
    a = float(a)
    return (-a) / ((-a) + 100.0) if a < 0 else 100.0 / (a + 100.0)


def main() -> None:
    REP.mkdir(parents=True, exist_ok=True)
    out = {}
    for sid, name in SPORTS.items():
        # ⚠ THE JOIN IS THE WHOLE POINT, AND v1 OF THIS FILE GOT IT WRONG.
        # `special.category` ("Player Props") lives on the MATCHUP record.
        # `prices` and `limits` live on the MARKETS/STRAIGHT record. They are
        # joined by `matchupId`. v1 looked for `special` on the straight records,
        # found 0 across four sports, and would have "confirmed" M024's absence
        # claim -- by reading the wrong object, which is precisely how M024 got
        # it wrong in the first place on a different feed.
        mu = V.get(f"https://guest.api.arcadia.pinnacle.com/0.1/sports/{sid}"
                   f"/matchups", pace=0.5)
        st = V.get(f"https://guest.api.arcadia.pinnacle.com/0.1/sports/{sid}"
                   f"/markets/straight", pace=0.5)
        if mu is None or st is None or mu.status_code != 200 or st.status_code != 200:
            print(f"{name}: matchups/straight HTTP problem")
            continue
        try:
            mus, sts = mu.json(), st.json()
        except ValueError:
            continue

        special = {}
        for m in mus:
            sp = m.get("special") or {}
            if sp.get("category"):
                special[m.get("id")] = sp
        print("\n" + "=" * 68)
        print(f"{name.upper()}  — {len(mus):,} matchups, "
              f"{len(sts):,} straight markets")
        print("=" * 68)
        print(f"   matchups carrying `special.category` : {len(special):,}")
        if special:
            cats = Counter(v.get("category") for v in special.values())
            for c, n in cats.most_common(6):
                print(f"      {str(c)[:44]:44} {n:>7,}")

        props, one_sided = [], 0
        for m in sts:
            sp = special.get(m.get("matchupId"))
            if not sp:
                continue
            vals = [pr.get("price") for pr in (m.get("prices") or [])
                    if pr.get("price") is not None]
            if len(vals) < 2:
                one_sided += 1
                continue
            lim = None
            for l in (m.get("limits") or []):
                if l.get("type") == "maxRiskStake":
                    lim = l.get("amount")
            try:
                ps = [a2p(v) for v in vals[:2]]
            except (TypeError, ValueError, ZeroDivisionError):
                continue
            orr = 100.0 * (sum(ps) - 1.0)
            if not (-1 < orr < 80):
                continue
            props.append({"category": sp.get("category"),
                          "description": sp.get("description", ""),
                          "overround_pp": orr, "max_risk": lim,
                          "type": m.get("type")})

        print(f"   priced markets on those matchups     : "
              f"{len(props) + one_sided:,}")
        print(f"   of those, TWO-SIDED                  : {len(props):,}"
              f"   (one-sided {one_sided:,})")
        if not props:
            out[name] = {"matchups": len(mus), "special": len(special),
                         "two_sided": 0, "one_sided": one_sided}
            continue

        o = np.array([p["overround_pp"] for p in props])
        lims = [p["max_risk"] for p in props if p["max_risk"]]
        print(f"   overround out of 100: median {np.median(o):.2f}   "
              f"p10 {np.percentile(o,10):.2f}   p90 {np.percentile(o,90):.2f}")
        if lims:
            print(f"   max stake: median ${np.median(lims):,.0f}   "
                  f"p90 ${np.percentile(lims,90):,.0f}")
        bycat = defaultdict(list)
        for p in props:
            bycat[p["category"]].append(p["overround_pp"])
        for c, v in sorted(bycat.items(), key=lambda x: -len(x[1]))[:8]:
            print(f"      {str(c)[:34]:34} n={len(v):>5}  median "
                  f"{np.median(v):>6.2f} out of 100")
        out[name] = {"matchups": len(mus), "special": len(special),
                     "two_sided": len(props), "one_sided": one_sided,
                     "overround_median_pp": round(float(np.median(o)), 3),
                     "overround_p10_pp": round(float(np.percentile(o, 10)), 3),
                     "overround_p90_pp": round(float(np.percentile(o, 90)), 3),
                     "max_stake_median": (float(np.median(lims)) if lims else None),
                     "by_category": {str(c): [len(v), round(float(np.median(v)), 3)]
                                     for c, v in bycat.items()},
                     "examples": props[:6]}

    (REP / "pinnacle_props_census.json").write_text(
        json.dumps(out, indent=1, default=str), encoding="utf-8")
    print("\nwrote reports/pinnacle_props_census.json")


if __name__ == "__main__":
    main()

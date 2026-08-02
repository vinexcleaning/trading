"""Emit the shortlist's numeric table straight from the final scorecard.

Hand-copying numbers between an artifact and a write-up is how a report ends up
disagreeing with the data it cites. This generates the markdown rows.
"""
import json
import os

REP = os.path.join(os.path.dirname(__file__), "..", "reports")
rows = {r["series"]: r for r in
        json.load(open(os.path.join(REP, "family_scorecard.json"),
                       encoding="utf-8"))}

GROUPS = [
    ("1. South American / Mexican soccer",
     ["KXLIGAMXGAME", "KXARGPREMDIVGAME", "KXCOPADOBRASILGAME",
      "KXLIGAMXTOTAL", "KXDIMAYORGAME"]),
    ("2. MLB first-inning and game derivatives",
     ["KXMLBRFI", "KXMLBTOTAL", "KXMLBSPREAD", "KXMLBF5TOTAL", "KXMLBGAME"]),
    ("3. MLB player props",
     ["KXMLBKS", "KXMLBHIT", "KXMLBTB", "KXMLBHRR", "KXMLBHR"]),
    ("4. NPB / KBO baseball",
     ["KXNPBGAME", "KXNPBTOTAL", "KXKBOGAME"]),
    ("EXCLUDED - tennis (best market, no data)",
     ["KXITFMATCH", "KXITFWMATCH", "KXATPCHALLENGERMATCH", "KXATPMATCH",
      "KXWTAMATCH"]),
    ("EXCLUDED - crypto / golf / esports",
     ["KXBTCD", "KXBTC15M", "KXPGATOUR", "KXLOLGAME", "KXCS2GAME"]),
]


def f(v, nd=1, dash="-"):
    if v is None:
        return dash
    if isinstance(v, float):
        return f"{v:,.{nd}f}"
    return f"{v:,}"


for title, series in GROUPS:
    print(f"\n#### {title}\n")
    print("| Series | trades/day | mkts/day | settles/wk | 2-sided uptime | "
          "spread med / p90 | >tick | bid size | depth 5¢ | cost bar | fee_type |")
    print("|---|---|---|---|---|---|---|---|---|---|---|")
    for s in series:
        r = rows.get(s)
        if not r:
            print(f"| {s} | *(not in tape)* | | | | | | | | | |")
            continue
        up = r.get("two_sided_uptime")
        print(f"| **{s}** | {f(r['trades_day'],0)} | {f(r['markets_traded_day'],0)} | "
              f"{f(r.get('settlements_per_week_est'),0)} | "
              f"{(str(round(up*100,1))+'%') if up is not None else 'not sampled'} "
              f"(n={r['depth_snaps']}) | "
              f"{f(r.get('spread_med_c'),1)} / {f(r.get('spread_p90_c'),1)}¢ | "
              f"{f(r.get('frac_spread_above_tick'),2)} | "
              f"{f(r.get('bid_sz_med'),0)} | {f(r.get('depth_5c_med'),0)} | "
              f"{f(r.get('cost_bar_c'),2)}¢ | "
              f"{str(r.get('fee_type')).replace('quadratic_with_maker_fees','quad+maker').replace('quadratic','quad')} |")

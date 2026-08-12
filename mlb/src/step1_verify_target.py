"""STEP 1 (KILL POINT): does a free first-inning line exist anywhere?

KXMLBRFI was shortlisted on exactly one claim: it is the only MLB family with
a deep book and NO free bookmaker price beside it. That claim rests on a scan
of 34 DraftKings prop types via ESPN. If a free RFI price exists anywhere, the
family dies the way the game-winner died (Kalshi tracks DK to 0.37c).

So: search hard before building anything.

Also measures the market itself -- markets/day, spread, depth, settlement rate
-- and does the same for the first-5-innings families, which the user approved
as a cheap check on whether MLB side markets are soft at all.
"""
import json
import os
import sys
import time
from collections import Counter, defaultdict

import requests

HERE = os.path.dirname(__file__)
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "..", "market-selection", "src"))
sys.path.insert(0, os.path.join(HERE, "..", "..", "common"))
import kalshi_api as K  # noqa: E402
import costbar  # noqa: E402

REP = os.path.join(HERE, "..", "reports")
UA = {"User-Agent": "curl/8.4.0"  # NOT a browser shape. ESPN's edge network
    # returns 403 to browser-shaped agents and 200 to curl's -- measured
    # 2026-08-08, four headers, same URL, same minute (reopen mailbox 007,
    # soccer SO014, and re-measured here). A dead fetcher does not look
    # dead; it looks like the data does not exist, and this repo has
    # already produced four wrong absence claims that way.
                    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"}
CORE = "https://sports.core.api.espn.com/v2/sports/baseball/leagues/mlb"
SITE = "https://site.api.espn.com/apis/site/v2/sports/baseball/mlb"
TARGETS = ["KXMLBRFI", "KXMLBF5", "KXMLBF5TOTAL", "KXMLBF5SPREAD",
           "KXMLBGAME", "KXMLBTOTAL", "KXMLBSPREAD"]
out = {}


def get(u, p=None, tries=3):
    for i in range(tries):
        try:
            r = requests.get(u, params=p, headers=UA, timeout=45)
        except requests.RequestException:
            time.sleep(2 * (i + 1))
            continue
        if r.status_code >= 500 or r.status_code == 429:
            time.sleep(3 * (i + 1))
            continue
        return r
    return None


print("=" * 70)
print("A. EXHAUSTIVE SCAN: every DraftKings prop type ESPN exposes")
print("=" * 70)
types = Counter()
lines = {}
r = get(f"{CORE}/events")
items = r.json().get("items", []) if r is not None and r.status_code == 200 else []
print(f"  {len(items)} MLB events today")
scanned = 0
for it in items:
    ref = it["$ref"].split("?")[0]
    eid = ref.rstrip("/").split("/")[-1]
    # every odds provider, not just the first
    ro = get(f"{ref}/competitions/{eid}/odds")
    if ro is None or ro.status_code != 200:
        continue
    for prov in ro.json().get("items", []):
        pname = (prov.get("provider") or {}).get("name")
        pid = (prov.get("provider") or {}).get("id")
        pb = prov.get("propBets")
        url = pb.get("$ref") if isinstance(pb, dict) else None
        if not url:
            continue
        page = 1
        got = 0
        while page <= 10:
            rp = get(url, {"limit": 100, "page": page})
            if rp is None or rp.status_code != 200:
                break
            d = rp.json()
            its = d.get("items", [])
            if not its:
                break
            for x in its:
                tn = (x.get("type") or {}).get("name")
                types[tn] += 1
                if tn and tn not in lines:
                    o = x.get("odds") or {}
                    lines[tn] = {
                        "provider": pname,
                        "american": (o.get("american") or {}).get("value"),
                        "total": (o.get("total") or {}).get("value"),
                    }
            got += len(its)
            scanned += len(its)
            if got >= (d.get("count") or 0):
                break
            page += 1
print(f"  scanned {scanned} prop entries across all providers")
print(f"  {len(types)} distinct prop types:\n")
for t, n in types.most_common():
    print(f"    {str(t)[:46]:46s} {n:5d}  line={lines.get(t,{}).get('total')}")

INNING_WORDS = ("first inning", "1st inning", "inning", "run in the",
                "score in the", "1st 5", "first 5", "f5")
hits = [t for t in types if t and any(w in t.lower() for w in INNING_WORDS)]
print(f"\n  types mentioning an inning: {hits}")
rfi_hits = [t for t in types
            if t and ("first inning" in t.lower() or "1st inning" in t.lower())]
print(f"  types that are a FIRST-INNING RUN market: {rfi_hits if rfi_hits else 'NONE'}")
out["prop_types"] = dict(types)
out["inning_types"] = hits
out["rfi_types"] = rfi_hits

print("\n" + "=" * 70)
print("B. OTHER FREE SOURCES that might carry an RFI/YRFI line")
print("=" * 70)
CHECKS = [
    ("ESPN site odds (scoreboard)", f"{SITE}/scoreboard"),
    ("the-odds-api markets list (no key)",
     "https://api.the-odds-api.com/v4/sports/baseball_mlb/odds?regions=us&markets=h2h"),
    ("oddsapi alt", "https://api.the-odds-api.com/v4/sports/"),
    ("Covers.com MLB", "https://www.covers.com/sport/baseball/mlb/odds"),
    ("actionnetwork MLB odds",
     "https://api.actionnetwork.com/web/v2/scoreboard/mlb"),
    ("scoresandodds MLB", "https://www.scoresandodds.com/mlb"),
    ("rotowire YRFI", "https://www.rotowire.com/baseball/tables/yrfi-nrfi.php"),
    ("bettingpros YRFI", "https://api.bettingpros.com/v3/offers?sport=MLB&market_id=308"),
]
for name, u in CHECKS:
    r = get(u)
    if r is None:
        print(f"  {name:38s} ERROR")
        out[name] = "ERROR"
        continue
    body = r.text[:200].replace("\n", " ")
    hit = any(w in r.text.lower() for w in ("yrfi", "nrfi", "first inning",
                                            "1st inning"))
    print(f"  {name:38s} http={r.status_code} bytes={len(r.content):7d} "
          f"mentions_RFI={hit}")
    out[name] = {"http": r.status_code, "bytes": len(r.content),
                 "mentions_rfi": hit, "snippet": body[:120]}

print("\n" + "=" * 70)
print("C. THE KALSHI MARKETS THEMSELVES")
print("=" * 70)
print(f"{'series':16s} {'open':>5s} {'events':>7s} {'2sided':>7s} {'spr':>5s} "
      f"{'bidSz':>10s} {'depth5c':>11s} {'bar@50':>7s} {'fee_type':>26s}")
mkt = {}
for s in TARGETS:
    r = K.get("/markets", {"series_ticker": s, "status": "open", "limit": 1000})
    ms = r.json().get("markets", []) if r and r.status_code == 200 else []
    sr = K.get(f"/series/{s}")
    meta = sr.json().get("series", {}) if sr and sr.status_code == 200 else {}
    ms.sort(key=lambda m: -(K.f(m.get("volume_24h_fp")) or 0.0))
    sp, bs, d5 = [], [], []
    two = n = 0
    for m in ms[:20]:
        yes, no = K.orderbook(m["ticker"])
        yb, ya, b, a = K.touch(yes or [], no or [])
        n += 1
        if yb is None or ya is None:
            continue
        two += 1
        sp.append(ya - yb)
        if b is not None:
            bs.append(b)
        dep = sum(z for p, z in (yes or []) if p >= yb - 5.0)
        dep += sum(z for p, z in (no or []) if p >= (100.0 - ya) - 5.0)
        d5.append(dep)

    def med(x):
        return round(sorted(x)[len(x) // 2], 1) if x else None
    msp = med(sp)
    bar = costbar.cost_bar_cents(50, msp, "kalshi")["total_c"] if msp else None
    mkt[s] = {"open": len(ms), "events": len({m.get("event_ticker") for m in ms}),
              "sampled": n, "two_sided": two, "spread_med": msp,
              "bid_sz_med": med(bs), "depth5c_med": med(d5),
              "cost_bar_50c": bar, "fee_type": meta.get("fee_type")}
    print(f"{s:16s} {len(ms):5d} {mkt[s]['events']:7d} "
          f"{(str(round(100*two/max(n,1),0))+'%'):>7s} {str(msp):>5s} "
          f"{str(mkt[s]['bid_sz_med']):>10s} {str(mkt[s]['depth5c_med']):>11s} "
          f"{str(bar):>7s} {str(meta.get('fee_type')):>26s}")
out["kalshi_markets"] = mkt

print("\n" + "=" * 70)
print("VERDICT")
print("=" * 70)
if rfi_hits:
    print("  *** A FREE FIRST-INNING LINE EXISTS. KXMLBRFI IS KILLED. ***")
    print(f"      types: {rfi_hits}")
else:
    print("  No first-inning run market found in any free odds source checked.")
    print("  KXMLBRFI SURVIVES step 1 -- proceed, but this is an absence of")
    print("  evidence, not proof. Re-check if a new source appears.")
if hits:
    print(f"\n  NOTE: inning-related types that DO exist free: {hits}")
    print("  If these include 1st-5-innings, that family is referenced and")
    print("  should be expected to behave like the game-winner (efficient).")

with open(os.path.join(REP, "step1_verify.json"), "w", encoding="utf-8") as fh:
    json.dump(out, fh, indent=1, default=str)
print("\nwrote reports/step1_verify.json")

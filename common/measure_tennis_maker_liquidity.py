"""Do the maker-fee tennis series hold the liquidity?

LEDGER S010 says Challenger + ITF are ~91% of the tennis book and pay NO maker
fee, while ATP/WTA do. That 91% is a COUNT. A maker strategy cares about
VOLUME, and the two can differ by an order of magnitude.

Answers, per series: market count, total volume, share of each, and whether the
series charges makers (read from fee_type, not assumed).

Public unauthenticated endpoints, paced well under the 15 req/s sustained limit
established in LEDGER C018.
"""
import collections
import json
import sys
import time

import requests

BASE = "https://api.elections.kalshi.com/trade-api/v2"
S = requests.Session()
S.headers["User-Agent"] = "tennis-liquidity-audit/1.0"
PACE = 0.14


def get(path, **params):
    for attempt in range(6):
        r = S.get(BASE + path, params=params, timeout=40)
        if r.status_code == 429:
            time.sleep(2 * (attempt + 1))
            continue
        if r.status_code == 404:
            return None
        r.raise_for_status()
        return r.json()
    raise RuntimeError(f"rate limited out on {path}")


# ---- find every tennis series, rather than assuming the five I know ------
print("enumerating series...", file=sys.stderr)
allser, cursor = [], None
while True:
    p = {"limit": 200}
    if cursor:
        p["cursor"] = cursor
    j = get("/series", **p)
    allser.extend(j.get("series", []))
    cursor = j.get("cursor")
    if not cursor or not j.get("series"):
        break
    time.sleep(PACE)

# Prefix match, NOT substring. "KXNEWTAYLOR" contains "WTA" and
# "KXNEWTARIFFS" contains "WTA"; a substring filter pulls in a Taylor Swift
# album series and a tariffs series. LEDGER T017 is a retraction caused by
# exactly this class of hand-written tennis regex, so the rule here is
# explicit prefixes plus a title check, and every exclusion is printed.
PREFIXES = ("KXATP", "KXWTA", "KXITF", "KXTENNIS")
EXCLUDE_TITLE = ("table tennis",)

tennis, rejected = [], []
for s_ in allser:
    tk = (s_.get("ticker") or "").upper()
    ti = (s_.get("title") or "").lower()
    hit = tk.startswith(PREFIXES) or "tennis" in ti
    if hit and any(x in ti for x in EXCLUDE_TITLE):
        rejected.append((s_.get("ticker"), s_.get("title"), "table tennis"))
        continue
    if hit:
        tennis.append(s_)
    elif any(k in tk for k in ("ATP", "WTA", "ITF")):
        rejected.append((s_.get("ticker"), s_.get("title"), "substring-only"))

print("excluded by the tightened filter:", file=sys.stderr)
for tk, ti, why in rejected:
    print(f"    {tk:26s} {str(ti)[:44]:46s} ({why})", file=sys.stderr)
print(file=sys.stderr)

print(f"{len(allser)} series total, {len(tennis)} look like tennis\n",
      file=sys.stderr)


def volume_of(ticker):
    """Sum volume over every market in a series, paginating fully."""
    n, vol, oi, cursor = 0, 0, 0, None
    while True:
        p = {"series_ticker": ticker, "limit": 1000}
        if cursor:
            p["cursor"] = cursor
        j = get("/markets", **p)
        if j is None:
            break
        rows = j.get("markets", [])
        n += len(rows)
        # Kalshi renamed these to *_fp (floating-point strings). Reading the
        # old names returns None and silently sums to zero - the exact trap
        # LEDGER C024 records. Guarded below by an all-zero assertion.
        for m in rows:
            if "volume_fp" not in m:
                raise KeyError(
                    "no volume_fp on the market object; the schema moved "
                    f"again. keys={sorted(m)[:14]}")
        vol += sum(float(m.get("volume_fp") or 0) for m in rows)
        oi += sum(float(m.get("open_interest_fp") or 0) for m in rows)
        cursor = j.get("cursor")
        if not cursor or not rows:
            break
        time.sleep(PACE)
    return n, int(vol), int(oi)


rows = []
for s in tennis:
    t = s["ticker"]
    n, vol, oi = volume_of(t)
    if n == 0:
        continue
    rows.append({
        "ticker": t,
        "title": (s.get("title") or "")[:38],
        "fee_type": s.get("fee_type"),
        "charges_maker": s.get("fee_type") == "quadratic_with_maker_fees",
        "markets": n, "volume": vol, "open_interest": oi,
    })
    print(f"  {t:26s} n={n:>6}  vol={vol:>12,}  "
          f"{'MAKER FEE' if rows[-1]['charges_maker'] else 'taker only'}",
          file=sys.stderr)
    time.sleep(PACE)

if sum(r["volume"] for r in rows) == 0:
    raise SystemExit("ABORT: every series reports zero volume. That is a "
                     "schema error, not a finding.")

rows.sort(key=lambda r: -r["volume"])
tot_n = sum(r["markets"] for r in rows)
tot_v = sum(r["volume"] for r in rows)

print("\n" + "=" * 104)
print("TENNIS SERIES — market count vs traded volume, by maker-fee status")
print("=" * 104)
print(f"{'series':26s} {'maker?':>8} {'markets':>9} {'% cnt':>7} "
      f"{'volume':>15} {'% vol':>7}  title")
print("-" * 104)
for r in rows:
    print(f"{r['ticker']:26s} {'YES' if r['charges_maker'] else 'no':>8} "
          f"{r['markets']:>9,} {r['markets']/tot_n*100:>6.1f}% "
          f"{r['volume']:>15,} {r['volume']/tot_v*100:>6.1f}%  {r['title']}")

mk = [r for r in rows if r["charges_maker"]]
tk = [r for r in rows if not r["charges_maker"]]
mk_n, mk_v = sum(r["markets"] for r in mk), sum(r["volume"] for r in mk)
tk_n, tk_v = sum(r["markets"] for r in tk), sum(r["volume"] for r in tk)

print("\n" + "=" * 104)
print("THE ANSWER")
print("=" * 104)
print(f"  maker-fee series ({len(mk)}): "
      f"{mk_n:>7,} markets ({mk_n/tot_n*100:5.1f}% of count)   "
      f"{mk_v:>14,} volume ({mk_v/tot_v*100:5.1f}% of volume)")
print(f"  taker-only series ({len(tk)}): "
      f"{tk_n:>7,} markets ({tk_n/tot_n*100:5.1f}% of count)   "
      f"{tk_v:>14,} volume ({tk_v/tot_v*100:5.1f}% of volume)")
print()
if tot_n and tot_v:
    print(f"  S010 says taker-only (Challenger+ITF) is ~91% of the book "
          f"by COUNT.  measured: {tk_n/tot_n*100:.1f}%")
    print(f"  by VOLUME the same series are:                              "
          f"        {tk_v/tot_v*100:.1f}%")
    ratio = (mk_v / tot_v) / (mk_n / tot_n) if mk_n else float("nan")
    print(f"\n  maker-fee series are {ratio:.1f}x more traded per market "
          f"than their share of count implies")

with open("tennis_liquidity.json", "w") as f:
    json.dump({"rows": rows,
               "maker": {"series": len(mk), "markets": mk_n, "volume": mk_v},
               "taker": {"series": len(tk), "markets": tk_n, "volume": tk_v}},
              f, indent=2)
print("\nwrote tennis_liquidity.json")

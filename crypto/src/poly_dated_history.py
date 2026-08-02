"""Phase 1.6: do the DATED Polymarket crypto families persist historically?

The unix-stamped 5m/15m series vanish from Gamma once settled, and the trade tape
is a ~10-minute rolling window. The dated families use human-readable slugs
(bitcoin-up-or-down-july-31-2026-7pm-et, bitcoin-above-62k-on-august-1-2026) and
may persist. If they do, they are the only retrievable Polymarket history here.
"""
import datetime as dt
import json
import time

import requests

UA = {"User-Agent": "research-readonly/0.1"}
GAMMA = "https://gamma-api.polymarket.com"
DATA = "https://data-api.polymarket.com"


def get(url, params=None):
    for attempt in range(4):
        r = requests.get(url, params=params, headers=UA, timeout=40)
        if r.status_code == 429:
            time.sleep(1.5 * (attempt + 1))
            continue
        if r.status_code >= 400:
            return None
        return r.json()
    return None


def section(t):
    print("\n" + "=" * 100)
    print(t)
    print("=" * 100)


MONTHS = ["january", "february", "march", "april", "may", "june", "july",
          "august", "september", "october", "november", "december"]


def main():
    today = dt.date(2026, 7, 31)

    section("1. HOURLY dated up/down — walk backwards day by day")
    hits = 0
    for back in range(0, 21):
        d = today - dt.timedelta(days=back)
        slug = (f"bitcoin-up-or-down-{MONTHS[d.month-1]}-{d.day}-"
                f"{d.year}-7pm-et")
        r = get(f"{GAMMA}/markets", {"slug": slug})
        ok = isinstance(r, list) and r
        if ok:
            hits += 1
            m = r[0]
            print(f"  -{back:>2}d {slug[:46]:<46} HIT  closed={m.get('closed')} "
                  f"vol={str(m.get('volumeNum'))[:10]:>10} "
                  f"price={m.get('outcomePrices')}")
        else:
            print(f"  -{back:>2}d {slug[:46]:<46} miss")
        time.sleep(0.12)
    print(f"\n  {hits}/21 days resolvable")

    section("2. DATED THRESHOLD ladder — bitcoin-above-NNk-on-<date>")
    for back in range(0, 12):
        d = today - dt.timedelta(days=back)
        got = []
        for k in [58, 60, 62, 64, 66]:
            slug = f"bitcoin-above-{k}k-on-{MONTHS[d.month-1]}-{d.day}-{d.year}"
            r = get(f"{GAMMA}/markets", {"slug": slug})
            if isinstance(r, list) and r:
                got.append((k, r[0].get("volumeNum"),
                            r[0].get("outcomePrices")))
            time.sleep(0.08)
        print(f"  -{back:>2}d {d}: {len(got)} strikes resolvable  "
              f"{[(g[0], str(g[1])[:8]) for g in got]}")

    section("3. Deep history probe on the hourly dated family (months back)")
    for back in [30, 45, 60, 90, 120, 150, 180, 270, 365]:
        d = today - dt.timedelta(days=back)
        slug = (f"bitcoin-up-or-down-{MONTHS[d.month-1]}-{d.day}-"
                f"{d.year}-7pm-et")
        r = get(f"{GAMMA}/markets", {"slug": slug})
        ok = isinstance(r, list) and r
        extra = ""
        if ok:
            m = r[0]
            extra = (f"closed={m.get('closed')} vol={str(m.get('volumeNum'))[:10]} "
                     f"prices={m.get('outcomePrices')}")
        print(f"  -{back:>4}d {str(d):<12} {'HIT ' if ok else 'miss'} {extra}")
        time.sleep(0.12)

    section("4. If a dated market resolves, what can we get for it?")
    for back in range(1, 15):
        d = today - dt.timedelta(days=back)
        slug = (f"bitcoin-up-or-down-{MONTHS[d.month-1]}-{d.day}-"
                f"{d.year}-7pm-et")
        r = get(f"{GAMMA}/markets", {"slug": slug})
        if not (isinstance(r, list) and r):
            continue
        m = r[0]
        print(f"  using {slug}")
        for k in ("conditionId", "closed", "volumeNum", "liquidityNum",
                  "outcomePrices", "startDate", "endDate", "lastTradePrice",
                  "orderPriceMinTickSize", "umaResolutionStatus"):
            print(f"    {k:<24} {str(m.get(k))[:100]}")
        toks = json.loads(m.get("clobTokenIds") or "[]")
        if toks:
            h = get("https://clob.polymarket.com/prices-history",
                    {"market": toks[0], "interval": "max", "fidelity": 1})
            pts = (h or {}).get("history", [])
            print(f"    prices-history points: {len(pts)}")
            if pts:
                t0, t1 = pts[0]["t"], pts[-1]["t"]
                print(f"      {time.strftime('%Y-%m-%d %H:%M', time.gmtime(t0))}"
                      f" -> {time.strftime('%Y-%m-%d %H:%M', time.gmtime(t1))}"
                      f"  ({(t1-t0)/3600:.1f}h)")
                print(f"      first={pts[:2]}")
                print(f"      last={pts[-2:]}")
        tr = get(f"{DATA}/trades", {"market": m.get("conditionId"),
                                    "limit": 1000})
        print(f"    trades via data-api: "
              f"{len(tr) if isinstance(tr, list) else 'err'}")
        break


if __name__ == "__main__":
    main()

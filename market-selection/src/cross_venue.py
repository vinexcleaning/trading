"""STANDING BACKLOG #3 — the same event on two venues.

For MLB games listed on BOTH Kalshi and Polymarket, measure the executable
price gap and both cost bars.

MATCHING. Kalshi names teams by CITY (`yes_sub_title` = "Seattle", title =
"Detroit vs Seattle Winner?"). Polymarket names them by full franchise
("Arizona Diamondbacks vs. Cleveland Guardians") and encodes the fixture in the
event ticker (`mlb-ari-cle-2026-08-02`). A first version keyed on nicknames and
matched 0 of 76 -- reported here rather than silently fixed, because a join that
matches nothing looks identical to two venues that share no events.

The join is: {franchise code pair} + game date, both sides. Exact, not fuzzy.
Every market that fails to join is counted and reported.

PRICES ARE EXECUTABLE, NEVER MIDS (GUARDS #7). Kalshi's YES ask is
1 - (best NO bid), read from `orderbook_fp`. Polymarket's is the best ask on
that team's own token, read from the CLOB `/book` endpoint, so the side is
unambiguous -- gamma's `bestBid`/`bestAsk` do not say which outcome they
describe, and guessing would be exactly the kind of sign error that made
LEDGER W015 report a fee fit of 0.96.

Read-only, public endpoints. No credentials.
"""
import json
import os
import re
import sys
import time
from collections import defaultdict

import requests

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "common"))
import kalshi_api as K  # noqa: E402
import costbar  # noqa: E402

ROOT = os.path.join(os.path.dirname(__file__), "..")
REP = os.path.join(ROOT, "reports")
GAMMA = "https://gamma-api.polymarket.com"
CLOB = "https://clob.polymarket.com"
UA = {"User-Agent": "market-selection-research/1.0"}

# franchise code -> (city forms, nickname, polymarket 3-letter)
TEAMS = {
    "ARI": (["arizona"], "diamondbacks", "ari"), "ATL": (["atlanta"], "braves", "atl"),
    "BAL": (["baltimore"], "orioles", "bal"), "BOS": (["boston"], "red sox", "bos"),
    # Kalshi truncates two-team cities in its titles: "Los Angeles D",
    # "Chicago WS", "Chicago C". A first pass without these forms dropped 30 of
    # 76 markets as unparseable.
    "CHC": (["chicago cubs", "chicago c", "cubs"], "cubs", "chc"),
    "CWS": (["chicago white sox", "chicago ws", "white sox"], "white sox", "cws"),
    "CIN": (["cincinnati"], "reds", "cin"), "CLE": (["cleveland"], "guardians", "cle"),
    "COL": (["colorado"], "rockies", "col"), "DET": (["detroit"], "tigers", "det"),
    "HOU": (["houston"], "astros", "hou"), "KC": (["kansas city"], "royals", "kc"),
    "LAA": (["los angeles angels", "los angeles a", "anaheim", "la angels"], "angels", "laa"),
    "LAD": (["los angeles dodgers", "los angeles d", "la dodgers"], "dodgers", "lad"),
    "MIA": (["miami"], "marlins", "mia"), "MIL": (["milwaukee"], "brewers", "mil"),
    "MIN": (["minnesota"], "twins", "min"),
    "NYM": (["new york mets", "new york m", "ny mets"], "mets", "nym"),
    "NYY": (["new york yankees", "new york y", "ny yankees"], "yankees", "nyy"),
    "ATH": (["athletics", "oakland", "sacramento"], "athletics", "ath"),
    "PHI": (["philadelphia"], "phillies", "phi"), "PIT": (["pittsburgh"], "pirates", "pit"),
    "SD": (["san diego"], "padres", "sd"), "SF": (["san francisco"], "giants", "sf"),
    "SEA": (["seattle"], "mariners", "sea"), "STL": (["st. louis", "st louis"], "cardinals", "stl"),
    "TB": (["tampa bay"], "rays", "tb"), "TEX": (["texas"], "rangers", "tex"),
    "TOR": (["toronto"], "blue jays", "tor"), "WSH": (["washington"], "nationals", "wsh"),
}
POLY3 = {v[2]: k for k, v in TEAMS.items()}
MONTHS = {m: i + 1 for i, m in enumerate(
    ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"])}


def franchises(text):
    """Franchise codes named in a string. City forms first (longest match wins),
    nickname as a fallback."""
    t = " " + re.sub(r"[^a-z ]", " ", (text or "").lower()) + " "
    hits = set()
    for code, (cities, nick, _) in TEAMS.items():
        for c in sorted(cities, key=len, reverse=True):
            if f" {c} " in t or t.strip().startswith(c) or f" {c}" in t:
                hits.add(code)
                break
        else:
            if f" {nick} " in t or nick in t:
                hits.add(code)
    return hits


def kalshi_games():
    r = K.get("/markets", {"series_ticker": "KXMLBGAME", "status": "open",
                           "limit": 1000})
    out = []
    if r is None or r.status_code != 200:
        return out
    for m in r.json().get("markets", []):
        tk = m["ticker"]
        mm = re.match(r"KXMLBGAME-(\d\d)([A-Z]{3})(\d\d)", tk)
        if not mm:
            continue
        yy, mon, dd = mm.groups()
        date = f"20{yy}-{MONTHS[mon]:02d}-{int(dd):02d}"
        pair = franchises(m.get("title"))
        yes = franchises(m.get("yes_sub_title"))
        if len(pair) != 2 or len(yes) != 1:
            out.append({"ticker": tk, "bad": True, "title": m.get("title"),
                        "yes_sub": m.get("yes_sub_title")})
            continue
        yes_bids, no_bids = K.orderbook(tk)
        yb, ya, bsz, asz = K.touch(yes_bids or [], no_bids or [])
        out.append({"ticker": tk, "date": date, "pair": frozenset(pair),
                    "yes": next(iter(yes)), "yes_bid_c": yb, "yes_ask_c": ya,
                    "bid_sz": bsz, "ask_sz": asz, "bad": False,
                    "title": m.get("title")})
    return out


def poly_games():
    """MLB game events, keyed by (date, franchise pair), with CLOB token ids."""
    out = {}
    for off in range(0, 600, 100):
        try:
            r = requests.get(GAMMA + "/events",
                             {"limit": 100, "offset": off, "closed": "false",
                              "tag_slug": "mlb", "order": "startDate",
                              "ascending": "true"}, headers=UA, timeout=45)
        except requests.RequestException:
            break
        if r.status_code != 200:
            break
        batch = r.json()
        if not batch:
            break
        for e in batch:
            tick = e.get("ticker") or ""
            mm = re.match(r"mlb-([a-z]{2,3})-([a-z]{2,3})-(\d{4}-\d\d-\d\d)$", tick)
            if not mm:
                continue
            a, b, date = mm.groups()
            if a not in POLY3 or b not in POLY3:
                continue
            pair = frozenset({POLY3[a], POLY3[b]})
            # the moneyline market is the one whose question is exactly "X vs. Y"
            for m in (e.get("markets") or []):
                q = m.get("question") or ""
                if " vs. " not in q or ":" in q or q.lower().startswith("spread"):
                    continue
                try:
                    outs = json.loads(m.get("outcomes") or "[]")
                    toks = json.loads(m.get("clobTokenIds") or "[]")
                except json.JSONDecodeError:
                    continue
                if len(outs) != 2 or len(toks) != 2:
                    continue
                out[(date, pair)] = {
                    "slug": m.get("slug"), "event": tick, "question": q,
                    "outcomes": outs, "tokens": toks,
                    "accepting": m.get("acceptingOrders"),
                    "tick": m.get("orderPriceMinTickSize"),
                }
                break
        time.sleep(0.3)
        if len(batch) < 100:
            break
    return out


def clob_book(token):
    """Executable book for one Polymarket token. Returns (best_bid_c, best_ask_c,
    bid_sz, ask_sz)."""
    try:
        r = requests.get(CLOB + "/book", {"token_id": token}, headers=UA,
                         timeout=30)
    except requests.RequestException:
        return (None,) * 4
    time.sleep(0.2)
    if r.status_code != 200:
        return (None,) * 4
    d = r.json() or {}
    bids = d.get("bids") or []
    asks = d.get("asks") or []
    def best(levels, hi):
        if not levels:
            return None, None
        f = max(levels, key=lambda x: float(x["price"])) if hi else \
            min(levels, key=lambda x: float(x["price"]))
        return float(f["price"]) * 100.0, float(f["size"])
    bb, bsz = best(bids, True)
    ba, asz = best(asks, False)
    return bb, ba, bsz, asz


def main():
    print("Kalshi KXMLBGAME with executable books ...", flush=True)
    kal = kalshi_games()
    bad = [k for k in kal if k["bad"]]
    kal = [k for k in kal if not k["bad"]]
    print(f"  {len(kal)} parsed, {len(bad)} unparseable")
    for b in bad[:4]:
        print(f"    unparsed: {b['ticker']}  title={b['title']!r} "
              f"yes={b['yes_sub']!r}")

    print("Polymarket MLB game events ...", flush=True)
    pol = poly_games()
    print(f"  {len(pol)} game events with a moneyline market")

    rows, nojoin = [], 0
    for k in kal:
        if k["yes_bid_c"] is None or k["yes_ask_c"] is None:
            continue
        p = pol.get((k["date"], k["pair"]))
        if not p or not p["accepting"]:
            nojoin += 1
            continue
        # pick the token for the SAME team Kalshi's YES refers to
        want = k["yes"]
        idx = None
        for i, name in enumerate(p["outcomes"]):
            if want in franchises(name):
                idx = i
                break
        if idx is None:
            nojoin += 1
            continue
        pb, pa, pbs, pas = clob_book(p["tokens"][idx])
        if pb is None or pa is None:
            nojoin += 1
            continue
        k_mid, p_mid = (k["yes_bid_c"] + k["yes_ask_c"]) / 2, (pb + pa) / 2
        # executable both ways: buy the cheaper ask, sell the richer bid
        cross = max(pb - k["yes_ask_c"], k["yes_bid_c"] - pa)
        px = int(min(max(round(k_mid), 1), 99))
        fee = (float(costbar.kalshi_fee_cents(px))
               + float(costbar.poly_fee_cents(px)))
        rows.append({
            "date": k["date"], "game": "/".join(sorted(k["pair"])),
            "yes_team": want, "kalshi": k["ticker"], "poly": p["slug"],
            "k_bid": k["yes_bid_c"], "k_ask": k["yes_ask_c"],
            "k_spread": round(k["yes_ask_c"] - k["yes_bid_c"], 2),
            "p_bid": round(pb, 2), "p_ask": round(pa, 2),
            "p_spread": round(pa - pb, 2),
            "mid_gap_c": round(k_mid - p_mid, 2),
            "abs_mid_gap_c": round(abs(k_mid - p_mid), 2),
            "cross_gross_c": round(cross, 2),
            "two_venue_fee_c": round(fee, 3),
            "cross_net_c": round(cross - fee, 2),
            "k_bid_sz": k["bid_sz"], "k_ask_sz": k["ask_sz"],
            "p_bid_sz": pbs, "p_ask_sz": pas,
        })

    rows.sort(key=lambda r: -r["abs_mid_gap_c"])
    with open(os.path.join(REP, "cross_venue_mlb.json"), "w",
              encoding="utf-8") as fh:
        json.dump(rows, fh, indent=1)
    print(f"\nmatched pairs: {len(rows)}   failed to join: {nojoin}")
    if not rows:
        print("nothing matched")
        return

    g = sorted(r["abs_mid_gap_c"] for r in rows)
    n = len(g)
    ks = sorted(r["k_spread"] for r in rows)
    ps = sorted(r["p_spread"] for r in rows)
    print(f"\nunit of observation: one MLB game side, n={n}")
    print(f"|mid gap| cents      median {g[n//2]:.2f}  p75 {g[int(n*.75)]:.2f}  "
          f"p90 {g[min(int(n*.9),n-1)]:.2f}  max {g[-1]:.2f}")
    print(f"Kalshi spread     median {ks[n//2]:.2f}  p90 {ks[min(int(n*.9),n-1)]:.2f}")
    print(f"Polymarket spread median {ps[n//2]:.2f}  p90 {ps[min(int(n*.9),n-1)]:.2f}")
    prof = [r for r in rows if r["cross_net_c"] > 0]
    print(f"\nexecutable cross-venue trips NET POSITIVE after both fees: "
          f"{len(prof)} of {n}")
    print(f"\n{'date':11s} {'game':9s} {'yes':4s} {'k_bid':>6s} {'k_ask':>6s} "
          f"{'p_bid':>6s} {'p_ask':>6s} {'midgap':>7s} {'gross':>6s} {'net':>6s}")
    for r in rows[:30]:
        print(f"{r['date']:11s} {r['game']:9s} {r['yes_team']:4s} "
              f"{r['k_bid']:6.1f} {r['k_ask']:6.1f} {r['p_bid']:6.2f} "
              f"{r['p_ask']:6.2f} {r['mid_gap_c']:7.2f} "
              f"{r['cross_gross_c']:6.2f} {r['cross_net_c']:6.2f}")
    print("\nwrote reports/cross_venue_mlb.json")


if __name__ == "__main__":
    main()

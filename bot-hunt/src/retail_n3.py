"""R1's N3 arm, run on DAY ONE: does the RETAIL book disagree with the SHARP one?

`PREREGISTRATION_RETAIL.md` §7 names this measurement and names it as the reason
to run R1 at all:

    "What would genuinely surprise me, and is the reason to run it: Bovada
    disagreeing with Pinnacle by more than the cost bar on the same games. That
    would mean the retail book carries information the sharp one does not -- and
    it is measurable on day one, before any settlement, because N3 runs both
    arms on the same games."

**No settled outcome is used or needed here, so nothing in this script can be a
result-dependent choice.** It is a pure agreement measurement between two live
price feeds, plus Kalshi's live ask for the cost bar.

WHY IT IS A KILL-TEST AND NOT A FISHING TRIP
--------------------------------------------
R1's whole premise is that a soft book with a fat margin knows something the
tight one does not. If, after each book's own margin is stripped out, the two
land on the SAME fair value, then Bovada's fat margin is just a fat margin -- it
is the retail book charging more for the same opinion -- and R1 cannot work no
matter how many games accrue. That is `PREREGISTRATION_RETAIL.md` §6's spirit:
say it early and cheaply rather than after a fortnight of accrual.

THE CONFOUND THAT MATTERS MOST, HANDLED FIRST
----------------------------------------------
Two books quoted at different MINUTES will disagree simply because the market
moved. That would manufacture exactly the finding under test. So all three feeds
are pulled back to back in one pass and **the spread of fetch times is printed
next to the result**. A disagreement is only interesting if it is larger than
what a couple of minutes of drift can explain.

⚠ AND THE FIELD-NAME TRAP, FOR THE FOURTH TIME THIS WEEK
---------------------------------------------------------
Bovada's competitor objects use `name`, NOT `description`. Reading the wrong one
returns None for every team, joins nothing, and produces a confident "0%
coverage -- route dead". That has now happened three times in this repo in one
week (C024, M024, and my own first pass at the census). So this script ASSERTS a
non-empty join at each stage and dies loudly rather than reporting an absence.
"""
from __future__ import annotations

import json
import time
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(ROOT.parent))
import venues as V  # noqa: E402
from common.kalshi_fees import fee_rate_cents  # noqa: E402

REP = ROOT / "reports"
BOV_BASE = "https://www.bovada.lv/services/sports/event/coupon/events/A/description/"
BOVADA = BOV_BASE + "baseball/mlb"
# the control: a coupon on the SAME host that must be populated if we have
# access at all. See bovada_available() for why this is not optional.
CONTROL = BOV_BASE + "football/nfl"
PIN = "https://guest.api.arcadia.pinnacle.com/0.1/sports/3"

# same map as devig_where.py -- Kalshi ticker suffix to club name.
CLUB = {
    "ATH": "Athletics", "ATL": "Atlanta Braves", "AZ": "Arizona Diamondbacks",
    "BAL": "Baltimore Orioles", "BOS": "Boston Red Sox", "CHC": "Chicago Cubs",
    "CIN": "Cincinnati Reds", "CLE": "Cleveland Guardians",
    "COL": "Colorado Rockies", "CWS": "Chicago White Sox",
    "DET": "Detroit Tigers", "HOU": "Houston Astros", "KC": "Kansas City Royals",
    "LAA": "Los Angeles Angels", "LAD": "Los Angeles Dodgers",
    "MIA": "Miami Marlins", "MIL": "Milwaukee Brewers", "MIN": "Minnesota Twins",
    "NYM": "New York Mets", "NYY": "New York Yankees",
    "PHI": "Philadelphia Phillies", "PIT": "Pittsburgh Pirates",
    "SD": "San Diego Padres", "SEA": "Seattle Mariners",
    "SF": "San Francisco Giants", "STL": "St. Louis Cardinals",
    "TB": "Tampa Bay Rays", "TEX": "Texas Rangers", "TOR": "Toronto Blue Jays",
    "WSH": "Washington Nationals",
}
# the join key: the last word of a club name is unique across all 30 clubs
# EXCEPT that "Athletics" has no city. Checked, not assumed -- see verify_key().
NICK = {k: v.split()[-1].lower() for k, v in CLUB.items()}


def verify_key() -> None:
    """A join key that silently collides invents matches. So prove it does not."""
    seen = defaultdict(list)
    for abbr, nick in NICK.items():
        seen[nick].append(abbr)
    dupes = {n: a for n, a in seen.items() if len(a) > 1}
    assert not dupes, f"join key collides: {dupes}"
    assert len(NICK) == 30, f"expected 30 clubs, have {len(NICK)}"


def nick_of(text: str):
    """Which club does a free-text team name refer to? None if unclear."""
    if not text:
        return None
    low = text.lower()
    hits = {n for n in NICK.values() if n in low}
    # "Athletics" is a substring of nothing else; "Sox" appears in two names but
    # the nicknames are "sox" for BOS ("Red Sox") and CWS ("White Sox") -- both
    # end in the same word, so the full two-word tail is used for those.
    if "red sox" in low:
        hits = {"sox_red"}
    elif "white sox" in low:
        hits = {"sox_white"}
    return next(iter(hits)) if len(hits) == 1 else None


# the two Sox share a last word, so give them distinct keys everywhere
NICK["BOS"] = "sox_red"
NICK["CWS"] = "sox_white"


def a2p(american):
    a = float(american)
    return (-a) / ((-a) + 100.0) if a < 0 else 100.0 / (a + 100.0)


def devig(ph, pa):
    """Three margin-removal methods, as pre-registered. Returns {method: (h, a)}."""
    s = ph + pa
    if s <= 0 or ph <= 0 or pa <= 0:
        return {}
    out = {"proportional": (ph / s, pa / s)}

    # power / logarithmic: solve sum(p^k) = 1
    lo, hi = 0.2, 5.0
    for _ in range(80):
        k = (lo + hi) / 2
        if ph ** k + pa ** k > 1:
            lo = k
        else:
            hi = k
    k = (lo + hi) / 2
    t = ph ** k + pa ** k
    out["power"] = (ph ** k / t, pa ** k / t)

    # Shin, solved numerically rather than from a remembered closed form -- a
    # misremembered algebraic identity is a silent error and this is not the
    # place to spend one.
    def shin(z):
        f = lambda p: (np.sqrt(z * z + 4 * (1 - z) * p * p / s) - z) / (2 * (1 - z))
        return f(ph), f(pa)
    lo, hi = 1e-9, 0.4999
    for _ in range(80):
        z = (lo + hi) / 2
        if sum(shin(z)) > 1:
            lo = z
        else:
            hi = z
    out["shin"] = shin((lo + hi) / 2)
    return out


def bovada_available():
    """Is Bovada's MLB board populated, or is it 200-with-an-empty-array?

    ⚠ MEASURED 2026-08-14 06:00 UTC AND IT IS THE NASTIEST FAILURE SHAPE HERE.
    Bovada answered `baseball/mlb` with **HTTP 200 and a 2-byte body, `[]`** for
    twenty minutes -- no error, no 429, no redirect. Read naively that is
    "Bovada lists no MLB games", which is one sentence away from "the retail
    route is dead", and it would have been WRONG: Pinnacle listed twelve MLB
    games starting the same day.

    The discriminator is a CONTROL ENDPOINT on the same host in the same second:

        baseball/mlb    200,         2 bytes,   0 events
        football/nfl    200,   625,438 bytes,  17 events
        tennis          200, 1,926,596 bytes, 160 events

    So the connection is fine and we are not blocked -- that particular coupon
    is genuinely empty at that hour. **An empty payload is only evidence of an
    empty board once a control endpoint on the same host has returned a full
    one.** Without that check, absence of data and absence of access look
    identical, and this repo has now manufactured three false absences that way.
    """
    r = V.get(BOVADA, pace=0.5, tries=2, timeout=30)
    if r is not None and r.status_code == 200 and len(r.content) > 2000:
        return "POPULATED", r
    c = V.get(CONTROL, pace=0.5, tries=1, timeout=30)
    ok = c is not None and c.status_code == 200 and len(c.content) > 100_000
    return ("EMPTY BOARD" if ok else "NO ACCESS - do not read as absence"), r


def fetch_bovada(resp=None):
    r = resp if resp is not None else V.get(BOVADA, pace=0.5, tries=2, timeout=30)
    ts = datetime.now(timezone.utc)
    assert r is not None and r.status_code == 200, f"bovada HTTP {r and r.status_code}"
    d = r.json()
    games = {}
    for grp in d:
        for e in (grp.get("events") or []):
            comps = e.get("competitors") or []
            # ⚠ `name`, not `description`. See the module docstring.
            home = next((c.get("name") for c in comps if c.get("home")), None)
            away = next((c.get("name") for c in comps if not c.get("home")), None)
            nh, na = nick_of(home), nick_of(away)
            if not nh or not na or nh == na:
                continue
            for dg in (e.get("displayGroups") or []):
                for m in (dg.get("markets") or []):
                    if m.get("description") != "Moneyline":
                        continue
                    per = m.get("period") or {}
                    if not per.get("main"):
                        continue
                    px = {}
                    for o in (m.get("outcomes") or []):
                        k = nick_of(o.get("description"))
                        am = ((o.get("price") or {}).get("american") or "").strip()
                        if k and am and am not in ("EVEN",):
                            px[k] = float(am.replace("+", ""))
                    if nh in px and na in px:
                        games[frozenset((nh, na))] = {
                            "home": nh, "away": na, "ph": a2p(px[nh]),
                            "pa": a2p(px[na]), "am_h": px[nh], "am_a": px[na],
                            "start": e.get("startTime")}
    return games, ts


def fetch_pinnacle():
    mus = V.get(f"{PIN}/matchups", pace=0.3, tries=2, timeout=30)
    mk = V.get(f"{PIN}/markets/straight", pace=0.3, tries=2, timeout=30)
    ts = datetime.now(timezone.utc)
    assert mus is not None and mus.status_code == 200, "pinnacle matchups failed"
    assert mk is not None and mk.status_code == 200, "pinnacle markets failed"
    meta = {}
    for m in mus.json():
        lg = (m.get("league") or {})
        if (lg.get("name") if isinstance(lg, dict) else None) != "MLB":
            continue
        if m.get("isLive") or m.get("parentId"):
            continue          # live prices and derivative books are a different question
        parts = m.get("participants") or []
        h = next((p.get("name") for p in parts if p.get("alignment") == "home"), None)
        a = next((p.get("name") for p in parts if p.get("alignment") == "away"), None)
        nh, na = nick_of(h), nick_of(a)
        if nh and na and nh != na:
            meta[m.get("id")] = {"home": nh, "away": na, "start": m.get("startTime")}
    games = {}
    for m in mk.json():
        mid = m.get("matchupId")
        if mid not in meta or m.get("type") != "moneyline" or m.get("period") != 0:
            continue
        px = {p.get("designation"): p.get("price") for p in (m.get("prices") or [])}
        if px.get("home") is None or px.get("away") is None:
            continue
        g = meta[mid]
        games[frozenset((g["home"], g["away"]))] = {
            "home": g["home"], "away": g["away"], "ph": a2p(px["home"]),
            "pa": a2p(px["away"]), "am_h": px["home"], "am_a": px["away"],
            "start": g["start"]}
    return games, ts


def fetch_kalshi():
    mkts = list(V.k_paginate("/markets", {"series_ticker": "KXMLBGAME",
                                          "status": "open", "limit": 200},
                             "markets", max_pages=8))
    ev = defaultdict(list)
    for m in mkts:
        tk = m.get("ticker") or ""
        abbr = tk.rsplit("-", 1)[-1]
        if abbr in NICK:
            ev[m.get("event_ticker")].append((tk, NICK[abbr], m.get("close_time")))
    games, ts = {}, None
    for e, rows in ev.items():
        if len(rows) != 2:
            continue
        key = frozenset(r[1] for r in rows)
        if len(key) != 2:
            continue
        sides = {}
        for tk, nick, ct in rows:
            ylv, nlv = V.k_orderbook(tk)
            yb, ya, bs, asz = V.k_touch(ylv, nlv)
            sides[nick] = {"ticker": tk, "bid": yb, "ask": ya, "ask_size": asz}
        games[key] = {"sides": sides, "event": e}
        ts = datetime.now(timezone.utc)
    return games, ts or datetime.now(timezone.utc)


def main() -> None:
    verify_key()
    REP.mkdir(parents=True, exist_ok=True)
    print("=" * 78)
    print("N3 DAY-ONE ARM — does the RETAIL book disagree with the SHARP book?")
    print("=" * 78)
    print("No settled games are used. This is an agreement measurement between")
    print("two live price feeds, with Kalshi's live ask only to price the cost bar.\n")

    # --wait N : poll up to N minutes for Bovada's MLB board to populate. The
    # board was measured empty at 2am ET with games listed elsewhere, so the
    # hour matters and guessing it wastes a day per guess.
    wait_min = 0
    if "--wait" in sys.argv:
        wait_min = int(sys.argv[sys.argv.index("--wait") + 1])
    deadline = time.time() + wait_min * 60
    while True:
        state, resp = bovada_available()
        print(f"   Bovada MLB board: {state}"
              f"   ({datetime.now(timezone.utc):%H:%M:%SZ})", flush=True)
        if state == "POPULATED" or time.time() >= deadline:
            break
        # ⚠ 20 MINUTES, NOT 5, AND THE REASON IS MEASURED. After ~15 fetches in
        # a few minutes Bovada stopped serving the CONTROL endpoint too -- i.e.
        # we had made ourselves the problem. Polling a host that has just gone
        # quiet, faster, is how a temporary throttle becomes a permanent block,
        # and a blocked host would then look exactly like a dead route.
        time.sleep(1200)
    if state != "POPULATED":
        print("\n   Bovada's MLB board never populated inside the wait window.")
        print("   ⚠ THAT IS AN APPARATUS RESULT, NOT A FINDING. It says nothing")
        print("   about whether the retail book disagrees with the sharp one.")
        return

    bov, t_b = fetch_bovada(resp)
    pin, t_p = fetch_pinnacle()
    kal, t_k = fetch_kalshi()
    spread = (max(t_b, t_p, t_k) - min(t_b, t_p, t_k)).total_seconds()
    print(f"   Bovada games with a two-sided main moneyline : {len(bov)}")
    print(f"   Pinnacle MLB pre-match moneylines            : {len(pin)}")
    print(f"   Kalshi open events with both clubs resolved  : {len(kal)}")
    print(f"   ⚠ all three feeds pulled within              : {spread:.0f} seconds")
    assert bov, "Bovada join produced ZERO games -- check competitors[].name"
    assert pin, "Pinnacle join produced ZERO games"

    both = sorted(set(bov) & set(pin), key=lambda k: sorted(k))
    tri = [k for k in both if k in kal]
    print(f"\n   Bovada ∩ Pinnacle                            : {len(both)}")
    print(f"   Bovada ∩ Pinnacle ∩ Kalshi                   : {len(tri)}")
    if not both:
        print("\n   NOTHING JOINS. That is an apparatus result, not a finding.")
        return

    # ---------------- the measurement -------------------------------------
    print("\n" + "-" * 78)
    print("PER GAME — de-vigged fair value, retail vs sharp, in cents")
    print("-" * 78)
    print(f"   {'game':22} {'margin_B':>8} {'margin_P':>8} "
          f"{'B_fair':>7} {'P_fair':>7} {'diff':>7} {'bar':>6}  verdict")

    rows, diffs_by_method = [], defaultdict(list)
    for key in both:
        b, p = bov[key], pin[key]
        # orient both books onto the SAME side before comparing anything
        side = b["home"]
        pb_raw = b["ph"] if b["home"] == side else b["pa"]
        pp_raw = p["ph"] if p["home"] == side else p["pa"]
        ob_raw = b["pa"] if b["home"] == side else b["ph"]
        op_raw = p["pa"] if p["home"] == side else p["ph"]
        mb, mp = 100 * (pb_raw + ob_raw - 1), 100 * (pp_raw + op_raw - 1)
        fb, fp = devig(pb_raw, ob_raw), devig(pp_raw, op_raw)
        if not fb or not fp:
            continue
        for meth in ("proportional", "power", "shin"):
            diffs_by_method[meth].append(100 * (fb[meth][0] - fp[meth][0]))

        bfair = 100 * fb["power"][0]
        pfair = 100 * fp["power"][0]
        diff = bfair - pfair

        ask = None
        if key in kal:
            s = kal[key]["sides"].get(side)
            ask = s and s.get("ask")
        bar = float(fee_rate_cents(ask)) if ask else float(fee_rate_cents(bfair))
        verdict = "clears bar" if abs(diff) > bar else "inside the bar"
        rows.append({"game": "/".join(sorted(key)), "margin_bovada": mb,
                     "margin_pinnacle": mp, "bovada_fair_c": bfair,
                     "pinnacle_fair_c": pfair, "diff_c": diff,
                     "kalshi_ask_c": ask, "bar_c": bar,
                     "clears": abs(diff) > bar})
        print(f"   {'/'.join(sorted(key))[:22]:22} {mb:>7.2f} {mp:>7.2f} "
              f"{bfair:>7.2f} {pfair:>7.2f} {diff:>+7.2f} {bar:>6.2f}  {verdict}")

    d = np.array([r["diff_c"] for r in rows])
    ad = np.abs(d)
    print("\n" + "=" * 78)
    print("THE ANSWER")
    print("=" * 78)
    print(f"   games compared                       : {len(d)}")
    print(f"   Bovada's margin, median              : {np.median([r['margin_bovada'] for r in rows]):.2f} out of 100")
    print(f"   Pinnacle's margin, median            : {np.median([r['margin_pinnacle'] for r in rows]):.2f} out of 100")
    print(f"   |retail fair − sharp fair|  median   : {np.median(ad):.2f}c")
    print(f"                               p90      : {np.percentile(ad, 90):.2f}c")
    print(f"                               MAX      : {ad.max():.2f}c")
    print(f"   median cost bar                      : {np.median([r['bar_c'] for r in rows]):.2f}c")
    n_clear = sum(r["clears"] for r in rows)
    print(f"   games where the gap CLEARS the bar   : {n_clear} of {len(rows)} "
          f"({100*n_clear/max(1,len(rows)):.1f}%)")
    print(f"   mean signed difference               : {d.mean():+.2f}c "
          f"(a bias means one book is systematically higher on the home side)")

    print("\n   Method disagreement — if the three disagree in SIGN, §6 stops R1:")
    for meth, v in diffs_by_method.items():
        v = np.array(v)
        print(f"      {meth:14} mean {v.mean():+6.2f}c   median {np.median(v):+6.2f}c   "
              f"share positive {100*np.mean(v > 0):5.1f}%")

    out = {"pulled_utc": t_b.strftime("%Y-%m-%dT%H:%M:%SZ"),
           "feed_spread_seconds": spread, "n_bovada": len(bov),
           "n_pinnacle": len(pin), "n_kalshi": len(kal), "n_joined": len(rows),
           "rows": rows,
           "method_means_c": {k: float(np.mean(v)) for k, v in diffs_by_method.items()}}
    (REP / "retail_n3_dayone.json").write_text(json.dumps(out, indent=1),
                                               encoding="utf-8")
    print("\n   wrote reports/retail_n3_dayone.json")


if __name__ == "__main__":
    main()

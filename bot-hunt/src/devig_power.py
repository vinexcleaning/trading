"""How many MLB events until H11 is testable? Measures `q`, and NOTHING else.

Run AFTER PREREGISTRATION_DEVIG.md was committed (d163484). The design is fixed;
this only fills in the one number section 9 left blank: the QUALIFYING RATE,

    q = P(an event produces an entry) = events where edge > cost / events joined

`q` is a property of the two venues' price disagreement and the fee schedule. It
contains no outcome information, and this script never opens a settlement field.
There is no `result`, no `y`, no P&L anywhere in it. The panel it builds is the
same panel Stage B will use, so the count is the real one and not a proxy.

Everything is done by the pre-registered rules:
  * join on EXACT game start from the ticker, club names as confirmation
  * one-to-one matchup <-> event
  * disjointness boundary: no game starting before 2026-08-05T00:00:00Z
  * anchor windows measured from the ticker start, never from close_time
  * cost = fee(ask) + slippage, fee from common/kalshi_fees.py only
  * worst_case de-vig primary
  * Pinnacle isLive observations discarded
"""
from __future__ import annotations

import json
import re
import sqlite3
import sys
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT.parent))
from common.kalshi_fees import fee_rate_cents  # noqa: E402

DB = ROOT / "data" / "record.db"
REP = ROOT / "reports"
TS = "%Y-%m-%dT%H:%M:%SZ"
ET = ZoneInfo("America/New_York")
MON = {m: i + 1 for i, m in enumerate(
    "JAN FEB MAR APR MAY JUN JUL AUG SEP OCT NOV DEC".split())}
PAT = re.compile(r"^KXMLBGAME-(\d{2})([A-Z]{3})(\d{2})(\d{2})(\d{2})")

# PREREGISTRATION_DEVIG.md section 3.3. The control set's latest game start is
# 2026-08-04T23:40:00Z; nothing at or before this boundary may enter H11.
DISJOINT_FROM = datetime(2026, 8, 5, tzinfo=timezone.utc)

ANCHORS = {"24h": timedelta(hours=24), "6h": timedelta(hours=6),
           "2h": timedelta(hours=2)}
BUFFER = timedelta(minutes=30)
SLIPPAGES = [0.0, 0.5, 1.0, 2.0]
STOPW = re.compile(r"\b(the|of)\b")

# AMENDMENT D1 to PREREGISTRATION_DEVIG.md section 3.2, made 2026-08-06 BEFORE
# any settlement was joined and for RECALL ONLY -- it can add matched events, it
# can never change which of a matched event's quotes fire.
#
# Section 3.2 confirmed the start-time key with a contained-substring test on
# club names and a length floor of 4. That floor is exactly what the Polymarket
# join needed to stop "A Team" normalising to "a" and swallowing a quarter of
# the sample -- and here it drops the Athletics, because Kalshi writes "A's",
# which normalises to "a s" (length 3) and can never reach "athletics".
# 5 of 53 events were lost to it.
#
# The fix is not a looser fuzzy match. Kalshi's MARKET TICKER ends in a
# canonical 2-3 letter club code and there are exactly 30 of them, so the map
# below is an EXACT key with no similarity test anywhere in it. It also removes
# a phantom the name test could not see: Pinnacle's MLB league carries
# aggregate props named "Home Runs (15 Games)" / "Away Runs (15 Games)", which
# are matchups with participant names, and no club code can ever match them.
CLUB = {
    "ATH": "Athletics",             "ATL": "Atlanta Braves",
    "AZ": "Arizona Diamondbacks",   "BAL": "Baltimore Orioles",
    "BOS": "Boston Red Sox",        "CHC": "Chicago Cubs",
    "CIN": "Cincinnati Reds",       "CLE": "Cleveland Guardians",
    "COL": "Colorado Rockies",      "CWS": "Chicago White Sox",
    "DET": "Detroit Tigers",        "HOU": "Houston Astros",
    "KC": "Kansas City Royals",     "LAA": "Los Angeles Angels",
    "LAD": "Los Angeles Dodgers",   "MIA": "Miami Marlins",
    "MIL": "Milwaukee Brewers",     "MIN": "Minnesota Twins",
    "NYM": "New York Mets",         "NYY": "New York Yankees",
    "PHI": "Philadelphia Phillies", "PIT": "Pittsburgh Pirates",
    "SD": "San Diego Padres",       "SEA": "Seattle Mariners",
    "SF": "San Francisco Giants",   "STL": "St. Louis Cardinals",
    "TB": "Tampa Bay Rays",         "TEX": "Texas Rangers",
    "TOR": "Toronto Blue Jays",     "WSH": "Washington Nationals",
}


def norm(s):
    if not s:
        return ""
    s = STOPW.sub(" ", s.lower())
    s = re.sub(r"[^a-z0-9 ]+", " ", s)
    return " ".join(s.split())


def ticker_start(tk):
    m = PAT.match(tk)
    if not m:
        return None
    yy, mon, dd, hh, mi = m.groups()
    try:
        return datetime(2000 + int(yy), MON[mon], int(dd), int(hh), int(mi),
                        tzinfo=ET).astimezone(timezone.utc)
    except (ValueError, KeyError):
        return None


def american_to_prob(a):
    a = float(a)
    return (-a) / ((-a) + 100.0) if a < 0 else 100.0 / (a + 100.0)


def devig(ph, pa):
    s = ph + pa
    if s <= 0:
        return {}
    out = {"multiplicative": (ph / s, pa / s)}
    lo, hi = 0.2, 5.0
    for _ in range(60):
        k = (lo + hi) / 2
        if ph ** k + pa ** k > 1:
            lo = k
        else:
            hi = k
    k = (lo + hi) / 2
    tot = ph ** k + pa ** k
    out["power"] = (ph ** k / tot, pa ** k / tot)
    out["worst_case"] = (min(v[0] for v in out.values()),
                         min(v[1] for v in out.values()))
    return out


def main():
    REP.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(f"file:{DB.as_posix()}?mode=ro", uri=True, timeout=300)
    rep = {"preregistration": "PREREGISTRATION_DEVIG.md @ d163484"}

    # ------------------------------------------------------- Pinnacle side
    pin_meta = {}
    for mid, lg, home, away, st in con.execute(
            "select matchup_id, max(league), max(home), max(away), max(starts_utc) "
            "from pin_matchup where sport='baseball' and league='MLB' "
            "group by matchup_id"):
        if home and away and st:
            pin_meta[mid] = {"home": home, "away": away, "starts": st}

    # isLive is per-observation, so the liveness filter is applied at quote
    # level, not matchup level: the same matchup is pre-match and then live.
    live_ts = defaultdict(set)
    for mid, ts in con.execute(
            "select matchup_id, ts_utc from pin_matchup "
            "where sport='baseball' and live=1"):
        live_ts[mid].add(ts)

    pin_q = defaultdict(dict)
    for mid, ts, desig, price in con.execute(
            "select matchup_id, ts_utc, designation, price_american from pin_market "
            "where sport='baseball' and market_type='moneyline' and period=0 "
            "and designation is not null and price_american is not null"):
        if mid in pin_meta and ts not in live_ts.get(mid, ()):
            pin_q[mid].setdefault(ts, {})[desig] = price
    for mid in list(pin_q):
        pin_q[mid] = {t: d for t, d in pin_q[mid].items()
                      if "home" in d and "away" in d}
        if not pin_q[mid]:
            del pin_q[mid]

    by_start = defaultdict(list)
    for mid, m in pin_meta.items():
        if mid in pin_q:
            by_start[m["starts"]].append(mid)

    # --------------------------------------------------------- Kalshi side
    kn = defaultdict(list)
    for tk, ev, sub in con.execute(
            "select ticker, event_ticker, yes_sub_title from k_names "
            "where series='KXMLBGAME'"):
        if sub:
            kn[ev].append((tk, sub))

    # ------------------------------------------------------------ the join
    drops = defaultdict(int)
    joined, used_matchup = [], set()
    for ev, tks in sorted(kn.items()):
        if len(tks) != 2:
            drops["kalshi_event_not_two_sided"] += 1
            continue
        st = ticker_start(tks[0][0])
        if st is None:
            drops["ticker_unparseable"] += 1
            continue
        if st < DISJOINT_FROM:
            drops["before_disjointness_boundary"] += 1
            continue
        key = st.strftime(TS)
        cands = [m for m in by_start.get(key, []) if m not in used_matchup]
        if not cands:
            drops["no_pinnacle_matchup_at_that_start"] += 1
            continue
        hit = None
        for mid in cands:
            h, a = norm(pin_meta[mid]["home"]), norm(pin_meta[mid]["away"])
            mp = {}
            for tk, sub in tks:
                # Amendment D1: the club CODE is exact; the displayed name is
                # only a fallback for a code the map does not know, and a code
                # it does not know is a schedule change worth seeing in the
                # drop counts rather than papering over.
                code = tk.rsplit("-", 1)[-1]
                o = norm(CLUB.get(code, sub))
                if not o:
                    continue
                if o == h or (len(o) >= 4 and (o in h or h in o)):
                    mp[tk] = "home"
                elif o == a or (len(o) >= 4 and (o in a or a in o)):
                    mp[tk] = "away"
            if len(mp) == 2 and set(mp.values()) == {"home", "away"}:
                hit = (mid, mp)
                break
        if hit is None:
            drops["club_names_disagree"] += 1
            continue
        used_matchup.add(hit[0])
        joined.append({"event": ev, "start": st, "matchup": hit[0],
                       "map": hit[1],
                       "pin": f"{pin_meta[hit[0]]['home']} vs {pin_meta[hit[0]]['away']}"})

    print(f"== JOIN (pre-registered rules)")
    print(f"   Kalshi MLB events considered : {len(kn)}")
    for k, v in sorted(drops.items(), key=lambda x: -x[1]):
        print(f"      dropped, {k:38} {v}")
    print(f"   JOINED                       : {len(joined)}")
    rep["join"] = {"events_considered": len(kn), "joined": len(joined),
                   "drops": dict(drops)}
    if not joined:
        print("   nothing joined — stop rather than force it")
        return

    # --------------------------------- the panel, and the qualifying gate
    pin_ts_cache = {m: sorted(pin_q[m]) for m in {j["matchup"] for j in joined}}
    pin_dt_cache = {m: [datetime.strptime(t, TS).replace(tzinfo=timezone.utc)
                        for t in v] for m, v in pin_ts_cache.items()}

    results = {}
    edge_pool = defaultdict(list)   # method -> best per-event edge, for context
    for aname, alead in ANCHORS.items():
        for method in ("worst_case", "power", "multiplicative"):
            for slip in SLIPPAGES:
                fired, considered = 0, 0
                both_sides_same_ts = 0
                for j in joined:
                    lo, hi = j["start"] - alead, j["start"] - BUFFER
                    got_any = False
                    fire_ts, fire_sides = None, set()
                    best_edge = None
                    for tk, side in j["map"].items():
                        for ts, ya in con.execute(
                                "select ts_utc, yes_ask_c from k_book where ticker=? "
                                "and yes_ask_c is not null order by ts_utc", (tk,)):
                            kdt = datetime.strptime(ts, TS).replace(tzinfo=timezone.utc)
                            if not (lo <= kdt <= hi):
                                continue
                            pdts = pin_dt_cache[j["matchup"]]
                            if not pdts:
                                continue
                            near = min(range(len(pdts)),
                                       key=lambda i: abs((pdts[i] - kdt).total_seconds()))
                            if abs((pdts[near] - kdt).total_seconds()) > 900:
                                continue
                            got_any = True
                            d = pin_q[j["matchup"]][pin_ts_cache[j["matchup"]][near]]
                            fv = devig(american_to_prob(d["home"]),
                                       american_to_prob(d["away"]))
                            if not fv:
                                continue
                            fh, fa = fv[method]
                            fair = fh if side == "home" else fa
                            edge = 100 * fair - ya
                            cost = float(fee_rate_cents(ya)) + slip
                            if best_edge is None or edge - cost > best_edge:
                                best_edge = edge - cost
                            if edge > cost:
                                if fire_ts is None or ts < fire_ts:
                                    fire_ts, fire_sides = ts, {side}
                                elif ts == fire_ts:
                                    fire_sides.add(side)
                    if got_any:
                        considered += 1
                        if best_edge is not None:
                            edge_pool[(aname, method, slip)].append(best_edge)
                    if fire_ts is not None:
                        if len(fire_sides) == 2:
                            both_sides_same_ts += 1   # discarded per section 2.4
                        else:
                            fired += 1
                q = fired / considered if considered else 0.0
                results[f"{aname}|{method}|{slip}"] = {
                    "events_with_aligned_quotes": considered,
                    "events_firing": fired, "q": round(q, 4),
                    "discarded_both_sides": both_sides_same_ts}

    print("\n== THE QUALIFYING RATE q  (no settlement touched)")
    print(f"   {'anchor':7} {'de-vig':16} {'slip':>5} {'events':>7} {'fire':>5} {'q':>7}")
    for k, v in results.items():
        a, m, s = k.split("|")
        print(f"   {a:7} {m:16} {s:>5} {v['events_with_aligned_quotes']:>7} "
              f"{v['events_firing']:>5} {v['q']:>7.3f}")
    rep["q"] = results

    print("\n== best per-event NET gap (edge - cost), primary cell only")
    key = ("24h", "worst_case", 1.0)
    pool = np.array(edge_pool.get(key, []))
    if len(pool):
        print(f"   n_events={len(pool)}  median {np.median(pool):+.2f}c  "
              f"p75 {np.percentile(pool,75):+.2f}c  p90 {np.percentile(pool,90):+.2f}c  "
              f"max {pool.max():+.2f}c")
        rep["primary_net_gap"] = {
            "n": len(pool), "median": float(np.median(pool)),
            "p90": float(np.percentile(pool, 90)), "max": float(pool.max())}

    # ------------------------------------------------------------- power
    print("\n== EVENTS NEEDED  (section 9 formula, sigma = 100*sqrt(pi(1-pi)))")
    sigma = 50.0
    z = (1.96 + 0.84) ** 2
    qs = {k: v["q"] for k, v in results.items()
          if k.startswith("24h|worst_case|1.0")}
    q_prim = list(qs.values())[0] if qs else 0.0
    print(f"   measured q at the primary cell (-24 h, worst_case, 1.0c slip): "
          f"{q_prim:.3f}")
    rows = []
    for delta in (2.0, 3.0, 5.0, 8.0):
        nt = z * sigma ** 2 / delta ** 2
        ne = nt / q_prim if q_prim > 0 else float("inf")
        rows.append({"delta_c": delta, "n_trades": round(nt),
                     "n_events": None if ne == float("inf") else round(ne),
                     "mlb_days": None if ne == float("inf") else round(ne / 15.0, 1),
                     "mlb_seasons": None if ne == float("inf") else round(ne / 2430.0, 2)})
        print(f"   delta {delta:>4.1f}c -> {nt:>8.0f} trades -> "
              f"{'inf' if ne == float('inf') else f'{ne:>9,.0f}'} events"
              f"{'' if ne == float('inf') else f'  = {ne/15.0:>7,.0f} MLB days = {ne/2430.0:.2f} seasons'}")
    rep["power_stage_b"] = {"sigma_c": sigma, "q_primary": q_prim, "rows": rows}

    print("\n   Stage A (paired Brier) needs sigma_delta, which requires "
          "settlements and is NOT computed here.")

    con.close()
    (REP / "devig_power.json").write_text(json.dumps(rep, indent=1, default=str),
                                          encoding="utf-8")
    print("\nwrote reports/devig_power.json")


if __name__ == "__main__":
    main()

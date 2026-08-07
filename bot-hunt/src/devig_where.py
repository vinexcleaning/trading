"""WHERE, if anywhere, can a de-vig gap clear the cost bar? And is Stage A on track?

Answers three questions asked of SCOREBOARD.md, and CORRECTS AN OVERSTATEMENT OF
MY OWN in RESULTS_DEVIG.md along the way.

Q1  Is the de-vig idea dead on arithmetic, or underpowered?
    RESULTS_DEVIG.md leads with "the cost bar is larger than the entire vig",
    and SCOREBOARD.md restates it as "the cost of trading is bigger than the
    whole margin you're trying to exploit". **That framing is wrong and this
    script is partly here to show why.** The overround is what you STRIP to
    estimate fair value; it does not BOUND the edge. If Kalshi's ask sat 8c
    below Pinnacle's de-vigged fair, the edge would be 8c on a 2pp-overround
    market. What actually kills it is an EMPIRICAL fact -- the two venues agree
    more tightly than the cost bar -- and that is a measurement, not an
    identity. So this measures the agreement directly.

Q2  Stage A (does the sharp price simply FORECAST better than Kalshi's?) needs
    ~440 games. Is it on track? -> the join and settlement census below.

Q3  Is there any market whose bookmaker margin is wide enough to leave room?
    -> the overround census by sport and league. High overround does not
    guarantee a gap, but a market the bookmaker prices lazily is where a gap is
    most likely, so it is the right place to look and the right thing to rank.

Reads the recorder read-only. Settlement is pulled fresh from Kalshi's listing.
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
sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(ROOT.parent))
import venues as V  # noqa: E402
from common.kalshi_fees import fee_rate_cents  # noqa: E402

DB = ROOT / "data" / "record.db"
REP = ROOT / "reports"
TS = "%Y-%m-%dT%H:%M:%SZ"
ET = ZoneInfo("America/New_York")
MON = {m: i + 1 for i, m in enumerate(
    "JAN FEB MAR APR MAY JUN JUL AUG SEP OCT NOV DEC".split())}
PAT = re.compile(r"^KXMLBGAME-(\d{2})([A-Z]{3})(\d{2})(\d{2})(\d{2})")
DISJOINT_FROM = datetime(2026, 8, 5, tzinfo=timezone.utc)

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
STOPW = re.compile(r"\b(the|of)\b")


def norm(s):
    if not s:
        return ""
    s = STOPW.sub(" ", s.lower())
    return " ".join(re.sub(r"[^a-z0-9 ]+", " ", s).split())


def ticker_start(tk):
    m = PAT.match(tk)
    if not m:
        return None
    yy, mo, dd, hh, mi = m.groups()
    try:
        return datetime(2000 + int(yy), MON[mo], int(dd), int(hh), int(mi),
                        tzinfo=ET).astimezone(timezone.utc)
    except (ValueError, KeyError):
        return None


def a2p(a):
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
    t = ph ** k + pa ** k
    out["power"] = (ph ** k / t, pa ** k / t)
    out["worst_case"] = (min(v[0] for v in out.values()),
                         min(v[1] for v in out.values()))
    return out


# ============================== Q3 — the overround census ==================

def overround_census(con, rep):
    print("=" * 74)
    print("Q3  WHERE IS THE BOOKMAKER'S MARGIN WIDE?  (Pinnacle overround)")
    print("=" * 74)
    print("A two-way moneyline's two implied probabilities sum to more than 1.")
    print("That excess IS the margin. Bigger margin = the book is priced less")
    print("competitively = the most likely place for a gap to exist.\n")

    # league per matchup, and its sport
    meta = {}
    for mid, sport, lg in con.execute(
            "select matchup_id, max(sport), max(league) from pin_matchup "
            "group by matchup_id"):
        meta[mid] = (sport, lg)

    by_sport, by_league = defaultdict(list), defaultdict(list)
    cur = con.execute(
        "select matchup_id, ts_utc, designation, price_american from pin_market "
        "where market_type='moneyline' and period=0 and designation is not null "
        "and price_american is not null")
    pend = defaultdict(dict)
    for mid, ts, des, pr in cur:
        pend[(mid, ts)][des] = pr
    for (mid, _ts), d in pend.items():
        if "home" not in d or "away" not in d or mid not in meta:
            continue
        try:
            orr = 100.0 * (a2p(d["home"]) + a2p(d["away"]) - 1.0)
        except (TypeError, ValueError, ZeroDivisionError):
            continue
        if not (-1 < orr < 60):
            continue
        sport, lg = meta[mid]
        by_sport[sport].append(orr)
        if lg:
            by_league[(sport, lg)].append(orr)

    print(f"   {'sport':13} {'quotes':>9} {'median':>8} {'p10':>7} {'p90':>7}")
    srows = {}
    for s, v in sorted(by_sport.items(), key=lambda x: -np.median(x[1])):
        a = np.array(v)
        print(f"   {s:13} {len(a):>9,} {np.median(a):>7.2f}pp "
              f"{np.percentile(a,10):>6.2f} {np.percentile(a,90):>6.2f}")
        srows[s] = {"n": len(a), "median_pp": round(float(np.median(a)), 3),
                    "p90_pp": round(float(np.percentile(a, 90)), 3)}
    rep["overround_by_sport"] = srows

    print(f"\n   Widest LEAGUES with >=200 quotes (this is where to look):")
    print(f"   {'sport':11} {'league':34} {'quotes':>8} {'median':>9}")
    lrows = []
    cand = [(k, v) for k, v in by_league.items() if len(v) >= 200]
    for (s, lg), v in sorted(cand, key=lambda x: -np.median(x[1]))[:14]:
        a = np.array(v)
        print(f"   {s:11} {lg[:33]:34} {len(a):>8,} {np.median(a):>8.2f}pp")
        lrows.append({"sport": s, "league": lg, "n": len(a),
                      "median_pp": round(float(np.median(a)), 3)})
    print(f"\n   TIGHTEST leagues, for contrast:")
    for (s, lg), v in sorted(cand, key=lambda x: np.median(x[1]))[:6]:
        a = np.array(v)
        print(f"   {s:11} {lg[:33]:34} {len(a):>8,} {np.median(a):>8.2f}pp")
    rep["widest_leagues"] = lrows
    return by_sport


# ======================= Q1/Q2 — the MLB join, gap and settlement ==========

def mlb_join(con, rep):
    print("\n" + "=" * 74)
    print("Q1/Q2  MLB — the join, the GAP, and how much has settled")
    print("=" * 74)

    pin_meta, pin_q = {}, defaultdict(dict)
    for mid, lg, h, a, st in con.execute(
            "select matchup_id, max(league), max(home), max(away), max(starts_utc) "
            "from pin_matchup where sport='baseball' and league='MLB' "
            "group by matchup_id"):
        if h and a and st:
            pin_meta[mid] = {"home": h, "away": a, "starts": st}
    live = defaultdict(set)
    for mid, ts in con.execute("select matchup_id, ts_utc from pin_matchup "
                               "where sport='baseball' and live=1"):
        live[mid].add(ts)
    for mid, ts, des, pr in con.execute(
            "select matchup_id, ts_utc, designation, price_american from pin_market "
            "where sport='baseball' and market_type='moneyline' and period=0 "
            "and designation is not null and price_american is not null"):
        if mid in pin_meta and ts not in live.get(mid, ()):
            pin_q[mid].setdefault(ts, {})[des] = pr
    for mid in list(pin_q):
        pin_q[mid] = {t: d for t, d in pin_q[mid].items()
                      if "home" in d and "away" in d}
        if not pin_q[mid]:
            del pin_q[mid]
    by_start = defaultdict(list)
    for mid, m in pin_meta.items():
        if mid in pin_q:
            by_start[m["starts"]].append(mid)

    kn = defaultdict(list)
    for tk, ev, sub in con.execute(
            "select ticker, event_ticker, yes_sub_title from k_names "
            "where series='KXMLBGAME'"):
        if sub:
            kn[ev].append((tk, sub))

    drops = defaultdict(int)
    joined, used = [], set()
    for ev, tks in sorted(kn.items()):
        if len(tks) != 2:
            drops["not_two_sided"] += 1
            continue
        st = ticker_start(tks[0][0])
        if st is None:
            drops["ticker_unparseable"] += 1
            continue
        if st < DISJOINT_FROM:
            drops["before_disjointness_boundary"] += 1
            continue
        cands = [m for m in by_start.get(st.strftime(TS), []) if m not in used]
        if not cands:
            drops["pinnacle_has_not_listed_it_yet"] += 1
            continue
        hit = None
        for mid in cands:
            h, a = norm(pin_meta[mid]["home"]), norm(pin_meta[mid]["away"])
            mp = {}
            for tk, sub in tks:
                o = norm(CLUB.get(tk.rsplit("-", 1)[-1], sub))
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
        used.add(hit[0])
        joined.append({"event": ev, "start": st, "matchup": hit[0], "map": hit[1]})

    print(f"   Kalshi MLB events seen      : {len(kn)}")
    for k, v in sorted(drops.items(), key=lambda x: -x[1]):
        print(f"      dropped, {k:34} {v}")
    print(f"   JOINED                      : {len(joined)}")

    # ---- settlement, pulled fresh (the recorder deliberately stores no outcome)
    print("\n   Pulling settlement for joined events…")
    res = {}
    for m in V.k_paginate("/markets", {"series_ticker": "KXMLBGAME",
                                       "status": "settled", "limit": 200},
                          "markets", max_pages=12):
        if m.get("result") in ("yes", "no"):
            res[m["ticker"]] = m["result"]
    n_settled = sum(1 for j in joined
                    if all(t in res for t in j["map"]))
    print(f"   settled Kalshi MLB markets retrievable : {len(res):,}")
    print(f"   JOINED events with BOTH sides settled  : {n_settled}")

    # ---- the gap distribution, which is the real Q1
    pts = {m: sorted(pin_q[m]) for m in {j["matchup"] for j in joined}}
    pdt = {m: [datetime.strptime(t, TS).replace(tzinfo=timezone.utc) for t in v]
           for m, v in pts.items()}
    gaps, nets, n_obs = [], [], 0
    for j in joined:
        for tk, side in j["map"].items():
            for ts, ya in con.execute(
                    "select ts_utc, yes_ask_c from k_book where ticker=? and "
                    "yes_ask_c is not null order by ts_utc", (tk,)):
                kdt = datetime.strptime(ts, TS).replace(tzinfo=timezone.utc)
                if not (j["start"] - timedelta(hours=24) <= kdt
                        <= j["start"] - timedelta(minutes=30)):
                    continue
                dl = pdt[j["matchup"]]
                if not dl:
                    continue
                i = min(range(len(dl)), key=lambda x: abs((dl[x] - kdt).total_seconds()))
                if abs((dl[i] - kdt).total_seconds()) > 900:
                    continue
                d = pin_q[j["matchup"]][pts[j["matchup"]][i]]
                fv = devig(a2p(d["home"]), a2p(d["away"]))
                if not fv:
                    continue
                fh, fa = fv["worst_case"]
                fair = 100 * (fh if side == "home" else fa)
                n_obs += 1
                gaps.append(abs(fair - ya))
                nets.append(fair - ya - float(fee_rate_cents(ya)) - 1.0)
    rep["mlb"] = {"events_seen": len(kn), "joined": len(joined),
                  "settled_both_sides": n_settled, "drops": dict(drops),
                  "paired_observations": n_obs}

    if gaps:
        g, nt = np.array(gaps), np.array(nets)
        print(f"\n   THE NUMBER Q1 ACTUALLY TURNS ON — how far apart are the two "
              f"venues?\n   |de-vigged Pinnacle fair - Kalshi ask|, n={len(g):,} "
              f"paired observations")
        print(f"      median {np.median(g):.2f}c   p75 {np.percentile(g,75):.2f}c   "
              f"p90 {np.percentile(g,90):.2f}c   p99 {np.percentile(g,99):.2f}c   "
              f"max {g.max():.2f}c")
        print(f"      cost bar at 50c = 2.75c.  Fraction of observations whose "
              f"GAP alone exceeds it: {100*(g>2.75).mean():.1f}%")
        print(f"      net edge after cost: median {np.median(nt):+.2f}c   "
              f"p90 {np.percentile(nt,90):+.2f}c   max {nt.max():+.2f}c   "
              f"positive on {100*(nt>0).mean():.2f}% of observations")
        rep["mlb_gap"] = {
            "n": len(g), "median_c": round(float(np.median(g)), 3),
            "p90_c": round(float(np.percentile(g, 90)), 3),
            "max_c": round(float(g.max()), 3),
            "frac_gap_over_cost": round(float((g > 2.75).mean()), 5),
            "net_max_c": round(float(nt.max()), 3),
            "frac_net_positive": round(float((nt > 0).mean()), 5)}

    # ---- Q2 accrual
    print("\n   Q2 — ACCRUAL")
    days = defaultdict(set)
    for j in joined:
        days[str(j["start"].date())].add(j["event"])
    for d in sorted(days):
        print(f"      games starting {d}: {len(days[d])} joined")
    span_d = (datetime.now(timezone.utc)
              - datetime(2026, 8, 4, 21, 27, tzinfo=timezone.utc)).total_seconds() / 86400
    rate = len(joined) / span_d if span_d else 0
    print(f"      recorder up {span_d:.2f} d  ->  {rate:.1f} joined events/day")
    need = 440
    print(f"      Stage A needs ~{need} games -> "
          f"{(need - n_settled) / max(rate, 0.01):.0f} more days "
          f"(~{(datetime.now(timezone.utc) + timedelta(days=(need-n_settled)/max(rate,0.01))).date()})")
    rep["accrual"] = {"joined_per_day": round(rate, 2), "settled": n_settled,
                      "need": need,
                      "days_to_stage_a": round((need - n_settled) / max(rate, 0.01), 1)}


def main():
    REP.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(f"file:{DB.as_posix()}?mode=ro", uri=True, timeout=300)
    rep = {}
    overround_census(con, rep)
    mlb_join(con, rep)
    con.close()
    (REP / "devig_where.json").write_text(json.dumps(rep, indent=1, default=str),
                                          encoding="utf-8")
    print("\nwrote reports/devig_where.json")


if __name__ == "__main__":
    main()

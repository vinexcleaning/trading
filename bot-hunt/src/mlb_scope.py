"""Can the DE-VIG TEST be run on MLB, and how long until it is powered?

The question this answers is narrow and was asked precisely: take Pinnacle's
price, strip the vig, treat that as fair value, compare it to the Kalshi price,
and COUNT ONLY THE CASES WHERE THE GAP BEATS COST. Step 6 tested structural
cells (H1-H9) that need no reference price. RESULTS_CROSSVENUE measured the
DISTRIBUTION of the de-vigged gap on esports with no settlement attached. The
gated, settled test has never been run on anything.

MLB is the only family in the recorder with a 1.0c spread at every lead
(HANDOFF 3b), which is what makes a gated test possible at all: on esports the
pre-match cost bar is 3-6x the touch figure the shortlist ranked it on.

This script measures ONLY the apparatus, never a return:
  * does the recorder capture the three things the test needs
  * what fraction of Kalshi MLB events can be joined to a Pinnacle matchup
  * how many joined events accrue per day
  * how many are needed, from the observed edge dispersion

NO RETURN NUMBER IS COMPUTED HERE. Settlement is deliberately not joined.
"""
from __future__ import annotations

import json
import re
import sqlite3
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB = ROOT / "data" / "record.db"
REP = ROOT / "reports"

TS = "%Y-%m-%dT%H:%M:%SZ"

# MLB clubs: Kalshi uses the nickname ("Yankees"), Pinnacle the full club name
# ("New York Yankees"). Both are stable and there are exactly 30, so the join
# does NOT need fuzzy matching - which is the whole reason MLB is joinable and
# esports was not. Esports rosters are unbounded, renamed constantly, and cost
# this project two phantom joins (RESULTS_CROSSVENUE section 3).
STOP = re.compile(r"\b(the|of)\b")


def norm(s: str) -> str:
    if not s:
        return ""
    s = STOP.sub(" ", s.lower())
    s = re.sub(r"[^a-z0-9 ]+", " ", s)
    return " ".join(s.split())


def american_to_prob(a) -> float:
    a = float(a)
    return (-a) / ((-a) + 100.0) if a < 0 else 100.0 / (a + 100.0)


def main() -> None:
    REP.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(f"file:{DB.as_posix()}?mode=ro", uri=True, timeout=300)
    out: dict = {}

    print("== recorder window")
    n_cyc, t0, t1 = con.execute(
        "select count(*), min(started_utc), max(started_utc) from cycles"
    ).fetchone()
    span_h = (datetime.strptime(t1, TS) - datetime.strptime(t0, TS)).total_seconds() / 3600
    print(f"   {n_cyc} cycles  {t0} -> {t1}   ({span_h:.1f} h)")
    out["cycles"] = n_cyc
    out["window"] = [t0, t1]
    out["span_hours"] = round(span_h, 2)

    # ---------------------------------------------------------- LEG 1: Kalshi
    print("\n== LEG 1  Kalshi MLB book")
    for series in ("KXMLBGAME", "KXMLBTOTAL", "KXMLBRFI"):
        r = con.execute(
            "select count(*), count(distinct ticker) from k_book where series=?",
            (series,)).fetchone()
        nn = con.execute(
            "select count(*) from k_names where series=?", (series,)).fetchone()[0]
        two = con.execute(
            "select count(*) from k_book where series=? and yes_bid_c is not null "
            "and yes_ask_c is not null", (series,)).fetchone()[0]
        print(f"   {series:12} snapshots={r[0]:>8,}  tickers={r[1]:>5,}  "
              f"two-sided={100*two/max(r[0],1):5.1f}%  k_names={nn:,}")
        out.setdefault("kalshi", {})[series] = {
            "snapshots": r[0], "tickers": r[1], "two_sided_pct": round(100*two/max(r[0],1), 2),
            "k_names": nn}

    # spread, which is the cost bar's dominant term
    sp = con.execute(
        "select yes_ask_c - yes_bid_c from k_book where series='KXMLBGAME' "
        "and yes_bid_c is not null and yes_ask_c is not null").fetchall()
    sp = sorted(x[0] for x in sp)
    if sp:
        med = sp[len(sp)//2]
        p90 = sp[int(0.9*len(sp))]
        print(f"   KXMLBGAME spread: median {med:.1f}c  p90 {p90:.1f}c  n={len(sp):,}")
        out["kalshi_spread"] = {"median_c": med, "p90_c": p90, "n": len(sp)}

    # ------------------------------------------------------- LEG 2: Pinnacle
    print("\n== LEG 2  Pinnacle baseball")
    mus = con.execute(
        "select matchup_id, max(league), max(home), max(away), max(starts_utc), "
        "min(ts_utc), max(ts_utc) from pin_matchup where sport='baseball' "
        "group by matchup_id").fetchall()
    print(f"   {len(mus):,} distinct baseball matchups")
    lg = Counter(m[1] for m in mus)
    print(f"   leagues: {lg.most_common(6)}")
    mlb_mus = {m[0]: {"league": m[1], "home": m[2], "away": m[3], "starts": m[4]}
               for m in mus if m[1] and "mlb" in (m[1] or "").lower()
               and m[2] and m[3]}
    print(f"   MLB matchups with both club names: {len(mlb_mus):,}")
    out["pinnacle"] = {"baseball_matchups": len(mus),
                       "leagues": lg.most_common(10),
                       "mlb_matchups_named": len(mlb_mus)}

    priced = con.execute(
        "select count(*), count(distinct matchup_id) from pin_market "
        "where sport='baseball' and market_type='moneyline' and period=0").fetchone()
    print(f"   moneyline period-0 price rows: {priced[0]:,} over {priced[1]:,} matchups")
    out["pinnacle"]["moneyline_rows"] = priced[0]
    out["pinnacle"]["moneyline_matchups"] = priced[1]

    # ------------------------------------------------------------ THE JOIN
    print("\n== THE JOIN  Kalshi MLB event <-> Pinnacle MLB matchup")
    names = {}
    for tk, ev, sub, title, close in con.execute(
            "select ticker, event_ticker, yes_sub_title, title, close_utc "
            "from k_names where series='KXMLBGAME'"):
        if sub:
            names[tk] = {"event": ev, "sub": sub, "title": title, "close": close}
    print(f"   Kalshi MLB tickers carrying a full outcome name: {len(names):,}")
    if names:
        ex = list(names.items())[:4]
        for tk, d in ex:
            print(f"      {tk:34} yes_sub_title={d['sub']!r}")

    by_event = defaultdict(list)
    for tk, d in names.items():
        by_event[d["event"]].append(tk)
    print(f"   Kalshi MLB events (both sides listed): "
          f"{sum(1 for v in by_event.values() if len(v) == 2):,} of {len(by_event):,}")

    pin_index = []
    for mid, m in mlb_mus.items():
        pin_index.append((mid, norm(m["home"]), norm(m["away"]), m))

    matched, unmatched = [], []
    for ev, tks in by_event.items():
        if len(tks) != 2:
            continue
        outs = {tk: norm(names[tk]["sub"]) for tk in tks}
        hit = None
        for mid, h, a, m in pin_index:
            mp = {}
            for tk, o in outs.items():
                if not o:
                    continue
                # nickname-in-clubname, both directions, with a length floor.
                # The floor is what the Polymarket join lacked when Pinnacle's
                # "A Team" normalised to "a" and swallowed a quarter of the
                # sample (RESULTS_CROSSVENUE section 3b).
                if o == h or (len(o) > 3 and (o in h or h in o)):
                    mp[tk] = "home"
                elif o == a or (len(o) > 3 and (o in a or a in o)):
                    mp[tk] = "away"
            if len(mp) == 2 and set(mp.values()) == {"home", "away"}:
                hit = (mid, mp, m)
                break
        if hit:
            matched.append({"event": ev, "matchup": hit[0], "map": hit[1],
                            "pin": f"{hit[2]['home']} vs {hit[2]['away']}",
                            "kal": " / ".join(names[t]["sub"] for t in tks),
                            "close": names[tks[0]]["close"]})
        else:
            unmatched.append({"event": ev,
                              "kal": " / ".join(names[t]["sub"] for t in tks)})

    nboth = sum(1 for v in by_event.values() if len(v) == 2)
    print(f"   MATCHED {len(matched):,} of {nboth:,} two-sided Kalshi MLB events "
          f"({100*len(matched)/max(nboth,1):.1f}%)")
    for m in matched[:8]:
        print(f"      {m['kal']:32} <-> {m['pin']}")
    if unmatched:
        print(f"   UNMATCHED {len(unmatched)} — first few:")
        for u in unmatched[:6]:
            print(f"      {u['kal']}")
    out["join"] = {"kalshi_events_two_sided": nboth, "matched": len(matched),
                   "match_rate": round(len(matched)/max(nboth, 1), 4),
                   "examples": matched[:20], "unmatched": unmatched[:20]}

    # ------------------------------------- do the two legs QUOTE AT THE SAME TIME
    print("\n== TEMPORAL OVERLAP  (a joined event is only usable if both venues "
          "quoted it within the alignment tolerance)")
    pin_ts = defaultdict(dict)
    for mid, ts, desig, price in con.execute(
            "select matchup_id, ts_utc, designation, price_american from pin_market "
            "where sport='baseball' and market_type='moneyline' and period=0 "
            "and designation is not null"):
        if mid in mlb_mus:
            pin_ts[mid].setdefault(ts, {})[desig] = price

    usable, overround, aligns = [], [], []
    for m in matched:
        pts = sorted(t for t, d in pin_ts.get(m["matchup"], {}).items()
                     if "home" in d and "away" in d)
        if not pts:
            continue
        pt_dt = [datetime.strptime(t, TS) for t in pts]
        n_obs = 0
        for tk in m["map"]:
            for (ts,) in con.execute(
                    "select ts_utc from k_book where ticker=? and yes_bid_c is not null "
                    "and yes_ask_c is not null", (tk,)):
                kdt = datetime.strptime(ts, TS)
                best = min(pt_dt, key=lambda x: abs((x - kdt).total_seconds()))
                dt = abs((best - kdt).total_seconds())
                if dt <= 900:
                    n_obs += 1
                    aligns.append(dt)
        if n_obs:
            usable.append({"event": m["event"], "obs": n_obs, "close": m["close"],
                           "kal": m["kal"]})
            d = pin_ts[m["matchup"]][pts[len(pts)//2]]
            overround.append(100 * (american_to_prob(d["home"])
                                    + american_to_prob(d["away"]) - 1))

    aligns.sort()
    print(f"   events with BOTH venues quoting inside 900 s: {len(usable):,}")
    print(f"   paired observations: {sum(u['obs'] for u in usable):,}")
    if aligns:
        print(f"   time alignment: median {aligns[len(aligns)//2]:.0f}s  "
              f"p90 {aligns[int(0.9*len(aligns))]:.0f}s")
    if overround:
        overround.sort()
        print(f"   Pinnacle MLB overround: median "
              f"{overround[len(overround)//2]:.2f}pp  "
              f"p10 {overround[int(0.1*len(overround))]:.2f}  "
              f"p90 {overround[int(0.9*len(overround))]:.2f}")
    out["overlap"] = {
        "usable_events": len(usable),
        "paired_observations": sum(u["obs"] for u in usable),
        "align_median_s": aligns[len(aligns)//2] if aligns else None,
        "overround_median_pp": round(overround[len(overround)//2], 3) if overround else None,
    }

    # ------------------------------------------------------------- THE RATE
    print("\n== THE RATE  (how fast usable events accrue)")
    days = defaultdict(set)
    for u in usable:
        if u["close"]:
            days[u["close"][:10]].add(u["event"])
    for d in sorted(days):
        print(f"   {d}  {len(days[d])} usable events")
    per_day = (len(usable) / (span_h / 24)) if span_h > 0 else 0
    print(f"   over the whole {span_h:.1f} h window: {per_day:.1f} usable events/day")
    out["rate"] = {"per_day_observed": round(per_day, 2),
                   "by_close_date": {d: len(v) for d, v in sorted(days.items())}}

    con.close()
    (REP / "mlb_scope.json").write_text(json.dumps(out, indent=1, default=str),
                                        encoding="utf-8")
    print("\nwrote reports/mlb_scope.json")


if __name__ == "__main__":
    main()

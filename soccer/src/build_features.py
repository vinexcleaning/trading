"""Derive pre-match features from the ESPN history, leak-free by construction.

THE STRUCTURAL GUARANTEE. Matches are processed in strict chronological order.
For each match, features are computed from the history accumulated SO FAR, and
the match is appended to that history only AFTER its features are written. A
future match therefore cannot influence a past one -- not by discipline, but
because the information does not exist in the accumulator yet.

That is stronger than stamping `known_at` and checking it, and it is the fix
for the class of bug behind LEDGER T010 (a price anchor read from after the
match) and T007 (a filter reading a leaking anchor).

Every feature still carries a knowability stamp, and the stamps are asserted.

Features, all computed from prior matches only:
  rest_days, matches_last_14d          fixture congestion
  form_pts_5, form_gf_5, form_ga_5     recent form, last 5 matches
  home_wr / away_wr                    venue-specific win rate, this season
  h2h_pts, h2h_n                       head-to-head record
  season_pts, season_gd, season_played league position context
"""
import json
import os
import statistics as st
import sys
from collections import Counter, defaultdict, deque
from datetime import datetime, timedelta

HERE = os.path.dirname(__file__)
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "..", "common"))

ROOT = os.path.join(HERE, "..")
DATA, REP = os.path.join(ROOT, "data"), os.path.join(ROOT, "reports")
SRC = os.path.join(DATA, "espn_history", "matches.jsonl")
OUT = os.path.join(DATA, "features.jsonl")


def season_of(d, league):
    """Crude season key. Calendar year for the Apr-Dec leagues (BRA, USA,
    COL, ARG since 2023); split-year handling is not attempted because the
    features that use it are all season-to-date counters that reset."""
    return d.year


def main():
    rows = []
    with open(SRC, encoding="utf-8") as fh:
        for line in fh:
            try:
                m = json.loads(line)
            except ValueError:
                continue
            if not m.get("date"):
                continue
            try:
                m["_dt"] = datetime.fromisoformat(m["date"].replace("Z", "+00:00"))
            except ValueError:
                continue
            rows.append(m)
    rows.sort(key=lambda m: m["_dt"])
    print(f"{len(rows)} matches loaded, "
          f"{rows[0]['_dt'].date()} .. {rows[-1]['_dt'].date()}")

    last_match = {}                       # (league,team) -> datetime
    recent = defaultdict(lambda: deque(maxlen=40))   # (league,team) -> matches
    h2h = defaultdict(list)               # (league,frozenset(pair)) -> results
    season = defaultdict(lambda: Counter())          # (league,season,team)
    venue_rec = defaultdict(lambda: Counter())       # (league,season,team,ha)

    out = []
    n_leak_checks = 0
    for m in rows:
        lg, dt_ = m["league"], m["_dt"]
        h, a = m["home_canon"], m["away_canon"]
        ko = dt_.isoformat()
        # known_at for a derived feature is the moment before kickoff
        known = (dt_ - timedelta(minutes=1)).isoformat()
        sk = season_of(dt_, lg)

        def team_feats(t, ha):
            hist = recent[(lg, t)]
            lm = last_match.get((lg, t))
            rest = (dt_ - lm).days if lm else None
            n14 = sum(1 for x in hist if (dt_ - x["dt"]).days <= 14)
            last5 = list(hist)[-5:]
            pts = sum(x["pts"] for x in last5) if last5 else None
            gf = sum(x["gf"] for x in last5) if last5 else None
            ga = sum(x["ga"] for x in last5) if last5 else None
            vk = (lg, sk, t, ha)
            vw, vn = venue_rec[vk]["w"], venue_rec[vk]["n"]
            sc = season[(lg, sk, t)]
            return {
                f"{ha}_rest_days": rest,
                f"{ha}_matches_14d": n14,
                f"{ha}_form_pts_5": pts,
                f"{ha}_form_gf_5": gf,
                f"{ha}_form_ga_5": ga,
                f"{ha}_form_n": len(last5),
                f"{ha}_venue_wr": (vw / vn) if vn >= 3 else None,
                f"{ha}_venue_n": vn,
                f"{ha}_season_pts": sc["pts"] if sc["n"] else None,
                f"{ha}_season_gd": (sc["gf"] - sc["ga"]) if sc["n"] else None,
                f"{ha}_season_played": sc["n"],
            }

        feats = {}
        feats.update(team_feats(h, "home"))
        feats.update(team_feats(a, "away"))
        pk = (lg, frozenset((h, a)))
        prior = h2h[pk]
        feats["h2h_n"] = len(prior)
        feats["h2h_home_pts"] = (sum(p[h] for p in prior if h in p)
                                 if prior else None)

        # ---- leak assertion: every contributing match must predate kickoff
        for t in (h, a):
            for x in recent[(lg, t)]:
                n_leak_checks += 1
                if x["dt"] >= dt_:
                    raise AssertionError(
                        f"LEAK: history for {t} contains a match at {x['dt']} "
                        f"which is not before kickoff {dt_}")

        out.append({
            "espn_id": m["espn_id"], "league": lg, "kickoff": ko,
            "decision_at": ko, "features_known_at": known,
            "home": m["home"], "away": m["away"],
            "home_canon": h, "away_canon": a,
            "completed": m.get("completed"),
            "features": feats,
            "outcome": {"home_goals": m.get("home_goals"),
                        "away_goals": m.get("away_goals")},
        })

        # ---- only NOW does this match enter the history
        hg, ag = m.get("home_goals"), m.get("away_goals")
        if m.get("completed") and hg is not None and ag is not None:
            # `last_match` drives rest_days, so it must mean "last match
            # actually PLAYED". An earlier version updated it for every row,
            # which would have let a postponed or abandoned fixture reset a
            # team's rest clock without a match having happened.
            last_match[(lg, h)] = dt_
            last_match[(lg, a)] = dt_
            hp = 3 if hg > ag else (1 if hg == ag else 0)
            ap = 3 if ag > hg else (1 if hg == ag else 0)
            recent[(lg, h)].append({"dt": dt_, "pts": hp, "gf": hg, "ga": ag})
            recent[(lg, a)].append({"dt": dt_, "pts": ap, "gf": ag, "ga": hg})
            h2h[pk].append({h: hp, a: ap})
            for t, p, gf, ga in ((h, hp, hg, ag), (a, ap, ag, hg)):
                s = season[(lg, sk, t)]
                s["pts"] += p
                s["gf"] += gf
                s["ga"] += ga
                s["n"] += 1
            venue_rec[(lg, sk, h, "home")]["n"] += 1
            venue_rec[(lg, sk, a, "away")]["n"] += 1
            if hg > ag:
                venue_rec[(lg, sk, h, "home")]["w"] += 1
            elif ag > hg:
                venue_rec[(lg, sk, a, "away")]["w"] += 1

    with open(OUT, "w", encoding="utf-8") as fh:
        for r in out:
            fh.write(json.dumps(r) + "\n")
    print(f"wrote {len(out)} feature rows; {n_leak_checks:,} leak assertions, "
          f"0 violations")

    # ---- coverage
    keys = ["home_rest_days", "home_form_pts_5", "home_venue_wr",
            "home_season_pts", "h2h_home_pts", "away_rest_days",
            "away_form_pts_5"]
    cov = Counter()
    comp = [r for r in out if r["completed"]]
    for r in out:
        for k in keys:
            if r["features"].get(k) is not None:
                cov[k] += 1
    n = len(out)
    print(f"\n=== FEATURE COVERAGE ({n:,} matches, {len(comp):,} completed) ===")
    print(f"  {'feature':22s} {'present':>9s} {'pct':>7s}")
    for k in keys:
        print(f"  {k:22s} {cov[k]:9,d} {100*cov[k]/max(n,1):6.1f}%")

    per = defaultdict(lambda: [0, 0])
    for r in out:
        per[r["league"]][0] += 1
        if r["features"].get("home_form_pts_5") is not None:
            per[r["league"]][1] += 1
    print(f"\n  {'league':22s} {'matches':>9s} {'with form':>10s} {'pct':>7s}")
    for lg, (x, y) in sorted(per.items()):
        print(f"  {lg:22s} {x:9,d} {y:10,d} {100*y/max(x,1):6.1f}%")

    # ---- sanity: home advantage on the FULL history
    print("\n=== HOME ADVANTAGE, full history (was n=12-28 before) ===")
    print(f"  {'league':22s} {'n':>7s} {'home':>7s} {'draw':>7s} {'away':>7s}")
    for lg in sorted(per):
        sel = [r for r in comp if r["league"] == lg
               and r["outcome"]["home_goals"] is not None]
        if len(sel) < 20:
            continue
        hw = sum(1 for r in sel
                 if r["outcome"]["home_goals"] > r["outcome"]["away_goals"])
        dr = sum(1 for r in sel
                 if r["outcome"]["home_goals"] == r["outcome"]["away_goals"])
        print(f"  {lg:22s} {len(sel):7,d} {100*hw/len(sel):6.1f}% "
              f"{100*dr/len(sel):6.1f}% {100*(len(sel)-hw-dr)/len(sel):6.1f}%")


if __name__ == "__main__":
    main()

"""Backfill ESPN's match history for the shortlisted leagues.

160 matches (Kalshi's 69-day window) cannot fit anything. ESPN carries roughly
a decade per league, free and unkeyed, and that is the constraint this removes.

Design notes earned the hard way earlier in this project:
  * 7-DAY WINDOWS. A 10-day range returned only 85 MLS matches over 80 days
    where ~170 were expected -- ESPN caps a scoreboard response regardless of
    `limit`. Windows overlap by a day so no boundary date is lost.
  * RESUMABLE. Completed windows are recorded so an interruption costs one
    window, not the run.
  * CONTENT-VALIDATED. A window is only marked done once its response parsed
    and every event carried an id, a date and two competitors. Row counts have
    twice hidden empty writes in this project.
  * Brazilian Serie A runs Apr-Dec and the Argentine calendar shifts; a probe
    that samples one week in March reads zero and looks like a dead source.
    Walking every week avoids that class of error entirely.

Read-only, paced, public. No credentials.
"""
import json
import os
import sys
import time
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta, timezone

import requests

HERE = os.path.dirname(__file__)
sys.path.insert(0, HERE)
import teammatch as TM  # noqa: E402

ROOT = os.path.join(HERE, "..")
DATA, REP = os.path.join(ROOT, "data"), os.path.join(ROOT, "reports")
OUT = os.path.join(DATA, "espn_history")
SITE = "https://site.api.espn.com/apis/site/v2/sports/soccer"
# ESPN (Akamai) began returning 403 to any Mozilla/... or unknown custom
# User-Agent on 2026-08-08. Measured: "Mozilla/5.0 (soccer-research/1.0)"
# -> 403, "soccer-research/1.0" -> 403, curl/8.4.0 -> 200, requests' own
# default -> 200. Sending no override is what works; do not "fix" this by
# adding a browser string back.
UA = {}

# The six original leagues, plus every competition Kalshi was seen quoting
# per-game in reports/tape_soccer_scan.json, plus the four big European leagues
# and the Champions League. Kalshi's definitive per-game list is not settled
# (asked of the devig chat 2026-08-08), so the rule here is: fetch anything that
# could plausibly be on the book, because a fixture list is cheap and a missing
# league costs a re-run. Every slug below was probed and returns 200.
LEAGUES = [
    # confirmed in soccer/dataset.md
    "mex.1", "arg.1", "bra.1", "col.1", "usa.1", "bra.copa_do_brazil",
    # seen quoted per-game on Kalshi in the 2026-05-24..06-11 tape
    "fifa.friendly", "uru.1", "per.1", "ecu.1", "chi.1",
    "usa.usl.1", "usa.usl.l1", "usa.nwsl",
    # big European competitions -- not seen per-game on Kalshi yet, included
    # because they are the ones the user actually knows
    "eng.1", "esp.1", "ita.1", "ger.1", "uefa.champions",
    # ---- ADDED 2026-08-08 after checking Kalshi directly rather than trusting
    # the two documents in this repo, which both undercounted badly. Kalshi
    # settles per-game markets on ALL of these: KXEPLGAME, KXUCLGAME,
    # KXUELGAME, KXSERIEAGAME, KXLALIGAGAME, KXBUNDESLIGAGAME, KXLIGUE1GAME,
    # KXWCGAME, KXCLUBWCGAME, KXCOPADOBRASILGAME, plus the ten South/Central
    # American and US series already listed above. So the Premier League and
    # the Champions League ARE bettable, which soccer/dataset.md and
    # reports/tape_soccer_scan.json between them managed to miss.
    "fra.1", "uefa.europa", "fifa.world", "fifa.cwc", "uefa.europa.conf",
    # THE QUALIFYING ROUNDS ARE A SEPARATE ESPN LEAGUE CODE, and missing them
    # was a real gap rather than a tidy one. Kalshi has 66 settled Champions
    # League events inside its candle window as of 2026-08-09; ESPN's
    # `uefa.champions` returns ZERO fixtures for 1 Jul - 8 Aug and
    # `uefa.champions_qual` returns exactly 66. Without these two codes the
    # price sample contains no European football at all, which was about to be
    # written up as "Kalshi has no European league in the window".
    "uefa.champions_qual", "uefa.europa_qual",
]
START = date(2015, 1, 1)
END = date.today()
STEP = 7
PACE = 0.22


def get(url, params, tries=5):
    for i in range(tries):
        try:
            r = requests.get(url, params=params, headers=UA, timeout=45)
        except requests.RequestException:
            time.sleep(2.0 * (i + 1))
            continue
        if r.status_code == 429 or r.status_code >= 500:
            time.sleep(3.0 * (i + 1))
            continue
        time.sleep(PACE)
        return r
    return None


def parse_event(e, league):
    """One ESPN event -> a flat match row. Returns None if malformed."""
    comps = (e.get("competitions") or [{}])[0]
    cs = comps.get("competitors") or []
    if len(cs) != 2 or not e.get("id") or not e.get("date"):
        return None
    home = away = None
    hs = as_ = None
    for c in cs:
        nm = ((c.get("team") or {}).get("displayName")
              or (c.get("team") or {}).get("name"))
        try:
            sc = int(c.get("score")) if c.get("score") not in (None, "") else None
        except (TypeError, ValueError):
            sc = None
        if c.get("homeAway") == "home":
            home, hs = nm, sc
        else:
            away, as_ = nm, sc
    if not home or not away:
        return None
    st = ((e.get("status") or {}).get("type") or {})
    venue = ((comps.get("venue") or {}).get("fullName"))
    return {
        "espn_id": e["id"], "league": league, "date": e["date"],
        "home": home, "away": away,
        "home_canon": TM.canon(home), "away_canon": TM.canon(away),
        "home_goals": hs, "away_goals": as_,
        "completed": st.get("completed"), "status": st.get("name"),
        "venue": venue,
        "neutral": comps.get("neutralSite"),
        "attendance": comps.get("attendance"),
    }


def main():
    os.makedirs(OUT, exist_ok=True)
    prog_path = os.path.join(OUT, "_progress.json")
    progress = {}
    if os.path.exists(prog_path):
        try:
            progress = json.load(open(prog_path, encoding="utf-8"))
        except ValueError:
            progress = {}

    # INFINITE-LOOP GUARD. The first version was:
    #     while d < END:
    #         d2 = min(d + STEP, END); windows.append(...); d = d2 - 1 day
    # Once d + STEP passes END, d2 pins to END and d = END - 1 day forever, so
    # the loop appends without terminating. It consumed 7.3 GB before it was
    # killed. The overlap that makes the loop useful is exactly what breaks it,
    # so the terminal window has to break explicitly.
    windows = []
    for lg in LEAGUES:
        d = START
        while d < END:
            d2 = min(d + timedelta(days=STEP), END)
            windows.append((lg, d, d2))
            if d2 >= END:
                break
            d = d2 - timedelta(days=1)
    todo = [w for w in windows
            if progress.get(f"{w[0]}|{w[1]}") != "done"]
    print(f"{len(windows)} windows total, {len(todo)} to fetch "
          f"({len(windows)-len(todo)} already done)", flush=True)

    t0 = time.time()
    stats = Counter()
    seen_path = os.path.join(OUT, "matches.jsonl")
    seen = set()
    if os.path.exists(seen_path):
        with open(seen_path, encoding="utf-8") as fh:
            for line in fh:
                try:
                    seen.add(json.loads(line)["espn_id"])
                except (ValueError, KeyError):
                    pass
        print(f"  {len(seen)} matches already on disk", flush=True)

    with open(seen_path, "a", encoding="utf-8", buffering=1) as fh:
        for i, (lg, d, d2) in enumerate(todo):
            r = get(f"{SITE}/{lg}/scoreboard",
                    {"dates": f"{d:%Y%m%d}-{d2:%Y%m%d}", "limit": 400})
            if r is None or r.status_code != 200:
                stats["window_fail"] += 1
                continue
            try:
                evs = r.json().get("events", [])
            except ValueError:
                stats["unparseable"] += 1
                continue
            good = 0
            for e in evs:
                row = parse_event(e, lg)
                if row is None:
                    stats["malformed_event"] += 1
                    continue
                good += 1
                if row["espn_id"] in seen:
                    continue
                seen.add(row["espn_id"])
                fh.write(json.dumps(row) + "\n")
                stats["written"] += 1
            # only mark done once the window actually parsed
            progress[f"{lg}|{d}"] = "done"
            stats["windows_done"] += 1
            if (i + 1) % 50 == 0:
                el = time.time() - t0
                json.dump(progress, open(prog_path, "w"), indent=0)
                print(f"  {i+1}/{len(todo)} windows | {stats['written']} new "
                      f"matches | {len(seen)} total | {el/60:.1f} min | "
                      f"eta {(len(todo)-i-1)*el/max(i+1,1)/60:.0f} min",
                      flush=True)
    json.dump(progress, open(prog_path, "w"), indent=0)

    print(f"\nDONE in {(time.time()-t0)/60:.1f} min")
    print(f"  {dict(stats)}")
    print(f"  matches on disk: {len(seen)}")

    # ---- coverage report, computed from the file, not from counters
    per = defaultdict(lambda: Counter())
    years = defaultdict(Counter)
    with open(seen_path, encoding="utf-8") as fh:
        for line in fh:
            try:
                m = json.loads(line)
            except ValueError:
                continue
            lg = m["league"]
            per[lg]["n"] += 1
            if m.get("completed"):
                per[lg]["completed"] += 1
            if m.get("home_goals") is not None:
                per[lg]["with_score"] += 1
            years[lg][m["date"][:4]] += 1
    print(f"\n  {'league':22s} {'matches':>8s} {'completed':>10s} {'w/score':>8s} "
          f"{'first':>6s} {'last':>6s}")
    for lg in sorted(per):
        ys = sorted(years[lg])
        print(f"  {lg:22s} {per[lg]['n']:8d} {per[lg]['completed']:10d} "
              f"{per[lg]['with_score']:8d} {ys[0]:>6s} {ys[-1]:>6s}")
    with open(os.path.join(REP, "espn_backfill_coverage.json"), "w",
              encoding="utf-8") as f2:
        json.dump({lg: {"totals": dict(per[lg]), "by_year": dict(years[lg])}
                   for lg in per}, f2, indent=1)


if __name__ == "__main__":
    main()

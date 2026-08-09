"""Goal minutes for every match in the ESPN back-catalogue.

WHY THIS EXISTS. A final score cannot answer "who was losing in the 80th
minute". Only the minute of each goal can. `backfill_espn.py` gets the fixture
list and the final score from the scoreboard endpoint; this walks every one of
those fixtures through ESPN's `summary` endpoint, which carries `keyEvents`
with, for each goal, BOTH:

  * `clock.displayValue` -- the DISPLAYED match minute ("77'"). This is the
    right key for a comeback table. It is what a person watching the match
    sees, and "1-0 up in the 80th minute" means the 80th displayed minute.
  * `wallclock` -- an absolute UTC instant. This is the right key for joining
    to a Kalshi price, and ONLY for that.

Those two are not interchangeable and the difference is not small. The existing
measurement in reports/inplay_analysis.txt: the minute-implied timestamp is
17.52 minutes off true wallclock at the median, on 362 events, because halftime
and stoppage are real elapsed time the displayed minute does not count. Both
fields are stored on every event here so neither question has to be re-fetched.

PROBED BEFORE WRITING, back to 2015, on mex.1 / usa.1 / bra.1 / col.1: goals
carry both a displayed minute and a wallclock. The back-catalogue is usable.

Read-only, paced, public, unkeyed. No credentials. No orders.
"""
import json
import os
import queue
import sys
import threading
import time
from collections import Counter, defaultdict

import requests

HERE = os.path.dirname(__file__)
ROOT = os.path.join(HERE, "..")
DATA, REP = os.path.join(ROOT, "data"), os.path.join(ROOT, "reports")
SRC = os.path.join(DATA, "espn_history", "matches.jsonl")
OUT = os.path.join(DATA, "goal_minutes.jsonl")
PROG = os.path.join(DATA, "goal_minutes_progress.json")
SITE = "https://site.api.espn.com/apis/site/v2/sports/soccer"

# See the note in backfill_espn.py. ESPN 403s a browser-shaped or unknown
# User-Agent since 2026-08-08; requests' own default is served. Do not add one.
UA = {}

WORKERS = 4
PACE = 0.10          # per worker, so ~40 requests/sec/4 -> well under any cap
MAX_TRIES = 4

# Kalshi-bettable first, so a run stopped early still answers the real question.
PRIORITY = [
    "mex.1", "arg.1", "col.1", "usa.1", "bra.1", "bra.copa_do_brazil",
    "fifa.friendly", "uru.1", "per.1", "ecu.1", "chi.1",
    "usa.usl.1", "usa.usl.l1", "usa.nwsl",
    "eng.1", "esp.1", "ita.1", "ger.1", "uefa.champions",
]


def get(url, params, tries=MAX_TRIES):
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


def parse_minute(disp):
    """ "77'" -> 77 ;  "90'+3'" -> 90 (stoppage folded into its own field).

    Returns (minute, stoppage). Both None if unparseable -- and an unparseable
    minute must NOT silently become 0, which is why this returns None rather
    than a default. A goal with no minute cannot be placed on the timeline and
    is counted as a loss, visibly, in the report.
    """
    if not disp:
        return None, None
    s = str(disp).replace("'", "").strip()
    if "+" in s:
        a, _, b = s.partition("+")
        try:
            return int(a.strip()), int(b.strip())
        except ValueError:
            return None, None
    try:
        return int(s), 0
    except ValueError:
        return None, None


def fetch_one(m):
    """One fixture -> a row with every goal and red card, or None."""
    r = get(f"{SITE}/{m['league']}/summary", {"event": m["espn_id"]})
    if r is None or r.status_code != 200:
        return None, "http"
    try:
        d = r.json()
    except ValueError:
        return None, "unparseable"

    ke = d.get("keyEvents") or []
    if not ke:
        return None, "no_keyevents"

    kick = None
    for e in ke:
        if (e.get("type") or {}).get("type") == "kickoff" and e.get("wallclock"):
            kick = e["wallclock"]
            break

    evs = []
    for e in ke:
        typ = e.get("type") or {}
        txt = (typ.get("text") or "").lower()
        is_goal = bool(e.get("scoringPlay"))
        is_red = "red card" in txt
        if not (is_goal or is_red):
            continue
        minute, stoppage = parse_minute((e.get("clock") or {}).get("displayValue"))
        team = (e.get("team") or {}).get("displayName")
        evs.append({
            "kind": "red_card" if is_red else "goal",
            "detail": typ.get("text"),
            "minute": minute,
            "stoppage": stoppage,
            "minute_raw": (e.get("clock") or {}).get("displayValue"),
            "wallclock": e.get("wallclock"),
            "team": team,
            # ESPN marks own goals and penalties in the type text; keep the raw
            # text so a later pass can split them without re-fetching 70k pages.
            "own_goal": "own goal" in txt,
            "penalty": "penalty" in txt,
        })

    return {
        "espn_id": m["espn_id"],
        "league": m["league"],
        "date": m["date"],
        "home": m["home"],
        "away": m["away"],
        "home_goals": m.get("home_goals"),
        "away_goals": m.get("away_goals"),
        "kickoff_wallclock": kick,
        "events": evs,
    }, "ok"


def main():
    if not os.path.exists(SRC):
        sys.exit(f"missing {SRC} -- run backfill_espn.py first")

    matches = []
    with open(SRC, encoding="utf-8") as fh:
        for line in fh:
            try:
                m = json.loads(line)
            except ValueError:
                continue
            if m.get("completed") and m.get("home_goals") is not None:
                matches.append(m)

    done = set()
    if os.path.exists(OUT):
        with open(OUT, encoding="utf-8") as fh:
            for line in fh:
                try:
                    done.add(json.loads(line)["espn_id"])
                except (ValueError, KeyError):
                    pass

    order = {lg: i for i, lg in enumerate(PRIORITY)}
    todo = [m for m in matches if m["espn_id"] not in done]
    todo.sort(key=lambda m: (order.get(m["league"], 99), m["date"]))

    print(f"{len(matches)} completed fixtures on disk", flush=True)
    print(f"  {len(done)} already fetched, {len(todo)} to go", flush=True)
    if not todo:
        print("nothing to do")
        return

    q = queue.Queue()
    for m in todo:
        q.put(m)
    lock = threading.Lock()
    stats = Counter()
    t0 = time.time()
    fh = open(OUT, "a", encoding="utf-8", buffering=1)

    def worker():
        while True:
            try:
                m = q.get_nowait()
            except queue.Empty:
                return
            row, why = fetch_one(m)
            with lock:
                stats[why] += 1
                if row is not None:
                    fh.write(json.dumps(row) + "\n")
                n = sum(stats.values())
                if n % 250 == 0:
                    el = time.time() - t0
                    rate = n / max(el, 1e-9)
                    print(f"  {n}/{len(todo)} | {el/60:.1f} min | "
                          f"eta {(len(todo)-n)/max(rate,1e-9)/60:.0f} min | "
                          f"{dict(stats)}", flush=True)
            q.task_done()

    ts = [threading.Thread(target=worker, daemon=True) for _ in range(WORKERS)]
    for t in ts:
        t.start()
    for t in ts:
        t.join()
    fh.close()

    print(f"\nDONE in {(time.time()-t0)/60:.1f} min  {dict(stats)}", flush=True)
    report()


def report():
    """Coverage, computed from the file rather than from counters.

    Counters have twice hidden empty writes in this project, so everything
    below is re-read off disk.
    """
    per = defaultdict(Counter)
    years = defaultdict(Counter)
    n_rows = 0
    with open(OUT, encoding="utf-8") as fh:
        for line in fh:
            try:
                r = json.loads(line)
            except ValueError:
                continue
            n_rows += 1
            lg = r["league"]
            per[lg]["matches"] += 1
            years[lg][r["date"][:4]] += 1
            goals = [e for e in r["events"] if e["kind"] == "goal"]
            per[lg]["goals"] += len(goals)
            per[lg]["goals_no_minute"] += sum(1 for g in goals if g["minute"] is None)
            per[lg]["reds"] += sum(1 for e in r["events"] if e["kind"] == "red_card")
            # THE INTEGRITY CHECK THAT MATTERS: do the goals in the timeline add
            # up to the final score? If they do not, the match cannot be placed
            # on a minute-by-minute timeline and must be dropped, not patched.
            hs, as_ = r.get("home_goals"), r.get("away_goals")
            if hs is not None and as_ is not None:
                if len(goals) == (hs + as_):
                    per[lg]["timeline_agrees"] += 1
                else:
                    per[lg]["timeline_disagrees"] += 1

    lines = []
    lines.append(f"{n_rows} match rows with a timeline\n")
    lines.append(f"{'league':22s} {'matches':>8s} {'goals':>7s} {'no_min':>7s} "
                 f"{'reds':>6s} {'agrees':>8s} {'disagrees':>10s} {'first':>6s} {'last':>6s}")
    for lg in sorted(per, key=lambda x: -per[x]["matches"]):
        ys = sorted(years[lg])
        p = per[lg]
        lines.append(f"{lg:22s} {p['matches']:8d} {p['goals']:7d} "
                     f"{p['goals_no_minute']:7d} {p['reds']:6d} "
                     f"{p['timeline_agrees']:8d} {p['timeline_disagrees']:10d} "
                     f"{ys[0]:>6s} {ys[-1]:>6s}")
    tot = Counter()
    for lg in per:
        tot.update(per[lg])
    lines.append("")
    lines.append(f"TOTAL matches {tot['matches']}, goals {tot['goals']}, "
                 f"goals with no readable minute {tot['goals_no_minute']}")
    lines.append(f"timeline agrees with final score on {tot['timeline_agrees']} "
                 f"matches, disagrees on {tot['timeline_disagrees']} "
                 f"({tot['timeline_disagrees']/max(tot['matches'],1)*100:.1f}%)")
    lines.append("")
    lines.append("A match whose goal timeline does not add up to its final score "
                 "is UNUSABLE for a comeback table and is dropped, not repaired.")
    txt = "\n".join(lines)
    print("\n" + txt)
    os.makedirs(REP, exist_ok=True)
    with open(os.path.join(REP, "goal_minutes_coverage.txt"), "w",
              encoding="utf-8") as f2:
        f2.write(txt + "\n")
    print("\nwrote reports/goal_minutes_coverage.txt")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "report":
        report()
    else:
        main()

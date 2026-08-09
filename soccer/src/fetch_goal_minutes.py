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
GAPS = os.path.join(DATA, "goal_minutes_gaps.jsonl")
SITE = "https://site.api.espn.com/apis/site/v2/sports/soccer"

# See the note in backfill_espn.py. ESPN 403s a browser-shaped or unknown
# User-Agent since 2026-08-08; requests' own default is served. Do not add one.
UA = {}

WORKERS = 8
PACE = 0.05
MAX_TRIES = 4

# Kalshi-bettable first, so a run stopped early still answers the real question.
PRIORITY = [
    "mex.1", "arg.1", "col.1", "usa.1", "bra.1", "bra.copa_do_brazil",
    "fifa.friendly", "uru.1", "per.1", "ecu.1", "chi.1",
    "usa.usl.1", "usa.usl.l1", "usa.nwsl",
    "eng.1", "esp.1", "ita.1", "ger.1", "uefa.champions",
    "fra.1", "uefa.europa", "fifa.world", "fifa.cwc", "uefa.europa.conf",
    # See backfill_espn.py -- the qualifying rounds are where Kalshi's European
    # book actually is right now, and they are a different league code.
    "uefa.champions_qual", "uefa.europa_qual",
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


def fetch_one(m, empty_retries=1):
    """One fixture -> a row with every goal and red card, or None.

    AN EMPTY TIMELINE IS A REAL GAP IN ESPN, NOT A THROTTLE. This was measured
    twice and the first reading was wrong, so both are recorded:

      * First guess: 152 of 700 matches came back with no keyEvents, and three
        hand-picked "missing" ones had 21, 23 and 18 events when re-fetched. It
        looked like ESPN serving stub bodies under concurrency. That comparison
        was broken -- the fixture file was still being appended to, so those
        three had never been requested at all.
      * Measured properly: the empty rate is 10-17% at ONE worker, four workers
        and eight workers alike, so concurrency is not the cause. Then 26
        genuinely-empty matches were retried four times each with a second
        between: 0 of 26 ever returned a timeline. Checking the raw response,
        `commentary`, `header.details` and the boxscore are all empty too.

    So ESPN simply has no play-by-play for some fixtures, and it CLUSTERS BY
    COMPETITION -- Uruguay, Ecuador, Peru and cup ties, none in Mexico,
    Argentina, Brazil, Colombia or MLS. That is a coverage fact the report has
    to state out loud, because those are Kalshi-bettable leagues.

    One retry is kept because it costs almost nothing. Every failure is written
    to a gaps file so the loss can be counted per competition instead of
    vanishing.
    """
    d = None
    for attempt in range(empty_retries + 1):
        r = get(f"{SITE}/{m['league']}/summary", {"event": m["espn_id"]})
        if r is None or r.status_code != 200:
            return None, "http"
        try:
            d = r.json()
        except ValueError:
            return None, "unparseable"
        if d.get("keyEvents"):
            break
    if not d or not d.get("keyEvents"):
        # A 0-0 with no timeline costs nothing -- there are no goals to place
        # and the match was level throughout, so it belongs in no cell anyway.
        # A 4-2 with no timeline is a genuine loss. The two are counted apart.
        hg, ag = m.get("home_goals"), m.get("away_goals")
        if hg == 0 and ag == 0:
            return None, "no_timeline_but_goalless"
        return None, "no_timeline_and_had_goals"
    ke = d["keyEvents"]

    # Identify the two sides FROM THIS RESPONSE, by team id, not by name.
    # The scoreboard and the summary do not always use the same display name --
    # bra.1 calls the same club "Athletico-PR" in one and "Athletico
    # Paranaense" in the other, which sent 15 goals in the first sample to
    # neither side and broke 8 matches. Ids agree where names do not.
    hdr = ((d.get("header") or {}).get("competitions") or [{}])[0]
    home_id = away_id = None
    home_nm = away_nm = None
    home_sc = away_sc = None
    for c in hdr.get("competitors") or []:
        t = c.get("team") or {}
        try:
            sc = int(c.get("score")) if c.get("score") not in (None, "") else None
        except (TypeError, ValueError):
            sc = None
        if c.get("homeAway") == "home":
            home_id, home_nm, home_sc = t.get("id"), t.get("displayName"), sc
        elif c.get("homeAway") == "away":
            away_id, away_nm, away_sc = t.get("id"), t.get("displayName"), sc
    if not home_id or not away_id:
        return None, "no_team_ids"

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
        tid = (e.get("team") or {}).get("id")
        side = "home" if tid == home_id else ("away" if tid == away_id else None)
        evs.append({
            "kind": "red_card" if is_red else "goal",
            "detail": typ.get("text"),
            "minute": minute,
            "stoppage": stoppage,
            "minute_raw": (e.get("clock") or {}).get("displayValue"),
            "wallclock": e.get("wallclock"),
            # `side` is the field everything downstream uses. The name is kept
            # only so a human reading the file can tell what happened.
            "side": side,
            "team_id": tid,
            "team": (e.get("team") or {}).get("displayName"),
            # ESPN marks own goals and penalties in the type text; keep the raw
            # text so a later pass can split them without re-fetching 70k pages.
            "own_goal": "own goal" in txt,
            "penalty": "penalty" in txt,
        })

    return {
        "espn_id": m["espn_id"],
        "league": m["league"],
        "date": m["date"],
        # Identity and score taken from the SAME response as the timeline, so
        # the integrity check compares like with like. The scoreboard's own
        # names and scores are kept alongside for cross-reference.
        "home": home_nm, "away": away_nm,
        "home_id": home_id, "away_id": away_id,
        "home_goals": home_sc, "away_goals": away_sc,
        "sb_home": m["home"], "sb_away": m["away"],
        "sb_home_goals": m.get("home_goals"), "sb_away_goals": m.get("away_goals"),
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

    # `--limit N` fetches a spread-out sample instead of everything. It exists
    # so the table-building code downstream can be validated end to end on a few
    # hundred matches before several hours are committed to the full run. It
    # samples EVENLY across the sorted list rather than taking the first N,
    # because the first N would be one league in one era and would not exercise
    # the cases that break things.
    if "--limit" in sys.argv:
        n = int(sys.argv[sys.argv.index("--limit") + 1])
        if n < len(todo):
            step = len(todo) / n
            todo = [todo[int(i * step)] for i in range(n)]
        print(f"  --limit: sampling {len(todo)} matches evenly", flush=True)

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
    gh = open(GAPS, "a", encoding="utf-8", buffering=1)

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
                else:
                    # Every failure is recorded, so "what could you NOT get"
                    # is answerable per competition instead of being a number
                    # that only existed in a console log.
                    gh.write(json.dumps({
                        "espn_id": m["espn_id"], "league": m["league"],
                        "date": m["date"], "reason": why,
                        "home_goals": m.get("home_goals"),
                        "away_goals": m.get("away_goals"),
                    }) + "\n")
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
    gh.close()

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
            # THE INTEGRITY CHECK THAT MATTERS: replay the timeline and see
            # whether it reproduces the final score PER TEAM. Checking only the
            # total would pass a timeline that had the right number of goals on
            # the wrong sides -- which is exactly the failure an own goal would
            # cause if ESPN credited it to the offending team. (It does not:
            # probed on 40 matches, 32 with goals, all 32 reconstruct exactly,
            # including 5 own goals. Own goals are credited to the BENEFITING
            # team. This check is what keeps that true if ESPN ever changes it.)
            hs, as_ = r.get("home_goals"), r.get("away_goals")
            h = sum(1 for g in goals if g.get("side") == "home")
            a = sum(1 for g in goals if g.get("side") == "away")
            unattributed = len(goals) - h - a
            if r.get("sb_home_goals") is not None and hs is not None:
                if (r["sb_home_goals"], r["sb_away_goals"]) != (hs, as_):
                    per[lg]["scoreboard_disagrees_with_summary"] += 1
            per[lg]["goals_unattributed"] += unattributed
            if hs is not None and as_ is not None:
                if h == hs and a == as_ and unattributed == 0:
                    per[lg]["timeline_agrees"] += 1
                else:
                    per[lg]["timeline_disagrees"] += 1

    lines = []
    lines.append(f"{n_rows} match rows with a timeline\n")
    lines.append(f"{'league':22s} {'matches':>8s} {'goals':>7s} {'no_min':>7s} "
                 f"{'unattr':>7s} {'reds':>6s} {'agrees':>8s} {'disagrees':>10s} "
                 f"{'first':>6s} {'last':>6s}")
    for lg in sorted(per, key=lambda x: -per[x]["matches"]):
        ys = sorted(years[lg])
        p = per[lg]
        lines.append(f"{lg:22s} {p['matches']:8d} {p['goals']:7d} "
                     f"{p['goals_no_minute']:7d} {p['goals_unattributed']:7d} "
                     f"{p['reds']:6d} "
                     f"{p['timeline_agrees']:8d} {p['timeline_disagrees']:10d} "
                     f"{ys[0]:>6s} {ys[-1]:>6s}")
    tot = Counter()
    for lg in per:
        tot.update(per[lg])
    lines.append("")
    lines.append(f"scoreboard and summary disagree on the final score for "
                 f"{tot['scoreboard_disagrees_with_summary']} matches")
    lines.append(f"TOTAL matches {tot['matches']}, goals {tot['goals']}, "
                 f"goals with no readable minute {tot['goals_no_minute']}, "
                 f"goals credited to neither side {tot['goals_unattributed']}")
    lines.append(f"timeline reproduces the final score PER TEAM on "
                 f"{tot['timeline_agrees']} matches, fails on "
                 f"{tot['timeline_disagrees']} "
                 f"({tot['timeline_disagrees']/max(tot['matches'],1)*100:.1f}%)")
    # ---- WHAT COULD NOT BE GOT, per competition. This is the half of coverage
    # ---- that normally never gets written down.
    if os.path.exists(GAPS):
        gap = defaultdict(Counter)
        with open(GAPS, encoding="utf-8") as fh:
            for line in fh:
                try:
                    g = json.loads(line)
                except ValueError:
                    continue
                gap[g["league"]][g["reason"]] += 1
        lines.append("")
        lines.append("WHAT ESPN HAS NO TIMELINE FOR -- the gaps, per competition")
        lines.append("")
        lines.append("A match ESPN has no play-by-play for cannot be placed on a")
        lines.append("minute-by-minute timeline at all. Retrying does not help:")
        lines.append("26 such matches were retried four times each and 0 ever")
        lines.append("returned one. A 0-0 costs nothing (no goals to place, the")
        lines.append("match was level throughout). Anything else is a real loss.")
        lines.append("")
        lines.append(f"{'competition':22s} {'got':>7s} {'lost (had goals)':>18s} "
                     f"{'0-0, harmless':>15s} {'% lost':>8s}")
        for lg in sorted(set(list(gap) + list(per)),
                         key=lambda x: -gap[x]["no_timeline_and_had_goals"]):
            got = per[lg]["matches"]
            lost = gap[lg]["no_timeline_and_had_goals"]
            free = gap[lg]["no_timeline_but_goalless"]
            denom = got + lost
            lines.append(f"{lg:22s} {got:7d} {lost:18d} {free:15d} "
                         f"{lost/max(denom,1)*100:7.1f}%")

    lines.append("")
    lines.append("A match whose goal timeline does not reproduce its final score "
                 "is UNUSABLE for a comeback table and is dropped, not repaired.")
    lines.append("Note: knockout ties are EXPECTED to fail this check when they go "
                 "to extra time, because ESPN's final score includes it. The table "
                 "builder handles those separately rather than dropping them.")
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

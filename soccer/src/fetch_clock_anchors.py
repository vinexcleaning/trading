"""Every timestamped event in a match, so any displayed minute can be located.

THE PROBLEM THIS SOLVES. `price_at_state.py` could only read a price at the
instant of a goal, because a goal is the only thing whose real-world timestamp
was stored. That meant every price ever measured in this folder was *two minutes
after somebody scored*, and the ordinary settled scoreline -- one-nil since the
20th minute, now the 60th, nothing since -- was unmeasured at every minute.
That limitation is recorded at SO026-SO028 and it is what this removes.

WHY NOT JUST ADD 25 MINUTES TO KICKOFF. Because the displayed clock and real
elapsed time come apart badly -- SO009 measured a median gap of 17.5 minutes on
362 events. Halftime is fifteen real minutes during which the displayed clock
does not move at all, and stoppage is real time the displayed minute does not
count.

WHAT MAKES IT SOLVABLE. ESPN stamps `wallclock` on EVERY keyEvent, not just
goals: kickoff, yellow cards, substitutions, halftime, start-2nd-half,
end-regular-time, and stoppages in play. A typical match carries 20 to 30 of
them, spread across both halves. Probed on a 2026-08-02 MLS match: 25 events,
including `kickoff` at 00:42:31 with no clock, `halftime` at 45'+3', and
`start-2nd-half` at 45'. That is a dense set of (displayed minute -> real
instant) pairs, and any minute in between can be placed by interpolating
BETWEEN TWO ANCHORS IN THE SAME HALF -- which never crosses halftime and so
never inherits the error above.

`clock_map.py` does the interpolating and measures its own accuracy by
predicting each anchor from the others. This file only collects.

SCOPE. Only matches inside Kalshi's ~69-day candle window, because a clock map
is useless without a price to attach it to. That is a few hundred matches, not
the 66,000 in the full history.

Read-only, paced, public, unkeyed. No credentials. No orders.
"""
import json
import os
import queue
import sys
import threading
import time
from collections import Counter

import requests

HERE = os.path.dirname(__file__)
ROOT = os.path.join(HERE, "..")
DATA, REP = os.path.join(ROOT, "data"), os.path.join(ROOT, "reports")
GOALS = os.path.join(DATA, "goal_minutes.jsonl")
OUT = os.path.join(DATA, "clock_anchors.jsonl")
SITE = "https://site.api.espn.com/apis/site/v2/sports/soccer"

# See DECISIONS.md: ESPN 403s browser-shaped User-Agents since 2026-08-08.
UA = {}

# Kalshi keeps ~69 days of candles. A little earlier than that costs nothing
# and protects against the window being slightly longer than documented.
FROM_DATE = "2026-05-15"
WORKERS = 6
PACE = 0.10


def get(url, params, tries=4):
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
    """ "77'" -> (77, 0) ; "45'+3'" -> (45, 3). (None, None) if unreadable.

    An unreadable clock must not silently become zero -- an anchor at the wrong
    minute is worse than no anchor, because it drags every interpolation near it.
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

    anchors = []
    for e in ke:
        wc = e.get("wallclock")
        if not wc:
            continue
        typ = (e.get("type") or {}).get("type") or ""
        period = (e.get("period") or {}).get("number")
        minute, stoppage = parse_minute((e.get("clock") or {}).get("displayValue"))

        # KICKOFF is the one anchor with no clock value, and it is the most
        # useful one in the first half -- it pins minute 0 exactly. Give it the
        # minute it actually represents rather than dropping it.
        if typ == "kickoff" and minute is None:
            minute, stoppage, period = 0, 0, 1
        # START-2ND-HALF likewise pins minute 45 of the second period.
        if typ == "start-2nd-half" and minute is None:
            minute, stoppage, period = 45, 0, 2

        if minute is None or period not in (1, 2):
            continue
        anchors.append({
            "type": typ, "period": period,
            "minute": minute, "stoppage": stoppage or 0,
            "wallclock": wc,
        })
    if not anchors:
        return None, "no_anchors"

    return {
        "espn_id": m["espn_id"], "league": m["league"], "date": m["date"],
        "home": m["home"], "away": m["away"],
        "anchors": anchors,
    }, "ok"


def main():
    if not os.path.exists(GOALS):
        sys.exit("run fetch_goal_minutes.py first")

    matches = []
    with open(GOALS, encoding="utf-8") as fh:
        for line in fh:
            try:
                r = json.loads(line)
            except ValueError:
                continue
            if r["date"][:10] >= FROM_DATE:
                matches.append(r)
    print(f"{len(matches)} matches on or after {FROM_DATE}")

    done = set()
    if os.path.exists(OUT):
        with open(OUT, encoding="utf-8") as fh:
            for line in fh:
                try:
                    done.add(json.loads(line)["espn_id"])
                except (ValueError, KeyError):
                    pass
    todo = [m for m in matches if m["espn_id"] not in done]
    print(f"  {len(done)} already fetched, {len(todo)} to go", flush=True)
    if not todo:
        report()
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
                stats[why if row is None else "ok"] += 1
                if row is not None:
                    fh.write(json.dumps(row) + "\n")
                n = sum(stats.values())
                if n % 100 == 0:
                    el = time.time() - t0
                    print(f"  {n}/{len(todo)} | {el/60:.1f} min | "
                          f"eta {(len(todo)-n)*el/max(n,1)/60:.0f} min | "
                          f"{dict(stats)}", flush=True)
            q.task_done()

    ts = [threading.Thread(target=worker, daemon=True) for _ in range(WORKERS)]
    for t in ts:
        t.start()
    for t in ts:
        t.join()
    fh.close()
    print(f"\nDONE in {(time.time()-t0)/60:.1f} min  {dict(stats)}")
    report()


def report():
    rows = []
    with open(OUT, encoding="utf-8") as fh:
        for line in fh:
            try:
                rows.append(json.loads(line))
            except ValueError:
                pass
    per = Counter()
    n_anchor = []
    both_halves = 0
    for r in rows:
        per[r["league"]] += 1
        n_anchor.append(len(r["anchors"]))
        ps = {a["period"] for a in r["anchors"]}
        both_halves += (1 in ps and 2 in ps)
    n_anchor.sort()
    lines = [f"{len(rows)} matches with clock anchors", ""]
    if rows:
        lines.append(f"anchors per match: median {n_anchor[len(n_anchor)//2]}, "
                     f"fewest {n_anchor[0]}, most {n_anchor[-1]}")
        lines.append(f"matches with anchors in BOTH halves: {both_halves} "
                     f"({both_halves/len(rows)*100:.1f}%) -- a match with anchors "
                     f"in only one half can only be placed in that half")
        lines.append("")
        lines.append("by competition:")
        for lg, n in per.most_common():
            lines.append(f"  {lg:24s} {n:5d}")
    txt = "\n".join(lines)
    print("\n" + txt)
    os.makedirs(REP, exist_ok=True)
    with open(os.path.join(REP, "clock_anchors.txt"), "w",
              encoding="utf-8") as fh:
        fh.write(txt + "\n")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "report":
        report()
    else:
        main()

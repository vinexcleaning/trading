"""For every failed fixture, show the ESPN matches on that date in that league.

Guessing aliases from intuition is how a matcher acquires entries that are
wrong in a way nobody notices. This prints the candidate ESPN fixtures on the
same date so each alias is added against evidence.
"""
import json
import os
import sys
from collections import Counter, defaultdict
from datetime import datetime, timedelta

HERE = os.path.dirname(__file__)
sys.path.insert(0, HERE)
import teammatch as TM  # noqa: E402

ROOT = os.path.join(HERE, "..")
DATA = os.path.join(ROOT, "data")
LEAGUE_OF = {"KXLIGAMXGAME": "mex.1", "KXLIGAMXTOTAL": "mex.1",
             "KXARGPREMDIVGAME": "arg.1", "KXDIMAYORGAME": "col.1",
             "KXCOPADOBRASILGAME": "bra.copa_do_brazil",
             "KXMLSGAME": "usa.1"}

join = json.load(open(os.path.join(DATA, "join.json"), encoding="utf-8"))
evs = [json.loads(l) for l in open(os.path.join(DATA, "espn_events.jsonl"),
                                   encoding="utf-8")]

by_league_date = defaultdict(list)
espn_names = defaultdict(set)
for e in evs:
    h, a = TM.teams_from_espn_event(e)
    if not h or not a:
        continue
    d = (e.get("date") or "")[:10]
    by_league_date[(e["_league"], d)].append((h, a))
    espn_names[e["_league"]].add(h)
    espn_names[e["_league"]].add(a)

print("=== ESPN team names available, per league ===")
for lg in sorted(espn_names):
    names = sorted(espn_names[lg])
    print(f"\n{lg} ({len(names)} teams):")
    for n in names:
        print(f"    {n:34s} -> {TM.canon(n)}")

print("\n\n=== failed fixtures, with same-date ESPN candidates ===")
unmatched_tokens = Counter()
for f in join["failed"]:
    lg = LEAGUE_OF.get(f["series"])
    base = datetime.fromisoformat(f["kalshi_date"])
    cands = []
    for off in (0, 1, -1, 2):
        d = (base + timedelta(days=off)).strftime("%Y-%m-%d")
        cands += [(off, h, a) for h, a in by_league_date.get((lg, d), [])]
    print(f"\n{f['series']} {f['kalshi_date']}  "
          f"KALSHI: {f['team_a']!r} vs {f['team_b']!r}  -> {f['pair']}")
    if not cands:
        print("    no ESPN match on that date at all "
              "(outside the scoreboard window, or league mismatch)")
        unmatched_tokens["NO_ESPN_FIXTURE"] += 1
        continue
    for off, h, a in cands[:6]:
        print(f"    ESPN off={off:+d}: {h!r} vs {a!r} -> "
              f"({TM.canon(h)}, {TM.canon(a)})")

print("\n\n=== summary of failure causes ===")
print(dict(unmatched_tokens))

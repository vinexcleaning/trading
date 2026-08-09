"""How good was each team, on the day, knowing only what was knowable then.

THE CHOICE THIS FILE MAKES, AND WHY.

The user's example is the whole reason this dimension exists: first place 1-0
down to last place in the 80th minute is not the same bet as last place 1-0 down
to first place. A blanket comeback rate averages those together and hides
exactly the thing worth knowing.

Two candidate measures of "how good is this team":

  1. WHERE THEY SAT IN THE LEAGUE TABLE.
  2. WHAT THE BETTING MARKET THOUGHT before kickoff.

**The market price is the sharper of the two and is deliberately NOT the spine.**
It exists on 53 of 160 matches in soccer/dataset.md -- a third of a 69-day
window -- against a table spanning about ten years. A column present on well
under one percent of rows cannot be a column of a lookup table. It is kept as a
cross-check on the recent slice. `build_comeback_table.py` reports both where
both exist.

WHY NOT LITERAL LEAGUE POSITION. The first version of this file cut the fixture
list into seasons on a long gap and ranked teams within a season. It was thrown
away after measuring the gaps: Colombia's break between Apertura and Clausura is
41 to 48 days, so ANY threshold in that region splits some campaigns and merges
others, and the choice would be mine rather than the data's. A number that
depends on a threshold I picked is a number I fitted.

WHAT IS USED INSTEAD -- and it needs no threshold at all:

  * A team's strength on a date is its points per game over its **last WINDOW
    matches in that competition**, ending strictly before this one.
  * Teams are ranked against every other team that has played in the same
    competition within ACTIVE_DAYS -- i.e. against the league as it stands that
    week, not against clubs that were relegated four years ago.
  * That ranking is cut into thirds, which is the "top of the table / bottom of
    the table" language the question is actually asked in.
  * Fewer than MIN_MATCHES played, or fewer than MIN_RANKED teams to rank
    against, and the reading is "unknown". It is never guessed.

This also fixes two things the season version got wrong for free: cup ties and
international friendlies have no league table at all, and a rolling window gives
them a reading where a season position could not.

KNOWABILITY. Only matches strictly before this one, in the same competition.
Enforced by construction -- fixtures are walked in date order and the standing is
READ before the match is APPLIED -- and re-checked from scratch by
`test_no_lookahead()`, which rebuilds a sample independently and asserts it
agrees. That check is the reason to trust the rest.

Read-only. No network. No credentials.
"""
import json
import os
import sys
from collections import Counter, defaultdict, deque
from datetime import datetime

HERE = os.path.dirname(__file__)
ROOT = os.path.join(HERE, "..")
DATA, REP = os.path.join(ROOT, "data"), os.path.join(ROOT, "reports")
SRC = os.path.join(DATA, "espn_history", "matches.jsonl")
OUT = os.path.join(DATA, "strength.json")

WINDOW = 20          # matches in the rolling form window (the primary reading)
WINDOW_ALT = 10      # a second window, reported so nothing hinges on the first
MIN_MATCHES = 5      # below this, a team has no reading
ACTIVE_DAYS = 120    # a team is "in the league now" if it played this recently
MIN_RANKED = 6       # fewer teams than this to rank against -> no reading


def load_matches():
    rows = []
    with open(SRC, encoding="utf-8") as fh:
        for line in fh:
            try:
                m = json.loads(line)
            except ValueError:
                continue
            if not m.get("completed"):
                continue
            if m.get("home_goals") is None or m.get("away_goals") is None:
                continue
            rows.append(m)
    rows.sort(key=lambda m: (m["date"], m["espn_id"]))
    return rows


def day(m):
    return m["date"][:10]


def _pts(gf, ga):
    return 3 if gf > ga else (1 if gf == ga else 0)


def _ppg(dq, n):
    """Points per game over the last n entries of a deque of point values."""
    if len(dq) < MIN_MATCHES:
        return None
    last = list(dq)[-n:]
    return round(sum(last) / len(last), 4)


def build(rows=None):
    # The caller may pass the row list so that build() and the no-lookahead
    # check see EXACTLY the same fixtures. They did not, once: the ESPN
    # backfill was still appending to matches.jsonl between the two loads, the
    # check found a team with 20 prior matches where build() had seen 4, and it
    # reported a look-ahead leak that was really a growing file. A canary that
    # cries wolf gets switched off, so the race is closed rather than tolerated.
    if rows is None:
        rows = load_matches()

    # league -> team -> deque of points from that team's recent matches
    form = defaultdict(lambda: defaultdict(lambda: deque(maxlen=WINDOW)))
    last_played = defaultdict(dict)          # league -> team -> date
    out, stats = {}, Counter()

    for m in rows:
        lg, h, a = m["league"], m["home"], m["away"]
        d = datetime.strptime(day(m), "%Y-%m-%d")

        # ---------- READ. Only matches already applied, i.e. strictly earlier.
        active = []
        for tm, ld in last_played[lg].items():
            if (d - ld).days <= ACTIVE_DAYS and len(form[lg][tm]) >= MIN_MATCHES:
                v = _ppg(form[lg][tm], WINDOW)
                if v is not None:
                    active.append((v, tm))
        active.sort(key=lambda x: (-x[0], x[1]))
        n = len(active)
        pos = {tm: i for i, (_, tm) in enumerate(active)}

        def tier(team):
            if n < MIN_RANKED or team not in pos:
                return "unknown"
            frac = pos[team] / n
            return ("top third" if frac < 1 / 3 else
                    "middle third" if frac < 2 / 3 else "bottom third")

        out[m["espn_id"]] = {
            "league": lg, "date": day(m),
            "teams_ranked": n,
            "home_tier": tier(h), "away_tier": tier(a),
            "home_ppg": _ppg(form[lg][h], WINDOW),
            "away_ppg": _ppg(form[lg][a], WINDOW),
            "home_ppg_alt": _ppg(form[lg][h], WINDOW_ALT),
            "away_ppg_alt": _ppg(form[lg][a], WINDOW_ALT),
            "home_pos": pos.get(h), "away_pos": pos.get(a),
            "home_played": len(form[lg][h]), "away_played": len(form[lg][a]),
        }
        r = out[m["espn_id"]]
        stats[f"home={r['home_tier']}"] += 1
        if r["home_tier"] != "unknown" and r["away_tier"] != "unknown":
            stats["both known"] += 1

        # ---------- APPLY. Nothing above this line may see it.
        hg, ag = m["home_goals"], m["away_goals"]
        form[lg][h].append(_pts(hg, ag))
        form[lg][a].append(_pts(ag, hg))
        last_played[lg][h] = d
        last_played[lg][a] = d

    os.makedirs(DATA, exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(out, fh)

    both = stats["both known"]
    lines = [
        f"{len(out)} matches given a team-strength reading",
        f"  rolling window {WINDOW} matches (second reading at {WINDOW_ALT})",
        f"  a team needs {MIN_MATCHES} played, and {MIN_RANKED} rivals active "
        f"within {ACTIVE_DAYS} days, or it reads 'unknown'",
        "",
        f"BOTH teams' strength known on {both} of {len(out)} matches "
        f"({both/max(len(out),1)*100:.1f}%). The rest keep an 'unknown' bucket "
        f"in the table rather than being guessed or dropped.",
        "",
        "by competition:",
        f"  {'competition':22s} {'matches':>8s} {'both known':>11s} {'%':>6s}",
    ]
    per = defaultdict(Counter)
    for v in out.values():
        per[v["league"]]["n"] += 1
        if v["home_tier"] != "unknown" and v["away_tier"] != "unknown":
            per[v["league"]]["both"] += 1
    for lg in sorted(per, key=lambda x: -per[x]["n"]):
        p = per[lg]
        lines.append(f"  {lg:22s} {p['n']:8d} {p['both']:11d} "
                     f"{p['both']/max(p['n'],1)*100:5.1f}%")
    txt = "\n".join(lines)
    print(txt)
    os.makedirs(REP, exist_ok=True)
    with open(os.path.join(REP, "strength_build.txt"), "w",
              encoding="utf-8") as fh:
        fh.write(txt + "\n")
    print(f"\nwrote {OUT}")
    return out


def test_no_lookahead(rows=None, built=None):
    """The canary that matters: a reading must never use its own match.

    Rebuilds a sample of readings from scratch out of the raw fixture list,
    using only matches strictly earlier, and asserts they equal what build()
    wrote. If build() ever leaked the current or a later result, these disagree.

    Pass the same `rows` build() used. Re-reading the file here is only safe
    when nothing is writing to it.
    """
    if rows is None:
        rows = load_matches()
    if built is None:
        with open(OUT, encoding="utf-8") as fh:
            built = json.load(fh)

    by_lg = defaultdict(list)
    for m in rows:
        by_lg[m["league"]].append(m)

    checked = bad = 0
    for lg, ms in by_lg.items():
        step = max(len(ms) // 25, 1)
        for i in range(0, len(ms), step):
            m = ms[i]
            hist = []
            for e in ms[:i]:                     # strictly earlier ONLY
                if e["home"] == m["home"]:
                    hist.append(_pts(e["home_goals"], e["away_goals"]))
                elif e["away"] == m["home"]:
                    hist.append(_pts(e["away_goals"], e["home_goals"]))
            exp = (round(sum(hist[-WINDOW:]) / len(hist[-WINDOW:]), 4)
                   if len(hist) >= MIN_MATCHES else None)
            got = built.get(m["espn_id"], {}).get("home_ppg")
            checked += 1
            if exp != got:
                bad += 1
                if bad <= 5:
                    print(f"  LEAK? {lg} {day(m)} {m['home']}: "
                          f"independent={exp} built={got}")
    assert bad == 0, (f"team strength disagrees with an independent replay on "
                      f"{bad} of {checked} sampled matches -- a look-ahead leak")
    print(f"no-lookahead check: {checked} sampled matches, all agree")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "test":
        test_no_lookahead()
    else:
        shared = load_matches()
        built = build(shared)
        test_no_lookahead(shared, built)

"""The comeback table. Descriptive. It reports; it does not choose.

THE QUESTION. Late in a match one team is ahead. You bet against the team that
is behind, which pays if the leader wins or if it finishes level. So the whole
bet is one number: out of 100 matches sitting in that exact state, how often
does the trailing team come back and win outright?

WHAT THIS IS NOT. It is not a search for the best-looking cell, and it will not
name one. Slice minute x scoreline x strength x competition and you get
thousands of cells; the best few will look wonderful with nothing behind them.
That is not a worry, it is a measurement -- LEDGER.md B023 ran 2,008
pre-registered cells in this repo and the best of them came in BELOW the same
machinery run on shuffled data. So every cell carries the number of matches
behind it, nothing is ranked, and the summary refuses to nominate a winner.

THE UNIT OF OBSERVATION IS THE MATCH. One match contributes at most one
observation to any one cell. It does contribute to many DIFFERENT cells -- it
passes through minute 80 and minute 85 and it is in both -- so cells are heavily
correlated with each other and the per-cell counts must never be added up as
though they were separate matches. The report says so where it could mislead.

WHAT COUNTS AS A COMEBACK. The trailing team WINS AT FULL TIME. A draw is not a
comeback: betting against the trailing team pays on a draw.

REGULATION, NOT EXTRA TIME. The state and the result are both read at 90
minutes plus stoppage. A knockout tie that goes to extra time is scored on the
regulation result, and the count of matches where extra time changed the answer
is reported rather than buried. Goals in stoppage carry the minute of the half
they belong to (a "90'+4'" goal is minute 90), which is what the clock on the
screen says.

THE HELD-OUT YEARS. Everything from HOLDOUT_FROM onward is excluded and not
looked at. The table describes earlier years only. That is what makes it
possible to test a pocket properly afterwards: if the table had already used
every year, there would be nothing clean left to check it against.

Read-only. No network. No credentials. No orders.
"""
import csv
import json
import math
import os
import sys
from collections import Counter, defaultdict

HERE = os.path.dirname(__file__)
ROOT = os.path.join(HERE, "..")
DATA, REP = os.path.join(ROOT, "data"), os.path.join(ROOT, "reports")

GOALS = os.path.join(DATA, "goal_minutes.jsonl")
STRENGTH = os.path.join(DATA, "strength.json")

HOLDOUT_FROM = "2025-01-01"   # this date and later is never read
MINUTES = list(range(1, 91))
REPORT_MINUTES = [45, 60, 65, 70, 75, 80, 82, 85, 87, 88, 89, 90]

TIERS = ["top third", "middle third", "bottom third", "unknown"]


# ---------------------------------------------------------------- arithmetic

def wilson(k, n, z=1.96):
    """The range the true rate could plausibly sit in, given k out of n.

    Named after its author in the literature; described to the reader as "the
    range it could really be". Used instead of k/n +- something because at the
    rates that matter here -- two or three in a hundred -- the simple version
    produces ranges that include negative numbers.
    """
    if n == 0:
        return (0.0, 1.0)
    p = k / n
    d = 1 + z * z / n
    c = p + z * z / (2 * n)
    s = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return (max(0.0, (c - s) / d), min(1.0, (c + s) / d))


def breakeven_rate(price_cents):
    """How often the trailing side may come back before this price loses money.

    Uses the repo's single fee implementation. Held to settlement, so the entry
    fee only. GUARDS #6: fee arithmetic has exactly one home and this is not it.
    """
    sys.path.insert(0, os.path.join(ROOT, "..", "common"))
    import kalshi_fees as F
    fee = float(F.roundtrip_cost_cents(price_cents))
    win = 100 - price_cents - fee
    lose = price_cents + fee
    return win / (win + lose)


# ------------------------------------------------------------------- loading

def load():
    strength = {}
    if os.path.exists(STRENGTH):
        with open(STRENGTH, encoding="utf-8") as fh:
            strength = json.load(fh)

    matches, stats = [], Counter()
    with open(GOALS, encoding="utf-8") as fh:
        for line in fh:
            try:
                r = json.loads(line)
            except ValueError:
                stats["unparseable_line"] += 1
                continue
            stats["rows"] += 1

            date = (r.get("date") or "")[:10]
            if not date:
                stats["dropped: no date"] += 1
                continue
            if date >= HOLDOUT_FROM:
                stats["held out (not looked at)"] += 1
                continue

            goals = [e for e in r["events"] if e["kind"] == "goal"]
            if any(g["minute"] is None for g in goals):
                stats["dropped: a goal with no readable minute"] += 1
                continue

            # Sides come from ESPN team ids, resolved at fetch time. Matching on
            # display name broke on bra.1, where the scoreboard and the summary
            # call the same club two different things.
            if any(g.get("side") not in ("home", "away") for g in goals):
                stats["dropped: a goal credited to neither side"] += 1
                continue

            # Regulation result, from the timeline.
            reg_h = sum(1 for g in goals if g["side"] == "home" and g["minute"] <= 90)
            reg_a = sum(1 for g in goals if g["side"] == "away" and g["minute"] <= 90)
            # Full-time result as ESPN reports it, which includes extra time.
            ft_h, ft_a = r.get("home_goals"), r.get("away_goals")

            all_h = sum(1 for g in goals if g["side"] == "home")
            all_a = sum(1 for g in goals if g["side"] == "away")
            if ft_h is None or ft_a is None:
                stats["dropped: no final score"] += 1
                continue
            if (all_h, all_a) != (ft_h, ft_a):
                # The timeline does not reproduce the score even counting every
                # goal. The match cannot be replayed and is dropped, not patched.
                stats["dropped: timeline disagrees with final score"] += 1
                continue
            if (reg_h, reg_a) != (ft_h, ft_a):
                stats["extra time changed the score"] += 1

            st = strength.get(r["espn_id"], {})
            matches.append({
                "espn_id": r["espn_id"], "league": r["league"], "date": date,
                "goals": sorted(goals, key=lambda g: g["minute"]),
                "reg_h": reg_h, "reg_a": reg_a,
                "home_tier": st.get("home_tier", "unknown"),
                "away_tier": st.get("away_tier", "unknown"),
                "has_strength": bool(st),
            })
            stats["usable"] += 1
    return matches, stats


# ------------------------------------------------------------------ the walk

def observations(m):
    """Yield one observation per minute the match spends with someone ahead.

    An observation is: at this minute the score was X-Y in the leader's favour,
    the leader was this good and the trailer that good -- and did the trailer go
    on to win in regulation?
    """
    reg_h, reg_a = m["reg_h"], m["reg_a"]
    goals = m["goals"]
    gi = 0
    h = a = 0
    for minute in MINUTES:
        while gi < len(goals) and goals[gi]["minute"] <= minute:
            if goals[gi]["side"] == "home":
                h += 1
            else:
                a += 1
            gi += 1
        if h == a:
            continue
        if h > a:
            lead, trail = h, a
            leader_tier, trailer_tier = m["home_tier"], m["away_tier"]
            trailer_won = reg_a > reg_h
        else:
            lead, trail = a, h
            leader_tier, trailer_tier = m["away_tier"], m["home_tier"]
            trailer_won = reg_h > reg_a
        yield {
            "minute": minute, "lead": lead, "trail": trail,
            "leader_tier": leader_tier, "trailer_tier": trailer_tier,
            "league": m["league"], "trailer_won": trailer_won,
        }


# ------------------------------------------------------------------ the table

def tally(matches):
    """cells[key] = [comebacks, matches]. Key order is fixed and documented."""
    cells = defaultdict(lambda: [0, 0])
    for m in matches:
        for o in observations(m):
            for key in (
                ("ALL", o["minute"], o["lead"], o["trail"], "ALL", "ALL", "ALL"),
                ("ALL", o["minute"], o["lead"], o["trail"], "ALL", "ALL",
                 o["league"]),
                ("ALL", o["minute"], o["lead"], o["trail"],
                 o["leader_tier"], o["trailer_tier"], "ALL"),
                ("ALL", o["minute"], o["lead"], o["trail"],
                 o["leader_tier"], o["trailer_tier"], o["league"]),
            ):
                c = cells[key]
                c[0] += o["trailer_won"]
                c[1] += 1
    return cells


MIN_MATCHES_FOR_REPORT = 30


def write_csv(cells, path, min_matches=0):
    """Write the grid. `min_matches` trims cells too thin to mean anything.

    THE FULL GRID DOES NOT GO IN `reports/`. That directory is committed and
    this repo is PUBLIC, and the full grid is minute x scoreline x 16 strength
    pairs x 25 competitions -- hundreds of thousands of rows, most of them
    holding two or three matches. It goes to `data/`, which is gitignored. The
    committed copy is trimmed to cells with at least `min_matches` behind them,
    which is also the only version worth a human opening.
    """
    rows = 0
    with open(path, "w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["minute", "leader_goals", "trailer_goals",
                    "leader_strength", "trailer_strength", "competition",
                    "matches", "comebacks", "comebacks_per_100",
                    "could_really_be_low_per_100", "could_really_be_high_per_100"])
        for key in sorted(cells, key=lambda k: (k[6], k[1], -k[2], k[3], k[4], k[5])):
            _, minute, lead, trail, lt, tt, lg = key
            k, n = cells[key]
            if n < min_matches:
                continue
            lo, hi = wilson(k, n)
            w.writerow([minute, lead, trail, lt, tt, lg, n, k,
                        f"{k/n*100:.2f}", f"{lo*100:.2f}", f"{hi*100:.2f}"])
            rows += 1
    return rows


# ----------------------------------------------------------------- reporting

def pct(k, n):
    return f"{k/n*100:.1f}" if n else "-"


def section_by_minute_and_lead(cells, out):
    out.append("")
    out.append("=" * 78)
    out.append("1. EVERY COMPETITION TOGETHER, EVERY STRENGTH TOGETHER")
    out.append("=" * 78)
    out.append("")
    out.append("Out of 100 matches sitting at this minute with this lead, how")
    out.append("many times did the team behind come back and win?")
    out.append("")
    out.append("Bigger is WORSE for this bet. Break-even at 97 cents is 2.80.")
    out.append("")
    hdr = f"{'minute':>7s} |"
    for lead_gap in (1, 2, 3):
        hdr += f"{'behind by ' + str(lead_gap):>26s} |"
    out.append(hdr)
    out.append(f"{'':>7s} |" + ("{:>13s}{:>13s} |".format("per 100", "matches")) * 3)
    out.append("-" * len(hdr))
    for minute in REPORT_MINUTES:
        row = f"{minute:>7d} |"
        for gap in (1, 2, 3):
            k = n = 0
            for key, (kk, nn) in cells.items():
                if (key[1] == minute and key[4] == "ALL" and key[6] == "ALL"
                        and key[2] - key[3] == gap):
                    k += kk
                    n += nn
            row += f"{pct(k, n):>13s}{n:>13d} |"
        out.append(row)
    out.append("")
    out.append("A match appears at every minute it was in that state, so the")
    out.append("match counts down a column are the SAME matches over and over.")
    out.append("Never add them up.")


def section_scorelines(cells, out):
    out.append("")
    out.append("=" * 78)
    out.append("2. THE EXACT SCORELINE MATTERS, NOT JUST THE GAP")
    out.append("=" * 78)
    out.append("")
    out.append("1-0 and 3-2 are both 'one goal up' and are not the same match.")
    out.append("")
    out.append(f"{'minute':>7s} {'score':>8s} {'matches':>9s} {'per 100':>9s} "
               f"{'could really be':>20s}")
    out.append("-" * 60)
    for minute in (70, 75, 80, 85, 88, 90):
        seen = []
        for key, (k, n) in cells.items():
            if key[1] == minute and key[4] == "ALL" and key[6] == "ALL" and n >= 200:
                seen.append((key[2], key[3], k, n))
        for lead, trail, k, n in sorted(seen, key=lambda x: (-x[3])):
            lo, hi = wilson(k, n)
            out.append(f"{minute:>7d} {f'{lead}-{trail}':>8s} {n:>9d} "
                       f"{pct(k, n):>9s} {f'{lo*100:.1f} to {hi*100:.1f}':>20s}")
        out.append("")


def section_strength(cells, out, minute=80):
    out.append("=" * 78)
    out.append(f"3. DOES IT MATTER HOW GOOD THE TWO TEAMS ARE?  (minute {minute}, 1-0)")
    out.append("=" * 78)
    out.append("")
    out.append("This is the question the user asked for by name: first place")
    out.append("1-0 down to last place is not the same bet as the reverse.")
    out.append("")
    out.append("Rows are how good the team IN FRONT is. Columns are how good the")
    out.append("team BEHIND is. Bigger is WORSE for this bet.")
    out.append("")
    hdr = f"{'leader is':>14s} |"
    for tt in TIERS:
        hdr += f"{'behind: ' + tt:>26s} |"
    out.append(hdr)
    out.append(f"{'':>14s} |" + ("{:>13s}{:>13s} |".format("per 100", "matches")) * len(TIERS))
    out.append("-" * len(hdr))
    for lt in TIERS:
        row = f"{lt:>14s} |"
        for tt in TIERS:
            k = n = 0
            for key, (kk, nn) in cells.items():
                if (key[1] == minute and key[2] == 1 and key[3] == 0
                        and key[4] == lt and key[5] == tt and key[6] == "ALL"):
                    k += kk
                    n += nn
            row += f"{pct(k, n):>13s}{n:>13d} |"
        out.append(row)
    out.append("")


def section_by_competition(cells, out, minute=80):
    out.append("=" * 78)
    out.append(f"4. BY COMPETITION  (minute {minute}, one goal up, any strength)")
    out.append("=" * 78)
    out.append("")
    out.append("An international friendly is a different sport for this purpose:")
    out.append("six substitutions, and nobody is trying. It is listed on its own.")
    out.append("")
    out.append(f"{'competition':>22s} {'matches':>9s} {'per 100':>9s} "
               f"{'could really be':>20s}")
    out.append("-" * 64)
    rows = []
    for key, (k, n) in cells.items():
        if (key[1] == minute and key[2] == 1 and key[3] == 0
                and key[4] == "ALL" and key[6] != "ALL"):
            rows.append((key[6], k, n))
    for lg, k, n in sorted(rows, key=lambda x: -x[2]):
        lo, hi = wilson(k, n)
        out.append(f"{lg:>22s} {n:>9d} {pct(k, n):>9s} "
                   f"{f'{lo*100:.1f} to {hi*100:.1f}':>20s}")
    out.append("")
    out.append("These are DIFFERENT matches from each other, so unlike the")
    out.append("columns above, these counts may be added up.")


def section_sanity(matches, out):
    """The naive benchmark, in a form a football fan can check by eye.

    Everything in this report is derived from replayed timelines. If the replay
    is wrong, the comeback rates are wrong in a way that still looks completely
    normal. So the same replay is asked a question whose answer is already
    common knowledge: how often does the home team win? Anyone who watches
    football knows it is a bit under half, with draws around a quarter. If these
    come out at 30% or 70%, nothing else on this page should be believed.
    """
    out.append("")
    out.append("=" * 78)
    out.append("6. A CHECK YOU CAN DO IN YOUR HEAD")
    out.append("=" * 78)
    out.append("")
    out.append("Everything above comes from replaying matches minute by minute.")
    out.append("If that replay is broken, the comeback numbers would be wrong")
    out.append("AND would still look perfectly reasonable. So here is the same")
    out.append("replay answering something you already know the answer to:")
    out.append("how often does the home team win?")
    out.append("")
    out.append("If these are not roughly 'home wins a bit under half, draws")
    out.append("about a quarter', something is broken and nothing above counts.")
    out.append("")
    out.append(f"{'competition':>22s} {'matches':>9s} {'home wins':>10s} "
               f"{'draws':>8s} {'away wins':>10s}")
    out.append("-" * 62)
    per = defaultdict(Counter)
    for m in matches:
        c = per[m["league"]]
        c["n"] += 1
        if m["reg_h"] > m["reg_a"]:
            c["h"] += 1
        elif m["reg_h"] < m["reg_a"]:
            c["a"] += 1
        else:
            c["d"] += 1
        t = per["ALL"]
        t["n"] += 1
        t["h" if m["reg_h"] > m["reg_a"] else
          ("a" if m["reg_h"] < m["reg_a"] else "d")] += 1
    for lg in ["ALL"] + sorted((k for k in per if k != "ALL"),
                               key=lambda x: -per[x]["n"]):
        c = per[lg]
        out.append(f"{lg:>22s} {c['n']:>9d} {pct(c['h'], c['n']):>9s}% "
                   f"{pct(c['d'], c['n']):>7s}% {pct(c['a'], c['n']):>9s}%")
    out.append("")
    out.append("(These are results at 90 minutes, so a cup tie decided in extra")
    out.append("time counts as the draw it was at 90.)")


def section_breakeven(out):
    out.append("")
    out.append("=" * 78)
    out.append("5. WHAT THE NUMBER HAS TO BEAT")
    out.append("=" * 78)
    out.append("")
    out.append("Computed from this repo's one fee implementation, held to")
    out.append("settlement. Bigger is better for you -- it means you can afford")
    out.append("more comebacks before the bet loses money.")
    out.append("")
    out.append(f"{'you pay':>9s} {'if you did it 100 times':>44s} "
               f"{'comebacks allowed per 100':>27s}")
    out.append("-" * 82)
    for p in (90, 93, 95, 96, 97, 98):
        b = breakeven_rate(p) * 100
        shape = f"win {100-p} cents {int(round(100-b))}x, lose {p} cents {int(round(b))}x"
        out.append(f"{str(p) + ' cents':>9s} {shape:>44s} {b:>27.2f}")
    out.append("")
    out.append("The price is not in this table yet. Kalshi keeps about 69 days")
    out.append("of market history, so a real price can only be attached to very")
    out.append("recent matches -- that is a separate job on a much smaller set.")


def main():
    matches, stats = load()
    if not matches:
        sys.exit("no usable matches -- has fetch_goal_minutes.py finished?")

    cells = tally(matches)
    os.makedirs(REP, exist_ok=True)
    full_path = os.path.join(DATA, "comeback_table_full.csv")
    csv_path = os.path.join(REP, "comeback_table.csv")
    n_full = write_csv(cells, full_path)
    n_trim = write_csv(cells, csv_path, MIN_MATCHES_FOR_REPORT)

    leagues = Counter(m["league"] for m in matches)
    years = Counter(m["date"][:4] for m in matches)

    out = []
    out.append("THE COMEBACK TABLE")
    out.append("=" * 78)
    out.append("")
    out.append("How often does a team that is behind late in a match come back")
    out.append("and win? Every minute, every scoreline, every competition.")
    out.append("")
    out.append("This is a description, not a recommendation. No cell is")
    out.append("nominated, nothing is ranked, and the number of matches behind")
    out.append("every cell is printed next to it.")
    out.append("")
    out.append(f"Matches used: {len(matches)}")
    out.append(f"Years: {min(years)} to {max(years)}  "
               f"(everything from {HOLDOUT_FROM} is held back and NOT looked at)")
    out.append("")
    out.append("Competitions:")
    for lg, n in leagues.most_common():
        out.append(f"    {lg:24s} {n:6d}")
    out.append("")
    out.append("What was thrown away, and why:")
    for k in sorted(stats):
        out.append(f"    {k:48s} {stats[k]:7d}")

    section_by_minute_and_lead(cells, out)
    section_scorelines(cells, out)
    section_strength(cells, out, minute=80)
    section_by_competition(cells, out, minute=80)
    section_breakeven(out)
    section_sanity(matches, out)

    out.append("")
    out.append("=" * 78)
    out.append(f"reports/comeback_table.csv -- {n_trim} cells, every one with at")
    out.append(f"least {MIN_MATCHES_FOR_REPORT} matches behind it. This is the one to open.")
    out.append(f"data/comeback_table_full.csv -- all {n_full} cells including the")
    out.append("thin ones. Not committed: most of it is cells holding two or")
    out.append("three matches, and this repo is public.")
    out.append("=" * 78)

    txt = "\n".join(out)
    print(txt)
    with open(os.path.join(REP, "comeback_table.txt"), "w",
              encoding="utf-8") as fh:
        fh.write(txt + "\n")
    print(f"\nwrote reports/comeback_table.txt and {os.path.basename(csv_path)}")


if __name__ == "__main__":
    main()

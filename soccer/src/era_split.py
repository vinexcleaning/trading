"""Has the comeback rate changed over the ten years the table averages?

WHY THIS EXISTS. The comeback rates are 2015-2024. Every Kalshi price is from a
69-day window in 2026. Turning a ten-year rate into a "fair price" for 2026 is a
HYPOTHESIS ABOUT 2026, not a measurement of it, and this file is the cheapest
available check on how bad that assumption is.

There is a specific reason to worry rather than a general one. **Five
substitutes became permanent in 2022.** More fresh legs late in a match is
exactly the kind of change that would move late comeback rates, and it lands
inside the window being averaged. If the recent years look like the old ones,
the ten-year rate is a reasonable stand-in. If they do not, every "fair price"
computed from the ten-year number is wrong and the recent slice must be used
instead -- at the cost of a much smaller sample.

**This does not touch the held-out years.** 2025 and 2026 stay shut. The recent
slice here is 2022-2024, which is inside the descriptive period the table
already used.

Reuses `build_comeback_table`'s own replay so the two cannot drift apart.

Read-only. No network. No credentials.
"""
import os
import sys
from collections import defaultdict

HERE = os.path.dirname(__file__)
sys.path.insert(0, HERE)
import build_comeback_table as B    # noqa: E402

ROOT = os.path.join(HERE, "..")
REP = os.path.join(ROOT, "reports")

ERAS = [("2015-2018", "2015", "2018"),
        ("2019-2021", "2019", "2021"),
        ("2022-2024", "2022", "2024")]
STATES = [(1, 0), (2, 1), (2, 0), (3, 2)]
SHOW_MINUTES = [15, 25, 35, 45, 55, 65, 70, 75, 80, 85, 89]


def main():
    matches, stats = B.load()
    if not matches:
        sys.exit("no usable matches -- run the pipeline first")

    # cells[(era, minute, lead, trail)] = [comebacks, matches]
    cells = defaultdict(lambda: [0, 0])
    per_era_matches = defaultdict(int)
    for m in matches:
        y = m["date"][:4]
        era = None
        for name, lo, hi in ERAS:
            if lo <= y <= hi:
                era = name
                break
        if era is None:
            continue
        per_era_matches[era] += 1
        for o in B.observations(m):
            c = cells[(era, o["minute"], o["lead"], o["trail"])]
            c[0] += o["trailer_won"]
            c[1] += 1

    out = []
    out.append("HAS THE COMEBACK RATE CHANGED OVER TEN YEARS?")
    out.append("=" * 78)
    out.append("")
    out.append("Why it matters: every Kalshi price in this folder is from 2026,")
    out.append("and the comeback rates are an average of 2015-2024. If the game")
    out.append("has changed, that average is the wrong thing to price against.")
    out.append("")
    out.append("Five substitutes became permanent in 2022, which is the specific")
    out.append("reason to look rather than a general worry.")
    out.append("")
    for name, lo, hi in ERAS:
        out.append(f"    {name}: {per_era_matches[name]:6d} matches")
    out.append("")
    out.append("Out of 100 matches in that state, how often the team behind")
    out.append("came back and won. Bigger is worse for betting against them.")
    out.append("")

    for lead, trail in STATES:
        out.append("-" * 78)
        out.append(f"SCORE {lead}-{trail}")
        out.append("-" * 78)
        hdr = f"{'minute':>7s} |"
        for name, _, _ in ERAS:
            hdr += f"{name:>22s} |"
        out.append(hdr)
        out.append(f"{'':>7s} |" + ("{:>11s}{:>11s} |".format("per 100", "matches")) * len(ERAS))
        for minute in SHOW_MINUTES:
            row = f"{minute:>7d} |"
            for name, _, _ in ERAS:
                k, n = cells.get((name, minute, lead, trail), [0, 0])
                row += f"{(f'{k/n*100:.1f}' if n else '-'):>11s}{n:>11d} |"
            out.append(row)
        out.append("")

    # The single comparison that decides whether the ten-year rate is usable.
    out.append("=" * 78)
    out.append("THE ONE THAT DECIDES IT")
    out.append("=" * 78)
    out.append("")
    out.append("For each state and minute, the oldest era against the newest,")
    out.append("with the range each could really be. If the ranges overlap, the")
    out.append("ten-year average is a fair stand-in for today. If they do not,")
    out.append("it is not.")
    out.append("")
    out.append(f"{'minute':>7s} {'score':>7s} {'2015-2018':>22s} {'2022-2024':>22s} "
               f"{'overlap?':>10s}")
    out.append("-" * 74)
    disagree = agree = 0
    for lead, trail in STATES:
        for minute in SHOW_MINUTES:
            ko, no_ = cells.get(("2015-2018", minute, lead, trail), [0, 0])
            kn, nn = cells.get(("2022-2024", minute, lead, trail), [0, 0])
            if no_ < 200 or nn < 200:
                continue
            lo1, hi1 = B.wilson(ko, no_)
            lo2, hi2 = B.wilson(kn, nn)
            ov = not (hi1 < lo2 or hi2 < lo1)
            agree += ov
            disagree += (not ov)
            out.append(
                f"{minute:>7d} {f'{lead}-{trail}':>7s} "
                f"{f'{ko/no_*100:.1f}  ({lo1*100:.1f}-{hi1*100:.1f})':>22s} "
                f"{f'{kn/nn*100:.1f}  ({lo2*100:.1f}-{hi2*100:.1f})':>22s} "
                f"{'yes' if ov else 'NO':>10s}")
    out.append("")
    out.append(f"**{agree} of {agree+disagree} comparisons overlap.**")
    out.append("")
    if disagree == 0:
        out.append("Every one overlaps, so nothing here says the game has changed")
        out.append("in a way that moves this bet. That is NOT proof it has not --")
        out.append("it is the absence of a detectable change at these sample")
        out.append("sizes, and small real changes would not show up.")
    else:
        out.append("Some do not overlap. Where they do not, the ten-year average")
        out.append("should not be used as a 2026 fair price -- use 2022-2024.")

    txt = "\n".join(out)
    print(txt)
    os.makedirs(REP, exist_ok=True)
    with open(os.path.join(REP, "era_split.txt"), "w", encoding="utf-8") as fh:
        fh.write(txt + "\n")
    print("\nwrote reports/era_split.txt")


if __name__ == "__main__":
    main()

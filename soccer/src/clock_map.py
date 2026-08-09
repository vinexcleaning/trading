"""Turn "the 25th minute" into a real instant, and measure how wrong it is.

THE RULE. Interpolate only BETWEEN TWO ANCHORS IN THE SAME HALF. Never across
halftime, never from kickoff alone. Inside one half the displayed clock and real
time advance together, minute for minute; the things that break that -- the
fifteen-minute interval, first-half stoppage, a long delay -- are either outside
the half or are themselves anchors.

WHY THIS IS ALLOWED WHEN SO009 SAID THE CLOCK IS 17.5 MINUTES OUT. SO009
measured `kickoff + displayed minute`, which walks straight through halftime and
through every minute of stoppage. That number is correct and it is a measurement
of a DIFFERENT method. This one never extrapolates further than the nearest
anchor in the same half, and a typical match here carries 20-30 anchors.

**And it does not ask to be believed.** `measure_accuracy()` hides each anchor
in turn, predicts its instant from the others, and reports the error. If that
error is not small, this file is wrong and the number says so.

WHAT IS DELIBERATELY NOT DONE. No match is placed using anchors from a different
match, no half is placed using the other half's anchors, and a minute outside
the anchored range is extrapolated at 60 seconds per minute only as far as
MAX_EXTRAPOLATE_MIN. Past that it returns None. A guessed instant reads a real
price off the wrong moment, which is worse than no price at all.

Read-only. No network. No credentials.
"""
import json
import os
import statistics
import sys
from datetime import datetime

HERE = os.path.dirname(__file__)
ROOT = os.path.join(HERE, "..")
DATA, REP = os.path.join(ROOT, "data"), os.path.join(ROOT, "reports")
ANCHORS = os.path.join(DATA, "clock_anchors.jsonl")

MAX_EXTRAPOLATE_MIN = 8   # beyond this far from any anchor, refuse


def ts(iso):
    if not iso:
        return None
    return datetime.fromisoformat(iso.replace("Z", "+00:00")).timestamp()


def period_of(minute):
    """Which half a displayed minute belongs to. 45 is the end of the first."""
    return 1 if minute <= 45 else 2


def build(anchors):
    """-> {period: sorted [(effective_minute, unix_ts)]}

    `effective_minute` folds stoppage in, because "45'+3'" is three minutes of
    real play after "45'" and treating both as minute 45 would put two anchors
    at the same x with different y and corrupt the interpolation.
    """
    by = {1: {}, 2: {}}
    for a in anchors:
        p = a.get("period")
        if p not in (1, 2):
            continue
        t = ts(a.get("wallclock"))
        if t is None:
            continue
        eff = a["minute"] + (a.get("stoppage") or 0)
        # Several events can share a minute (two substitutions, a delay pair).
        # Keep the earliest -- it is the one closest to the start of that minute.
        if eff not in by[p] or t < by[p][eff]:
            by[p][eff] = t
    return {p: sorted(v.items()) for p, v in by.items()}


def instant(m, minute, stoppage=0, period=None):
    """Real instant of a displayed minute in this match, or None.

    `m` is a built map from build(). Returns a unix timestamp.

    PASS `period` WHENEVER IT IS KNOWN. Minute 45 genuinely exists twice -- once
    as the end of the first half and once as the kickoff of the second, about
    seventeen real minutes apart. Guessing it from the number alone was worth a
    ~20-minute error on 314 readings in the first accuracy run, and it was the
    entire bad tail: 99-in-100 went from 23.67 minutes to well under one once
    the period was passed in. Callers that only have a minute get the first
    half for 45 and the second for 46 and up, which is the right reading of
    "the 45th minute" but is a convention, not a fact.
    """
    p = period if period in (1, 2) else period_of(minute)
    pts = m.get(p) or []
    if not pts:
        return None
    eff = minute + (stoppage or 0)

    # Exact anchor.
    for x, t in pts:
        if x == eff:
            return t

    lo = hi = None
    for x, t in pts:
        if x < eff:
            lo = (x, t)
        elif hi is None:
            hi = (x, t)
            break

    if lo and hi:
        # Between two anchors: straight-line, which is what a running clock is.
        span_x = hi[0] - lo[0]
        if span_x <= 0:
            return lo[1]
        return lo[1] + (eff - lo[0]) * (hi[1] - lo[1]) / span_x
    # Outside the anchored range: 60 seconds a minute, and only a little way.
    near = lo or hi
    if near is None:
        return None
    if abs(eff - near[0]) > MAX_EXTRAPOLATE_MIN:
        return None
    return near[1] + (eff - near[0]) * 60.0


def load():
    rows = []
    with open(ANCHORS, encoding="utf-8") as fh:
        for line in fh:
            try:
                rows.append(json.loads(line))
            except ValueError:
                pass
    return rows


def measure_accuracy():
    """Hide each anchor, predict it from the rest, and report the error.

    This is the only reason to trust anything downstream of this file. It is a
    real leave-one-out test on real anchors, not a plausibility argument.
    """
    rows = load()
    errs, errs_by_gap, refused = [], {}, 0
    for r in rows:
        anchors = r["anchors"]
        if len(anchors) < 4:
            continue
        for i, a in enumerate(anchors):
            if a.get("minute") is None or a["period"] not in (1, 2):
                continue
            truth = ts(a.get("wallclock"))
            if truth is None:
                continue
            rest = anchors[:i] + anchors[i + 1:]
            m = build(rest)
            got = instant(m, a["minute"], a.get("stoppage") or 0,
                          period=a["period"])
            if got is None:
                refused += 1
                continue
            e = abs(got - truth) / 60.0
            errs.append(e)
            # how far was the nearest surviving anchor in the same half?
            pts = m.get(a["period"]) or []
            eff = a["minute"] + (a.get("stoppage") or 0)
            gap = min((abs(x - eff) for x, _ in pts), default=None)
            if gap is not None:
                b = "0-2 min" if gap <= 2 else "3-5 min" if gap <= 5 else \
                    "6-10 min" if gap <= 10 else "over 10 min"
                errs_by_gap.setdefault(b, []).append(e)

    errs.sort()
    lines = ["HOW ACCURATE IS THE CLOCK MAP", "=" * 78, ""]
    lines.append("Each anchor was hidden in turn and its real instant predicted")
    lines.append("from the others. This is the error, in minutes.")
    lines.append("")
    lines.append(f"  anchors tested        {len(errs)}")
    lines.append(f"  refused to guess      {refused}")
    if errs:
        lines.append(f"  median error          {statistics.median(errs):.2f} min")
        lines.append(f"  9 in 10 within        {errs[int(len(errs)*0.9)]:.2f} min")
        lines.append(f"  99 in 100 within      {errs[int(len(errs)*0.99)]:.2f} min")
        lines.append(f"  worst                 {errs[-1]:.2f} min")
        lines.append(f"  within 1 minute       "
                     f"{sum(1 for e in errs if e <= 1)/len(errs)*100:.1f}%")
        lines.append(f"  within 2 minutes      "
                     f"{sum(1 for e in errs if e <= 2)/len(errs)*100:.1f}%")
    lines.append("")
    lines.append("by how far the nearest surviving anchor was:")
    lines.append(f"  {'gap to nearest anchor':24s} {'tested':>8s} {'median err':>12s} "
                 f"{'9 in 10 within':>16s}")
    for b in ["0-2 min", "3-5 min", "6-10 min", "over 10 min"]:
        v = sorted(errs_by_gap.get(b, []))
        if not v:
            continue
        lines.append(f"  {b:24s} {len(v):8d} {statistics.median(v):11.2f}m "
                     f"{v[int(len(v)*0.9)]:15.2f}m")
    lines.append("")
    lines.append("COMPARE: SO009 measured `kickoff + displayed minute` at a")
    lines.append("median of 17.52 minutes out, on 362 events. That method walks")
    lines.append("through halftime and through every minute of stoppage. This")
    lines.append("one never leaves the half it is in.")
    lines.append("")
    lines.append("WHAT THIS DOES NOT SAY. It measures how well the map places a")
    lines.append("minute ESPN also timestamped. Minutes with no nearby anchor")
    lines.append("are refused rather than guessed, so the errors above are the")
    lines.append("errors of the readings actually taken -- but a match with")
    lines.append("sparse anchors contributes fewer readings, not worse ones.")

    txt = "\n".join(lines)
    print(txt)
    os.makedirs(REP, exist_ok=True)
    with open(os.path.join(REP, "clock_map_accuracy.txt"), "w",
              encoding="utf-8") as fh:
        fh.write(txt + "\n")
    return errs


if __name__ == "__main__":
    measure_accuracy()

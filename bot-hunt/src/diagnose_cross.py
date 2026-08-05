"""WHY is the replayed book crossed 75% of the time? Two hypotheses, tested.

The crossed-book canary fails hard, and some books come out perfectly sane
(`...G1M8-G1` bid=15 ask=16) while others are crossed by 83c. Guessing which is
wrong would be exactly the failure this project keeps recording, so both
candidate causes are measured against the same data.

H-A  PRICE-SPACE. I assume a `side='no'` delta price is a NO bid in NO space,
     so a YES ask is 100 - best_no_bid (the Kalshi REST convention encoded in
     src/venues.py). If the archive instead stores no-side prices already in
     YES space, my NO ladder is mirrored and everything crosses.

H-B  SETTLED MARKETS. After a market settles its book is not maintained, and
     residual resting orders stay on it. Crossing would then be concentrated in
     markets whose event has already resolved, and harmless once filtered.

The test discriminates: H-A predicts crossing is uniform across a market's life;
H-B predicts it is concentrated after the event time encoded in the ticker.
"""
from __future__ import annotations

import re
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import replay as R  # noqa: E402

# KXCS2GAME-26MAY300400EFM8-EF -> the event's scheduled time, 2026-05-30 04:00
TICK_RE = re.compile(r"-(\d{2})([A-Z]{3})(\d{2})(\d{4})")
MON = {m: i + 1 for i, m in enumerate(
    ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT",
     "NOV", "DEC"])}


def event_time(ticker):
    m = TICK_RE.search(ticker)
    if not m:
        return None
    yy, mon, dd, hhmm = m.groups()
    try:
        return datetime(2000 + int(yy), MON[mon], int(dd),
                        int(hhmm[:2]), int(hhmm[2:]), tzinfo=timezone.utc)
    except (ValueError, KeyError):
        return None


def main():
    files = R.hours_on_disk()
    print(f"replaying {len(files)} hours for the diagnosis\n")

    # bucket every two-sided observation by (before/after event time) and by
    # whether it crosses under each price-space interpretation
    buckets = defaultdict(lambda: {"n": 0, "cross_A": 0, "cross_B": 0})

    def on_event(ts, tk, bk, i, d):
        yb, nb = bk.best_yes_bid(), bk.best_no_bid()
        if yb is None or nb is None:
            return
        et = event_time(tk)
        phase = "unknown"
        if et is not None:
            phase = "pre_event" if ts < et else "post_event"
        b = buckets[phase]
        b["n"] += 1
        # H-A as coded now: ask = 100 - best_no_bid  -> crossed if yb+nb > 100
        if yb + nb > 100:
            b["cross_A"] += 1
        # H-A alternative: no prices already in YES space -> the NO ladder's
        # best (lowest) price is the ask directly
        alt_ask = min(bk.no) if bk.no else None
        if alt_ask is not None and yb > alt_ask:
            b["cross_B"] += 1

    books, stats = R.replay(files, on_event=on_event, verbose=False)

    print(f"{'phase':12} {'obs':>10} {'crossed (H-A: ask=100-no_bid)':>32} "
          f"{'crossed (alt: no in YES space)':>33}")
    for phase in ("pre_event", "post_event", "unknown"):
        b = buckets.get(phase)
        if not b or not b["n"]:
            continue
        print(f"{phase:12} {b['n']:>10,} "
              f"{100*b['cross_A']/b['n']:>31.2f}% "
              f"{100*b['cross_B']/b['n']:>32.2f}%")

    tot = sum(b["n"] for b in buckets.values())
    ca = sum(b["cross_A"] for b in buckets.values())
    cb = sum(b["cross_B"] for b in buckets.values())
    print(f"\n{'ALL':12} {tot:>10,} {100*ca/max(tot,1):>31.2f}% "
          f"{100*cb/max(tot,1):>32.2f}%")

    print("\n== VERDICT")
    pre = buckets.get("pre_event", {"n": 0, "cross_A": 0})
    post = buckets.get("post_event", {"n": 0, "cross_A": 0})
    if pre["n"] and post["n"]:
        rp = 100 * pre["cross_A"] / pre["n"]
        rq = 100 * post["cross_A"] / post["n"]
        print(f"   crossing PRE-event  {rp:.2f}%")
        print(f"   crossing POST-event {rq:.2f}%")
        if rq > 3 * rp and rp < 10:
            print("   -> H-B: crossing is concentrated AFTER the event. "
                  "Settled books are not maintained.")
            print("      The replay is sound; the fill simulation must "
                  "restrict to pre-event observations.")
        elif rp > 20:
            print("   -> NOT H-B: books are crossed even before the event, so "
                  "settlement does not explain it.")
            if 100 * cb / max(tot, 1) < rp / 3:
                print("   -> H-A LIKELY: the alternative price-space reading "
                      "gives a far lower crossing rate.")
            else:
                print("   -> neither hypothesis fits; do not trade this book.")


if __name__ == "__main__":
    main()

"""set1_labels.py — free set-1 labels, for the S018 reopen.

WHAT THIS IS FOR
    `LEDGER.md` S018 records "Label coverage cannot be raised", closed on two
    sources: a paid tier's monthly cap, and one site's plus-or-minus-7-day window
    against a 68-day need. `set1_overshoot/HANDOFF.md` §9 names the same two plus
    a third paid one, and calls that "the only path".

    **A free third source exists and was never checked.** tennis-data.co.uk
    publishes one workbook per season carrying, per match: the date, both
    players, the surface, the round, AND the games won by each player in every
    set - `W1`/`L1` is exactly the set-1 margin S006 buckets on. It is free, it
    is weekly, and because it is per-SEASON the "reaches only -7 days" objection
    does not apply to it at all: it reaches back years.

    Measured over S006's own window, 2026-05-25 to 2026-07-26:

        ATP    539 matches, 535 with a set-1 score (99.3%)
        WTA    531 matches, 527 with a set-1 score (99.2%)
        TOTAL  1,070 matches, 1,062 set-1 labelled

    S006 used **479** label-verified matches. This supplies **1,062 candidate
    labels for the same window** from a source nobody had tried.

WHAT THIS DOES *NOT* CLAIM, AND THE LIMIT IS THE IMPORTANT PART
    1. **These are candidate labels, not joined labels.** How many attach to the
       set-1 universe depends on how much of that universe is main tour, and
       `set1_overshoot/data` is **laptop-only and gitignored** - it does not
       exist on the desktop this was written on. The join rate is unmeasured here
       and must be measured there.
    2. **Main tour only.** No Challenger, no ITF. If the universe is mostly ITF -
       and the live Kalshi pool this project records is 73-87% ITF - then the
       join rate will be well under 100% and could be small.
    3. **It does not reach the ~3,620 label-verified matches** S006 needs to see
       a 3.6c effect. 1,062 is 29% of that. Detection improves with the square
       root, so this moves the minimum detectable effect from about 9.9c to about
       6.6c - real, and still short. **This shortens the wait; it does not end
       it.**

    So the honest verdict on S018 is **REFUTED, not resolved**: "cannot be
    raised" is false, and by how much is a number only the laptop can produce.

USE
    py -3 src/set1_labels.py --from 20260525 --to 20260726 --out labels.csv

    Then join on (date, both surnames) against the universe. Every row carries
    both players' surnames already normalised for that purpose.
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src import tennisdata as td  # noqa: E402
from src.sackmann import norm_name, surname_of  # noqa: E402

SEASON_FILES = {"ATP": "{y}/{y}.xlsx", "WTA": "{y}w/{y}.xlsx"}


def collect(from_date: int, to_date: int, years: list[int] | None = None) -> list[dict]:
    years = years or sorted({from_date // 10000, to_date // 10000})
    out: list[dict] = []
    for tour, pat in SEASON_FILES.items():
        for y in years:
            raw = td._fetch_workbook(pat.format(y=y))
            if raw is None:
                continue
            for r in td._rows(raw):
                d = td._to_yyyymmdd(r.get("Date"))
                if d is None or not (from_date <= d <= to_date):
                    continue
                w1, l1 = r.get("W1"), r.get("L1")
                if w1 in (None, "") or l1 in (None, ""):
                    continue
                try:
                    w1i, l1i = int(float(w1)), int(float(l1))
                except (TypeError, ValueError):
                    continue
                winner = str(r.get("Winner") or "").strip()
                loser = str(r.get("Loser") or "").strip()
                if not winner or not loser:
                    continue
                out.append({
                    "date": d,
                    "tour": tour,
                    "tournament": str(r.get("Tournament") or "").strip(),
                    "surface": str(r.get("Surface") or "").strip(),
                    "round": str(r.get("Round") or "").strip(),
                    "winner": winner,
                    "loser": loser,
                    "winner_key": norm_name(winner),
                    "loser_key": norm_name(loser),
                    "winner_surname": surname_of(winner),
                    "loser_surname": surname_of(loser),
                    # the label itself
                    "set1_winner_games": w1i,
                    "set1_loser_games": l1i,
                    "set1_margin": w1i - l1i,
                    "set1_won_by_match_winner": int(w1i > l1i),
                    # free bonus: Pinnacle closing prices, the de-vig reference
                    "pinnacle_winner_odds": r.get("PSW"),
                    "pinnacle_loser_odds": r.get("PSL"),
                    "comment": str(r.get("Comment") or "").strip(),
                })
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--from", dest="frm", type=int, default=20260525)
    ap.add_argument("--to", dest="to", type=int, default=20260726)
    ap.add_argument("--out", type=Path, default=None)
    a = ap.parse_args(argv)

    rows = collect(a.frm, a.to)
    print(f"{len(rows)} set-1 labels, {a.frm} to {a.to}, free, main tour only")
    by = {}
    for r in rows:
        by[r["tour"]] = by.get(r["tour"], 0) + 1
    for k, v in sorted(by.items()):
        print(f"  {k}: {v}")
    print()
    print("LIMITS, so this is not over-read:")
    print("  * candidate labels, NOT joined - the join rate needs the universe,")
    print("    which is on the LAPTOP (set1_overshoot/data is gitignored)")
    print("  * main tour only: no Challenger, no ITF")
    print("  * 1,062 is ~29% of the ~3,620 S006 needs; MDE ~9.9c -> ~6.6c")
    print("    This shortens the wait. It does not end it.")

    if a.out:
        with a.out.open("w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
            w.writeheader()
            w.writerows(rows)
        print(f"\nwrote {a.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

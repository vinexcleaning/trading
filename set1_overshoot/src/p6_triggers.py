"""Phase 6d -- which markets does the entry rule actually fire on?

WHY THIS EXISTS. Trades for the whole universe would be roughly 28 GB and
nearly all of it belongs to markets where the rule never fires, so it could not
affect any result. This dumps the tickers that DO fire, and `p6_maker_pull.py
--trades-for <file>` pulls only those.

Both tickers of a firing match are dumped, because the position has two
representations (amendment A1): a bid on the underdog's ticker and an ask on
the favourite's ticker. Pulling only one would silently decide which
representation the study is allowed to measure.

⚠ THE UNTOUCHED CHECK PERIOD. Tickers after the cutoff are written to a
SEPARATE file. They have to be pulled -- the data expires -- but the count is
printed apart from the selection period and nothing else about them is shown.
Downloading is not looking.
"""
from __future__ import annotations

import argparse
import pathlib
import sqlite3
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import p6_maker_fill as F         # noqa: E402

DB = ROOT / "data" / "maker.db"

#: The original study's selection window ended here, so everything on or after
#: this date has never been fitted by anyone. Preregistration section 5.
CUTOFF = "2026-08-02"

#: The registered depth is 30. The rest of the grid is LOOKED at and gets no
#: verdict (preregistration, "The depth grid is LOOKED at"). deep:40 is in the
#: list because it is the version that was actually asked for.
GRID = [8, 12, 16, 20, 25, 30, 35, 40]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--min-minute", type=int, default=38)
    ap.add_argument("--pre-spread-max", type=int, default=10)
    ap.add_argument("--out", default=str(ROOT / "data" / "triggers_sel.txt"))
    ap.add_argument("--out-check",
                    default=str(ROOT / "data" / "triggers_check.txt"))
    a = ap.parse_args()

    con = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)

    print(f"firing rate by depth, entry search from minute {a.min_minute}, "
          f"pre-match spread <= {a.pre_spread_max}c")
    print(f"{'depth':>6}  {'selection':>10}  {'check':>8}   "
          f"{'sel tickers':>11}")
    sel_all, chk_all = set(), set()
    for d in GRID:
        sel = list(F.iter_events(con, depth=float(d),
                                 min_minute=a.min_minute,
                                 pre_spread_max=a.pre_spread_max,
                                 before=CUTOFF))
        chk = list(F.iter_events(con, depth=float(d),
                                 min_minute=a.min_minute,
                                 pre_spread_max=a.pre_spread_max,
                                 since=CUTOFF))
        for _ev, fav, dog, *_ in sel:
            sel_all.add(fav[0])
            sel_all.add(dog[0])
        for _ev, fav, dog, *_ in chk:
            chk_all.add(fav[0])
            chk_all.add(dog[0])
        mark = "  <- registered" if d == 30 else (
            "  <- the one he asked for" if d == 40 else "")
        print(f"{d:>6}  {len(sel):>10,}  {len(chk):>8,}   "
              f"{len(sel_all):>11,}{mark}")

    pathlib.Path(a.out).write_text(
        "\n".join(sorted(sel_all)) + "\n", encoding="utf-8")
    pathlib.Path(a.out_check).write_text(
        "\n".join(sorted(chk_all)) + "\n", encoding="utf-8")

    print(f"\nunion over the whole grid:")
    print(f"  selection period : {len(sel_all):,} tickers -> {a.out}")
    print(f"  check period     : {len(chk_all):,} tickers -> {a.out_check}")
    print(f"\nAt ~4,000 trade rows per market that is roughly "
          f"{(len(sel_all) + len(chk_all)) * 4000 / 1e6:.0f}M rows, against "
          f"144M\nfor the whole universe.")
    print("\nThe check-period file is written because the data expires, and is "
          "not\nexamined further here. Downloading is not looking.")


if __name__ == "__main__":
    sys.exit(main())

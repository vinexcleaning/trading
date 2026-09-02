"""What Kalshi charges on each series this desk touches.

    py -3 livedesk\tools\show_fees.py

READ ONLY. One GET per series.

⚠ THE CLIENT IS BUILT BY `demo_exec`, NOT HERE. `src/fees.py` had a demo block
that constructed its own, and the paper-only canary failed the build over it --
correctly. Only one file in this project may build a client that can reach the
exchange, and a convenience block is exactly the second door that rule exists
to keep shut.
"""
from __future__ import annotations

import sys
from pathlib import Path

LIVEDESK = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(LIVEDESK / "src"))

import fees                                                # noqa: E402
import demo_exec                                           # noqa: E402
from common.kalshi_fees import TAKER_RATE                  # noqa: E402

SERIES = ("KXMLBGAME", "KXMLBTOTAL", "KXATPMATCH", "KXNFLGAME")


def main() -> None:
    client = demo_exec._client()
    print()
    print(f"  the full taker rate is {float(TAKER_RATE):g}")
    print()
    for s in SERIES:
        f, known = fees.for_series(s, client)
        if not known:
            print(f"  {s:12s} COULD NOT READ -- the full rate will be charged")
            continue
        mult = float(f.fee_multiplier)
        tail = "  <- HALF FEE" if mult != 1 else ""
        print(f"  {s:12s} multiplier {mult:g}   taker rate "
              f"{float(f.taker_rate):g}{tail}")
    print()
    print("  Half fee is a fact about the SERIES, not about baseball: only the")
    print("  per-game series carry it. Season-long markets pay full.")
    print()


if __name__ == "__main__":
    main()

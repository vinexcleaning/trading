"""ch074_decomposition.py — is the decomposed market ever cheaper than the match market?

CH074 was closed by an ARGUMENT on one worked example: *"set-score and parlay
markets cannot be less efficient than the match market they decompose from"*.
The audit it proposed was never run.

**IT DOES NOT NEED THE PRE-REGISTRATION WIDENED, AND I SAID OTHERWISE ONCE.**
In mailbox 006 I said running this meant adding series to a pool under an active
pre-registration. That was wrong and it made a runnable thing look blocked. The
pre-registration governs what the sixteen BOTS trade. This reads public prices
and trades nothing, so it touches neither the bots nor the registered gates. It
is a separate, read-only measurement.

THE TEST
    For one matchup, a player can be bought two ways:

      direct        the match-winner market            -> one ask
      decomposed    every exact-score market in which
                    that player wins                   -> the sum of their asks

    Both pay exactly $1 if the player wins. So if the decomposed sum is CHEAPER
    than the direct ask, the decomposition is mispriced relative to the match
    market, and by how much. If it is dearer, the closure's argument holds.

    Prices are ASKS on both sides, because that is what you would pay. GUARDS #7:
    there is no mid here.

THE COST THAT DECIDES IT
    The decomposition needs N legs, so it pays N entry fees against the direct
    trade's one. `common/kalshi_fees.py` prices that, and the net column is the
    only one that means anything. This is the same arithmetic that killed the
    ladder-arbitrage thread: mispricings worth about a cent against a fee floor
    of roughly two.

USE
    py -3 src/ch074_decomposition.py            # open markets, both tours
    py -3 src/ch074_decomposition.py --settled  # the retention window
"""

from __future__ import annotations

import argparse
import re
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT.parent))

from common.kalshi_fees import TAKER_RATE, fee_rate_cents  # noqa: E402

from src import safety  # noqa: E402

BASE = "https://api.elections.kalshi.com/trade-api/v2/markets"

PAIRS = [
    ("KXATPMATCH", "KXATPEXACTMATCH", "ATP"),
    ("KXWTAMATCH", "KXWTAEXACTMATCH", "WTA"),
]


def _matchup(event_ticker: str) -> str:
    k = event_ticker.split("-", 1)[1] if "-" in event_ticker else event_ticker
    # set-winner events carry a trailing set number; exact-score ones do not
    return re.sub(r"-\d+$", "", k)


def _cents(v):
    try:
        return int(round(float(v) * 100))
    except (TypeError, ValueError):
        return None


def fetch(series: str, status: str) -> list[dict]:
    out, cursor = [], None
    for _ in range(10):
        p = {"series_ticker": series, "status": status, "limit": 200}
        if cursor:
            p["cursor"] = cursor
        b = safety.get(BASE, params=p)
        if not b:
            break
        ms = b.get("markets") or []
        out.extend(ms)
        cursor = b.get("cursor")
        if not cursor or not ms:
            break
    return out


def analyse(status: str = "open") -> list[dict]:
    rows: list[dict] = []
    for match_series, exact_series, tour in PAIRS:
        direct = fetch(match_series, status)
        decomp = fetch(exact_series, status)
        if not direct or not decomp:
            continue

        by_matchup_direct: dict[str, list[dict]] = defaultdict(list)
        for m in direct:
            by_matchup_direct[_matchup(m.get("event_ticker", ""))].append(m)
        by_matchup_decomp: dict[str, list[dict]] = defaultdict(list)
        for m in decomp:
            by_matchup_decomp[_matchup(m.get("event_ticker", ""))].append(m)

        for key in sorted(set(by_matchup_direct) & set(by_matchup_decomp)):
            for dm in by_matchup_direct[key]:
                player = (dm.get("yes_sub_title") or "").strip()
                direct_ask = _cents(dm.get("yes_ask_dollars"))
                if not player or not direct_ask or direct_ask <= 0:
                    continue
                # every exact-score outcome in which THIS player wins
                legs = [x for x in by_matchup_decomp[key]
                        if (x.get("yes_sub_title") or "").startswith(player)]
                asks = [_cents(x.get("yes_ask_dollars")) for x in legs]
                if not legs or any(a is None or a <= 0 for a in asks):
                    continue
                decomp_ask = sum(asks)

                direct_fee = float(fee_rate_cents(direct_ask, TAKER_RATE))
                decomp_fee = sum(float(fee_rate_cents(a, TAKER_RATE)) for a in asks)
                gross = direct_ask - decomp_ask          # +ve => decomposition cheaper
                net = gross - (decomp_fee - direct_fee)  # after the extra legs' fees

                rows.append({
                    "tour": tour, "matchup": key, "player": player,
                    "legs": len(legs),
                    "direct_ask": direct_ask, "decomp_ask": decomp_ask,
                    "gross_saving": gross, "extra_fees": decomp_fee - direct_fee,
                    "net_saving": net,
                })
    return rows


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--settled", action="store_true")
    a = ap.parse_args(argv)
    status = "settled" if a.settled else "open"

    rows = analyse(status)
    if not rows:
        print(f"no joinable {status} matchups")
        return 0

    import statistics as st
    gross = [r["gross_saving"] for r in rows]
    net = [r["net_saving"] for r in rows]
    cheaper_gross = [r for r in rows if r["gross_saving"] > 0]
    cheaper_net = [r for r in rows if r["net_saving"] > 0]

    print(f"CH074 - decomposition vs match market, {status} markets")
    print(f"  {len(rows)} player-sides across {len({r['matchup'] for r in rows})} matchups")
    print()
    print("  buying a player via the exact-score legs instead of the match market:")
    print(f"    gross: median {st.median(gross):+.1f}c  mean {st.mean(gross):+.2f}c "
          f"(positive = decomposition CHEAPER)")
    print(f"    net  : median {st.median(net):+.1f}c  mean {st.mean(net):+.2f}c "
          f"(after the extra legs' fees)")
    print()
    print(f"  cheaper GROSS: {len(cheaper_gross)} of {len(rows)} "
          f"({100*len(cheaper_gross)/len(rows):.1f}%)")
    print(f"  cheaper NET  : {len(cheaper_net)} of {len(rows)} "
          f"({100*len(cheaper_net)/len(rows):.1f}%)   <-- the only column that matters")
    if cheaper_net:
        best = max(cheaper_net, key=lambda r: r["net_saving"])
        print(f"    best: {best['player']} {best['net_saving']:+.2f}c net "
              f"({best['direct_ask']}c direct vs {best['decomp_ask']}c over "
              f"{best['legs']} legs)")
    print()
    print("  worked example:")
    ex = rows[0]
    print(f"    {ex['player']}: {ex['direct_ask']}c direct, {ex['decomp_ask']}c "
          f"over {ex['legs']} legs -> {ex['gross_saving']:+d}c gross, "
          f"{ex['net_saving']:+.2f}c net")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Settle bets from Kalshi's own settlement record. READ ONLY.

    py -3 livedesk\tools\settle_from_kalshi.py

⚠ WHY. Three of his real, settled, LOST bets were recorded as `void` with zero
contracts and zero loss. He had paid roughly $4.51 + $9.12 + $10.05 and lost all
three, and his own record said nothing had happened.

The cause: **a settled market DROPS OFF the positions endpoint**, so
`position_fp = 0` meant both "he never held it" and "he held it and it
finished". Those collapsed to the same row. It is the same mechanism as the
original $32 error in the tennis app.

`/portfolio/settlements` is the authority. It carries `market_result`, what was
paid, and the revenue -- so nothing here has to infer anything.
"""
from __future__ import annotations

import os
import re
import shutil
import sys
from pathlib import Path

LIVEDESK = Path(__file__).resolve().parents[1]
ENV_FILE = LIVEDESK / "kalshi_env.bat"
sys.path.insert(0, str(LIVEDESK / "src"))
sys.path.insert(0, str(LIVEDESK.parent / "kalshi-inplay-bot"))


def load_env() -> bool:
    if not ENV_FILE.exists():
        print(f"  no {ENV_FILE.name} -- run tools/set_key.py first.")
        return False
    for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
        m = re.match(r'\s*set\s+"?(KALSHI_[A-Z_]+)=([^"]*)"?\s*$', line)
        if m:
            os.environ[m.group(1)] = m.group(2)
    return bool(os.environ.get("KALSHI_KEY_ID"))


def main() -> None:
    if not load_env():
        sys.exit(1)
    from kalshi_client import KalshiClient
    import ledger as L

    client = KalshiClient(demo=False, read_only=True,
                          kill_switch=str(LIVEDESK / "TRADING_DISABLED"))
    rows = (client._get("/portfolio/settlements",
                        {"limit": 200}).get("settlements") or [])
    by_ticker = {str(r.get("ticker")): r for r in rows}

    led = L.Ledger()
    shutil.copy2(led.path, led.path.with_suffix(".before-settle.json"))
    print(f"  backup: {led.path.with_suffix('.before-settle.json').name}")
    print()

    changed = 0
    for e in led.entries:
        # A bet that was really placed and is not yet resolved. `void` is in
        # this list ON PURPOSE: three of his real losses were wrongly voided
        # and this is what puts them back.
        if e.status not in ("open", "awaiting-settlement", "void"):
            continue
        r = by_ticker.get(e.ticker)
        if r is None:
            continue
        result = str(r.get("market_result") or "").lower()
        if result not in ("yes", "no"):
            continue
        won = (result == (e.side or "YES").lower())

        # ⚠ WORK OUT THE NET FOR THE WHOLE MARKET, not for one side.
        #
        # My first version read only the YES row and reported Baltimore as
        # "lost $26.24 on 64 contracts". He never lost $26.24 -- he bought 64
        # YES for $26.24, then SOLD 53 of them back (which Kalshi records as
        # buying 53 NO for $31.80), and the NO side won. So 53 contracts paid
        # him $53 and the true net was about six dollars, not twenty-six.
        #
        # Reading one side of a market he traded both ways overstated his loss
        # more than fourfold, on exactly the bet that has been mis-recorded at
        # every previous step.
        yes_ct = abs(L._size(r.get("yes_count_fp")))
        no_ct = abs(L._size(r.get("no_count_fp")))
        yes_cost = abs(L._size(r.get("yes_total_cost_dollars")))
        no_cost = abs(L._size(r.get("no_total_cost_dollars")))
        fee = abs(L._size(r.get("fee_cost")))
        paid_all = yes_cost + no_cost + fee
        revenue = (yes_ct if result == "yes" else no_ct) * 1.00
        net = round(revenue - paid_all, 2)

        held = e.contracts if e.contracts > 0 else int(
            yes_ct if (e.side or "YES").upper() == "YES" else no_ct)
        cost = round(paid_all, 2)

        was = e.status
        e.contracts = int(held)
        e.cost_usd = cost
        e.lose_usd = cost
        e.win_profit_usd = round(max(0.0, net), 2)
        # The NET is the truth, whichever side won. A market traded both ways
        # can end slightly down even when "the result went against him".
        e.status = "won" if net > 0 else "lost"
        e.pnl_usd = net
        e.settled_utc = str(r.get("settled_time") or "")
        e.note = (f"{e.note} | settled from Kalshi: market_result={result}, "
                  f"{'WON' if won else 'LOST'} ${abs(e.pnl_usd):.2f} on "
                  f"{held} contracts").strip(" |")
        changed += 1
        print(f"  {e.team[:22]:<22} {was:>20} -> {e.status.upper():<5} "
              f"{held:>3} contracts, {'made' if e.pnl_usd > 0 else 'lost'} "
              f"${abs(e.pnl_usd):.2f}")

    if changed:
        led.save()
        fresh = L.Ledger()
        if len([x for x in fresh.entries if x.status in ("won", "lost")]) < \
                len([x for x in led.entries if x.status in ("won", "lost")]):
            sys.exit("  !! the change did not stick — close the desk window "
                     "and run this again.")

    print()
    print(f"  {changed} bet(s) settled from Kalshi's own record.")
    print(f"  realised so far: ${led.realised_usd():.2f}")
    print(f"  still riding:    ${led.at_risk_usd():.2f}")
    print()


if __name__ == "__main__":
    main()

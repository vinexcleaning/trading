"""What is actually open in his Kalshi account, and how big each one is.

    py -3 livedesk\\tools\\show_positions.py

READ ONLY. Two GETs. Built with `read_only=True`, so it structurally cannot
place or cancel anything.

Reads the credentials out of `kalshi_env.bat` (gitignored) and **never prints
them**. That file is the one source now -- the key id used to be hard-coded in
`run.bat`, which is how it ended up committed to a public repo.

WHY IT EXISTS
    He said the bot was "staking way too high -- 30 something percent". The
    ledger says every bet was about $4.27, roughly 5%. Those two cannot both be
    true, and the account is the thing that settles it. Guessing at this from
    the ledger alone is how you fix the wrong problem.
"""
from __future__ import annotations

import os
import re
import sys
from pathlib import Path

LIVEDESK = Path(__file__).resolve().parents[1]
ENV_FILE = LIVEDESK / "kalshi_env.bat"
sys.path.insert(0, str(LIVEDESK / "src"))
sys.path.insert(0, str(LIVEDESK.parent / "kalshi-inplay-bot"))


def load_env() -> bool:
    """Set the two variables from the local file. Values are never printed."""
    if not ENV_FILE.exists():
        print(f"  no {ENV_FILE.name} — run tools/set_key.py first.")
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
    try:
        balance = client.balance()
        rows = client.positions(open_only=True)
    except Exception as exc:
        sys.exit(f"  could not read the account: {exc}")

    print()
    print(f"  CASH IN YOUR ACCOUNT:  ${balance:.2f}")
    print()
    if not rows:
        print("  No open positions at all.")
    else:
        print("  OPEN POSITIONS")
        print("  " + "-" * 72)
        risked = 0.0
        for r in rows:
            size = abs(L._size(r.get("position_fp")))
            # Kalshi reports exposure in cents on some fields and dollars on
            # others. Prefer an explicit dollars field, fall back to cents.
            exp = r.get("market_exposure_dollars")
            if exp is None:
                exp = (r.get("market_exposure") or 0) / 100.0
            exp = float(exp)
            risked += exp
            print(f"  {str(r.get('ticker'))[:46]:<46} {size:>6.0f} contracts "
                  f"${exp:>8.2f}")
        print("  " + "-" * 72)
        total = risked + balance
        print(f"  money riding on open bets: ${risked:.2f}")
        print(f"  cash plus open bets:       ${total:.2f}")
        if total:
            print(f"  so open bets are {100.0 * risked / total:.1f}% of "
                  f"everything you have")
    print()

    led = L.Ledger()
    mine = {e.ticker for e in led.entries if e.status == "open"}
    theirs = {str(r.get("ticker")) for r in rows}
    not_ours = theirs - mine
    if not_ours:
        print("  Of those, these are NOT from this bot — your own trades:")
        for t in sorted(not_ours):
            print(f"    {t}")
        print()


if __name__ == "__main__":
    main()

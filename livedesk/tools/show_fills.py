"""Every order this account has actually had filled, newest first. READ ONLY.

    py -3 livedesk\\tools\\show_fills.py

Built with `read_only=True` and only ever issues GETs.

WHY: the ledger said 10 contracts on Baltimore; the account held 64. The
ledger is what this tool believes; the fills are what happened. When they
disagree, the fills win, and guessing from the ledger is how you fix the wrong
thing.
"""
from __future__ import annotations

import os
import re
import sys
from collections import defaultdict
from pathlib import Path

LIVEDESK = Path(__file__).resolve().parents[1]
ENV_FILE = LIVEDESK / "kalshi_env.bat"
sys.path.insert(0, str(LIVEDESK / "src"))
sys.path.insert(0, str(LIVEDESK.parent / "kalshi-inplay-bot"))


def load_env() -> bool:
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

    client = KalshiClient(demo=False, read_only=True,
                          kill_switch=str(LIVEDESK / "TRADING_DISABLED"))
    try:
        data = client._get("/portfolio/fills", {"limit": 200})
    except Exception as exc:
        sys.exit(f"  could not read fills: {exc}")

    fills = data.get("fills", []) or []
    print()
    print(f"  {len(fills)} fill(s) on this account")
    print("  " + "-" * 78)
    print(f"  {'when':<21} {'ticker':<34} {'side':<5} {'count':>6} {'price':>6}")
    print("  " + "-" * 78)
    per = defaultdict(lambda: [0, 0])
    for f in fills:
        t = str(f.get("ticker") or "")
        cnt = f.get("count") or f.get("count_fp") or 0
        try:
            cnt = float(cnt)
        except (TypeError, ValueError):
            cnt = 0.0
        px = f.get("yes_price") or f.get("price") or 0
        when = str(f.get("created_time") or "")[:19].replace("T", " ")
        print(f"  {when:<21} {t[:34]:<34} {str(f.get('side'))[:5]:<5} "
              f"{cnt:>6.0f} {str(px):>6}")
        per[t][0] += cnt
        per[t][1] += 1

    print()
    print("  TOTAL PER MARKET")
    print("  " + "-" * 78)
    for t, (cnt, n) in sorted(per.items()):
        flag = "   <-- MORE THAN ONE ORDER" if n > 1 else ""
        print(f"  {t[:46]:<46} {cnt:>6.0f} contracts over {n} fill(s){flag}")
    print()


if __name__ == "__main__":
    main()

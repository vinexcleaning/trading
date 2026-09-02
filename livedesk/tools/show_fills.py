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


def _num(*values) -> float:
    """First value that reads as a number. Kalshi sends decimal STRINGS."""
    for v in values:
        if v in (None, ""):
            continue
        try:
            return float(v)
        except (TypeError, ValueError):
            continue
    return 0.0


def _price_cents(fill):
    """What he ACTUALLY PAID on this fill, in cents, or None if unreadable.

    ⚠ TWO SEPARATE DEFECTS LIVED ON ONE LINE HERE, and both printed a
    confident wrong number rather than failing.

    **1. The field name was dead.** It read
    `f.get("yes_price") or f.get("price") or 0`. Both are legacy names that
    Kalshi no longer sends -- checked against a real fills response on
    2026-09-02, where the keys are `yes_price_dollars` and `no_price_dollars`.
    Both `.get()`s returned None, so **every row printed a price of 0** in a
    tool whose only job is to show him what he paid. GUARD #23 records that
    these names moved once already.

    **2. Even with the right name, the YES price is wrong on a NO fill.** The
    two are complements -- the sampled fill carried `yes_price_dollars 0.5800`
    and `no_price_dollars 0.4200`. Printing the yes price on a no fill would
    have reported 58 cents when he paid 42. **That is not a zero he would
    notice; it is a plausible number that is wrong**, which is worse.

    So the side decides which field is read, and an unreadable price prints
    `??` rather than a zero pretending to be a price.
    """
    side = str(fill.get("side") or fill.get("outcome_side") or "").lower()
    key = "no_price_dollars" if side == "no" else "yes_price_dollars"
    raw = fill.get(key)
    if raw in (None, ""):
        return None
    try:
        return float(raw) * 100.0
    except (TypeError, ValueError):
        return None


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
    print(f"  {'when':<21} {'ticker':<32} {'side':<4} {'count':>6} "
          f"{'paid':>6} {'fee':>6}")
    print("  " + "-" * 78)
    per = defaultdict(lambda: [0, 0])
    for f in fills:
        t = str(f.get("ticker") or f.get("market_ticker") or "")
        cnt = _num(f.get("count_fp"), f.get("count"))
        px = _price_cents(f)
        fee = _num(f.get("fee_cost"))
        when = str(f.get("created_time") or "")[:19].replace("T", " ")
        shown = "??" if px is None else f"{px:.0f}c"
        print(f"  {when:<21} {t[:32]:<32} {str(f.get('side'))[:4]:<4} "
              f"{cnt:>6.0f} {shown:>6} {fee:>6.2f}")
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

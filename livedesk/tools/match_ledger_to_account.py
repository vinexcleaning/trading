"""Make the ledger say what his account actually holds. READ ONLY on Kalshi.

    py -3 livedesk\\tools\\match_ledger_to_account.py

WHY: the desk placed 8 orders on one Baltimore market -- 64 contracts -- while
recording one bet of 10. He then sold it down himself to 11. So the ledger, the
account, and reality were three different numbers.

Guard 4 compares our open bets against his account, so until the ledger tells
the truth it will keep refusing every new bet with "shows 11 contracts, not the
10 it placed". That is the guard doing its job on a record that is wrong.

This only ever edits the LEDGER. It cannot place, cancel or change anything on
Kalshi -- the client is built `read_only=True`.
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
    rows = client.positions(open_only=True)
    held = {}
    for r in rows:
        held[str(r.get("ticker"))] = abs(L._size(r.get("position_fp")))

    led = L.Ledger()
    backup = led.path.with_suffix(".before-match.json")
    shutil.copy2(led.path, backup)
    print(f"  backup: {backup.name}")
    print()

    changed = 0

    # ⚠ FIRST: bring back anything the account HOLDS that the ledger has
    # written off. This direction was missing, and it is the one that mattered.
    #
    # A bug voided his live Baltimore position at zero contracts. This tool
    # only walked `status == "open"` entries, so it found nothing to correct
    # and cheerfully reported "0 corrected" while he was still holding 11
    # contracts. The account is the truth in BOTH directions: it can tell us a
    # bet shrank, and it can tell us a bet we wrote off is still very much on.
    covered = {e.ticker for e in led.entries if e.status == "open"}
    for e in led.entries:
        if e.status not in ("void", "deferred", "expired"):
            continue
        real = held.get(e.ticker, 0.0)
        if real <= 0 or e.ticker in covered:
            continue
        was = e.status
        e.status = "open"
        e.contracts = int(real)
        e.cost_usd = round(e.contracts * e.price_c / 100.0 + e.fee_usd, 2)
        e.lose_usd = e.cost_usd
        e.win_profit_usd = round(e.contracts * 1.00 - e.cost_usd, 2)
        e.note = (f"{e.note} | RESTORED from {was}: your account holds "
                  f"{e.contracts} contracts").strip(" |")
        covered.add(e.ticker)
        changed += 1
        print(f"  {e.team[:24]:<24} was {was} -> RESTORED as open, "
              f"{e.contracts} contracts, ${e.cost_usd:.2f} riding")

    for e in led.entries:
        if e.status != "open":
            continue
        real = held.get(e.ticker, 0.0)
        if abs(real - e.contracts) < 0.001:
            print(f"  {e.team[:24]:<24} {e.contracts:>4} contracts  — agrees")
            continue
        if real <= 0:
            print(f"  {e.team[:24]:<24} {e.contracts:>4} -> GONE from your "
                  f"account. Marking void (no money on it).")
            e.status = "void"
            e.note = "not in the account — sold or never filled"
            changed += 1
            continue
        # Rescale the money to the size he actually holds, at the recorded
        # price. Fees are left as recorded: he paid what he paid, and inventing
        # a new fee would be worse than carrying the old one.
        old = e.contracts
        e.contracts = int(real)
        e.cost_usd = round(e.contracts * e.price_c / 100.0 + e.fee_usd, 2)
        e.lose_usd = e.cost_usd
        e.win_profit_usd = round(e.contracts * 1.00 - e.cost_usd, 2)
        e.note = (f"{e.note} | resized {old} -> {e.contracts} to match the "
                  f"account").strip(" |")
        print(f"  {e.team[:24]:<24} {old:>4} -> {e.contracts} contracts, "
              f"${e.cost_usd:.2f} at risk")
        changed += 1

    if changed:
        led.save()
        # ⚠ VERIFY THE WRITE SURVIVED, because on 2026-08-16 it did not.
        #
        # The desk window was still open. Its background loop reads the account
        # every 60 seconds and saves, writing its own in-memory entries over
        # the top -- so this correction was silently undone within the minute,
        # and the next run found the old numbers again with no error anywhere.
        #
        # Last writer wins on this file. Whoever edits it must check they were
        # the last writer.
        fresh = L.Ledger()
        for e in led.entries:
            if e.status != "open":
                continue
            back = next((x for x in fresh.entries
                         if x.ticker == e.ticker and x.status == "open"), None)
            if back is None or back.contracts != e.contracts:
                print()
                print("  !! THE CHANGE DID NOT STICK.")
                print("     Something else is writing this file -- almost")
                print("     certainly the desk window is still open.")
                print()
                print("     CLOSE THE DESK WINDOW COMPLETELY, then run this")
                print("     again. Nothing was lost; the backup is beside it.")
                print()
                sys.exit(1)

    print()
    print(f"  {changed} entry(ies) corrected.")
    print("  Guard 4 now says:", led.reconcile_positions(rows)[0].upper())
    print(" ", led.reconcile_positions(rows)[1][:150])
    print()


if __name__ == "__main__":
    main()

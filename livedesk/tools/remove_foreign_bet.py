"""Take his own manual bet back out of the bot's record.

    py -3 livedesk\tools\remove_foreign_bet.py

⚠ WHAT WENT WRONG. A restore loop I wrote keyed on the TICKER: if his account
held a market and any old entry mentioned it, the entry was restored and resized
from the account. **A ticker cannot tell whose bet it is.**

On 2026-08-17 he placed his own 64-contract Baltimore bet on a game the bot had
also looked at. The bot's own entry there had EXPIRED at 9 contracts, so the
loop found a matching ticker and pulled his $59.03 into the record as though the
bot had done it -- against a rule that sizes at $3 to $10.

The loop is gone (see `adopt_fills`). This removes what it already wrote.

**The row is written to `data/removed-entries.json` with the reason and the
date, never silently dropped.** A settled bet that vanishes with no trace is
how a record stops being auditable.
"""
from __future__ import annotations

import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import ledger as L                                        # noqa: E402

REASON = ("his own manual bet, pulled in by the ticker-keyed restore loop. "
          "64 contracts against a rule that sizes at $3-$10, on a game whose "
          "genuine bot entry expired at 9 contracts.")


def main() -> None:
    led = L.Ledger()
    shutil.copy2(led.path, led.path.with_suffix(".before-foreign-removal.json"))

    doomed = [e for e in led.entries
              if "RESTORED from" in (e.note or "")]
    if not doomed:
        print("  nothing to remove — no entry carries a RESTORED note.")
        return

    out = led.path.parent / "removed-entries.json"
    kept = json.loads(out.read_text(encoding="utf-8")) if out.exists() else []
    for e in doomed:
        print(f"  removing  {e.team[:22]:<22} {e.contracts:>3} @ {e.price_c}c "
              f"= ${e.cost_usd:.2f}  ({e.status})")
        kept.append({"removed_utc": datetime.now(timezone.utc).isoformat(
            timespec="seconds"), "reason": REASON,
            "entry": {k: getattr(e, k) for k in
                      ("game_key", "ticker", "team", "side", "price_c",
                       "contracts", "cost_usd", "pnl_usd", "status",
                       "confirmed_utc", "note")}})
    out.write_text(json.dumps(kept, indent=1), encoding="utf-8")

    before = led.realised_usd()
    led.entries = [e for e in led.entries if e not in doomed]
    led.save()

    fresh = L.Ledger()
    if any("RESTORED from" in (e.note or "") for e in fresh.entries):
        sys.exit("  !! it did not stick — close the desk window and re-run.")

    print()
    print(f"  kept for the record in {out.name}")
    print(f"  realised  ${before:.2f}  ->  ${fresh.realised_usd():.2f}")
    print()


if __name__ == "__main__":
    main()

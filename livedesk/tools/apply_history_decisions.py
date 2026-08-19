"""His decisions on the three games from mailbox 016/017. Ledger only.

    py -3 livedesk\tools\apply_history_decisions.py

⚠ REQUIRES THE DESK WINDOW CLOSED. It saves its own copy every 60 seconds and
will write straight over this. The script checks and refuses rather than
reporting a success that gets reverted a minute later.

HIS DECISIONS, and he chose the unbiased option on the one that would have
flattered him, unprompted:

  Baltimore/Tampa    DELETE     the bot's bet never got placed; nothing real
  Miami/Philadelphia KEEP       the fixed rule would have bet the same 10%.
                                His words: "we wanna be completely unbiased"
  San Diego/NY Mets  RESTATE    placed at 10% before tiering landed; the rule
                                now in force sizes it alone -> 5%

**The original stays visible on the restatement, and the deleted row goes to a
side file with the reason and the date.** Never overwrite a real number with a
corrected one (CLAUDE.md §6).
"""
from __future__ import annotations

import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import ledger as L                                        # noqa: E402


def main() -> None:
    led = L.Ledger()
    shutil.copy2(led.path, led.path.with_suffix(".before-history.json"))
    removed_path = led.path.parent / "removed-entries.json"
    removed = (json.loads(removed_path.read_text(encoding="utf-8"))
               if removed_path.exists() else [])
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    changed = 0

    # --- Baltimore: DELETE. The bot's bet expired; nothing was ever placed.
    doomed = [e for e in led.entries
              if e.game_key == "2026-08-17:BAL@TB" and e.status == "expired"]
    for e in doomed:
        removed.append({"removed_utc": now,
                        "reason": "his decision (mailbox 017): the bot's bet "
                                  "never got placed, so there is nothing real "
                                  "to keep",
                        "entry": {k: getattr(e, k) for k in
                                  ("game_key", "ticker", "team", "price_c",
                                   "contracts", "cost_usd", "pnl_usd",
                                   "status", "confirmed_utc")}})
        print(f"  DELETED   {e.team[:22]:<22} {e.contracts:>3} @ {e.price_c}c "
              f"(never placed)")
        changed += 1
    led.entries = [e for e in led.entries if e not in doomed]

    # --- Miami: KEEP. His call, and the unbiased one.
    for e in led.entries:
        if e.game_key == "2026-08-17:MIA@PHI" and e.status == "lost":
            print(f"  KEPT      {e.team[:22]:<22} {e.contracts:>3} @ "
                  f"{e.price_c}c = ${e.cost_usd:.2f} — the fixed rule would "
                  f"have bet the same")

    # --- San Diego: RESTATE to 5%, original left visible.
    for e in led.entries:
        if e.game_key != "2026-08-17:SD@NYM" or e.status != "lost":
            continue
        if "restated" in (e.note or ""):
            print("  San Diego already restated — leaving it alone.")
            continue
        was_ct, was_cost, was_pnl = e.contracts, e.cost_usd, e.pnl_usd
        e.contracts = int(round(was_ct / 2))
        e.cost_usd = round(was_cost / 2, 2)
        e.lose_usd = e.cost_usd
        e.win_profit_usd = round(e.contracts * 1.00 - e.cost_usd, 2)
        e.pnl_usd = -e.cost_usd
        e.note = (f"{e.note} | RESTATED: placed at ${was_cost:.2f} "
                  f"({was_ct} contracts) under the old flat 10% rule; restated "
                  f"to ${e.cost_usd:.2f} ({e.contracts}), which is what the "
                  f"tiered rule now in force would have bet on a game nothing "
                  f"else was on. Original loss was ${abs(was_pnl):.2f}."
                  ).strip(" |")
        print(f"  RESTATED  {e.team[:22]:<22} ${was_cost:.2f} -> "
              f"${e.cost_usd:.2f}  (original kept in the note)")
        changed += 1

    if not changed:
        print("  nothing to do.")
        return

    removed_path.write_text(json.dumps(removed, indent=1), encoding="utf-8")
    led.save()

    fresh = L.Ledger()
    still = [e for e in fresh.entries
             if e.game_key == "2026-08-17:BAL@TB" and e.status == "expired"]
    if still:
        sys.exit("\n  !! IT DID NOT STICK. The desk window is still open and "
                 "wrote its own copy back.\n     Close it completely, then run "
                 "this again. Nothing was lost.")

    print()
    print(f"  kept for the record in {removed_path.name}")
    print(f"  realised now ${fresh.realised_usd():.2f}")
    print(f"  {fresh.two_window_line()}")
    print()


if __name__ == "__main__":
    main()

"""Reset the trailing-stop peak to where the bot actually is. Ledger only.

    py -3 livedesk\tools\reset_peak.py

HIS DECISION, 2026-08-18: "reset it and make the new floor 40".

The peak was $106 -- the figure from before three losses -- so the 35% trailing
rule was holding the stop at $68.90 while the bot sat at $62.61. It could never
have restarted on its own.

⚠ NOTE WHAT THIS MAKES TRUE, because it is not obvious: at $62.61 the trailing
stop lands at $40.70, essentially ON TOP of the new $40 floor. That is only safe
because both cut-offs are now a PAUSE rather than a stop. If the trailing rule
had stayed terminal this reset would have armed it to permanently kill a tool he
had just asked to resume by itself.

Kept in the repo rather than run from a shell, because it edits the record of
his money and that should be reviewable afterwards.
"""
from __future__ import annotations

import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import ledger as L                                        # noqa: E402


def main() -> None:
    led = L.Ledger()
    backup = led.path.with_suffix(".before-peak-reset.json")
    shutil.copy2(led.path, backup)
    print(f"  backup: {backup.name}")

    was = led.peak_total_usd
    now = led.running_total_usd()
    led.peak_total_usd = round(now, 2)
    led.save()

    fresh = L.Ledger()
    if abs(fresh.peak_total_usd - round(now, 2)) > 0.005:
        sys.exit("  !! the change did not stick — close the desk window and "
                 "run this again.")

    print()
    print(f"  peak      ${was:.2f}  ->  ${fresh.peak_total_usd:.2f}")
    print(f"  floor     ${L.ACCOUNT_FLOOR_USD:.2f}   (was $50, and it is now a "
          f"PAUSE not a stop)")
    print(f"  35% stop  ${fresh.trailing_stop_usd():.2f}")
    print()
    paused, why = fresh.paused()
    print(f"  paused now? {paused}")
    if why:
        print(f"    {why}")
    print()


if __name__ == "__main__":
    main()

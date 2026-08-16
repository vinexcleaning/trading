"""Point the desk at a new Kalshi API key, and check it actually works.

    py -3 livedesk\\tools\\set_key.py

WHAT IT DOES
    Asks for the two things Kalshi gives you when you create a key, writes them
    to `livedesk/kalshi_env.bat` (which is gitignored), and then **proves it
    works** by reading your balance. Read only -- it cannot place a bet.

WHAT IT NEVER DOES
    It never prints your private key, never sends either value anywhere, and
    never puts them in a file git can see. The key file stays where you put it;
    this only records the PATH to it.

WHY IT EXISTS
    The old key id was sitting in `run.bat` in plain text, committed to a PUBLIC
    repo. Hand-editing a config file at 3am is how that kind of thing happens
    twice, so this does it instead.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
LIVEDESK = HERE.parent
ENV_FILE = LIVEDESK / "kalshi_env.bat"
CLIENT_DIR = LIVEDESK.parent / "kalshi-inplay-bot"


def ask(prompt: str) -> str:
    try:
        return input(prompt).strip().strip('"').strip("'")
    except (EOFError, KeyboardInterrupt):
        print("\n  cancelled -- nothing was changed.")
        sys.exit(1)


def main() -> None:
    print()
    print("  Setting up a Kalshi key for the baseball desk.")
    print("  Nothing here is sent anywhere. It stays on this computer.")
    print()

    key_id = ask("  1. Paste the Key ID from Kalshi and press Enter:\n     ")
    if not key_id:
        sys.exit("  no key id given -- nothing changed.")
    if len(key_id) < 20 or "-" not in key_id:
        print(f"  !! '{key_id}' does not look like a Kalshi key id.")
        print("    They look like  950b93d7-d7c1-4128-b487-1d03dc4406e9")
        if not ask("    Use it anyway? type yes: ").lower().startswith("y"):
            sys.exit("  stopped -- nothing changed.")

    print()
    print("  2. Now the key FILE Kalshi downloaded. Drag it into this window,")
    print("     or paste the full path, then press Enter.")
    key_path = ask("     ")
    p = Path(key_path)
    if not p.exists():
        sys.exit(f"  there is no file at {p} -- nothing changed.")

    # Read only enough to check it is the right KIND of file. Never printed.
    head = p.read_text(encoding="utf-8", errors="replace")[:64]
    if "PRIVATE KEY" not in head:
        print(f"  !! {p.name} does not start like a private key file.")
        print("    It should begin with -----BEGIN RSA PRIVATE KEY-----")
        if not ask("    Use it anyway? type yes: ").lower().startswith("y"):
            sys.exit("  stopped -- nothing changed.")

    ENV_FILE.write_text(
        "@echo off\n"
        "REM LOCAL ONLY. Gitignored. Never commit this file -- the repo is PUBLIC.\n"
        "REM Written by tools/set_key.py\n"
        f"set KALSHI_KEY_ID={key_id}\n"
        f'set "KALSHI_KEY_PATH={p}"\n',
        encoding="utf-8")
    print()
    print(f"  Saved to {ENV_FILE.name}. That file is gitignored.")

    # ---- prove it works, read only ------------------------------------
    print()
    print("  3. Checking it against Kalshi (reading your balance only)...")
    os.environ["KALSHI_KEY_ID"] = key_id
    os.environ["KALSHI_KEY_PATH"] = str(p)
    sys.path.insert(0, str(CLIENT_DIR))
    try:
        from kalshi_client import KalshiClient
        client = KalshiClient(demo=False, read_only=True,
                              kill_switch=str(LIVEDESK / "TRADING_DISABLED"))
        balance = client.balance()
    except Exception as exc:
        print()
        print("  XX   IT DID NOT WORK.")
        print(f"    Kalshi said: {exc}")
        print()
        print("    Most likely one of these:")
        print("      - the Key ID and the key file are from different keys")
        print("      - you deleted this key on Kalshi already")
        print("      - the file is the wrong one (check it is the newest download)")
        print()
        print("    Nothing is broken. Run this again with the right pair.")
        sys.exit(1)

    print()
    print(f"  OK   IT WORKS. Your Kalshi balance reads ${balance:.2f}.")
    print()
    print("    You can now delete the OLD key on Kalshi -- this one is live.")
    print("    Start the desk with:  livedesk\\run.bat")
    print()


if __name__ == "__main__":
    main()

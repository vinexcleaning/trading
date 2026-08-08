"""Canary: the coordinator can never touch money or the network.

In the style of GUARDS.md -- it asserts nothing about intent, it just makes the
change loud. If a future session adds an HTTP client or order-placing code to
coordinator/, this fails.

Run:  py -3 coordinator\\tests\\test_no_money_no_network.py
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

COORD = Path(__file__).resolve().parent.parent
PY_FILES = sorted(p for p in COORD.rglob("*.py") if ".venv" not in p.parts)

# Anything that could reach the outside world.
BANNED_IMPORTS = [
    "requests", "httpx", "aiohttp", "urllib", "urllib3", "http.client",
    "socket", "websocket", "websockets", "ftplib", "smtplib", "telnetlib",
    "boto3", "paramiko", "ccxt",
]

# Anything order-shaped, in code or in string literals.
BANNED_TOKENS = [
    "create_order", "place_order", "submit_order", "cancel_order",
    "/trade-api/", "kalshi.com/trade", "polymarket.com/api",
    "private_key", "api_secret", "api_key", "access_token", "bearer ",
]

# Words that are fine in prose but never in coordinator code.
ALLOW_IN_DOCS = {".md", ".bat", ".txt"}


def fail(msg: str) -> None:
    print(f"FAIL: {msg}")
    fail.count += 1  # type: ignore[attr-defined]


fail.count = 0  # type: ignore[attr-defined]


def main() -> int:
    assert PY_FILES, "no python files found -- the test is pointed at the wrong place"

    for path in PY_FILES:
        if path.name == Path(__file__).name:
            continue
        src = path.read_text(encoding="utf-8", errors="replace")
        rel = path.relative_to(COORD.parent)

        for mod in BANNED_IMPORTS:
            top = mod.split(".")[0]
            if re.search(rf"^\s*(import|from)\s+{re.escape(top)}\b", src, re.MULTILINE):
                fail(f"{rel} imports '{top}'. The coordinator makes no network calls.")

        low = src.lower()
        for tok in BANNED_TOKENS:
            if tok in low:
                fail(f"{rel} contains '{tok}'. The coordinator holds no credential "
                     f"and places no order.")

    # subprocess is allowed, but only to read git. Not curl, not anything else.
    for path in PY_FILES:
        if path.name == Path(__file__).name:
            continue
        src = path.read_text(encoding="utf-8", errors="replace")
        for m in re.finditer(r"subprocess\.\w+\(\s*\[\s*\"([^\"]+)\"", src):
            if m.group(1) != "git":
                fail(f"{path.name} shells out to '{m.group(1)}'. The coordinator "
                     f"may only run read-only git commands.")
        for bad in ("git push", "git commit", "git reset", "git checkout",
                    "git clean", "git rm", "git fetch", "git pull"):
            if bad in src.lower():
                fail(f"{path.name} contains '{bad}'. The coordinator only reads. "
                     f"If this is PROSE telling another session what to run, it "
                     f"belongs in coordinator/prompt_template.md, which is a "
                     f"document and is not scanned. Do not weaken this check.")

    # newprompt.py's output tells a new session to pull the repo, which is a
    # writing git verb and would trip the scan above. The way that is allowed
    # is by living in a document, so the document has to actually be there --
    # if it goes missing, the temptation is to paste the text back into the .py.
    template = COORD / "prompt_template.md"
    if (COORD / "newprompt.py").exists():
        if not template.exists():
            fail("newprompt.py exists but prompt_template.md does not. The "
                 "prompt text must live in the document, not in the module.")
        elif len(template.read_text(encoding="utf-8", errors="replace")) < 500:
            fail("prompt_template.md is nearly empty. A prompt that omits this "
                 "repo's standing rules is worse than no prompt.")

    # It must also not be able to write outside coordinator/ except BRIEF.md.
    for path in PY_FILES:
        src = path.read_text(encoding="utf-8", errors="replace")
        for m in re.finditer(r"REPO\s*/\s*\"([^\"]+)\"", src):
            target = m.group(1)
            if target not in {"BRIEF.md"} and "write" in src[max(0, m.start() - 200):m.start()]:
                fail(f"{path.name} may write to repo root path '{target}'. "
                     f"Only BRIEF.md is allowed outside coordinator/.")

    # A test that redirects brief.BRIEF to a temp file must ALSO redirect
    # brief.BRIEFS, or it publishes its fixtures into the real briefs/ folder
    # and they enter the public chain looking like genuine briefs. This is not
    # hypothetical -- it happened on 2026-08-07 and four fake pages were
    # published locally before the scan caught them.
    for path in PY_FILES:
        src = path.read_text(encoding="utf-8", errors="replace")
        if "brief.BRIEF =" in src and "brief.BRIEFS =" not in src:
            fail(f"{path.name} redirects brief.BRIEF but not brief.BRIEFS. It "
                 f"will write test fixtures into the real briefs/ folder.")

    # Nothing in the real briefs/ folder may contain a test fixture.
    briefs = COORD.parent / "briefs"
    if briefs.is_dir():
        for p in sorted(briefs.glob("BRIEF-*.md")):
            if "SENTINEL" in p.read_text(encoding="utf-8", errors="replace"):
                fail(f"{p.name} contains a test fixture and is not a real brief.")

    # And there must be no credential file lying around.
    for junk in ("*.env", ".env", "*.key", "*.pem", "credentials*"):
        for p in COORD.rglob(junk):
            fail(f"credential-shaped file present: {p.relative_to(COORD.parent)}")

    n = fail.count  # type: ignore[attr-defined]
    if n:
        print(f"\n{n} failure(s). The coordinator is supposed to be inert.")
        return 1
    print(f"OK: {len(PY_FILES)} coordinator file(s) checked. "
          f"No network, no credentials, no order-placing code.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

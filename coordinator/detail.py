"""Layer two of the report: what each chat has actually tried, in plain English.

The table in `where.py` says what each chat is doing. It does not say what has
already been learned, and a table cannot -- so this prints, per chat: what it
tried, what data it used, when that data is from, what came out, and what was
later corrected and why.

Every number carries the dates it was measured over, because a measurement from
June is not a fact about today. Nothing here is recomputed. Every line is read
off `LEDGER.md` (and the ledgers it points at), off that chat's own section of
`BRIEF.md`, or off git. If a claim is wrong, it is wrong in the file it came
from, and this shows you where to go and argue with it.

WHAT THIS CANNOT DO
-------------------
* **It does not judge any of it.** It repeats what each chat recorded. Whether
  a result is real is decided by reading the code, not by reading this.
* **It only sees what was written down.** Work done and never recorded in a
  ledger row or a brief section is invisible here, and looks like idleness.
* **It cannot tell you what is worth doing next.** That is a judgement and it
  is not in this file.

No network. No credentials. Reads files and read-only git.

Usage
-----
  py -3 coordinator\\detail.py            # every chat
  py -3 coordinator\\detail.py --chat mlb  # one chat
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import chats as chatreg  # noqa: E402
import ledger  # noqa: E402

REPO = HERE.parent
WRAP = 74
MAX_PER_GROUP = 4

# The opening marker carries a timestamp -- `<!-- SECTION:mlb updated=... -->`
# -- so anything matching a bare `-->` finds nothing and reports a chat that
# has written a brief as having written none. That is a worse failure than no
# report at all, because it looks like an accusation.
SECTION_RE = r"<!-- SECTION:{slug}[^>]*-->(.*?)<!-- /SECTION:{slug} -->"


def wrap(text: str, indent: str = "    ", width: int = WRAP) -> str:
    words, line, out = text.split(), "", []
    for w in words:
        if line and len(line) + 1 + len(w) > width:
            out.append(line)
            line = w
        else:
            line = f"{line} {w}".strip()
    if line:
        out.append(line)
    return "\n".join(indent + l for l in out) if out else ""


def git(*args: str) -> str:
    try:
        r = subprocess.run(["git", *args], cwd=REPO, capture_output=True,
                           text=True, timeout=60)
        return r.stdout.strip()
    except Exception:
        return ""


def brief_section(slug: str) -> str:
    p = ledger.repo_file(ledger.BRIEF_NAME)
    if not p.exists():
        return ""
    m = re.search(SECTION_RE.format(slug=re.escape(slug)),
                  p.read_text(encoding="utf-8", errors="replace"), re.S)
    if not m:
        return ""
    # Drop the COORDINATOR-STATE comment block: it is machine plumbing that
    # the table above already reads, and printing it here buries the English.
    return re.sub(r"<!--.*?-->", "", m.group(1), flags=re.S).strip()


def rows_for(folders: list[str], rows: list[dict]) -> tuple[list[dict], list[dict]]:
    """(claims this chat owns, claims about its subject owned by someone else).

    Owning is by the row's project column matching one of this chat's folders.
    But several tables in LEDGER.md have no project column at all -- the MLB
    rows are in one of them -- so a chat with real recorded work reads as
    having none. Those are found by name instead and reported separately,
    because "someone else measured this about your subject" is a different
    fact from "you measured this", and merging them would misattribute work.
    """
    want = {f.lower() for f in folders}
    owned, mentioned = [], []
    for r in rows:
        proj = ledger.project_of(r).lower().strip()
        if proj and (proj in want or any(f in proj for f in want)):
            owned.append(r)
            continue
        hay = (" ".join(str(v) for k, v in r.items() if not k.startswith("_"))
               + " " + str(r.get("_section", ""))).lower()
        if any(re.search(rf"\b{re.escape(f)}\b", hay) for f in want):
            mentioned.append(r)
    return owned, mentioned


def recent_commits(folders: list[str], n: int = 5) -> list[str]:
    args = ["log", "-n", str(n), "--format=%h|%ad|%s", "--date=short", "--"]
    out = git(*args, *folders)
    return [l for l in out.splitlines() if l.strip()]


def one_line(row: dict) -> str:
    """A claim, its sample, its dates and its result, on as few lines as it takes."""
    claim = ledger.claim_of(row)
    n = ledger.plain(row.get("n_unit", "") or row.get("n", ""))
    dates = ledger.plain(row.get("date_range", ""))
    effect = ledger.plain(row.get("effect_ci", "") or row.get("result", ""))
    bits = [claim.rstrip(".") + "."]
    if n and n not in {"—", "-", "--"}:
        bits.append(f"Measured on {n}.")
    if dates and dates not in {"—", "-", "--"}:
        bits.append(f"Data from {dates}.")
    else:
        bits.append("No date range was recorded, so it cannot be said how old "
                    "this is.")
    if effect and effect not in {"—", "-", "--"}:
        bits.append(f"Result: {effect}")
    return " ".join(bits)


def group(rows: list[dict], status: str) -> list[dict]:
    return [r for r in rows if ledger.status_of(r) == status]


def chat_block(chat: dict, all_ledger: list[dict]) -> str:
    slug = chat["slug"]
    folders = chat.get("folders", [])
    mine, elsewhere = rows_for(folders, all_ledger)
    L = []
    add = L.append

    add("")
    add("-" * WRAP)
    add(chat["name"].upper())
    add("-" * WRAP)
    add(wrap(chat.get("purpose", ""), "  "))
    add("")
    add(f"  Folders it owns : {', '.join(folders) or '(none)'}")
    add(f"  You type        : {chat.get('opening', 'next')}")
    add("")

    section = brief_section(slug)
    if section:
        add("  IN ITS OWN WORDS -- copied from its section of BRIEF.md, not")
        add("  rewritten, and not checked:")
        add("")
        for line in section.splitlines():
            t = ledger.plain(line)
            if t:
                add(wrap(t, "    "))
        add("")
    else:
        add("  IN ITS OWN WORDS: nothing. This chat has not written a section of")
        add("  BRIEF.md, so there is no summary from it in its own words. That is")
        add("  a gap in the record, not evidence it has done nothing.")
        add("")

    if not mine:
        add("  WHAT IT HAS TRIED: no claim in any ledger names its folders. Either")
        add("  it has not produced a recorded result yet, or its results were")
        add("  written up somewhere the ledger does not point at.")
        add("")
    else:
        retracted = group(mine, "RETRACTED")
        settled = group(mine, "SETTLED")
        suggestive = group(mine, "SUGGESTIVE")
        broken = group(mine, "BROKEN")
        unverified = group(mine, "UNVERIFIED")

        add(f"  WHAT IT HAS TRIED -- {len(mine)} recorded claims: "
            f"{len(settled)} settled, {len(retracted)} later withdrawn, "
            f"{len(suggestive)} only suggestive, {len(broken)} known broken, "
            f"{len(unverified)} never verified.")
        add("")

        if retracted:
            add("  THINGS THAT TURNED OUT TO BE WRONG -- read these first, they are")
            add("  the ones that cost time:")
            add("")
            for r in retracted[:MAX_PER_GROUP]:
                add(wrap(f"[{r['_id']}] {ledger.claim_of(r)}", "    - "[:4] + "  "))
                why = ledger.why_of(r) or ledger.plain(r.get("effect_ci", ""))
                if why:
                    add(wrap(f"Why it died: {why}", "        "))
                add("")
            if len(retracted) > MAX_PER_GROUP:
                add(f"      ...and {len(retracted) - MAX_PER_GROUP} more.")
                add("")

        if settled:
            add("  THINGS IT CONSIDERS SETTLED -- reproducible, enough data, checked")
            add("  on data it did not fit to:")
            add("")
            for r in settled[:MAX_PER_GROUP]:
                add(wrap(f"[{r['_id']}] {one_line(r)}", "      "))
                add("")
            if len(settled) > MAX_PER_GROUP:
                add(f"      ...and {len(settled) - MAX_PER_GROUP} more.")
                add("")

        if suggestive or broken or unverified:
            add("  NOT DECIDED EITHER WAY -- do not build on these:")
            add("")
            for r in (suggestive + broken + unverified)[:MAX_PER_GROUP]:
                add(wrap(f"[{r['_id']}] ({ledger.status_of(r).lower()}) "
                         f"{one_line(r)}", "      "))
                add("")

    if elsewhere:
        add(f"  ALSO ON ITS SUBJECT, but measured by another chat -- "
            f"{len(elsewhere)} claim(s). Worth knowing before repeating any of it:")
        add("")
        for r in elsewhere[:MAX_PER_GROUP]:
            add(wrap(f"[{r['_id']}] ({ledger.status_of(r).lower()}) {one_line(r)}",
                     "      "))
            add("")
        if len(elsewhere) > MAX_PER_GROUP:
            add(f"      ...and {len(elsewhere) - MAX_PER_GROUP} more.")
            add("")

    commits = recent_commits(folders)
    if commits:
        add("  WHAT IT ACTUALLY CHANGED, most recent first:")
        add("")
        for c in commits:
            parts = c.split("|", 2)
            if len(parts) == 3:
                h, when, subject = parts
                add(wrap(f"{when}  {subject}  ({h})", "      "))
        add("")
    else:
        add("  WHAT IT ACTUALLY CHANGED: nothing in its folders has been committed.")
        add("")
    return "\n".join(L)


def _ascii_safe_console():
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass


def main() -> int:
    _ascii_safe_console()
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--chat", help="one chat's short code. Default: all of them")
    a = ap.parse_args()

    rows, files_read, files_missing = ledger.all_rows()
    wanted = [c for c in chatreg.chats()
              if not a.chat or c["slug"] == a.chat]
    if a.chat and not wanted:
        known = ", ".join(c["slug"] for c in chatreg.chats())
        sys.exit(f"No chat called '{a.chat}'. Known: {known}")

    print("=" * WRAP)
    print("WHAT EACH CHAT HAS ACTUALLY TRIED")
    print("=" * WRAP)
    print()
    print(wrap(
        "Nothing below is recomputed. Every claim is copied from the chat that "
        "made it, and every number is printed with the dates the data covers. "
        "This does not check whether any of it is right -- it tells you where "
        "to go and look.", "  "))
    print()
    print(f"  Read from: {', '.join(files_read)}")
    if files_missing:
        print(f"  MISSING, so the picture is incomplete: {', '.join(files_missing)}")

    for c in wanted:
        print(chat_block(c, rows))

    print("-" * WRAP)
    print(wrap(
        "A chat with nothing here has written nothing down. That is a gap in "
        "the record and not proof it has been idle -- and it is worth asking "
        "that window to write its section.", "  "))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

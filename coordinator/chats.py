"""The names of the chats, and the exact words to type in each one.

Every chat gets a proper name, a short code, a set of folders, and one sentence
saying what it is for. Without that, the sixth window opened in a month is "the
other tennis one" and nobody can say what it owns.

Naming rules, enforced below rather than remembered:
  * a name is unique, and so is a slug;
  * a slug is lowercase letters, digits and hyphens, because it is also a
    folder name and a BRIEF.md section marker;
  * no chat may claim a folder another chat already owns -- that is the
    "one session per folder" rule from HOW_THIS_WORKS.md, checked instead of
    trusted.

It also compares this list against WORKSTREAMS in scan.py and reports anything
in one and not the other. The two lists are NOT merged; see chats.json.

No network. No credentials. Reads and writes one JSON file inside coordinator/.

Usage
-----
  py -3 coordinator\\chats.py list
  py -3 coordinator\\chats.py check
  py -3 coordinator\\chats.py new --name "Soccer - de-vig against a retail book" \\
        --slug soccer-retail --folder soccer-retail \\
        --purpose "Tests whether a fat-margin retail book beats Kalshi on soccer."
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
REGISTRY = HERE / "chats.json"

SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9-]{1,30}$")


def load() -> dict:
    if not REGISTRY.exists():
        return {"chats": []}
    return json.loads(REGISTRY.read_text(encoding="utf-8"))


def chats() -> list[dict]:
    return load().get("chats", [])


def by_slug(slug: str) -> dict | None:
    for c in chats():
        if c["slug"] == slug:
            return c
    return None


def name_of(slug: str) -> str:
    c = by_slug(slug)
    return c["name"] if c else slug


def folder_owner(folder: str) -> str | None:
    for c in chats():
        if folder in c.get("folders", []):
            return c["slug"]
    return None


def workstreams() -> dict:
    """WORKSTREAMS out of scan.py, or {} if it cannot be imported."""
    try:
        sys.path.insert(0, str(HERE))
        import scan  # noqa: E402

        return dict(scan.WORKSTREAMS)
    except Exception:
        return {}


def drift() -> list[str]:
    """Everything the two lists disagree about. Empty is the good case."""
    out = []
    ws = workstreams()
    if not ws:
        return ["could not read WORKSTREAMS out of scan.py, so no comparison was "
                "made -- the two lists could be anything"]
    mine = {c["slug"] for c in chats()}
    theirs = set(ws)
    for slug in sorted(mine - theirs):
        out.append(f"'{slug}' is a named chat but is not a workstream in scan.py, "
                   f"so it will not appear in the where-is-everything table")
    for slug in sorted(theirs - mine):
        out.append(f"'{slug}' is a workstream in scan.py but has no name in "
                   f"chats.json, so it has no opening line to tell anyone")
    for slug in sorted(mine & theirs):
        a = set(by_slug(slug).get("folders", []))
        b = set(ws[slug].get("folders", []))
        for f in sorted(a - b):
            out.append(f"'{slug}' claims folder '{f}' in chats.json; scan.py does not")
        for f in sorted(b - a):
            out.append(f"scan.py gives '{slug}' folder '{f}'; chats.json does not")
    return out


def validate() -> list[str]:
    """Rule breaks inside chats.json itself."""
    out = []
    seen_names: dict[str, str] = {}
    seen_slugs: set[str] = set()
    owners: dict[str, str] = {}
    for c in chats():
        slug, name = c.get("slug", ""), c.get("name", "")
        if not SLUG_RE.match(slug):
            out.append(f"'{slug}' is not a valid short code (lowercase, digits, hyphens)")
        if slug in seen_slugs:
            out.append(f"short code '{slug}' is used twice")
        seen_slugs.add(slug)
        key = name.strip().lower()
        if key in seen_names:
            out.append(f"the name '{name}' is used by two chats")
        seen_names[key] = slug
        if not c.get("purpose", "").strip():
            out.append(f"'{slug}' has no purpose line, so nobody can tell what it is for")
        for f in c.get("folders", []):
            if f in owners and owners[f] != slug:
                out.append(f"folder '{f}' is claimed by both '{owners[f]}' and '{slug}' "
                           f"-- one folder, one chat")
            owners[f] = slug
    return out


def cmd_list() -> None:
    print("THE CHATS")
    print()
    for c in chats():
        print(f"  {c['name']}")
        print(f"      short code : {c['slug']}")
        print(f"      what it is : {c.get('purpose','')}")
        print(f"      folders    : {', '.join(c.get('folders', [])) or '(none)'}")
        print(f"      you type   : {c.get('opening','next')}")
        subs = c.get("subjects", [])
        print(f"      routes on  : {', '.join(subs) if subs else 'NOTHING -- no idea will route here on its own'}")
        print(f"      named on   : {c.get('created','?')}")
        print()
    print("To use any of them: open a Claude Code window in C:\\Users\\vinig\\trading")
    print("and type the words on its 'you type' line. Nothing else.")


def cmd_check() -> int:
    problems = validate()
    d = drift()
    if problems:
        print("PROBLEMS INSIDE chats.json")
        for p in problems:
            print(f"  - {p}")
        print()
    if d:
        print("THE TWO LISTS OF CHATS DISAGREE")
        print("  chats.json says what each chat is called; scan.py says which")
        print("  folders each one owns. Neither is authoritative over the other,")
        print("  so this is reported and not silently fixed.")
        for line in d:
            print(f"  - {line}")
        print()
    if not problems and not d:
        print(f"OK: {len(chats())} named chats, and chats.json agrees with scan.py.")
    return 1 if problems else 0


def cmd_new(name: str, slug: str, folder: str, purpose: str, opening: str,
            subjects: str = "") -> int:
    data = load()
    if by_slug(slug):
        sys.exit(f"'{slug}' already exists: {name_of(slug)}. Pick another short code.")
    if not SLUG_RE.match(slug):
        sys.exit(f"'{slug}' is not a valid short code. Lowercase letters, digits "
                 f"and hyphens, 2 to 31 characters.")
    for c in data["chats"]:
        if c["name"].strip().lower() == name.strip().lower():
            sys.exit(f"A chat is already called '{name}'. Names have to be unique "
                     f"or you cannot tell two windows apart.")
    owner = folder_owner(folder)
    if owner:
        sys.exit(f"Folder '{folder}' already belongs to '{name_of(owner)}'. One "
                 f"folder, one chat -- otherwise two windows edit the same files.")
    if not purpose.strip():
        sys.exit("Refusing to name a chat with no purpose line.")

    words = [w.strip().lower() for w in re.split(r"[,\s]+", subjects) if w.strip()]
    data["chats"].append({
        "name": name.strip(),
        "slug": slug,
        "folders": [folder],
        "purpose": purpose.strip(),
        "opening": opening.strip() or "next",
        "created": f"{datetime.now():%Y-%m-%d}",
        "subjects": words,
    })
    REGISTRY.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n",
                        encoding="utf-8", newline="\n")
    print(f"Named it: {name}")
    print(f"  short code : {slug}")
    print(f"  folder     : {folder}")
    print(f"  you type   : {opening or 'next'}")
    if not words:
        print("  subjects   : NONE GIVEN -- a new idea will never route here on")
        print("               its own. Add --subjects next time.")
    else:
        print(f"  subjects   : {', '.join(words)}")
    print()
    print("Two things this could not do, both outside coordinator/:")
    print(f"  - add '{slug}' to WORKSTREAMS in coordinator\\scan.py, which is what")
    print("    puts it in the where-is-everything table")
    print(f"  - create the folder '{folder}'. The new chat does that itself.")
    return 0


def _ascii_safe_console():
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass


def main() -> int:
    _ascii_safe_console()
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("list")
    sub.add_parser("check")
    n = sub.add_parser("new")
    n.add_argument("--name", required=True)
    n.add_argument("--slug", required=True)
    n.add_argument("--folder", required=True)
    n.add_argument("--purpose", required=True)
    n.add_argument("--opening", default="next")
    n.add_argument("--subjects", default="",
                   help="words an idea might use for this subject, comma separated. Without them, a new idea will not route here.")
    a = ap.parse_args()
    if a.cmd == "list":
        cmd_list()
        return 0
    if a.cmd == "check":
        return cmd_check()
    return cmd_new(a.name, a.slug, a.folder, a.purpose, a.opening,
                   a.subjects)


if __name__ == "__main__":
    raise SystemExit(main())

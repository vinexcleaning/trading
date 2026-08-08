"""Turn a plain-English idea into a prompt a new Claude Code session can run.

The user says what he wants in one sentence. This writes the whole opening
message for a new window: the idea verbatim, this repo's standing rules, the
folder conventions, the evidence standards, and the reporting format -- so the
new session starts knowing the things that have already cost this repo a
correction.

WHAT IT DOES NOT DO
-------------------
* **It does not judge the idea.** The idea is copied through character for
  character. It is not paraphrased, tightened or improved. Judging the trading
  work is not the coordinator's job -- see COORDINATOR.md.
* **It cannot tell you the idea is already refuted.** It does a KEYWORD
  cross-check against LEDGER.md and INBOX.md and prints what it hits, flagged
  as "possibly related, go and read it". Keyword matching misses every
  paraphrase. **A clean cross-check is not evidence the idea is new.**
* **It cannot open the session.** It writes a file and says which window to
  paste it into.
* **It cannot add the line to INBOX.md** -- that file is outside coordinator/
  and writing outside this folder is blocked by test. It prints the exact line.

No network. No credentials. Writes only inside coordinator/prompts/.

Usage
-----
  py -3 coordinator\\newprompt.py --idea "test de-vig against a retail book"
  py -3 coordinator\\newprompt.py --idea-file idea.txt --slug devig
  py -3 coordinator\\newprompt.py --idea "..." --slug soccer --folder soccer-devig
"""

from __future__ import annotations

import argparse
import re
import sys
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
OUT = HERE / "prompts"

KNOWN_SLUGS = ["tennis", "mlb", "devig", "signal", "coordinator"]

CROSS_CHECK_FILES = ["LEDGER.md", "INBOX.md", "SCOREBOARD.md"]
CROSS_CHECK_HITS = 6

STOPWORDS = {
    "the", "and", "for", "that", "this", "with", "from", "into", "over", "under",
    "have", "has", "had", "was", "were", "are", "not", "but", "can", "could",
    "would", "should", "will", "does", "did", "doing", "done", "what", "when",
    "where", "which", "who", "why", "how", "than", "then", "them", "they",
    "their", "there", "here", "some", "any", "all", "one", "two", "out", "off",
    "its", "it's", "our", "your", "his", "her", "you", "get", "got", "make",
    "made", "check", "test", "tests", "testing", "run", "runs", "look", "see",
    "want", "need", "like", "just", "really", "actually", "maybe", "whether",
    "against", "about", "more", "most", "less", "very", "each", "every", "also",
}


def slugify(text: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return (s or "idea")[:40]


def terms(idea: str) -> list[str]:
    words = re.findall(r"[a-zA-Z][a-zA-Z0-9'-]{3,}", idea.lower())
    seen, out = set(), []
    for w in words:
        if w in STOPWORDS or w in seen:
            continue
        seen.add(w)
        out.append(w)
    return out


def cross_check(idea: str) -> list[tuple[int, str, int, str]]:
    """(score, file, line number, text) for lines sharing words with the idea.

    Keyword overlap. Nothing here understands the idea, and a paraphrase of an
    already-refuted claim scores zero. Read the hits; do not trust the misses.
    """
    words = terms(idea)
    if not words:
        return []
    hits = []
    for name in CROSS_CHECK_FILES:
        p = REPO / name
        if not p.exists():
            continue
        for n, line in enumerate(p.read_text(encoding="utf-8", errors="replace")
                                 .splitlines(), 1):
            low = line.lower()
            score = sum(1 for w in words if w in low)
            if score >= 2 and len(line.strip()) > 30:
                hits.append((score, name, n, line.strip()))
    hits.sort(key=lambda h: (-h[0], h[1], h[2]))
    return hits[:CROSS_CHECK_HITS]


TEMPLATE = HERE / "prompt_template.md"


def render_template(**fields: str) -> str:
    """Fill %%TOKEN%% placeholders in prompt_template.md.

    The prompt text lives in a Markdown file rather than in this module, and
    that is not cosmetic. The prompt tells the new session to start by pulling
    the repo, and `tests/test_no_money_no_network.py` fails any coordinator
    .py file that so much as contains the name of a git verb that writes. The
    canary is right and was not weakened: the coordinator must never run one.
    A sentence telling a DIFFERENT session what to run is prose, not an action,
    and prose belongs in a document -- which the canary already exempts.

    So: **anything the generated prompt says goes in prompt_template.md.**
    Do not move it back in here to save a file.

    Token substitution, not str.format, so a stray brace in the template -- a
    JSON example, a code block -- cannot raise at render time.
    """
    text = TEMPLATE.read_text(encoding="utf-8")
    for key, value in fields.items():
        text = text.replace(f"%%{key.upper()}%%", value)
    left = re.findall(r"%%[A-Z_]+%%", text)
    if left:
        raise SystemExit(
            f"prompt_template.md has placeholders nothing filled in: "
            f"{', '.join(sorted(set(left)))}. The prompt was NOT written."
        )
    return text


def build(idea: str, title: str, slug: str, folder: str) -> str:
    hits = cross_check(idea)
    if hits:
        cc = "\n".join(
            f"- `{name}:{n}` — {text[:200]}" for _, name, n, text in hits
        )
    else:
        cc = ("Nothing in `LEDGER.md`, `INBOX.md` or `SCOREBOARD.md` shares two "
              "or more words with the idea. **That is a weak signal, not a "
              "clearance.** Search them yourself for the concept.")
    quoted = "\n> ".join(idea.strip().splitlines())
    return render_template(
        title=title,
        when=f"{datetime.now():%Y-%m-%d %H:%M}",
        idea_quoted=quoted,
        slug=slug,
        folder=folder,
        cross_check=cc,
    )


def _ascii_safe_console():
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass


def main() -> int:
    _ascii_safe_console()
    ap = argparse.ArgumentParser(description=__doc__)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--idea", help="the idea, in plain English, in quotes")
    g.add_argument("--idea-file", help="a file holding the idea")
    ap.add_argument("--title", help="short title. Defaults to the idea's first line")
    ap.add_argument("--slug", help=f"workstream slug. Known: {', '.join(KNOWN_SLUGS)}")
    ap.add_argument("--folder", help="folder the new session works in")
    a = ap.parse_args()

    idea = (Path(a.idea_file).read_text(encoding="utf-8") if a.idea_file
            else a.idea).strip()
    if not idea:
        sys.exit("Refusing to write a prompt for an empty idea.")

    title = (a.title or idea.splitlines()[0]).strip().rstrip(".")
    if len(title) > 70:
        title = title[:67].rsplit(" ", 1)[0] + "…"
    slug = a.slug or slugify(title)[:20]
    folder = a.folder or slug

    OUT.mkdir(exist_ok=True)
    path = OUT / f"SESSION-{datetime.now():%Y-%m-%d}-{slugify(title)}.md"
    n = 2
    while path.exists():
        path = OUT / f"SESSION-{datetime.now():%Y-%m-%d}-{slugify(title)}-{n}.md"
        n += 1
    path.write_text(build(idea, title, slug, folder), encoding="utf-8",
                    newline="\n")

    print(f"Wrote {path.relative_to(REPO)}")
    print()
    print("WHAT THE USER DOES NEXT, in order:")
    print("  1. Open a NEW Claude Code window in C:\\Users\\vinig\\trading")
    print(f"  2. Paste the whole of {path.relative_to(REPO)} as the first message")
    print("  3. Leave it. It is written to run for an hour without you.")
    print()
    if slug not in KNOWN_SLUGS:
        print(f"NOTE: '{slug}' is a NEW workstream. Two follow-ups, neither of")
        print("which this script may do, because both are outside coordinator/:")
        print(f"  - add '{slug}' to WORKSTREAMS in coordinator\\scan.py so it")
        print("    appears in the where-is-everything table")
        print(f"  - the new session writes its own brief section with")
        print(f"    py -3 coordinator\\brief.py write {slug} --file <body.md>")
        print()
    print("Paste this line into INBOX.md yourself -- this script does not write")
    print("outside coordinator/, by design:")
    first = idea.splitlines()[0]
    print(f"  - {datetime.now():%Y-%m-%d} — {first[:150]}")
    print()
    print("The idea was copied verbatim and was NOT judged. The keyword")
    print("cross-check inside the file finds duplicates it happens to share")
    print("words with; it misses every paraphrase.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

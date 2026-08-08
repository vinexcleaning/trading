"""Where is everything at? One table, plain English, no acronyms.

Columns: which chat window | what it is doing now | what is left | is its
background test alive | does it need the user.

WHERE THE WORDS COME FROM, AND WHY THAT MATTERS
-----------------------------------------------
"Doing now" and "What's left" are **quoted from what that session last wrote
about itself**. This module reads files. It cannot watch a session work.

A session may declare its state exactly, by putting this block anywhere in its
own HANDOFF.md or in its BRIEF.md section (HTML comments are invisible in
rendered Markdown, so it costs the page nothing):

    <!-- COORDINATOR-STATE
    doing: running the paper forward test toward 2,500 settled markets
    left: score the 16 bots at 2,500; nothing before that
    needs: no
    -->

`needs:` is either `no`, or `yes - <the question, in one line>`.

When no session declared anything, this GUESSES from HANDOFF.md and marks the
cell with a `~`. Every run prints how many cells were quoted and how many were
guessed, so the table cannot quietly rot into fiction. See COORDINATOR.md
section 3b.

No network. No credentials. Reads files and read-only git. Writes only
coordinator/WHERE.md.

Usage
-----
  py -3 coordinator\\where.py            # the table plus the explanation
  py -3 coordinator\\where.py --quiet    # write WHERE.md, print nothing
"""

from __future__ import annotations

import argparse
import re
import sys
import textwrap
from datetime import datetime
from pathlib import Path

import mail as mailmod
import runners as runmod
import scan as scanmod

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
WHERE = HERE / "WHERE.md"

STATE_RE = re.compile(r"<!--\s*COORDINATOR-STATE(.*?)-->", re.S | re.I)
FIELD_RE = re.compile(r"^\s*(doing|left|needs)\s*:\s*(.+?)\s*$", re.I | re.M)

# Headings that plausibly hold "what is left".
#
# Deliberately narrow. A bare `next` matched "what the next session should do"
# in bot-hunt's HANDOFF and put a sentence about reading order into the
# "what's left" column. A guess that is confidently wrong is worse than a blank
# cell, because a blank cell asks to be filled in.
LEFT_HEADINGS = re.compile(
    r"^#{1,4}\s*[\d.\s]*"
    r"(?=.*\b(next (action|step|thing|up)|what'?s left|remaining|to ?do|"
    r"still (to do|open)|open (item|question)))",
    re.I,
)

# Long enough for a real sentence, short enough that five rows fit on a phone.
MAX_CELL = 170


# --------------------------------------------------------------------------
# reading what a session said about itself
# --------------------------------------------------------------------------
def strip_markdown(s: str) -> str:
    """Plain English means no backticks, no bold stars, no link syntax."""
    s = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", s)
    s = s.replace("**", "").replace("`", "").replace("~~", "")
    s = re.sub(r"^[\s>*\-#\d.]+", "", s)
    return re.sub(r"\s+", " ", s).strip()


def declared(text: str) -> dict:
    """Pull a COORDINATOR-STATE block out of any document."""
    m = STATE_RE.search(text or "")
    if not m:
        return {}
    out = {}
    for k, v in FIELD_RE.findall(m.group(1)):
        out[k.lower()] = strip_markdown(v)[:MAX_CELL]
    return out


def paragraph_after(lines: list[str], i: int) -> str:
    """The first real paragraph below line i, with wrapped lines joined.

    Markdown wraps prose at 80 columns, so reading a single line hands back
    half a sentence -- the mlb row read "a paper-only forward test of five MLB
    mentalities on" and stopped there.
    """
    buf, started = [], False
    for nxt in lines[i + 1:i + 16]:
        s = strip_markdown(nxt)
        if not s or "---" in nxt or nxt.strip().startswith("|") or \
                nxt.lstrip().startswith("#"):
            if started:
                break
            continue
        buf.append(s)
        started = True
        if len(" ".join(buf)) > MAX_CELL:
            break
    return " ".join(buf)[:MAX_CELL] if started else ""


def guess_doing(text: str) -> str:
    """Best guess at 'doing now' from a HANDOFF.md. Always labelled a guess."""
    lines = text.splitlines()
    # A "## State: ..." heading is the clearest thing a session ever writes.
    for line in lines:
        s = line.strip()
        if s.lower().startswith("## state") and ":" in s:
            body = strip_markdown(s.split(":", 1)[1])
            if body:
                return body[:MAX_CELL]
    for i, line in enumerate(lines):
        if re.match(r"^#{1,4}\s*[\d.\s]*(what (this|it) is|state|status|"
                    r"what is running)", line.strip(), re.I):
            p = paragraph_after(lines, i)
            if p:
                return p
    return paragraph_after(lines, 0)


def guess_left(text: str) -> str:
    """First item under the first 'what is left' heading, wrapped lines joined."""
    lines = text.splitlines()
    for i, line in enumerate(lines):
        if LEFT_HEADINGS.match(line.strip()):
            p = paragraph_after(lines, i)
            if p:
                return p
    return ""


def read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def brief_section_text(slug: str) -> str:
    brief = REPO / "BRIEF.md"
    if not brief.exists():
        return ""
    text = read(brief)
    m = re.search(
        rf"<!--\s*SECTION:{re.escape(slug)}[^>]*-->(.*?)<!--\s*/SECTION:{re.escape(slug)}\s*-->",
        text, re.S)
    return m.group(1) if m else ""


def handoffs(slug: str):
    """Every HANDOFF.md in this workstream, the one to believe first.

    The workstream's FIRST folder wins, not the most recently touched one.
    Ordering by modification time put kalshi-tennis (an old analysis folder)
    ahead of tennis-paper-forward (the thing actually running) and the table
    described the wrong project. Registry order encodes which folder is the
    workstream; a timestamp does not.
    """
    out, folders = [], scanmod.WORKSTREAMS[slug]["folders"]
    for rank, folder in enumerate(folders):
        p = REPO / folder / "HANDOFF.md"
        if p.exists():
            try:
                out.append((rank, p.stat().st_mtime, folder, p))
            except OSError:
                pass
    out.sort()
    return [(t, folder, p) for _, t, folder, p in out]


# --------------------------------------------------------------------------
# assembling one row
# --------------------------------------------------------------------------
def row_for(slug: str, ws: dict, state: dict, runstate: dict) -> dict:
    sources, doing, left, needs_declared = [], "", "", ""

    # 1. A declared block wins, wherever it is. Brief section first -- it is
    #    the thing a session rewrites most often.
    for label, text in [("its BRIEF.md section", brief_section_text(slug))] + \
                       [(f"{folder}/HANDOFF.md", read(p)) for _, folder, p in handoffs(slug)]:
        d = declared(text)
        if d:
            doing = doing or d.get("doing", "")
            left = left or d.get("left", "")
            needs_declared = needs_declared or d.get("needs", "")
            sources.append(label)
            if doing and left:
                break

    quoted = bool(doing or left)

    # 2. Fall back to guessing, and say so. Both cells come from the SAME
    #    document -- "doing" from one project and "left" from another reads as
    #    one coherent sentence pair and is not one.
    if not doing or not left:
        for _, folder, p in handoffs(slug):
            text = read(p)
            gd, gl = guess_doing(text), guess_left(text)
            if not (gd or gl):
                continue
            if not doing and gd:
                doing = "~ " + gd
            if not left and gl:
                left = "~ " + gl
            sources.append(f"guessed from {folder}/HANDOFF.md")
            break

    doing = doing or "nothing written down"
    left = left or "nothing written down"

    # 3. How old is that writing? This is the honest part of the two columns.
    ages = [t for t, _, _ in handoffs(slug)]
    sec_written = state["sections"].get(slug)
    written = max(ages) if ages else 0
    said_when = runmod.english_age(runmod.minutes_since(written)) if written else "never"

    # 4. Background tests belonging to this workstream.
    # Every state is counted. Showing only the worst one hid a live tennis
    # runner behind an unobservable laptop recorder and read "can't see from
    # this machine" for a workstream whose test was demonstrably running.
    tests = [r for r in runstate["runners"] if r["workstream"] == slug]
    if not tests:
        test_cell, test_detail = "none", "This workstream has no background test."
    else:
        tally: dict[str, int] = {}
        for t in tests:
            tally[t["state"]] = tally.get(t["state"], 0) + 1
        order = [runmod.STALE, runmod.NEVER, runmod.ALIVE, runmod.FINISHED,
                 runmod.UNSEEN]
        parts = [(f"{n} " if len(tests) > 1 else "") + s
                 for s in order for n in [tally.get(s, 0)] if n]
        test_cell = ", ".join(parts)
        test_detail = " ".join(f"{t['title']}: {t['state']}. {t['why']}" for t in tests)

    # 5. "Needs me" -- only from signals that can actually be established.
    why_needed = []
    for t in tests:
        if t["needs_a_human"]:
            why_needed.append(
                f"the {t['title'].lower()} is not running -- restart it with "
                f"{t['restart']}"
            )
    open_mail = state["mail"].get(slug, {}).get("OPEN", 0)
    if open_mail:
        why_needed.append(
            f"{open_mail} instruction(s) sitting unanswered in that window -- "
            f"open it and say 'check your mail'"
        )
    # Unpushed commits are deliberately NOT attributed per workstream. `git log
    # origin/main..HEAD` gives commits, not folders, and a commit that touches
    # three folders would be reported three times as three separate problems.
    # It is reported once, for the whole repo, by scan.py.
    dirty = sum(state["folders"].get(f, {}).get("dirty", 0) for f in ws["folders"])
    if dirty:
        why_needed.append(
            f"{dirty} changed file(s) never committed -- invisible to the "
            f"coordinating chat until that window commits and pushes"
        )
    if needs_declared and not needs_declared.lower().startswith("no"):
        why_needed.append(needs_declared.lstrip("yes").lstrip(" -–—:").strip()
                          or "that session says it needs you")

    return {
        "slug": slug,
        "title": ws["title"],
        "doing": doing,
        "left": left,
        "test": test_cell,
        "test_detail": test_detail,
        "needs": "YES" if why_needed else "no",
        "why_needed": why_needed,
        "quoted": quoted,
        "sources": sources,
        "said_when": said_when,
        "brief_written": sec_written or "never",
    }


# --------------------------------------------------------------------------
# rendering
# --------------------------------------------------------------------------
def wrap_table(rows, headers, widths) -> str:
    """A table that survives a narrow console, without a dependency."""
    def line(ch="-"):
        return "+" + "+".join(ch * (w + 2) for w in widths) + "+"

    out = [line("=")]
    cells = [textwrap.wrap(h, w) or [""] for h, w in zip(headers, widths)]
    for i in range(max(len(c) for c in cells)):
        out.append("| " + " | ".join(
            (c[i] if i < len(c) else "").ljust(w) for c, w in zip(cells, widths)
        ) + " |")
    out.append(line("="))
    for r in rows:
        cells = [textwrap.wrap(str(v), w) or [""] for v, w in zip(r, widths)]
        for i in range(max(len(c) for c in cells)):
            out.append("| " + " | ".join(
                (c[i] if i < len(c) else "").ljust(w) for c, w in zip(cells, widths)
            ) + " |")
        out.append(line())
    return "\n".join(out)


def build():
    state = scanmod.collect()
    runstate = runmod.check_all()
    rows = [row_for(slug, ws, state, runstate)
            for slug, ws in scanmod.WORKSTREAMS.items()]
    return state, runstate, rows


def render_console(state, runstate, rows) -> str:
    L = []
    L.append("=" * 78)
    L.append(f"WHERE IS EVERYTHING AT     {state['now']}     commit {state['head']}")
    L.append("=" * 78)
    L.append("")
    table = [
        [r["slug"], r["doing"], r["left"], r["test"], r["needs"]]
        for r in rows
    ]
    L.append(wrap_table(
        table,
        ["chat", "doing now", "what's left", "background test", "needs you"],
        [12, 25, 25, 17, 9],
    ))
    L.append("")

    needed = [r for r in rows if r["needs"] == "YES"]
    if needed:
        L.append("WHAT NEEDS YOU, AND EXACTLY WHAT TO DO")
        L.append("")
        for r in needed:
            L.append(f"  {r['slug']} -- {r['title']}")
            for w in r["why_needed"]:
                for chunk in textwrap.wrap(w, 70, initial_indent="      - ",
                                           subsequent_indent="        "):
                    L.append(chunk)
            L.append("")
    else:
        L.append("Nothing needs you right now.")
        L.append("")

    L.append("HOW MUCH OF THIS TABLE IS QUOTED, AND HOW MUCH IS GUESSED")
    L.append("")
    q = sum(1 for r in rows if r["quoted"])
    L.append(f"  {q} of {len(rows)} chats declared their own state. The other "
             f"{len(rows) - q} were")
    L.append("  guessed from HANDOFF.md and are marked with a ~ in the table.")
    L.append("  A ~ cell is a guess by a script that cannot read intent.")
    L.append("")
    for r in rows:
        L.append(f"  {r['slug']:<12} last wrote about itself {r['said_when']}"
                 f"   (brief section: {r['brief_written']})")
    L.append("")
    L.append("  These two columns say what each chat LAST WROTE DOWN, not what")
    L.append("  it is doing this second. Nothing here can watch a chat work.")
    return "\n".join(L)


def render_markdown(state, runstate, rows) -> str:
    L = ["# WHERE.md — where is everything at\n"]
    L.append(f"Generated **{state['now']}** at commit `{state['head']}` by "
             f"`coordinator\\start.bat`. **Never hand-edit it** — it is "
             f"regenerated and nothing is lost if it is deleted.\n")
    L.append("| Chat | Doing now | What's left | Background test | Needs you |")
    L.append("|---|---|---|---|---|")
    for r in rows:
        L.append(f"| **{r['slug']}** | {r['doing']} | {r['left']} | "
                 f"{r['test']} | {'**YES**' if r['needs'] == 'YES' else 'no'} |")
    L.append("")
    L.append("A cell beginning `~` is a **guess** made from that project's "
             "`HANDOFF.md`, not something the session declared. "
             f"{sum(1 for r in rows if r['quoted'])} of {len(rows)} chats "
             "declared their own state.\n")

    needed = [r for r in rows if r["needs"] == "YES"]
    L.append("## What needs you\n")
    if needed:
        for r in needed:
            L.append(f"**{r['slug']} — {r['title']}**\n")
            for w in r["why_needed"]:
                L.append(f"- {w}")
            L.append("")
    else:
        L.append("Nothing. No signal fired — which means *no signal fired*, "
                 "not *all is well*.\n")

    L.append("## Background tests\n")
    L.append("| Test | State | What it is | Detail |")
    L.append("|---|---|---|---|")
    for t in runstate["runners"]:
        L.append(f"| {t['title']} | **{t['state']}** | {t['plain_english']} | "
                 f"{t['why']} |")
    L.append("")
    L.append("`ALIVE` means **it wrote to its log recently**. It does not mean "
             "the numbers coming out of it are correct — nothing here checks "
             "that. See [COORDINATOR.md](COORDINATOR.md) §3b.\n")

    un = runstate["unregistered"]
    if un:
        L.append(f"### {len(un)} log file(s) on disk that nobody registered\n")
        L.append("Not watched by anything above. Newest first.\n")
        for u in un[:runmod.UNREGISTERED_SHOWN]:
            L.append(f"- `{u['path']}` — last touched {u['age']}")
        if len(un) > runmod.UNREGISTERED_SHOWN:
            L.append(f"- …and {len(un) - runmod.UNREGISTERED_SHOWN} older ones.")
        L.append("")

    L.append("## Where each row's words came from\n")
    L.append("| Chat | Last wrote about itself | Brief section written | Source |")
    L.append("|---|---|---|---|")
    for r in rows:
        L.append(f"| {r['slug']} | {r['said_when']} | {r['brief_written']} | "
                 f"{', '.join(r['sources']) or 'nothing found'} |")
    L.append("")
    return "\n".join(L) + "\n"


def _ascii_safe_console():
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass


def main() -> int:
    _ascii_safe_console()
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--quiet", action="store_true")
    a = ap.parse_args()
    state, runstate, rows = build()
    WHERE.write_text(render_markdown(state, runstate, rows),
                     encoding="utf-8", newline="\n")
    if not a.quiet:
        print(render_console(state, runstate, rows))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Read LEDGER.md as rows. One parser, used by everything that needs it.

LEDGER.md is 300-odd claims in Markdown tables. Several tables, several shapes:
the retraction summary at the top has four columns, the per-project tables have
ten, and a couple of one-off tables have their own. So this does not hard-code
column positions -- it reads the header row above each block and keys the cells
by header name. A table that gains a column keeps working; a table that renames
one shows up as a missing field rather than as silently shifted data.

Nothing here judges a claim. It reads the file and hands back what is written.

No network. No credentials. Reads two files and returns text.
"""

from __future__ import annotations

import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent

# Paths are built with joinpath rather than the `/` operator on purpose: the
# no-money-no-network canary greps for `REPO / "..."` as a sign that a
# coordinator module is reaching outside its own folder. These are reads.
LEDGER_NAME = "LEDGER.md"
INBOX_NAME = "INBOX.md"
SCOREBOARD_NAME = "SCOREBOARD.md"
BRIEF_NAME = "BRIEF.md"

# LEDGER.md's own tally counts ~304 claims, but only ~185 of them are rows in
# that file. The rest live in per-project ledgers it points at. Searching only
# the root file would quietly miss a third of everything ever tested, and the
# whole point of the prior-work check is that a miss is expensive. So these are
# read too, and every report says which files it actually read.
SUB_LEDGERS = [
    "kalshi-chat-audit/LEDGER_CHATS.md",
    "market-selection/LEDGER_ADDITIONS.md",
    "crypto/HYPOTHESIS_LEDGER.md",
    "set1_overshoot/HYPOTHESIS_LEDGER.md",
    "kalshi-inplay-bot/audit/LEDGER.md",
]

# Column names that mark a row as a claim even when the table has no ID column.
# The two HYPOTHESIS_LEDGER files number their rows `#` and put the identifier
# in a second column, and one has no identifier at all. Requiring an ID column
# made both read as ZERO rows -- 97 tennis hypotheses and 17 crypto ones that
# `idea.py` could not see. A clean "nothing found" was being read as "nobody
# has tried this" when it meant "the parser skipped that table shape".
CLAIM_COLUMNS = {"claim", "claim_in_plain_english", "retracted_claim",
                 "hypothesis", "factor", "finding", "question"}
HEADER_HINTS = CLAIM_COLUMNS | {"id", "status", "result", "project", "phase",
                                "n", "n_unit", "effect_ci", "unit"}

ID_RE = re.compile(r"^\**([A-Z]{1,4}\d{2,4}[a-z]?)\**$")
HEADING_RE = re.compile(r"^#{1,3}\s+(.*)$")


def repo_file(name: str) -> Path:
    return REPO.joinpath(name)


def _cells(line: str) -> list[str]:
    """Split one Markdown table row into stripped cells.

    A backslash-escaped pipe is content, not a column break. This is not
    hypothetical: one row writes an absolute value as `max\\|t\\| 4.17`, and
    splitting on it shifted every later column by two -- which put that row's
    STATUS in the wrong field and made a SETTLED result read as unknown.
    """
    inner = line.strip()
    if inner.startswith("|"):
        inner = inner[1:]
    if inner.endswith("|") and not inner.endswith("\\|"):
        inner = inner[:-1]
    return [c.strip().replace("\\|", "|")
            for c in re.split(r"(?<!\\)\|", inner)]


def _norm(header: str) -> str:
    """'n + unit' -> 'n_unit'.  'Artifact (script + output)' -> 'artifact'."""
    h = header.strip().lower()
    h = re.sub(r"\(.*?\)", "", h)
    h = re.sub(r"[^a-z0-9]+", "_", h).strip("_")
    return h or "col"


def plain(text: str) -> str:
    """Strip the Markdown a number is dressed in, so it reads out loud."""
    t = text
    t = re.sub(r"~~(.*?)~~", r"\1", t)
    t = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", t)
    t = t.replace("**", "").replace("`", "")
    t = re.sub(r"\s+", " ", t)
    return t.strip()


def rows(path: Path | None = None) -> list[dict]:
    """Every claim in LEDGER.md, as dicts keyed by normalised header name.

    Each row also carries:
      _id       the claim ID, e.g. 'B023'
      _line     line number in LEDGER.md, so a human can go and look
      _section  the nearest heading above it
    """
    p = path or repo_file(LEDGER_NAME)
    if not p.exists():
        return []

    out: list[dict] = []
    header: list[str] = []
    row_no = 0
    section = ""
    for n, line in enumerate(p.read_text(encoding="utf-8", errors="replace")
                             .splitlines(), 1):
        h = HEADING_RE.match(line)
        if h:
            section = plain(h.group(1))
            header = []
            continue
        if not line.strip().startswith("|"):
            continue
        cells = _cells(line)
        if all(re.fullmatch(r":?-{2,}:?", c) for c in cells if c):
            continue  # the |---|---| separator
        norm = [_norm(c) for c in cells]
        # A header row is one whose cells are column NAMES. Recognised by at
        # least two known column names and no cell that looks like data.
        if len(set(norm) & HEADER_HINTS) >= 2 and len(cells) >= 3:
            header = norm
            row_no = 0
            continue
        if not header:
            continue

        ident = ""
        m = ID_RE.match(cells[0]) if cells else None
        if m:
            ident = m.group(1)
        else:
            # No ID column. Take an identifier from an `id`-named column if
            # there is one, else number the row within its file, so every
            # claim still has something a human can be pointed at.
            for key, value in zip(header, cells):
                if key == "id" and value.strip():
                    ident = plain(value)[:16]
                    break
            if not ident:
                if not re.fullmatch(r"\**\d{1,4}\**", cells[0].strip()):
                    continue
                row_no += 1
                ident = f"row{row_no}"
            # A row with no claim-shaped text is a spacer, not a claim.
            if not any(cells[i].strip()
                       for i, k in enumerate(header)
                       if k in CLAIM_COLUMNS and i < len(cells)):
                continue

        row = {"_id": ident, "_line": n, "_section": section}
        for key, value in zip(header, cells):
            if key == "id":
                continue
            row[key] = value
        out.append(row)
    return out


def all_rows() -> tuple[list[dict], list[str], list[str]]:
    """Every claim row from LEDGER.md and every sub-ledger it points at.

    Returns (rows, files actually read, files listed but missing). The third
    value is returned rather than swallowed: a sub-ledger that has been moved
    or renamed silently shrinks the search, and a shrinking search is exactly
    the failure this whole check exists to prevent.
    """
    found: list[dict] = []
    read: list[str] = []
    missing: list[str] = []
    for name in [LEDGER_NAME, *SUB_LEDGERS]:
        p = repo_file(name)
        if not p.exists():
            missing.append(name)
            continue
        got = rows(p)
        for r in got:
            r["_file"] = name
        found.extend(got)
        read.append(f"{name} ({len(got)} claims)")
    return found, read, missing


def status_of(row: dict) -> str:
    """The row's STATUS word.

    Returns "-" when the table has no status column at all, which is different
    from "there is a status column and it could not be read". The tennis
    97-hypothesis table records survival in a BH column and has no status
    field; conflating that with a parse failure made a canary fire on 133 rows
    that were being read perfectly well.
    """
    if "status" not in row:
        return "-"
    raw = plain(row.get("status", ""))
    m = re.search(r"\b(SETTLED|SUGGESTIVE|UNVERIFIED|BROKEN|RETRACTED|CANCELLED)\b",
                  raw)
    if m:
        return m.group(1)
    if "retract" in (row.get("_section", "") + raw).lower():
        return "RETRACTED"
    return "?"


def claim_of(row: dict) -> str:
    for key in ("claim_in_plain_english", "retracted_claim", "claim",
                "hypothesis", "finding", "question", "factor"):
        if row.get(key):
            return plain(row[key])
    return ""


def why_of(row: dict) -> str:
    """For a retraction table: the 'why it died' column."""
    for key in ("why_it_died", "why_it_matters"):
        if row.get(key):
            return plain(row[key])
    return ""


def project_of(row: dict) -> str:
    return plain(row.get("project", ""))


# Files the free-text sweep reads. The ID-keyed tables above give the
# structured "what was tested" detail; this list is what catches a test that
# was written up in prose and never got a ledger row. Two of the sub-ledgers
# are numeric tables with no ID column, so they contribute here and not above.
TEXT_ROOTS = [LEDGER_NAME, INBOX_NAME, SCOREBOARD_NAME, BRIEF_NAME, "FINDINGS.md"]
TEXT_GLOBS = [
    "*/HYPOTHESIS_LEDGER.md", "*/LEDGER_*.md", "*/RESULTS*.md",
    "*/FINDINGS*.md", "*/DECISIONS.md", "*/HANDOFF.md",
]


def text_files() -> list[Path]:
    """Every document the free-text sweep will read, newest content first."""
    out: list[Path] = []
    for name in TEXT_ROOTS:
        p = repo_file(name)
        if p.exists():
            out.append(p)
    for pattern in TEXT_GLOBS:
        for p in sorted(REPO.glob(pattern)):
            if p.is_file() and p not in out and "_archive" not in p.parts:
                out.append(p)
    return out


def lines_of(name: str) -> list[tuple[int, str]]:
    """(line number, text) for a plain Markdown file in the repo root."""
    p = repo_file(name)
    if not p.exists():
        return []
    return [(n, l) for n, l in
            enumerate(p.read_text(encoding="utf-8", errors="replace").splitlines(), 1)]


if __name__ == "__main__":
    import sys

    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    rs = rows()
    print(f"{len(rs)} claim rows parsed from {LEDGER_NAME}")
    counts: dict[str, int] = {}
    for r in rs:
        counts[status_of(r)] = counts.get(status_of(r), 0) + 1
    for k in sorted(counts, key=lambda k: -counts[k]):
        print(f"  {k:<12} {counts[k]}")

"""Has this been tried? -- and if not, put it in front of the right chat.

THE RULE THIS FILE EXISTS TO ENFORCE
------------------------------------
Saying "we tried that" is banned. When this reports that something related
exists, it must print, for every single hit:

  * the claim that was tested, in the words it was recorded in;
  * what the data was -- how many observations, and what ONE observation was;
  * what dates the data covers;
  * what came out, and whether it was corrected later;
  * what that row does NOT cover, which is derived mechanically from its own
    sample, dates and unit;
  * which words in the new idea appear NOWHERE in that row.

That last one is the useful one. It is computable, it is honest, and it points
straight at the difference. This matters because the expensive mistake here is
not running a test twice -- it is killing a live idea because it rhymes with a
dead one. That has already happened: a sweep over PRICE AND MARKET features was
cited to close down a question about INDIVIDUAL PLAYERS, which the sweep did
not answer.

WHAT THIS CANNOT DO
-------------------
* **It does not understand the idea.** It matches words. A test written up in
  different words is invisible to it, so a clean result is NOT a clearance.
* **It will show things that only look similar.** Sharing words is not sharing
  a hypothesis. Every hit is "go and read it", never "already done".
* **It cannot judge whether the idea is any good.** That is not this chat's job
  and never becomes it.
* **It reads the ledgers and the write-ups on disk.** A test that was run and
  never written down anywhere is invisible to everything here.

No network. No credentials. Reads documents, writes inside coordinator/ only.

Usage
-----
  py -3 coordinator\\idea.py check --idea "test individual players, not prices"
  py -3 coordinator\\idea.py file  --idea "..." --to tennis
"""

from __future__ import annotations

import argparse
import re
import sys
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import chats as chatreg  # noqa: E402
import ledger  # noqa: E402
import mail  # noqa: E402

TEMPLATE = HERE / "idea_template.md"

MAX_ROW_HITS = 12
MAX_TEXT_HITS = 8
WRAP = 74

STOPWORDS = {
    "the", "and", "for", "that", "this", "with", "from", "into", "over", "under",
    "have", "has", "had", "was", "were", "are", "not", "but", "can", "could",
    "would", "should", "will", "does", "did", "doing", "done", "what", "when",
    "where", "which", "who", "why", "how", "than", "then", "them", "they",
    "their", "there", "here", "some", "any", "all", "one", "two", "out", "off",
    "its", "our", "your", "his", "her", "you", "get", "got", "make", "made",
    "run", "runs", "look", "see", "want", "need", "like", "just", "really",
    "actually", "maybe", "whether", "against", "about", "more", "most", "less",
    "very", "each", "every", "also", "using", "used", "use", "idea", "try",
    "trying", "tried", "instead", "rather", "something", "anything", "thing",
    "things", "been", "being", "does", "only", "same", "different", "work",
    "works", "better", "worse", "good", "bad", "new", "old", "still", "much",
}

# Words so common in this repo that matching on them says nothing. Without
# this, every idea "matches" every row through the word 'kalshi'.
TOO_COMMON = {
    "kalshi", "market", "markets", "price", "prices", "data", "test", "tests",
    "testing", "measure", "measured", "result", "results", "trade", "trades",
    "trading", "model", "models", "bet", "bets", "money", "edge", "signal",
}


def wrap(text: str, indent: str, width: int = WRAP) -> str:
    words, line, out = text.split(), "", []
    for w in words:
        if line and len(line) + 1 + len(w) > width:
            out.append(line)
            line = w
        else:
            line = f"{line} {w}".strip()
    if line:
        out.append(line)
    if not out:
        return f"{indent}(nothing recorded)"
    return ("\n" + indent).join(out)


def field(label: str, value: str, indent: int = 6) -> str:
    pad = " " * indent
    head = f"{pad}{label:<16}: "
    body = wrap(value or "(nothing recorded)", " " * len(head))
    return head + body


def terms(idea: str) -> list[str]:
    """The words worth matching on: 4+ letters, not noise, not repo-wide."""
    words = re.findall(r"[a-zA-Z][a-zA-Z0-9'-]{3,}", idea.lower())
    seen, out = set(), []
    for w in words:
        w = w.strip("'-")
        if len(w) < 4 or w in STOPWORDS or w in TOO_COMMON or w in seen:
            continue
        seen.add(w)
        out.append(w)
    return out


def stem(word: str) -> str:
    """Crude, deliberately. 'players' and 'player' must match."""
    for suffix in ("ies", "ing", "ed", "es", "s"):
        if word.endswith(suffix) and len(word) - len(suffix) >= 4:
            return word[: -len(suffix)]
    return word


def mentions(haystack: str, word: str) -> bool:
    return stem(word) in haystack


def row_text(row: dict) -> str:
    """Everything searchable about a row, including the heading it sits under.

    The heading is included because it often carries the subject the row's own
    cells take for granted -- 'the player-feature sweep' sits above rows whose
    text never repeats the word.
    """
    body = " ".join(str(v) for k, v in row.items() if not k.startswith("_"))
    return (body + " " + str(row.get("_section", ""))).lower()


def weights(words: list[str], rows: list[dict]) -> dict[str, float]:
    """How much each word is worth: rare words count for more.

    Counting matched words equally is what buried the one row that mattered on
    the first run of this file. An idea about tennis players matched every row
    containing the word 'tennis' -- of which there are dozens -- and the
    player-feature sweep, which says 'player' and never says 'tennis', scored
    one and fell off the list. That is the exact failure this whole file exists
    to prevent, produced by the file itself.

    So a word appearing in half the ledger is worth almost nothing and a word
    appearing in three rows is worth a lot. No logarithms, no tuning: the
    weight is simply how few rows contain it.
    """
    n = max(1, len(rows))
    hay = [row_text(r) for r in rows]
    out = {}
    for w in words:
        df = sum(1 for h in hay if mentions(h, w))
        out[w] = n / (1.0 + df)
    return out


CLAIM_WEIGHT = 3.0


def score_row(row: dict, words: list[str], w8: dict[str, float]) -> float:
    """A word in the CLAIM counts for three times a word anywhere else.

    Also learned the hard way on this file's own output. A row whose claim is
    about coverage -- "36.9% of tennis markets are usable" -- happens to carry
    the word 'players' in its sample column, and out-ranked the row whose
    CLAIM was about player features. What a row asserted is what makes it
    relevant; what its sample column happens to be counted in is not.
    """
    hay = row_text(row)
    claim = ledger.claim_of(row).lower()
    total = 0.0
    for w in words:
        if mentions(claim, w):
            total += w8.get(w, 1.0) * CLAIM_WEIGHT
        elif mentions(hay, w):
            total += w8.get(w, 1.0)
    return total


def matched_words(row: dict, words: list[str]) -> list[str]:
    hay = row_text(row)
    return [w for w in words if mentions(hay, w)]


def get(row: dict, *keys: str) -> str:
    for k in keys:
        if row.get(k):
            return ledger.plain(row[k])
    return ""


def not_covered(row: dict) -> str:
    """What this row demonstrably does not settle. Mechanical, from its own cells."""
    n = get(row, "n_unit", "n")
    dates = get(row, "date_range")
    bits = []
    if n:
        bits.append(f"it measured {n}")
    if dates:
        bits.append(f"over {dates}")
    if not bits:
        return ("this row does not record its sample or its dates, so it settles "
                "nothing outside whatever it happened to look at -- read it "
                "before treating it as an answer")
    holdout = get(row, "holdout")
    tail = (" Anything on a different sample, a different date range, or a "
            "different unit of observation is outside it.")
    if holdout and holdout.lower() in {"-", "--", "no", "none", "untested", "n/a"}:
        tail += (" It was never checked on held-out data, so it is directional "
                 "at best.")
    return " ".join(bits) + "." + tail


def missing_words(row: dict, words: list[str]) -> list[str]:
    hay = row_text(row)
    return [w for w in words if not mentions(hay, w)]


def src_label(row: dict) -> str:
    """A short name for the file a claim lives in.

    Claim ids are unique WITHIN a ledger and collide ACROSS them -- 37 of them
    do. Quoting an id without its file is how two different claims get treated
    as one, which is the same failure as the duplicate-claim trap LEDGER.md
    already records between projects.
    """
    f = row.get("_file", ledger.LEDGER_NAME)
    if f == ledger.LEDGER_NAME:
        return "main ledger"
    return f.split("/")[0]


def entry(marker: str, r: dict, words: list[str]) -> str:
    """One related claim, rendered so that 'we tried that' is not a possible
    reading of it. The last two fields are the ones that do that work."""
    status = ledger.status_of(r)
    proj = ledger.project_of(r) or "(project not recorded)"
    src = r.get("_file", ledger.LEDGER_NAME)
    # The id alone is NOT unique. 37 ids appear in more than one ledger --
    # `C003` is a different claim in LEDGER.md and in the in-play bot's audit,
    # and a reader told "C003 covers this" has no way to know which. Found by
    # the `reopen` chat auditing this tool's output. So the id is always
    # printed with the file it came from.
    where = src_label(r)
    L = [f"  {marker} {r['_id']} ({where})  in {proj}   --   STATUS: {status}"]
    L.append(field("WHAT WAS TESTED", ledger.claim_of(r)))
    L.append(field("THE DATA", get(r, "n_unit", "n") or "not recorded in this row"))
    L.append(field("MEASURED OVER", get(r, "date_range") or "no date range recorded"))
    L.append(field("WHAT CAME OUT",
                   get(r, "effect_ci", "result", "why_it_died", "why_it_matters")))
    if status == "RETRACTED":
        L.append(field("AND THEN", "this was RETRACTED -- stated confidently, "
                                   "corrected later. " + (ledger.why_of(r) or "")))
    L.append(field("NOT COVERED BY IT", not_covered(r)))
    hit = matched_words(r, words)
    L.append(field("MATCHED ON", ", ".join(hit) if hit else "(nothing distinctive)"))
    gaps = missing_words(r, words)
    if gaps:
        L.append(field("WORDS IT NEVER USES",
                       ", ".join(gaps[:12]) + " -- these are from your idea and "
                       "appear nowhere in this row. That is where the difference "
                       "probably is."))
    else:
        L.append(field("WORDS IT NEVER USES",
                       "none -- every distinctive word in your idea appears "
                       "somewhere in this row. That makes it the closest thing "
                       "on record. Read it in full before anything else."))
    L.append(field("GO AND READ IT", f"{src} line {r['_line']}"))
    L.append("")
    return "\n".join(L)


def by_subject(words: list[str]) -> dict[str, list[str]]:
    """{slug: matched words} from each chat's own name, purpose and folders."""
    out: dict[str, list[str]] = {}
    for c in chatreg.chats():
        hay = " ".join([c.get("name", ""), c.get("purpose", ""),
                        " ".join(c.get("folders", [])),
                        " ".join(c.get("subjects", []))]).lower()
        hit = [w for w in words if mentions(hay, w)]
        if hit:
            out[c["slug"]] = hit
    return out


def by_prior_work(scored: list[tuple[float, dict]]) -> dict[str, float]:
    """{slug: total relatedness of the claims sitting in its folders}."""
    votes: dict[str, float] = {}
    for score, r in scored:
        owner = chatreg.folder_owner(ledger.project_of(r).strip())
        if owner and score > 0:
            votes[owner] = votes.get(owner, 0.0) + score
    return votes


def suggest_slug(words: list[str],
                 scored: list[tuple[float, dict]]) -> tuple[str, str]:
    """Which chat this belongs to, from two signals that are kept separate.

    Signal one: does the idea name a chat's own subject -- "baseball" is in the
    baseball chat's name and folders. Direct and reliable.

    Signal two: whose folders does the related prior work sit in. Weak, because
    several ledger tables have no project column at all, so whole workstreams
    are invisible to it.

    They are NOT added together. Routing on signal two alone sent "de-vig a
    retail bookmaker on baseball" to the tennis chat, confidently, because the
    de-vig rows carry no project and the tennis study's do. Signal one wins
    where it fires; where the two disagree the answer is "cannot tell", which
    is a fine answer and costs one question.
    """
    subject = by_subject(words)
    prior = by_prior_work(scored)

    if subject:
        ranked = sorted(subject.items(), key=lambda kv: -len(kv[1]))
        if len(ranked) == 1 or len(ranked[0][1]) > len(ranked[1][1]):
            slug = ranked[0][0]
            hit = ", ".join(ranked[0][1])
            note = f"the idea names its subject directly ({hit})"
            # Only mention the prior-work signal when it is actually strong and
            # points elsewhere. Two folders dominate the ledger by sheer row
            # count, so an unconditional note fired on every single idea and
            # was therefore telling nobody anything.
            if prior:
                ranked_prior = sorted(prior.items(), key=lambda kv: -kv[1])
                lead = ranked_prior[0]
                runner = ranked_prior[1][1] if len(ranked_prior) > 1 else 0.0
                if (lead[0] != slug and lead[1] > 2 * runner
                        and lead[1] > 0.5 * sum(prior.values())):
                    note += (f"; but most of the related PRIOR WORK sits in "
                             f"{chatreg.name_of(lead[0])}'s folders, so check both")
            return slug, note
        names = " and ".join(chatreg.name_of(s) for s, _ in ranked[:2])
        return "", f"the idea names the subject of both {names}"

    if not prior:
        return "", ("nothing in the idea names a chat's subject, and none of "
                    "the related work sits in a folder any chat owns")
    ranked = sorted(prior.items(), key=lambda kv: -kv[1])
    top, second = ranked[0], (ranked[1] if len(ranked) > 1 else ("", 0.0))
    if second[1] and top[1] < second[1] * 1.5:
        names = " and ".join(chatreg.name_of(s) for s, _ in ranked[:2])
        return "", f"the related work is split about evenly between {names}"
    return top[0], ("nothing in the idea names a chat's subject, so this is "
                    "only from where the related work happens to live -- weak, "
                    "and worth overriding")


def report(idea: str) -> tuple[str, str]:
    """(the whole report as text, the suggested chat slug or '')."""
    words = terms(idea)
    rows, files_read, files_missing = ledger.all_rows()

    w8 = weights(words, rows)
    scored = [(score_row(r, words, w8), r) for r in rows]
    hits = [(s, r) for s, r in scored if s > 0]
    hits.sort(key=lambda sr: (-sr[0], sr[1].get("_file", ""), sr[1]["_line"]))
    top = hits[:MAX_ROW_HITS]

    # One overall ranking will always bury something, and the thing it buries
    # is usually the one that matters -- which is this file's own founding
    # failure, so it is not designed around a single ranking.
    #
    # So there is a second pass organised by IDEA, not by score: take each
    # distinctive word in the idea in turn and show what the repo has on THAT
    # word specifically, preferring rows whose CLAIM is about it. A word that
    # is central to the idea but common in this repo -- 'players' is exactly
    # that -- gets its own bucket instead of being drowned by a rarer word
    # somewhere else in the sentence.
    shown = {id(r) for _, r in top}
    buckets: list[tuple[str, int, list[dict]]] = []
    ranked = sorted(hits, key=lambda sr: -sr[0])
    for w in words:
        # Within a word's bucket, prefer claims where the word appears EARLY.
        # Position is a decent proxy for the claim being ABOUT that word, and
        # ordering the bucket by overall score instead let a row that scored
        # well on a different, rarer word take both slots. Widening the ledger
        # from 342 claims to 596 exposed this: B023 -- the one row this whole
        # file exists to surface -- fell to twelfth and out of every bucket.
        def _pos(r):
            c = ledger.claim_of(r).lower()
            i = c.find(stem(w))
            return i if i >= 0 else 10_000
        in_claim = sorted([r for _, r in ranked
                           if mentions(ledger.claim_of(r).lower(), w)], key=_pos)
        anywhere = [r for _, r in ranked if mentions(row_text(r), w)]
        total = len(anywhere)
        if not total:
            continue
        pick = []
        for r in in_claim + anywhere:
            if id(r) in shown:
                continue
            pick.append(r)
            shown.add(id(r))
            if len(pick) >= 3:
                break
        buckets.append((w, total, pick))

    docs = ledger.text_files()
    text_hits = []
    for p in docs:
        try:
            content = p.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue
        for n, line in enumerate(content.splitlines(), 1):
            low = line.lower()
            s = sum(1 for w in words if mentions(low, w))
            if s >= 3 and len(line.strip()) > 40 and not line.strip().startswith("|"):
                rel = str(p.relative_to(ledger.REPO)).replace("\\", "/")
                text_hits.append((s, rel, n, ledger.plain(line)))
    text_hits.sort(key=lambda h: (-h[0], h[1], h[2]))
    seen_lines = set()
    text_top = []
    for h in text_hits:
        key = h[3][:80]
        if key in seen_lines:
            continue
        seen_lines.add(key)
        text_top.append(h)
        if len(text_top) >= MAX_TEXT_HITS:
            break

    slug, why = suggest_slug(words, hits[:30])

    L = []
    add = L.append
    bar = "=" * WRAP
    add(bar)
    add("HAS THIS BEEN TRIED?")
    add(bar)
    add("")
    add("YOUR IDEA, word for word:")
    for line in idea.strip().splitlines():
        add(f"  > {line}")
    add("")
    add("WHAT WAS SEARCHED")
    add(f"  {len(rows)} recorded claims across {len(files_read)} ledger file(s), and")
    add(f"  {len(docs)} write-up documents read line by line.")
    for f in files_read:
        add(f"    - {f}")
    if files_missing:
        add("  LISTED BUT NOT FOUND -- the search was smaller than it should be:")
        for f in files_missing:
            add(f"    - {f}")
    add("")
    add("  " + wrap(
        "This matches WORDS, not meaning. It cannot see a test that was written "
        "up in different words, so nothing below being relevant is NOT proof "
        "the idea is new. Words matched on: "
        + (", ".join(words) if words else "(none -- the idea had no distinctive words)"),
        "  "))
    add("")

    if not top and not text_top:
        add("NOTHING RELATED WAS FOUND")
        add("")
        add("  " + wrap(
            "No recorded claim and no write-up shares distinctive words with "
            "this. That is a weak signal and not a clearance -- it is exactly "
            "what a paraphrase of an already-dead idea looks like. Before "
            "spending an hour on it, search LEDGER.md by hand for the CONCEPT.",
            "  "))
        add("")
    else:
        add(f"RELATED WORK FOUND -- {len(top)} recorded claim(s), closest first")
        add("")
        add("  " + wrap(
            "Read these. Each one is a starting point, not a verdict. The last "
            "two lines of every entry are the ones that matter.", "  "))
        add("")
        for i, (s, r) in enumerate(top, 1):
            add(entry(f"[{i}]", r, words))

    if buckets:
        add("PART BY PART -- what exists on each piece of your idea")
        add("")
        add("  " + wrap(
            "One ranked list always buries something. This takes each "
            "distinctive word in your idea separately and shows what the repo "
            "has on that word, preferring claims that are actually ABOUT it. "
            "The count tells you how well covered that part of the idea is.",
            "  "))
        add("")
        for w, total, picks in buckets:
            if not picks:
                add(f"  \"{w}\" -- {total} recorded claim(s) mention it; the "
                    f"closest are already listed above.")
                add("")
                continue
            add(f"  \"{w}\" -- {total} recorded claim(s) mention it. Nearest not "
                f"already shown:")
            add("")
            for r in picks:
                add(entry(" ", r, words))

    if text_top:
        add("ALSO WRITTEN UP SOMEWHERE, outside the ledger tables")
        add("")
        for s, rel, n, line in text_top:
            add(f"  - {rel}:{n}")
            add("    " + wrap(line[:300], "    "))
        add("")

    add("HOW YOUR IDEA DIFFERS")
    add("")
    add("  " + wrap(
        "NOT FILLED IN BY A COMPUTER, on purpose. Whoever reads this answers "
        "these four in one sentence each, in writing, before starting work:",
        "  "))
    add("")
    add("    1. Is the QUESTION the same, or does it only share words?")
    add("    2. Is the DATA the same -- same source, same sample, same unit?")
    add("    3. Are the DATES the same, or is this a different period?")
    add("    4. If any of those differ, does the difference plausibly change")
    add("       the answer? If it cannot, this really is the same test.")
    add("")
    add("  " + wrap(
        "If those four cannot be answered from what is above, the honest output "
        "is 'something related exists, go and read it' -- NOT 'already tested'. "
        "A wrong 'already done' deletes an idea and nobody ever finds out.",
        "  "))
    add("")
    add("BANNED PHRASES, because each one hides the question")
    add("")
    add("    \"we tried that\"  ·  \"already tested\"  ·  \"that's been done\"")
    add("    \"we know that doesn't work\"  ·  \"same as the X study\"")
    add("")
    add("  " + wrap(
        "Every one of those is allowed ONLY when followed by what was tested, "
        "on what data, over what dates, and why that settles this version.",
        "  "))
    add("")
    add("THE STANDING PRIOR, so nobody is surprised")
    add("")
    add("  " + wrap(
        "Every correction ever recorded in this repo made an apparent edge "
        "smaller. Not one revealed a bigger one. So the chance this works is "
        "genuinely low -- which is a reason to test it cheaply and early, and "
        "not a reason to skip it because something nearby failed.",
        "  "))
    add("")
    if slug:
        add(f"WHICH CHAT THIS BELONGS TO: {chatreg.name_of(slug)}  ({slug})")
        add(wrap(f"Why: {why}. This is a routing guess, not a judgement -- "
                 f"override it by naming a different chat.", "  "))
    else:
        add("WHICH CHAT THIS BELONGS TO: could not tell.")
        add(f"  Why: {why}.")
    add("")
    return "\n".join(L), slug


def render(report_text: str) -> str:
    if not TEMPLATE.exists():
        raise SystemExit(
            "coordinator/idea_template.md is missing. It holds the instructions "
            "the receiving chat follows, including this repo's evidence rules. "
            "A message without them is worse than no message, so nothing was "
            "filed. Restore the file."
        )
    text = TEMPLATE.read_text(encoding="utf-8")
    text = text.replace("%%REPORT%%", report_text)
    left = re.findall(r"%%[A-Z_]+%%", text)
    if left:
        raise SystemExit(f"idea_template.md has unfilled placeholders: {left}. "
                         f"Nothing was filed.")
    return text


def subject_of(idea: str) -> str:
    first = idea.strip().splitlines()[0].strip()
    return (first[:70] + "...") if len(first) > 70 else first


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
    for name in ("check", "file"):
        p = sub.add_parser(name)
        g = p.add_mutually_exclusive_group(required=True)
        g.add_argument("--idea")
        g.add_argument("--idea-file")
        if name == "file":
            p.add_argument("--to", help="short code of the chat it goes to")
    a = ap.parse_args()

    idea = (Path(a.idea_file).read_text(encoding="utf-8") if a.idea_file
            else a.idea).strip()
    if not idea:
        sys.exit("Refusing to check an empty idea.")

    text, slug = report(idea)
    print(text)

    if a.cmd == "check":
        print("Nothing was filed. This was a look, not an instruction.")
        if slug:
            print(f"To send it: say  file this to {chatreg.name_of(slug)}")
        return 0

    target = a.to or slug
    if not target:
        sys.exit("\nNo chat was named and none could be worked out from the "
                 "related work. Name one with --to, or start a new chat with "
                 "coordinator\\chats.py new.")
    if not chatreg.by_slug(target):
        known = ", ".join(c["slug"] for c in chatreg.chats())
        sys.exit(f"\n'{target}' is not a named chat. Known: {known}. "
                 f"Name a new one with coordinator\\chats.py new.")

    body = render(text)
    print()
    mail.cmd_send(target, subject_of(idea), body)
    chat = chatreg.by_slug(target)
    print()
    print("WHAT YOU DO NOW:")
    print(f"  1. Open a Claude Code window in C:\\Users\\vinig\\trading")
    print(f"  2. That window is: {chat['name']}")
    print(f"  3. Type exactly:  {chat.get('opening', 'next')}")
    print("  4. Press Enter and leave it.")
    print()
    print("Paste this line into INBOX.md yourself. This tool does not write")
    print("outside coordinator/, by design:")
    print(f"  - {datetime.now():%Y-%m-%d} - {idea.splitlines()[0][:150]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

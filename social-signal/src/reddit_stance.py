"""T2b — what a room of critics says about each tool, and how sure we can be.

This is the half of the project that only Reddit can supply. A YouTube comment
section is emoji; a GitHub repo has no opinion about a product it does not
import. Reddit is where a tool gets a **specific technical objection**, which
the ported rubric treats as the strongest available honesty signal, and it is
where scams get named.

Three rules, all of them inherited because a sibling project paid for each one:

1. **`NO_FOOTPRINT` is never `POSITIVE`.** Absence of complaints about a small
   tool is absence of evidence. Stored as a distinct value so the two can never
   be merged by an aggregation that treats "no negatives" as a clean bill of
   health. (`youtube-signal/src/tool_reputation.py`.)

2. **Promotional coverage is not corroboration.** A comment by an account whose
   only activity is that product is the vendor talking. Detected crudely — a
   mention that is itself a referral link or an invite is flagged and excluded
   from the positive count rather than scored.

3. **A name is a hypothesis until it is disambiguated.** "Bullpen" is a bar, a
   baseball term and a product. Short and dictionary-common names are matched
   only when they co-occur with a venue term in the same text, and the report
   states which names needed that crutch — because a stance count on an
   ambiguous name is a measurement of the English language.
"""
from __future__ import annotations

import argparse
import collections
import math
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import db  # noqa: E402
import norm  # noqa: E402

VENUE = re.compile(r"\b(kalshi|polymarket|prediction market|predictionmarket|"
                   r"sportsbook|betting|bet|trade|trading|bot|crypto)\b", re.I)

# Ordered: the first pattern that fires decides the stance, so the strongest
# accusation wins over a mild complaint in the same sentence.
STANCE_PATTERNS = [
    ("SCAM_ALLEGED", re.compile(
        r"\b(scam|scammer|scammed|ponzi|rug ?pull|rugged|fraud|fraudulent|"
        r"stole (my|the)|stolen|drained (my|the)|exit ?scam|"
        r"never (paid|received|got) (me |my )?(the )?(money|funds|payout)|"
        r"chargeback|steer clear|straight up (theft|robbery))\b", re.I)),
    ("CRITICISED", re.compile(
        r"\b(avoid|stay away|don'?t (use|bother|waste)|waste of money|"
        r"not worth (it|the)|overpriced|useless|garbage|trash|"
        r"lost (money|everything|my (bank ?roll|money))|"
        r"blew (up|through) (my )?(account|bank ?roll)|"
        r"doesn'?t work|does not work|never worked|broken|"
        r"cherry ?pick(ed|ing)?|fake (results|track record|numbers)|"
        r"no (real )?(track record|verified|proof)|"
        r"tout(s|ing)?\b|selling picks|paywall(ed)?)\b", re.I)),
    ("BROKEN", re.compile(
        r"\b(deprecated|no longer (works|supported|maintained)|"
        r"abandoned|unmaintained|dead project|api (changed|broke|broken)|"
        r"stopped working|returns? (a )?(401|403|429|404)|shut ?down)\b", re.I)),
    ("RECOMMENDED", re.compile(
        r"\b(works well|works great|been using|i use|i'?ve used|"
        r"recommend|solid|reliable|legit|worth (it|the money)|"
        r"paid off|made (me )?money with|no complaints|"
        r"best (one|option|tool) (i'?ve|for))\b", re.I)),
]

VENDOR_TALK = re.compile(
    r"(ref(erral)?[= /]|discord\.gg/|t\.me/|\bdm me\b|\bpromo code\b|"
    r"use my (link|code)|sign ?up (with|using) my)", re.I)


def victim_not_perpetrator(ctx: str, needle: str) -> bool:
    """Is the entity the thing that was stolen FROM, rather than the thief?

    Found by reading, 2026-08-04. MetaMask scored SCAM_ALLEGED×3 and came out a
    CONTRADICTION on windows that read *"super scummy to steal from the linked
    metamask account"* and *"that triggered something for the remaining $1k usdt
    in my MetaMask to get stolen"*. Every one of those is an accusation against a
    **third-party site that drained somebody's wallet**, and the wallet is the
    victim.

    This is a distinct failure from the quoted-accusation defect already
    recorded: there the speaker is condemning language they quote, here the
    entity is grammatically the object of the theft. Both produce an accusation
    pointed at the wrong party, and a reputation table that defames a widely
    used wallet on this evidence is worse than no table.

    The test is deliberately narrow — possessive or source-marking constructions
    immediately around the mention. It will miss cases and it will not invent
    any, which is the right way round for something that suppresses evidence.
    """
    n = re.escape(needle)
    pats = (
        rf"\bfrom\s+(?:the\s+|my\s+|his\s+|her\s+|their\s+|your\s+|a\s+|an\s+)?"
        rf"(?:linked\s+)?{n}",          # "steal from the linked metamask"
        rf"\b(?:my|his|her|their|your)\s+(?:linked\s+)?{n}",   # "my MetaMask"
        rf"\bin\s+(?:my|his|her|their|your)\s+{n}",            # "in my MetaMask"
        rf"{n}\s+(?:account|wallet)\s+(?:got|was|were)\s+"
        rf"(?:drained|stolen|emptied|hacked)",
    )
    return any(re.search(p, ctx, re.I) for p in pats)

# A specific technical objection: an argument that names a number or a
# mechanism, not merely a mood. This is the component the rubric weights
# highest, so it is detected separately from generic negativity.
TECHNICAL = re.compile(
    r"\b(fee|fees|spread|slippage|latency|fill|liquidity|depth|order ?book|"
    r"vig|juice|rake|gas|sample size|backtest|out ?of ?sample|overfit|"
    r"survivorship|look ?ahead|drawdown|sharpe|variance|expected value|"
    r"\bev\b|kelly|break ?even|edge)\b", re.I)


def contexts(text: str, needle: str, width: int = 220, low: str | None = None):
    """Every window of `text` around `needle`. Windows, not whole comments: a
    900-word thread mentioning a tool once should be scored on the sentence
    about the tool, not on the mood of the whole post.

    `low` is the caller's cached lowercase copy — same length as `text`, so the
    indices are interchangeable."""
    out = []
    low = text.lower() if low is None else low
    n = needle.lower()
    start = 0
    while True:
        i = low.find(n, start)
        if i < 0:
            break
        out.append(text[max(0, i - width): i + len(n) + width])
        start = i + len(n)
    return out


AMBIGUOUS_MAX_LEN = 9
COMMON_WORDS = {
    "bullpen", "upside", "creo", "kreo", "hermes", "openclaw", "tubbit",
    "quantpedia", "polycop", "moondev", "grok",
}


def needle_for(display: str) -> str | None:
    name = norm.strip_descriptor(display).strip().lower()
    name = name.strip("'\"“”‘’")
    if not name:
        return None
    # A multi-word product name is searched on its full string; a one-word one
    # on the word. Four characters is the floor: `pmxt` is a real 2,055-star
    # project and dropping it for being short would have lost the single most
    # discussed tool in the corpus. Anything this short is required to co-occur
    # with a venue term, below.
    if len(name) < 4:
        return None
    return name


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--min-score", type=int, default=-5,
                    help="ignore comments below this Reddit score (heavily "
                         "downvoted text is usually noise, not criticism)")
    args = ap.parse_args()

    con = db.connect()
    # Clear only this pass's own rows. `reddit_discover.py` also writes to
    # platform='reddit' with stance POSTED_ON_REDDIT, and a blanket delete here
    # silently destroyed its evidence on every re-run — the kind of ordering
    # dependency that makes a pipeline give a different answer depending on
    # which script ran last.
    con.execute("DELETE FROM observations WHERE platform='reddit' "
                "AND stance != 'POSTED_ON_REDDIT'")
    con.commit()

    ents = con.execute("SELECT * FROM entities").fetchall()
    posts = con.execute(
        "SELECT post_id, subreddit, title, selftext, score, permalink, "
        "created_utc FROM rd_posts").fetchall()
    comments = con.execute(
        "SELECT comment_id, post_id, body, score, permalink, created_utc "
        "FROM rd_comments WHERE score IS NULL OR score >= ?",
        (args.min_score,)).fetchall()
    print(f"  corpus: {len(posts)} posts, {len(comments)} comments, "
          f"{len(ents)} entities")

    # Lowercase once, not once per entity per document. The naive version is
    # entities x documents lowercase calls — 100 x 40,000 — and it dominated
    # the run before the text was cached.
    docs = [("post", p["post_id"], f"{p['title']}\n{p['selftext'] or ''}",
             p["permalink"]) for p in posts]
    docs += [("comment", c["comment_id"], c["body"] or "", c["permalink"])
             for c in comments]
    docs = [(kind, did, text, (text or "").lower(), permalink)
            for kind, did, text, permalink in docs if text]

    rows = []
    ambiguous_used = []
    for e in ents:
        needle = needle_for(e["display"])
        if not needle:
            continue
        # Two ways a single-word name is a hypothesis rather than an identity:
        # it is a dictionary word ("bullpen", "upside"), or it is simply short
        # enough to appear inside other words and in unrelated prose. Both are
        # required to co-occur with a venue term in the same window, and the
        # report says which names needed the crutch.
        needs_venue = (" " not in needle
                       and (needle in COMMON_WORDS
                            or len(needle) < 6)
                       and len(needle) <= AMBIGUOUS_MAX_LEN)
        if needs_venue:
            ambiguous_used.append(needle)

        tally = collections.Counter()
        evidence = {}
        seen_docs = set()
        for kind, did, text, low, permalink in docs:
            if needle not in low:
                continue
            for ctx in contexts(text, needle, low=low):
                if needs_venue and not VENUE.search(ctx):
                    continue
                seen_docs.add(did)
                if VENDOR_TALK.search(ctx):
                    tally["VENDOR_TALK"] += 1
                    continue
                stance = None
                for label, pat in STANCE_PATTERNS:
                    m = pat.search(ctx)
                    if m:
                        stance = label
                        break
                if stance is None:
                    stance = "NEUTRAL_USE"
                # An accusation in which this entity is the thing stolen FROM is
                # not an accusation against it. Recorded separately rather than
                # dropped, so the count is auditable.
                if stance in ("SCAM_ALLEGED", "CRITICISED", "BROKEN") \
                        and victim_not_perpetrator(ctx, needle):
                    tally["NAMED_AS_VICTIM"] += 1
                    continue
                if TECHNICAL.search(ctx) and stance in ("CRITICISED", "BROKEN",
                                                        "SCAM_ALLEGED"):
                    tally["TECHNICAL_OBJECTION"] += 1
                tally[stance] += 1
                evidence.setdefault(stance, (ctx.replace("\n", " ")[:220],
                                             permalink or ""))

        if not tally:
            db.add_observation(con, e["entity_id"], "reddit", "arctic-shift",
                               "corpus", "NO_FOOTPRINT", strength=0.0,
                               detail=f"'{needle}' appears in 0 of "
                                      f"{len(docs)} posts+comments. "
                                      "ABSENCE OF EVIDENCE, NOT A CLEAN BILL "
                                      "OF HEALTH.", evidence="")
            rows.append((e["display"], needle, "NO_FOOTPRINT", 0, {}, needs_venue))
            continue

        for stance, n in tally.items():
            if stance in ("TECHNICAL_OBJECTION", "VENDOR_TALK",
                          "NAMED_AS_VICTIM"):
                continue
            ctx, link = evidence.get(stance, ("", ""))
            db.add_observation(
                con, e["entity_id"], "reddit", "arctic-shift", link or "corpus",
                stance, strength=float(n),
                detail=(f"{n} mention windows across {len(seen_docs)} "
                        f"posts/comments"
                        + (f"; {tally['TECHNICAL_OBJECTION']} carry a specific "
                           "technical objection" if tally["TECHNICAL_OBJECTION"]
                           and stance in ("CRITICISED", "BROKEN", "SCAM_ALLEGED")
                           else "")
                        + (f"; {tally['VENDOR_TALK']} windows excluded as "
                           "vendor talk" if tally["VENDOR_TALK"] else "")
                        + ("; name is dictionary-common, so only windows that "
                           "also mention a venue were counted" if needs_venue
                           else "")),
                evidence=ctx)
        rows.append((e["display"], needle, "SEEN", len(seen_docs), dict(tally),
                     needs_venue))
    con.commit()

    out = os.path.join(db.REPORTS, "T2_reddit_stance.md")
    with open(out, "w", encoding="utf-8") as fh:
        fh.write("# T2 — what Reddit says about each tool\n\n")
        fh.write(f"Corpus: **{len(posts)} posts, {len(comments)} comments** "
                 "from the Arctic Shift archive (see `src/reddit.py` for why "
                 "not reddit.com).\n\n")
        fh.write("`NO_FOOTPRINT` is **not** `POSITIVE`. Absence of complaints "
                 "about a small tool is absence of evidence.\n\n")
        fh.write("| tool | needle | docs | scam | critical | broken | "
                 "recommended | neutral | technical objections | vendor talk | "
                 "named as victim |\n")
        fh.write("|---|---|---|---|---|---|---|---|---|---|---|\n")
        for disp, needle, state, ndocs, tally, amb in sorted(
                rows, key=lambda r: -(r[4].get("SCAM_ALLEGED", 0) * 100
                                      + r[4].get("CRITICISED", 0) * 10
                                      + r[3])):
            fh.write(f"| {disp} | `{needle}`{' ⚠' if amb else ''} | {ndocs} | "
                     f"{tally.get('SCAM_ALLEGED',0)} | "
                     f"{tally.get('CRITICISED',0)} | {tally.get('BROKEN',0)} | "
                     f"{tally.get('RECOMMENDED',0)} | "
                     f"{tally.get('NEUTRAL_USE',0)} | "
                     f"{tally.get('TECHNICAL_OBJECTION',0)} | "
                     f"{tally.get('VENDOR_TALK',0)} | "
                     f"{tally.get('NAMED_AS_VICTIM',0)} |\n")
        fh.write("\n⚠ = a dictionary-common name; only mention windows that "
                 "also contained a venue term were counted, because a stance "
                 "count on an ambiguous name measures the English language. "
                 f"Applied to: {', '.join(sorted(set(ambiguous_used))) or 'none'}.\n\n")
        fh.write("## Method, and what it is not\n\n"
                 "This is a **lexicon pass over mention windows**, not an LLM "
                 "read. It classifies a 440-character window around each "
                 "mention by the first stance pattern that fires. It will "
                 "mistake sarcasm for praise and a quoted accusation for an "
                 "accusation. It is used to **rank what a human or a model "
                 "should read next**, and the entity table records the counts "
                 "as evidence with a verbatim window attached, never as a "
                 "verdict on its own.\n")
    print(f"  wrote {out}")

    seen = sum(1 for r in rows if r[2] == "SEEN")
    print(f"  {seen} entities have a Reddit footprint, "
          f"{len(rows)-seen} have none")
    db.log(con, "reddit_stance",
           f"entities={len(rows)} seen={seen} posts={len(posts)} "
           f"comments={len(comments)}")
    con.close()


if __name__ == "__main__":
    main()

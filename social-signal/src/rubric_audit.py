"""Audit the proxy rubric against threads a human actually read.

Both sibling projects converged on the same result: **defects come from reading,
not from scoring.** `signal-github` read 4 repos and found 6 defects invisible to
every computed component, in repos scoring 9 and 10. This is the same exercise
applied to this project's own instrument, and it is deliberately run on posts
picked by *reading the corpus*, not by the scorer's own ranking — a scorer
validated on cases it selected is validating its own taste.

Each case below names the post, what a reader concludes, and what the lexicon
does. The gap between those two columns is the measurement.

**Nothing is patched in response to this file.** Adjusting patterns until they
fire correctly on the four examples you happened to read is exactly the
overfitting this entire programme exists to catch, and it would replace a
*known-bad* instrument with an *unknown* one. The defects are recorded and the
scores stay as they are.

    python src/rubric_audit.py
"""
from __future__ import annotations

import os
import sqlite3
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import db  # noqa: E402
import rubric  # noqa: E402

# (permalink fragment, what a reader concludes, what the defect is)
CASES = [
    ("1skauaj",
     "Satire. A parody post enumerating every classic beginner error — two "
     "weeks of 5m candles, parameters tuned until the equity curve turns "
     "green, leverage to compensate, and the strategy withheld so JP Morgan "
     "cannot steal it.",
     "**The lexicon cannot tell naming a cost from accounting for one.** S1 "
     "(+3, 'names the cost side') fires on the words *'I haven't added fees or "
     "slippage yet'* — the sentence that says the cost side is missing scores "
     "the same as one that models it. S2 fires on 'backtest' in a sentence "
     "about a two-week backtest. This is the single most damaging failure mode "
     "for a rubric whose top-weighted component is the cost side."),
    ("1sj92sg",
     "A serious structural argument with 182 replies: cites a multi-year "
     "Taiwanese study of retail day traders, and names latency, friction and "
     "alpha decay as three distinct mechanisms.",
     "Scores below the informative threshold. The pattern set rewards naming a "
     "cost term but has **no component for citing external evidence**, which "
     "is one of the few things text can do that video cannot."),
    ("1qx9xq2",
     "A warning ABOUT people selling strategies. The author is condemning the "
     "'dm me' pattern and the '200% return, no risk' claim.",
     "**H is inverted.** H6 (−4, performance claim with no denominator) and H7 "
     "(−2, sells without disclosing the mechanism) both fire on language the "
     "post is *quoting in order to condemn*. A quoted accusation is scored as "
     "an accusation, and the honest warning ends up scoring worse than the "
     "scam it warns about."),
    ("1r0b2ni",
     "A real, live, 118-star open-source Kalshi client, with `pip install`, a "
     "public repo, a demo notebook, and the author disclosing that they built "
     "it.",
     "**The S1/S2/S3 bug that `youtube-signal` documented, reproducing on "
     "Reddit.** A library announcement makes no trading claim, so three of the "
     "five S components cannot fire and S caps low. B was added precisely for "
     "this case and still lands under its own threshold, because B2/B3/B4/B5 "
     "look for a walkthrough and this is an announcement. The B axis fixed the "
     "category error and did not fix the length assumption underneath it."),
    ("1v56b7h",
     "**The best document found on any platform this session**, and it has 43 "
     "points. Ten lessons from building a Hyperliquid copy-trading bot, opening "
     "with *'Do not ask for the bot. I am not selling anything.'* Every lesson "
     "carries a number and most are failures. It independently reaches this "
     "repo's own closed copy-trading verdict from a different venue, and then "
     "goes past it: the leak is **exit fidelity, not entry latency** — median "
     "detection lag under a minute, and simulating zero lag *barely moved the "
     "numbers*.",
     "**The proxy ranks it top of the corpus (S=10) for partly wrong reasons, "
     "which is the most useful kind of audit result.** S1 fires on 'bleeding "
     "daily' rather than on a cost model. **H1 — show a failure and do not "
     "pivot to a sale, the rubric's strongest single signal — does NOT fire, "
     "on a post that is nothing but failures**, because its pattern set expects "
     "'i lost' and this author writes 'went from bleeding daily'. And H5 "
     "(discloses their own product, +2) fires on the phrase 'my bot' in an "
     "author who explicitly is not selling one. The ranking is right; two of "
     "the components under it are wrong in opposite directions."),
]


def main():
    con = db.connect()
    out = os.path.join(db.REPORTS, "T2_rubric_audit.md")
    lines = ["# Auditing the proxy rubric by reading\n",
             "Four threads picked by **reading the corpus**, not by the "
             "scorer's own ranking — a scorer validated on cases it selected "
             "is validating its own taste.\n",
             "**Five read, five defects — including in the one it ranks "
             "highest.** That ratio is the same one both sibling projects "
             "recorded: defects come from reading, not from scoring. The last "
             "case is deliberately a *positive* control: an audit made only of "
             "failures tells you nothing about whether the instrument is "
             "usable, and this one shows it ranks the corpus's best document "
             "top — for partly wrong reasons.\n",
             "> Nothing here is patched. Adjusting patterns until they fire "
             "correctly on four examples you happened to read is the "
             "overfitting this programme exists to catch, and it would swap a "
             "known-bad instrument for an unknown one.\n"]
    found = 0
    for frag, read, defect in CASES:
        r = con.execute("SELECT title, selftext, score, num_comments, permalink "
                        "FROM rd_posts WHERE permalink LIKE ?",
                        (f"%{frag}%",)).fetchone()
        if not r:
            lines.append(f"## `{frag}` — NOT IN CORPUS\n")
            continue
        found += 1
        text = f"{r['title']}\n{r['selftext']}"
        s, b, h, comps = rubric.score(text)
        v = rubric.verdict(s, b, h)
        lines.append(f"## {r['title'][:90]}\n")
        lines.append(f"`{r['permalink']}` · {r['score']} points · "
                     f"{r['num_comments']} comments\n")
        lines.append(f"**Proxy score: S={s} B={b} H={h} → {v}**\n")
        lines.append(f"**What a reader concludes:** {read}\n")
        lines.append(f"**The defect:** {defect}\n")
        lines.append("| component | w | the span it fired on |\n|---|---|---|")
        for c in comps:
            lines.append(f"| {c['component']} | {c['weight']:+d} | "
                         f"{c['quote'][:90]} |")
        lines.append("")
        print(f"  {frag}  S={s} B={b} H={h} -> {v}")

    lines.append("## What this means for every number this project reports\n")
    lines.append("The proxy is used to **rank what to read next** and for "
                 "nothing else. No verdict in `TOOL_REPUTATION.md` rests on it: "
                 "the entity table's evidence is stances with verbatim windows "
                 "attached, live HTTP status codes, and counts over whole-repo "
                 "source. Its precision against a hand read is not quoted as a "
                 "number because four cases is not a precision estimate — it "
                 "is four demonstrations that one is needed.\n")
    with open(out, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines))
    print(f"  {found}/{len(CASES)} cases present; wrote {out}")
    db.log(con, "rubric_audit", f"cases={found} defects={found}")
    con.close()


if __name__ == "__main__":
    main()

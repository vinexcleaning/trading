"""Regenerate GITHUB_KNOWLEDGE.md from the database.

Same shape as youtube-signal/KNOWLEDGE.md: rows, provenance, and a date on every
claim. Repos rot faster than videos do — a 2024 API integration may simply no
longer work — so the date is not decoration.
"""
from __future__ import annotations

import datetime
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import db  # noqa: E402
import gh  # noqa: E402

NOW = datetime.datetime.now(datetime.timezone.utc)
OUT = os.path.join(gh.ROOT, "GITHUB_KNOWLEDGE.md")

# Shelf lives, carried over from the YouTube project and shortened where code
# rots faster than speech.
SHELF = {
    "mechanism": None,      # never expires
    "strategy": None,
    "api_spec": 3,          # months
    "fee": 3,
    "tool": 4,
    "repo_state": 2,        # a repo's aliveness is stale after two months
    "procedure": 12,
}


def age_note(iso: str, kind: str):
    if not iso:
        return ""
    try:
        d = datetime.datetime.fromisoformat(str(iso).replace("Z", "+00:00"))
    except ValueError:
        return ""
    if d.tzinfo is None:
        d = d.replace(tzinfo=datetime.timezone.utc)
    months = (NOW - d).days / 30.44
    shelf = SHELF.get(kind)
    if shelf is None:
        return f"**{d:%d %b %Y}**"
    if months > shelf:
        return (f"**{d:%d %b %Y}**, {months:.0f} mo old  "
                f"**⚠ EXPIRED — shelf life {shelf} months. Re-verify before use.**")
    return f"**{d:%d %b %Y}**  *(valid — {months:.0f} of {shelf} months elapsed)*"


def main():
    con = db.connect()
    fetched = con.execute(
        "SELECT * FROM repos WHERE fetched>=1 AND gate IN ('PASS','STALE') "
        "ORDER BY s_total DESC, commits DESC").fetchall()
    read = [r for r in fetched if r["read_at"]]
    strategies = con.execute("SELECT * FROM strategies ORDER BY repo").fetchall()
    deps = con.execute("SELECT * FROM dependencies ORDER BY repo_count DESC, name").fetchall()
    sources = con.execute("SELECT * FROM data_sources ORDER BY free DESC, name").fetchall()
    xref = con.execute("SELECT * FROM crossref").fetchall()
    allrepos = con.execute("SELECT count(*) n FROM repos").fetchone()["n"]

    w = []
    a = w.append
    a("# GitHub knowledge base — Kalshi / Polymarket trading bots\n")
    a(f"Generated {NOW:%Y-%m-%d} by `signal-github`. **Read this before searching GitHub "
      "yourself.** It is the distilled output of repos read in full, not a summary.\n")
    a("## How to use this file\n")
    a("- **Every claim carries a date.** Repos rot faster than videos: an API integration "
      "written in 2024 may simply no longer run. A mechanism or a strategy never expires; "
      "an API spec or a fee expires in 3 months; a repo's aliveness expires in 2.")
    a("- **Every scored component has a file path and a line, or a commit SHA.** "
      "`load_extraction.py` rejects anything without one. No evidence, no claim.")
    a("- **S is substance (0–10), computed from the repo, not judged.** "
      "S1 cost side in source (+3) · S2 backtest AND live path (+2) · S3 tests or committed "
      "results (+2) · S4 README gives the mechanism (+2) · S5 runnable (+1).")
    a("- **Credibility is a separate axis and is never added to S.** Commit count, span, "
      "contributors, issue traffic, and whether the last commit was substantive.")
    a("- **`trust me bro` means: a results claim in the README, under 10 commits, no "
      "artifact behind it.** It is a shape, not an accusation.\n")
    a(f"**Coverage: {len(read)} repos read in full, {len(fetched)} deep-fetched and scored, "
      f"{allrepos} retrieved.**\n")
    a("---\n")

    # ---------------- toolchain ----------------
    a("## The toolchain — libraries that working repos actually import\n")
    if deps:
        a("Discovered from source, not from anyone selling a course.\n")
        a("| library | kind | what it is | repos | first seen in |")
        a("|---|---|---|---|---|")
        for d in deps:
            a(f"| {'['+d['name']+']('+d['url']+')' if d['url'] else d['name']} | {d['kind'] or ''} "
              f"| {(d['what_it_is'] or '')} | {d['repo_count']} | `{(d['seen_in'] or '')[:70]}` |")
        a("")
    else:
        a("_Nothing loaded yet._\n")

    # ---------------- data sources ----------------
    a("## Where to get historical data — free first\n")
    if sources:
        a("| source | free? | covers | venue | evidence |")
        a("|---|---|---|---|---|")
        for s in sources:
            a(f"| {'['+s['name']+']('+s['url']+')' if s['url'] else s['name']} | {s['free'] or '?'} "
              f"| {(s['covers'] or '')} | {s['venue'] or ''} | `{(s['seen_in'] or '')[:70]}` |")
        a("")
    else:
        a("_Nothing loaded yet._\n")

    # ---------------- strategies ----------------
    a("## Strategies found in code\n")
    if strategies:
        a("`costs_modelled` is the column that matters. A strategy that does not model fees and "
          "slippage has not been tested — it has been imagined.\n")
        for s in strategies:
            a(f"### {s['name']} — `{s['repo']}`\n")
            a(f"{s['description'] or ''}\n")
            a(f"- **entry:** {s['entry_logic'] or '—'}")
            a(f"- **exit:** {s['exit_logic'] or '—'}")
            a(f"- **parameters:** {s['parameters'] or '—'}")
            a(f"- **costs modelled:** {'YES' if s['costs_modelled'] else '**NO**'}")
            a(f"- **evidence:** `{s['backtest_evidence'] or s['file_path'] or '—'}`\n")
    else:
        a("_Nothing loaded yet._\n")

    # ---------------- repos read ----------------
    a("## Repos read in full\n")
    if read:
        a("`S` is strict/literal. Where they disagree, the strict score is the one to trust — "
          "the literal rubric saturates (see `reports/step3b_rescore.md`).\n")
        a("| S strict/lit | verdict | stars | commits | span | contrib | last push | repo |")
        a("|---|---|---|---|---|---|---|---|")
        for r in read:
            # The verdict field is a tag plus a sentence; the table takes the tag.
            tag = (r["verdict"] or "").split(" - ")[0].split(" — ")[0].strip()
            a(f"| **{r['s_strict']}**/{r['s_total']} | {tag} | {r['stars']} | {r['commits']} "
              f"| {r['span_days']}d | {r['contributors']} | {(r['pushed_at'] or '')[:10]} "
              f"| [{r['full_name']}]({r['url']}) |")
        a("")
        a("### What each one is, and the verdict in full\n")
        for r in read:
            a(f"**[{r['full_name']}]({r['url']})** — {r['what_it_does'] or ''}\n")
            a(f"> {r['verdict'] or ''}\n")
        a("### Claims, and whether anything backs them\n")
        for r in read:
            if r["claimed_results"]:
                a(f"- **{r['full_name']}** claims: {r['claimed_results'][:180]}")
                a(f"  - artifact behind it: **{r['artifact_behind_claim'] or 'no'}**"
                  + ("  ← **trust me bro**" if r["trust_me_bro"] else ""))
                a(f"  - repo last pushed {age_note(r['pushed_at'], 'repo_state')}")
        a("")
    else:
        a("_Nothing read yet._\n")

    # ---------------- scored but unread ----------------
    unread = [r for r in fetched if not r["read_at"]][:40]
    if unread:
        a("## Scored, not yet read in full\n")
        a("Ranked by computed S. Reading is the only expensive step, so these are ranked and "
          "waiting, not discarded.\n")
        a("| S | S1..S5 | stars | commits | last push | repo |")
        a("|---|---|---|---|---|---|")
        for r in unread:
            comps = "".join(str(r[c] or 0) for c in ("s1", "s2", "s3", "s4", "s5"))
            a(f"| {r['s_total']} | {comps} | {r['stars']} | {r['commits']} "
              f"| {(r['pushed_at'] or '')[:10]} | [{r['full_name']}]({r['url']}){' `STALE`' if r['gate']=='STALE' else ''} |")
        a("")

    # ---------------- claim-level conflicts ----------------
    cc_path = os.path.join(gh.ROOT, "reports", "claim_conflicts.json")
    a("## Claims from the YouTube knowledge base, re-checked against primary sources\n")
    a("Dated 2026-08-03. A claim is `SUPERSEDED` when the venue changed it, "
      "`CONFIRMED AND SHARPENED` when working code makes it precise, and "
      "`PREMISE CONTRADICTED` when a measurement disagrees with the framing.\n")
    if os.path.exists(cc_path):
        with open(cc_path, encoding="utf-8") as fh:
            for c in json.load(fh):
                a(f"### {c['verdict']} — {c['youtube_claim'][:110]}\n")
                a(f"- **YouTube said** ({c['youtube_source']}): {c['youtube_claim']}")
                a(f"- **GitHub / primary source says:** {c['github_finding']}")
                a(f"- **Evidence:** `{c['evidence']}`")
                a(f"- **Why it matters:** {c['why_it_matters']}\n")
    else:
        a("_`reports/claim_conflicts.json` not found._\n")

    # ---------------- defects found by reading ----------------
    rd_path = os.path.join(gh.ROOT, "reports", "repo_defects.json")
    if os.path.exists(rd_path):
        a("## Defects found by reading the code\n")
        a("Errors the computed scores could not see. Every one of these repos scores well "
          "on the strict scale; each was found only by opening the file. **This is the "
          "argument against automating the read step away.**\n")
        with open(rd_path, encoding="utf-8") as fh:
            for d in json.load(fh):
                a(f"### `{d['repo']}` ({d['stars']} stars) — {d['severity']}\n")
                a(f"**{d['defect']}**\n")
                a(f"- *The repo says:* {d['what_the_repo_says']}")
                a(f"- *Actually true:* {d['what_is_actually_true']}")
                a(f"- *Evidence:* `{d['evidence']}`")
                a(f"- *Why it matters:* {d['why_it_matters']}\n")

    # ---------------- repo-level conflicts ----------------
    conflicts = [x for x in xref if x["verdict"] in ("CONFLICT", "WATCH")]
    a("## Tools whose repos are dead or dying\n")
    if conflicts:
        a("A tool recommended in a recent video whose repo is dead is exactly the finding this "
          "system exists to produce.\n")
        a("| tool | repo | state | note |\n|---|---|---|---|")
        for x in conflicts:
            a(f"| {x['tool']} | `{x['repo']}` | **{x['verdict']}** | {x['note']} |")
        a("")
    else:
        a("_No conflicts recorded yet — run `src/crossref.py`._\n")

    a("---\n")
    a(f"_Regenerate: `youtube-signal\\.venv\\Scripts\\python.exe signal-github\\src\\"
      f"build_knowledge.py`. Database `signal-github/data/github.db`, "
      f"{allrepos} repos as of {NOW:%Y-%m-%d}._")

    with open(OUT, "w", encoding="utf-8") as fh:
        fh.write("\n".join(w) + "\n")
    print(f"wrote {OUT} ({len(read)} read, {len(fetched)} scored, {allrepos} retrieved)")


if __name__ == "__main__":
    main()

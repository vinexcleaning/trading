"""STEP 6 — cross-reference against the YouTube knowledge base.

For every tool named in youtube-signal/KNOWLEDGE.md, ask two separate questions:

  1. does a GitHub repo exist for it?
  2. is that repo alive?

A tool recommended in a recent video whose repo died two years ago is the exact
conflict this whole system exists to surface. Those get verdict `CONFLICT`.

Uses repo search (600/hour), never core.
"""
from __future__ import annotations

import datetime
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import db  # noqa: E402
import gh  # noqa: E402

UTC = datetime.timezone.utc
NOW = datetime.datetime.now(UTC)
KB = os.path.join(os.path.dirname(gh.ROOT), "youtube-signal", "KNOWLEDGE.md")

# Things that are institutions or concepts, not software. Marked without
# spending a search — the YouTube project's rule: do not ask whether the SEC is
# a scam.
NOT_SOFTWARE = {
    "Citadel Securities": "institution",
    "Virtu Financial": "institution",
    "SEC Rule 606 filings": "regulatory filing",
    "SEC net capital rule / FINRA broker-dealer registration": "regulation",
    "Exchange colocation and direct market data feeds": "infrastructure category",
    "Avellaneda-Stoikov model (2008)": "academic model, not a package",
    "VPIN (volume-synchronised probability of informed trading)": "academic metric",
    "Wintermute / Jump Crypto / GSR Markets": "firms",
    "ForecastEx": "exchange",
    "Kalshi": "exchange",
    "Polymarket": "exchange",
    "Grok": "hosted LLM",
    "Perplexity Sonar API": "hosted API",
}

# Direct repo guesses where the tool's canonical repo is known, so we do not
# resolve a tool by name search and get a confidently wrong different project —
# the failure mode the YouTube project hit resolving channels by name.
KNOWN_REPO = {
    "DuckDB": "duckdb/duckdb",
    "Gnosis Conditional Token Framework": "gnosis/conditional-tokens-contracts",
    "UMA optimistic oracle": "UMAprotocol/protocol",
    "Jon-Becker/prediction-market-analysis (72M Kalshi + Polymarket trades)":
        "Jon-Becker/prediction-market-analysis",
    "Hyperliquid tick data API": "hyperliquid-dex/hyperliquid-python-sdk",
}


def parse_tools():
    if not os.path.exists(KB):
        return []
    out = []
    inside = False
    for line in open(KB, encoding="utf-8"):
        if line.startswith("## Tools and sites mentioned"):
            inside = True
            continue
        if inside and line.startswith("## ") and "Tools" not in line:
            break
        if inside and line.startswith("|") and "---" not in line:
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if len(cells) < 4 or cells[0] in ("tool",):
                continue
            name = cells[0]
            m = re.match(r"\[(.+?)\]\((.+?)\)", name)
            url = ""
            if m:
                name, url = m.group(1), m.group(2)
            out.append({"tool": name, "url": url, "what": cells[1],
                        "own": cells[2], "verified": cells[3]})
    return out


def repo_state(full_name: str):
    r = gh.search("repositories", f"repo:{full_name}", per_page=1)
    items = r.get("items") or []
    if not items:
        return None
    it = items[0]
    pushed = it.get("pushed_at") or ""
    days = None
    if pushed:
        try:
            days = (NOW - datetime.datetime.fromisoformat(pushed.replace("Z", "+00:00"))).days
        except ValueError:
            pass
    return {"full_name": it["full_name"], "stars": it.get("stargazers_count"),
            "pushed_at": pushed, "days": days, "archived": it.get("archived"),
            "size": it.get("size")}


def main():
    con = db.connect()
    tools = parse_tools()
    print(f"{len(tools)} tools in KNOWLEDGE.md", flush=True)
    rows = []

    for t in tools:
        name = t["tool"]
        if name in NOT_SOFTWARE:
            rows.append((name, t["what"][:160], "", "n/a",
                         "NOT_SOFTWARE", NOT_SOFTWARE[name]))
            continue

        fn = KNOWN_REPO.get(name)
        if not fn:
            m = re.search(r"github\.com/([^/\s)]+/[^/\s)#?]+)", t["url"] or "")
            if m:
                fn = m.group(1)

        if not fn:
            # No known repo, and we deliberately do NOT resolve a tool by free-text
            # name search: the YouTube project proved that returns a different
            # project at rank 0, confidently.
            rows.append((name, t["what"][:160], "", "unknown", "NO_REPO_KNOWN",
                         "closed-source or hosted; no canonical repo to check. "
                         "Not name-searched on purpose — name resolution returns "
                         "the wrong project confidently."))
            continue

        st = repo_state(fn)
        if not st:
            rows.append((name, t["what"][:160], fn, "gone", "CONFLICT",
                         "repo named but GitHub returns nothing for it"))
            continue
        d = st["days"]
        if st["archived"]:
            alive, verdict = "archived", "CONFLICT"
            note = f"archived; last push {d} days ago"
        elif d is None:
            alive, verdict, note = "unknown", "UNKNOWN", "no pushed_at"
        elif d > 730:
            alive, verdict = f"stale {d}d", "CONFLICT"
            note = f"last push {d} days ago (> 24 months) while still being recommended"
        elif d > 365:
            alive, verdict = f"quiet {d}d", "WATCH"
            note = f"last push {d} days ago"
        else:
            alive, verdict = f"alive {d}d", "OK"
            note = f"last push {d} days ago, {st['stars']} stars"
        rows.append((name, t["what"][:160], fn, alive, verdict, note))

    for r in rows:
        con.execute(
            """INSERT INTO crossref (tool, yt_claim, repo, alive, verdict, note)
               VALUES (?,?,?,?,?,?)
               ON CONFLICT(COALESCE(tool,'')) DO UPDATE SET
                 repo=excluded.repo, alive=excluded.alive,
                 verdict=excluded.verdict, note=excluded.note""", r)
    con.commit()

    order = {"CONFLICT": 0, "WATCH": 1, "NO_REPO_KNOWN": 2, "UNKNOWN": 3, "OK": 4,
             "NOT_SOFTWARE": 5}
    rows.sort(key=lambda r: order.get(r[4], 9))
    out = os.path.join(gh.ROOT, "reports", "step6_crossref.md")
    with open(out, "w", encoding="utf-8") as fh:
        fh.write("# STEP 6 — YouTube tools vs their GitHub repos\n\n")
        fh.write(f"Checked {NOW:%Y-%m-%d} UTC against `youtube-signal/KNOWLEDGE.md` "
                 f"({len(tools)} tools).\n\n")
        fh.write("`CONFLICT` = a tool that a recent video recommends whose repo is archived, "
                 "stale past 24 months, or missing. That mismatch is the point of the exercise.\n\n")
        fh.write("| tool | repo | alive | verdict | note |\n|---|---|---|---|---|\n")
        for name, what, fn, alive, verdict, note in rows:
            fh.write(f"| {name} | {'`'+fn+'`' if fn else '—'} | {alive} | **{verdict}** | {note} |\n")
        counts: dict[str, int] = {}
        for r in rows:
            counts[r[4]] = counts.get(r[4], 0) + 1
        fh.write("\n## Census\n\n| verdict | tools |\n|---|---|\n")
        for k, v in sorted(counts.items(), key=lambda kv: order.get(kv[0], 9)):
            fh.write(f"| {k} | {v} |\n")
    print(open(out, encoding="utf-8").read()[:3000], flush=True)
    db.log(con, "crossref", f"tools={len(tools)} " +
           " ".join(f"{k}={v}" for k, v in sorted(counts.items())))


if __name__ == "__main__":
    main()

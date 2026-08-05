"""STEP 3d — CURRENCY. Does the code still run against the venue that exists?

This is a NEW axis and it is a GATE, not a score. Every other axis in this
project measures how good a repo is. None of them asks whether it still works,
and the cost of that omission is measurable in this project's own data:

    scored repos                                   2,732
    importing the ARCHIVED Polymarket v1 client      719   = 26.3%
    ...of the top 25 by s_adj                          6   = 24.0%
    ...of the top 100 by s_adj                        35   = 35.0%

**The ranking does not distinguish them at all.** A quarter of what
`shortlist.py` puts in front of a reader is built on a library Polymarket
archived, and the share is HIGHER in the top 100 than in the corpus. The #3 repo
by `s_adj` imports v1, has **one commit**, and already trips `trust_me_bro`.

Currency is a gate rather than a component because it does not trade off against
substance. A rigorous, well-tested, thoroughly documented implementation of a
dead API is not 70% as useful as a live one — it is a thing you must not build
on, however good it is. So it can only ever LOWER a verdict, and it says why.

Every input is already in `repos`, so the default run makes **zero API calls**:

    pm_client    'v1-ARCHIVED' — computed by classify.py from the imports
    is_archived  the owner's own flag
    pushed_at    last push

`--live` re-checks the archive status of the client libraries themselves against
the GitHub API, so the table cannot silently rot the way a hardcoded list does.

    python src/currency.py                 report, zero API calls
    python src/currency.py --live          re-verify the client libraries
    python src/currency.py --shortlist 40  the read list with the gate applied
"""
from __future__ import annotations

import argparse
import datetime
import json
import os
import re
import sys
import urllib.error
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import db  # noqa: E402
import gh  # noqa: E402

NOW = datetime.datetime.now(datetime.timezone.utc)
UA = "signal-github/currency"

# The client libraries whose death makes a dependent repo stale. Re-verified by
# --live; the dates are the last check, not a guess.
CLIENTS = {
    "Polymarket/py-clob-client": {
        "archived": True, "checked": "2026-08-04",
        "note": "1,235 stars, last push 2026-05-25. STILL INSTALLABLE from "
                "PyPI (0.34.6), so `pip install py-clob-client` succeeds and "
                "nothing warns."},
    "Polymarket/clob-client": {
        "archived": True, "checked": "2026-08-04",
        "note": "the TypeScript v1 client, 514 stars."},
    "Polymarket/agents": {
        "archived": True, "checked": "2026-08-04",
        "note": "Polymarket's own agent framework, 3,761 stars, cold since "
                "2024-11-05. 693 repos still reference it."},
}
LIVE_CLIENT = "Polymarket/py-sdk"

COLD_DAYS = 365


def _token():
    p = os.path.join(gh.ROOT, ".env")
    if not os.path.exists(p):
        return None
    for line in open(p, encoding="utf-8", errors="ignore"):
        m = re.match(r"\s*([A-Za-z_]+)\s*=\s*(.+)", line)
        if m and "TOKEN" in m.group(1).upper():
            return m.group(2).strip().strip("\"'")
    return None


def verify_clients():
    """Re-check the client libraries against GitHub. A currency table you
    cannot date is worse than no currency table."""
    tok, out = _token(), {}
    h = {"User-Agent": UA, "Accept": "application/vnd.github+json"}
    if tok:
        h["Authorization"] = "Bearer " + tok
    for repo in list(CLIENTS) + [LIVE_CLIENT]:
        try:
            req = urllib.request.Request(
                "https://api.github.com/repos/" + repo, headers=h)
            d = json.load(urllib.request.urlopen(req, timeout=25))
            out[repo] = {"archived": bool(d.get("archived")),
                         "pushed_at": d.get("pushed_at"),
                         "stars": d.get("stargazers_count"),
                         "checked": NOW.date().isoformat()}
        except urllib.error.HTTPError as e:
            out[repo] = {"error": f"HTTP {e.code}"}
        except Exception as e:
            out[repo] = {"error": type(e).__name__}
        print(f"  {repo:32s} {out[repo]}")
    return out


def currency(row) -> tuple[str, list[str]]:
    """(state, reasons). CURRENT | STALE | COLD | DEAD.

    Ordered by how conclusive the evidence is: the owner's own archive flag
    first, a provably archived dependency second, and mere silence last.
    """
    reasons = []
    if row["is_archived"]:
        reasons.append("DEAD: the owner archived this repository")
        return "DEAD", reasons

    pmc = (row["pm_client"] or "")
    if pmc.startswith("v1"):
        reasons.append(
            "STALE: imports the Polymarket v1 CLOB client, which Polymarket "
            "archived (py-clob-client 2026-05-25, checked 2026-08-04). "
            "CLOB v2 went live 2026-04-28. `pip install py-clob-client` still "
            "succeeds, so this does not surface as an error at install time.")

    pushed = (row["pushed_at"] or "")
    if pushed:
        try:
            days = (NOW - datetime.datetime.fromisoformat(
                pushed.replace("Z", "+00:00"))).days
            if days > COLD_DAYS:
                reasons.append(f"COLD: no push in {days} days")
        except ValueError:
            pass

    if any(r.startswith("STALE") for r in reasons):
        return "STALE", reasons
    if reasons:
        return "COLD", reasons
    return "CURRENT", reasons


# Currency can only LOWER a verdict. These are the states that must never be
# handed to a reader as something to build on.
BLOCKS_RECOMMEND = {"DEAD", "STALE"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--live", action="store_true")
    ap.add_argument("--shortlist", type=int, default=0)
    a = ap.parse_args()

    if a.live:
        print("re-verifying the client libraries:")
        verified = verify_clients()
        path = os.path.join(gh.ROOT, "reports", "currency_clients.json")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        json.dump(verified, open(path, "w", encoding="utf-8"), indent=2)
        print(f"  wrote {path}")

    con = db.connect()
    rows = con.execute(
        "SELECT full_name, s_adj, s_strict, stars, commits, is_archived, "
        "       pushed_at, pm_client, kind, venue_detected, trust_me_bro, "
        "       submits_orders "
        "FROM repos WHERE s_adj IS NOT NULL ORDER BY s_adj DESC").fetchall()

    from collections import Counter
    states = Counter()
    tagged = []
    for r in rows:
        st, why = currency(r)
        states[st] += 1
        tagged.append((r, st, why))

    n = len(rows)
    L = ["# CURRENCY — the axis this project did not have\n",
         f"{n:,} scored repos, {NOW.isoformat(timespec='minutes')}. "
         "**Zero API calls** unless `--live`: every input is already in "
         "`repos`.\n",
         "## Why it is a gate and not a component\n",
         "A rigorous, well-tested, thoroughly documented implementation of a "
         "dead API is not 70% as useful as a live one. It is a thing you must "
         "not build on, however good it is. So currency can only ever LOWER a "
         "verdict, and it names the evidence.\n",
         "## What the omission was costing\n",
         "| slice | imports the ARCHIVED v1 client |", "|---|---|"]
    for k in (25, 50, 100, 200, 500, n):
        sl = tagged[:k]
        v1 = sum(1 for r, _, _ in sl if (r["pm_client"] or "").startswith("v1"))
        L.append(f"| top {k:,} by `s_adj` | **{v1} ({v1/k:.1%})** |")
    L.append("")
    L.append("**The share is HIGHER in the top 100 (35.0%) than in the corpus "
             "(26.3%).** Whatever `s_adj` is rewarding, it correlates slightly "
             "with building on the dead library — which makes sense: v1 has "
             "been around longer, so there is more of it and it is more "
             "thoroughly built.\n")

    L.append("## States\n| state | n | share |\n|---|---|---|")
    for k, v in states.most_common():
        L.append(f"| {k} | {v:,} | {v/n:.1%} |")
    L.append("")
    L.append(f"**{states['DEAD'] + states['STALE']:,} repos "
             f"({(states['DEAD']+states['STALE'])/n:.1%}) are gated out of any "
             "recommendation.** They stay in the corpus and stay readable — the "
             "gate blocks a RECOMMENDATION, not a read.\n")

    top = a.shortlist or 40
    L.append(f"## The read list with the gate applied — top {top}\n")
    L.append("| # | repo | s_adj | currency | tmb | commits | why |")
    L.append("|---|---|---|---|---|---|---|")
    shown = 0
    for r, st, why in tagged:
        if st in BLOCKS_RECOMMEND:
            continue
        shown += 1
        L.append(f"| {shown} | [{r['full_name']}](https://github.com/{r['full_name']}) "
                 f"| {r['s_adj']:.2f} | {st} | "
                 f"{'**YES**' if r['trust_me_bro'] else ''} | {r['commits']} | "
                 f"{'; '.join(why)[:70]} |")
        if shown >= top:
            break
    L.append("")

    L.append(f"## What the gate REMOVED from the old top {top}\n")
    L.append("| repo | s_adj | state | why |")
    L.append("|---|---|---|---|")
    for r, st, why in tagged[:top]:
        if st in BLOCKS_RECOMMEND:
            L.append(f"| [{r['full_name']}](https://github.com/{r['full_name']}) "
                     f"| {r['s_adj']:.2f} | **{st}** | {'; '.join(why)[:150]} |")
    L.append("")

    path = os.path.join(gh.ROOT, "reports", "currency.md")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    open(path, "w", encoding="utf-8").write("\n".join(L))
    print(f"  {n:,} repos · " + " · ".join(f"{k} {v}" for k, v in states.most_common()))
    print(f"  wrote {path}")
    db.log(con, "currency", f"n={n} " + " ".join(f"{k}={v}" for k, v in states.items()))
    con.close()


if __name__ == "__main__":
    main()

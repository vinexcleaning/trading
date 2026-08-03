"""Free prescreen — decides the ORDER in which the 60/hour core budget is spent.

2,562 repos passed the gates. At 1–4 core calls each, deep-fetching all of them
is a multi-day job. This ranks them using only fields already in the database,
so nothing is spent deciding what to spend on.

This is a queue, not a verdict. A low prescreen score means "not yet", never
"rejected" — the same reason STALE repos are tagged and kept.
"""
from __future__ import annotations

import datetime
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import db  # noqa: E402

NOW = datetime.datetime.now(datetime.timezone.utc)

STRONG_WORDS = re.compile(
    r"\b(bot|trading|trader|arbitrage|arb|market[- ]?mak|backtest|strateg|quant|"
    r"clob|orderbook|order[- ]book|websocket|copy[- ]?trad|hedge|edge|alpha|"
    r"execution|signal)\b", re.I)
WEAK_WORDS = re.compile(
    r"\b(dashboard|tracker|viewer|scraper|frontend|ui|website|landing|portfolio|"
    r"tutorial|example|demo|template|awesome|list|clone|starter|boilerplate|docs?)\b", re.I)


def days(iso):
    if not iso:
        return 9999
    try:
        return (NOW - datetime.datetime.fromisoformat(iso.replace("Z", "+00:00"))).days
    except ValueError:
        return 9999


def score(r):
    fam = set((r["families"] or "").split(","))
    s = 0.0
    reasons = []

    if "F2_CODE" in fam:
        s += 4; reasons.append("+4 found by code search")
    if "SEED" in fam:
        s += 2; reasons.append("+2 built on the 72M-trade dataset")
    if "F2" in fam:
        s += 2; reasons.append("+2 insider vocabulary")
    if "F1" in fam and "F2" not in fam:
        s += 0.5

    st = r["stars"] or 0
    if st >= 200: s += 3; reasons.append(f"+3 {st} stars")
    elif st >= 50: s += 2; reasons.append(f"+2 {st} stars")
    elif st >= 10: s += 1; reasons.append(f"+1 {st} stars")

    kb = r["size_kb"] or 0
    if 60 <= kb <= 400_000:
        s += 2; reasons.append(f"+2 {kb} KB of code")
    elif kb < 20:
        s -= 2; reasons.append(f"-2 only {kb} KB")

    if (r["language"] or "") in ("Python", "TypeScript", "Rust", "Go", "JavaScript"):
        s += 1

    d = days(r["pushed_at"])
    if d <= 90: s += 2; reasons.append(f"+2 pushed {d}d ago")
    elif d <= 365: s += 1
    elif d > 730: s -= 1

    if (r["forks"] or 0) >= 3:
        s += 1

    if r["is_fork"]:
        s -= 3; reasons.append("-3 is a fork")
    if r["is_archived"]:
        s -= 1

    blob = f"{r['full_name']} {r['description'] or ''} {r['topics'] or ''}"
    strong = set(m.group(0).lower() for m in STRONG_WORDS.finditer(blob))
    weak = set(m.group(0).lower() for m in WEAK_WORDS.finditer(blob))
    if strong:
        s += min(3, len(strong)); reasons.append("+" + str(min(3, len(strong))) + " " + ",".join(sorted(strong)[:3]))
    if weak:
        s -= min(3, len(weak)); reasons.append("-" + str(min(3, len(weak))) + " " + ",".join(sorted(weak)[:3]))

    if "generic only" in (r["drop_reason"] or ""):
        s -= 3; reasons.append("-3 on-topic on generics only")

    return s, "; ".join(reasons)


def main():
    con = db.connect()
    con.execute("CREATE TABLE IF NOT EXISTS prescreen "
                "(full_name TEXT PRIMARY KEY, score REAL, why TEXT)")
    rows = con.execute("SELECT * FROM repos WHERE gate IN ('PASS','STALE')").fetchall()
    out = []
    for r in rows:
        s, why = score(r)
        out.append((r["full_name"], s, why))
    con.executemany("INSERT INTO prescreen (full_name,score,why) VALUES (?,?,?) "
                    "ON CONFLICT(full_name) DO UPDATE SET score=excluded.score, why=excluded.why",
                    out)
    con.commit()
    out.sort(key=lambda x: -x[1])
    print(f"prescreened {len(out)} repos; top 20:")
    for fn, s, why in out[:20]:
        print(f"  {s:5.1f}  {fn}")
    db.log(con, "prescreen", f"n={len(out)} top={out[0][1] if out else 0}")


if __name__ == "__main__":
    main()

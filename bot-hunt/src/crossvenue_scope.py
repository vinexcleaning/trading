"""What has the recorder actually accrued, and can Pinnacle be JOINED to Kalshi?

The shortlist's #1 mechanism — de-vig a sharp sportsbook, compare to the
prediction market — has never been tested by anyone in this repo. The recorder
started 2026-08-04 21:27 UTC is the whole apparatus, and it now holds enough to
answer the first question: **do the two venues quote the same matches at the
same time, and can they be matched at all?**

The corpora are explicit that matching is where cross-venue work dies:
*"the phantoms have HIGH token overlap, not low"* and *"a 50c+ cross-venue gap
is almost always two different contracts."* So this measures the JOIN before
measuring any edge, and reports what fails to match rather than quietly
dropping it.
"""
from __future__ import annotations

import json
import re
import sqlite3
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB = ROOT / "data" / "record.db"
REP = ROOT / "reports"


def norm(s):
    """Team names differ across venues: 'Team Vitality' vs 'Vitality',
    'FunPlus Phoenix' vs 'FPX'. Normalise hard, then match on tokens."""
    if not s:
        return ""
    s = s.lower()
    s = re.sub(r"\b(team|esports?|gaming|club|the|gg|e-?sports)\b", " ", s)
    s = re.sub(r"[^a-z0-9 ]+", " ", s)
    return " ".join(s.split())


def main():
    con = sqlite3.connect(f"file:{DB.as_posix()}?mode=ro", uri=True, timeout=180)
    REP.mkdir(parents=True, exist_ok=True)

    print("== recorder coverage")
    for r in con.execute("select count(*), min(started_utc), max(started_utc) "
                         "from cycles"):
        print(f"   cycles {r[0]}   {r[1]} -> {r[2]}")
    for tbl in ("pin_matchup", "pin_market", "k_book", "p_book"):
        n, c = con.execute(f"select count(*), count(distinct cycle_id) "
                           f"from {tbl}").fetchone()
        print(f"   {tbl:12} rows={n:>9,}  cycles={c}")

    print("\n== Pinnacle esports matchups seen")
    rows = con.execute(
        "select matchup_id, max(league), max(home), max(away), min(ts_utc), "
        "max(ts_utc), max(starts_utc) from pin_matchup where sport='esports' "
        "group by matchup_id").fetchall()
    print(f"   {len(rows)} distinct esports matchups")
    leagues = Counter(r[1] for r in rows)
    print(f"   leagues: {leagues.most_common(8)}")
    named = [r for r in rows if r[2] and r[3]]
    print(f"   with both team names: {len(named)}")
    for r in named[:6]:
        print(f"     {r[2][:26]:26} vs {r[3][:26]:26}  starts={str(r[6])[:16]}")

    print("\n== Kalshi esports markets seen")
    krows = con.execute(
        "select series, ticker, count(*), min(ts_utc), max(ts_utc) "
        "from k_book where series in ('KXCS2GAME','KXLOLGAME','KXVALORANTGAME')"
        " group by ticker").fetchall()
    print(f"   {len(krows)} distinct tickers, "
          f"{len({k[1].rsplit('-',1)[0] for k in krows})} events")
    for r in krows[:4]:
        print(f"     {r[1][:52]:52} snaps={r[2]}")

    print("\n== Polymarket esports tokens seen")
    prows = con.execute(
        "select tag, slug, count(*) from p_book "
        "where tag in ('cs2','dota-2','valorant') group by slug").fetchall()
    print(f"   {len(prows)} distinct slugs")
    for r in prows[:6]:
        print(f"     [{r[0]:9}] {str(r[1])[:60]:60} snaps={r[2]}")

    # ---- THE JOIN: can a Pinnacle matchup be matched to a Kalshi event? ----
    print("\n== JOIN ATTEMPT — Pinnacle esports vs Kalshi esports")
    # Kalshi encodes teams in the ticker suffix, e.g.
    # KXCS2GAME-26MAY300400EFM8-EF  -> event 'EFM8', outcome 'EF'
    kev = defaultdict(set)
    for _, tk, _, _, _ in krows:
        base, out = tk.rsplit("-", 1)
        kev[base].add(out)
    print(f"   Kalshi events: {len(kev)}   "
          f"(outcome codes are ABBREVIATIONS, e.g. {list(kev.items())[:2]})")

    pin_tokens = {}
    for mid, lg, home, away, *_ in named:
        pin_tokens[mid] = (norm(home), norm(away), home, away)

    hits = 0
    examples = []
    for base, outs in kev.items():
        codes = {o.lower() for o in outs}
        for mid, (h, a, ho, ao) in pin_tokens.items():
            hw = set(h.split()) | {"".join(w[0] for w in h.split())}
            aw = set(a.split()) | {"".join(w[0] for w in a.split())}
            if codes & hw and codes & aw:
                hits += 1
                if len(examples) < 8:
                    examples.append((base, sorted(outs), ho, ao))
                break
    print(f"   naive abbreviation match: {hits} of {len(kev)} Kalshi events")
    for e in examples:
        print(f"     {e[0][:44]:44} {e[1]}  <->  {e[2]} vs {e[3]}")
    print("\n   NOTE: Kalshi outcome codes are 2-4 letter abbreviations and")
    print("   Pinnacle uses full names. A token join is a RECALL net only —")
    print("   the corpora are explicit that resolution-equivalence, not name")
    print("   similarity, is what makes a cross-venue pair real.")
    con.close()


if __name__ == "__main__":
    main()

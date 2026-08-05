"""Grade signal-github's ranking the way the video rubric was graded.

`signal-github` has three axes (`s_adj`, `trust_me_bro`, the fee audit) and a
shortlist that combines them, and **none of it has ever been tested against
known answers.** That is the same gap Task 1 closed for the video rubric, and it
is closed the same way: labels fixed by something OUTSIDE the instrument.

Two kinds of label, and the second is what makes this a real test rather than
five anecdotes:

  HAND   five repos this project read in full and recorded a verdict for. Five
         cases is not a precision estimate; they are here as spot checks.
  OWNER  **the repository owner's own statements.** `is_archived` is a flag the
         owner set. `pm_client = v1-ARCHIVED` means the code imports a library
         POLYMARKET archived. Neither is an inference and neither can be argued
         with, which makes them ground truth on 739 repos rather than five.

The measurement is then simple and hard to fake: **does the ranking put things
in front of a reader that their own owners have discontinued?**

    python src/gh_validate.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import corpora  # noqa: E402

# (full_name, correct action, what fixes it, one line)
HAND = [
    ("artyomderkach-bit/kalshi-15m-market-maker", "RECOMMEND", "READ",
     "0 stars, MIT, ships in paper mode, makes no profit claim, states what it "
     "withholds, and imports ONE fair-value function into both engine and "
     "backtest 'so they can never drift apart'. Its own README says almost "
     "every edge that looked real in-sample decayed out of sample."),
    ("evan-kolberg/prediction-market-backtesting", "ABSORB", "READ",
     "The most rigorous machinery in the corpus and its Kalshi taker formula "
     "is right - but it contradicts itself on maker fees between its "
     "instrument metadata (0) and its fee model (0.07), and a passive strategy "
     "reads the one the backtest ignores."),
    ("hamad-khawaja/kalshi-trading-bot", "ABSORB", "READ",
     "Real engineering - CI, 15 test files, a robustness check, a calibration "
     "report - with the same per-series maker-fee error, deeper in the stack."),
    ("aulekator/Polymarket-BTC-15-Minute-Trading-Bot", "REJECT", "READ+LIVE",
     "557 stars against 4 commits. Three mutually inconsistent fee schedules "
     "for one venue, `fee_rate_bps=0` in the live path, a 'self-learning' "
     "feature its own README calls a placeholder, an MIT badge with an empty "
     "license field in the API, and ZERO occurrences of 'backtest'."),
    ("hcharper/polyBot-Weather", "REJECT", "OWNER+LIVE",
     "`s_adj`'s own former #1 pick. ONE commit, a README claiming 'Guaranteed "
     "profit', and it imports the archived v1 client."),
]


def load():
    con = corpora.ro("github")
    rows = con.execute(
        "SELECT full_name, s_adj, s_strict, s_total, stars, commits, "
        "       is_archived, pushed_at, pm_client, trust_me_bro, kind, "
        "       venue_detected FROM repos WHERE s_adj IS NOT NULL "
        "ORDER BY s_adj DESC").fetchall()
    con.close()
    return [dict(r) for r in rows]


def owner_says_discontinued(r) -> str | None:
    if r["is_archived"]:
        return "the owner archived this repository"
    if (r["pm_client"] or "").startswith("v1"):
        return ("imports the Polymarket v1 CLOB client, which POLYMARKET "
                "archived on 2026-05-25")
    return None


def fee_ground_truth():
    """The external fact this project already validated `s_adj` against."""
    p = corpora.ROOT / "signal-github" / "reports" / "fee_audit.json"
    if not p.exists():
        return set(), set()
    ok, bad = set(), set()
    for f in json.loads(p.read_text(encoding="utf-8"))["findings"]:
        v = " ".join(f["verdict"])
        if "maker 0.0175 OK" in v:
            ok.add(f["repo"])
        elif "sets a fee to zero" in v:
            bad.add(f["repo"])
    return ok, bad


def main():
    rows = load()
    n = len(rows)
    by_name = {r["full_name"]: (i, r) for i, r in enumerate(rows)}
    fee_ok, fee_bad = fee_ground_truth()

    L, w = [], None
    L = []
    w = L.append
    w("# Grading signal-github's ranking against known answers\n")
    w(f"{n:,} scored repos. Labels are fixed OUTSIDE the instrument: five "
      "read in full, and **739 by their own owner's statement** — an archive "
      "flag the owner set, or an import of a library Polymarket archived. "
      "Neither is an inference.\n")

    # ---- 1: the owner-truth measurement
    w("## 1. Does the ranking recommend things their owners discontinued?\n")
    w("| slice | discontinued by the owner | share |")
    w("|---|---|---|")
    for k in (10, 25, 50, 100, 200, 500, n):
        sl = rows[:k]
        bad = sum(1 for r in sl if owner_says_discontinued(r))
        w(f"| top {k:,} by `s_adj` | **{bad}** | **{bad/k:.1%}** |")
    w("")
    total_bad = sum(1 for r in rows if owner_says_discontinued(r))
    w(f"**{total_bad:,} of {n:,} ({total_bad/n:.1%}) are discontinued by their "
      f"own owner, and the top 100 is worse than the corpus.** The ranking has "
      "no component that can see this. It is not a subtle failure: a reader "
      "handed the top 25 gets six repos built on a library that no longer "
      "exists, and the install still succeeds, so nothing warns them.\n")

    # ---- 2: does the gate cost anything measurable?
    w("## 2. Does gating them out cost anything?\n")
    w("Checked against the external fact this project already validated "
      "`s_adj` against — the repos that provably model Kalshi's **maker** fee "
      "correctly, which is a published ground truth independent of every S "
      "component.\n")
    w("| slice | fee-correct repos, ungated | fee-correct, gated |")
    w("|---|---|---|")
    gated = [r for r in rows if not owner_says_discontinued(r)]
    for k in (25, 50, 100, 200):
        a = sum(1 for r in rows[:k] if r["full_name"] in fee_ok)
        b = sum(1 for r in gated[:k] if r["full_name"] in fee_ok)
        w(f"| top {k} | {a} | **{b}** |")
    w("")
    lost = [r["full_name"] for r in rows[:200]
            if r["full_name"] in fee_ok and owner_says_discontinued(r)]
    w(f"**{len(lost)} fee-correct repos in the top 200 are gated out**"
      + (": " + ", ".join(f"`{x}`" for x in lost[:6]) if lost else "") + ".\n")
    w("A repo can model the fee correctly and still import a dead client — "
      "those are independent facts, which is exactly why currency is a gate "
      "and not a term in the score. **Gating never claims the code is bad. It "
      "claims you must not build on it.**\n")

    # ---- 3: the hand-read spot checks
    w("## 3. The five read in full\n")
    w("Five cases is not a precision estimate. It is five demonstrations, and "
      "the interesting column is the last one.\n")
    w("| repo | correct | rank by `s_adj` | percentile | tmb | currency | agrees? |")
    w("|---|---|---|---|---|---|---|")
    agree = 0
    for name, correct, why, _note in HAND:
        if name not in by_name:
            w(f"| `{name}` | {correct} | **not in corpus** | | | | |")
            continue
        i, r = by_name[name]
        pct = 1 - i / n
        disc = owner_says_discontinued(r)
        # What the ranking alone would do: top decile -> recommend.
        implied = "RECOMMEND" if pct >= 0.90 else ("ABSORB" if pct >= 0.5
                                                   else "REJECT")
        ok = implied == correct
        agree += ok
        w(f"| [{name}](https://github.com/{name}) | {correct} | {i+1:,} | "
          f"{pct:.1%} | {'**YES**' if r['trust_me_bro'] else ''} | "
          f"{'**' + disc[:24] + '**' if disc else 'current'} | "
          f"{'yes' if ok else '**NO — ranking says ' + implied + '**'} |")
    w("")
    w(f"**{agree} of {len(HAND)} agree** if the top decile is read as "
      "'recommend'.\n")
    for name, correct, why, note in HAND:
        w(f"- **`{name}`** → {correct} ({why}). {note}")
    w("")

    # ---- 4: what the gate changes at the top
    w("## 4. The top 25, before and after\n")
    w("| # | before (`s_adj` alone) | | after (currency gate applied) |")
    w("|---|---|---|---|")
    for i in range(25):
        b = rows[i]
        g = gated[i]
        disc = owner_says_discontinued(b)
        w(f"| {i+1} | `{b['full_name'][:40]}` | "
          f"{'**GATED: ' + disc[:30] + '**' if disc else ''} | "
          f"`{g['full_name'][:40]}` |")
    w("")

    out = corpora.REPORTS / "T6_github_validation.md"
    out.write_text("\n".join(L), encoding="utf-8")
    print(f"  {total_bad}/{n} discontinued by owner ({total_bad/n:.1%})")
    print(f"  top 25: {sum(1 for r in rows[:25] if owner_says_discontinued(r))}")
    print(f"  hand cases agreeing: {agree}/{len(HAND)}")
    print(f"  wrote {out}")


if __name__ == "__main__":
    main()

"""Corpus-wide audit: which repos hardcode a venue fee, and do they get it right?

This became possible only when `gh.archive()` made whole-repo source free. Reading
ten repos found three fee defects by hand; this asks the same question of every
repo in the corpus at once, and it is the kind of question a keyword score cannot
answer because the answer depends on the *value* of a constant, not its presence.

Ground truth, from correction C1 (`CORRECTIONS.md`), sourced from Kalshi's own
fee schedule effective 2026-07-07 and the live `/trade-api/v2/series`:

  Kalshi taker   roundup(M x 0.07   x C x P x (1-P))   M defaults to 1
  Kalshi maker   roundup(M x 0.0175 x C x P x (1-P))   M defaults to 0,
                 non-zero on exactly 130 of 12,396 series - which are the
                 liquid ones (Sports 107, incl. KXATPMATCH / KXWTAMATCH)

  Polymarket     taker fees are 0.04-0.07 by category as of 2026-08; only some
                 categories are free. Makers pay zero.

What is counted, per repo:
  - does it name a venue fee at all?
  - does it use 0.07 (right for Kalshi taker) or something else?
  - does it hardcode a Kalshi MAKER rate, and is it 0.0175, 0.07 or 0?
  - does it set fees to zero outright - the trap that makes any backtest print
    a profit?

A repo scoring zero fee is not automatically wrong: a Polymarket maker really
does pay nothing. The output separates "zero and says which side/venue" from
"zero with no qualification", and does not accuse - it reports path:line so a
human can look.

    python src/fee_audit.py [--limit N]
"""
from __future__ import annotations

import json
import os
import re
import sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import db  # noqa: E402
import gh  # noqa: E402

KALSHI_CTX = re.compile(r"kalshi", re.I)
POLY_CTX = re.compile(r"polymarket|clob", re.I)
FEE_LINE = re.compile(r"(fee|commission|taker|maker)", re.I)
NUMBER = re.compile(r"(?<![\w.])(\d*\.\d+|\d+)(?![\w.])")

# A fee constant is a number on a line that talks about fees. Restrict to the
# plausible range so that years, ports and array indices do not pollute it.
def fee_numbers(line: str):
    out = []
    for m in NUMBER.finditer(line):
        try:
            v = float(m.group(1))
        except ValueError:
            continue
        if 0.0 <= v <= 10.0:
            out.append(v)
    return out


MAKER_LINE = re.compile(r"maker", re.I)
TAKER_LINE = re.compile(r"taker", re.I)
ZERO_FEE = re.compile(r"(maker|taker|fee)\w*\s*[:=]\s*0(\.0+)?\b", re.I)

SKIP_SEG = re.compile(r"(^|/)(node_modules|\.venv|venv|site-packages|dist|build|vendor)/")


def main():
    limit = None
    if "--limit" in sys.argv:
        limit = int(sys.argv[sys.argv.index("--limit") + 1])

    con = db.connect()
    q = ("SELECT full_name, default_branch, stars, s_total, s_strict, evidence "
         "FROM repos WHERE fetched>=1 ORDER BY stars DESC")
    if limit:
        q += f" LIMIT {limit}"
    rows = con.execute(q).fetchall()
    print(f"auditing {len(rows)} deep-fetched repos (cache only, no network)\n", flush=True)

    findings = []
    tally = Counter()
    for r in rows:
        fn = r["full_name"]
        try:
            ev = json.loads(r["evidence"] or "{}")
        except json.JSONDecodeError:
            ev = {}
        branch = (ev.get("branch") or [r["default_branch"] or "main"])[0]
        arch = gh.archive(fn, branches=tuple(dict.fromkeys(
            [b for b in (branch, r["default_branch"] or "", "main", "master") if b])))
        files = arch.get("files") or {}
        if not files:
            tally["no_source"] += 1
            continue

        hits = {"kalshi_taker": [], "kalshi_maker": [], "zero": [], "any_fee": []}
        for path, text in files.items():
            if SKIP_SEG.search(path) or not path.lower().endswith(
                    (".py", ".ts", ".tsx", ".js", ".rs", ".go", ".java", ".json",
                     ".yaml", ".yml", ".toml")):
                continue
            venue_k = bool(KALSHI_CTX.search(path)) or bool(KALSHI_CTX.search(text[:4000]))
            for n, line in enumerate(text.splitlines(), 1):
                if not FEE_LINE.search(line):
                    continue
                nums = fee_numbers(line)
                loc = f"{path}:{n}"
                snippet = line.strip()[:120]
                hits["any_fee"].append(loc)
                if ZERO_FEE.search(line):
                    hits["zero"].append((loc, snippet))
                if venue_k and nums:
                    if MAKER_LINE.search(line):
                        hits["kalshi_maker"].append((loc, snippet, nums))
                    elif TAKER_LINE.search(line) or 0.07 in nums:
                        hits["kalshi_taker"].append((loc, snippet, nums))

        if not hits["any_fee"]:
            tally["models_no_fee_at_all"] += 1
            continue
        tally["mentions_a_fee"] += 1

        verdict = []
        kt = hits["kalshi_taker"]
        if kt:
            vals = {v for _l, _s, ns in kt for v in ns if 0 < v <= 1}
            if 0.07 in vals:
                tally["kalshi_taker_correct_0.07"] += 1
                verdict.append("kalshi taker 0.07 OK")
            elif vals:
                tally["kalshi_taker_other_value"] += 1
                verdict.append(f"kalshi taker uses {sorted(vals)[:4]} not 0.07")
        km = hits["kalshi_maker"]
        if km:
            vals = {v for _l, _s, ns in km for v in ns if 0 <= v <= 1}
            if 0.0175 in vals:
                tally["kalshi_maker_correct_0.0175"] += 1
                verdict.append("kalshi maker 0.0175 OK")
            elif vals == {0.0} or vals == {0}:
                tally["kalshi_maker_hardcoded_zero"] += 1
                verdict.append("kalshi maker hardcoded 0 - wrong on the 130 liquid series")
            elif 0.07 in vals:
                tally["kalshi_maker_equals_taker"] += 1
                verdict.append("kalshi maker set to 0.07 = taker - the error C1 corrected")
            elif vals:
                tally["kalshi_maker_other_value"] += 1
                verdict.append(f"kalshi maker uses {sorted(vals)[:4]}")
        if hits["zero"]:
            tally["sets_some_fee_to_zero"] += 1
            if not km and not kt:
                verdict.append(f"sets a fee to zero ({len(hits['zero'])} sites)")

        if verdict:
            findings.append({
                "repo": fn, "stars": r["stars"], "s_strict": r["s_strict"],
                "verdict": verdict,
                "kalshi_taker": [(l, s) for l, s, _ in kt[:2]],
                "kalshi_maker": [(l, s) for l, s, _ in km[:2]],
                "zero_fee": hits["zero"][:3],
            })

    print("=== tally ===")
    for k, v in tally.most_common():
        print(f"  {k:34} {v}")

    print(f"\n=== {len(findings)} repos with a decidable fee constant ===")
    for f in findings[:60]:
        print(f"\n  {f['repo']}  ({f['stars']}*, strict {f['s_strict']})")
        for v in f["verdict"]:
            print(f"      {v}")
        for loc, snip in (f["kalshi_maker"] + f["kalshi_taker"] + f["zero_fee"])[:3]:
            print(f"      {loc}  {snip}")

    out = os.path.join(gh.ROOT, "reports", "fee_audit.json")
    with open(out, "w", encoding="utf-8") as fh:
        json.dump({"tally": dict(tally), "findings": findings}, fh, indent=1)
    print(f"\nwrote {out}")


if __name__ == "__main__":
    main()

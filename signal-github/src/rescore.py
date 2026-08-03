"""STEP 3c — a strict rescore, because the naive port of the YouTube rubric
saturates.

Premise 2 asked whether the S/H scoring transfers to code. Measured answer: the
S half transfers badly. Ported literally, 17 of the first 40 repos scored a
perfect 10/10, which is not a ranking, it is a ceiling. The reasons are specific:

  S1 "fee, slippage, spread appear in source" — `spread` is ordinary orderbook
     vocabulary. Any repo that reads a book mentions it. The term does not
     separate a repo that MODELS costs from one that merely displays a book.
  S2 "backtest and a live path, distinguishable" — matching those words against
     FILE PATHS fires on almost everything, because `order`, `trade` and `bot`
     appear in the path of every repo in this corpus.
  S4 "README explains the mechanism" — an LLM-written README hits every
     mechanism keyword while explaining nothing. Keyword presence is the wrong
     instrument here and this is the component that transfers worst.

So both scores are kept side by side. `s_total` is the literal rubric; `s_strict`
demands the same thing in a form that cannot be satisfied by vocabulary alone.
Neither is deleted — the gap between them is itself the measurement.

Free: reads only files already in the cache.
"""
from __future__ import annotations

import datetime
import hashlib
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import db  # noqa: E402
import gh  # noqa: E402

NOW = datetime.datetime.now(datetime.timezone.utc)

# S1 strict: a COST term used in arithmetic, not merely named.
COST_TERM = r"(fee|fees|slippage|commission|taker_fee|maker_fee|transaction_cost|trading_cost)"
COST_MATH = re.compile(rf"{COST_TERM}\w*\s*[-+*/]|[-+*/]\s*\w*{COST_TERM}|"
                       rf"{COST_TERM}\w*\s*=\s*[0-9.]", re.I)

# S2 strict: a backtest that is a MODULE, not a word in a filename.
BT_SEG = re.compile(r"(^|/)(backtest|backtests|backtesting|sim|simulation|replay|research)(/|_|\.)", re.I)
BT_LOOP = re.compile(r"for\s+\w+\s+in\s+.*(candle|bar|tick|row|trade|snapshot|history)|"
                     r"\.iterrows\(\)|itertuples\(\)", re.I)
# Real order submission, not the word "order".
SUBMIT = re.compile(r"(create_order|post_order|place_order|submit_order|create_and_post_order|"
                    r"createOrder|postOrder|placeOrder|create_market_order|CreateOrder|"
                    r"\.create_order\(|client\.post|orders\.create)")

TEST_FILE = re.compile(r"(^|/)tests?/|(^|/)test_[^/]+\.(py|ts|js)$|\.(test|spec)\.(js|ts|tsx)$", re.I)
ARTIFACT = re.compile(r"\.(csv|parquet|png|json)$", re.I)
ARTIFACT_DIR = re.compile(r"(^|/)(results?|outputs?|reports?|figures?|plots?|backtest_results|"
                          r"artifacts|analysis)/", re.I)

MECH = re.compile(r"\b(adverse selection|inventory|expected value|edge|break[- ]?even|"
                  r"slippage|fee|spread|hypothesis|assumption|why this works|"
                  r"the strategy is|we (buy|sell|quote)|reservation price|kelly|"
                  r"sharpe|drawdown|sizing)\b", re.I)
HEADER = re.compile(r"^#{1,3}\s+(?!.*(install|setup|getting started|usage|license|"
                    r"contribut|requirement|quick ?start))(.+)$", re.I | re.M)


def cache_read(fn, branch, path):
    url = f"https://raw.githubusercontent.com/{fn}/{branch}/{path}"
    cp = os.path.join(gh.CACHE, hashlib.sha1(url.encode()).hexdigest()[:20] + ".txt")
    if not os.path.exists(cp):
        return None
    try:
        t = open(cp, encoding="utf-8", errors="replace").read()
    except OSError:
        return None
    return None if t.startswith("\x00MISSING") else t


def grep(text, rx, path, limit=3):
    out = []
    for n, line in enumerate(text.splitlines(), 1):
        if rx.search(line):
            out.append(f"{path}:{n}  {line.strip()[:100]}")
            if len(out) >= limit:
                break
    return out


def strict_score(fn, branch, paths, corpus, readme):
    ev = {}
    src = [(p, t) for p, t in corpus if not TEST_FILE.search(p)]

    # ---- S1: cost arithmetic ----
    s1_ev = []
    for p, t in src:
        s1_ev += grep(t, COST_MATH, p, limit=2)
        if len(s1_ev) >= 4:
            break
    s1 = 3 if s1_ev else 0
    ev["S1"] = s1_ev[:4] or ["no cost term used in arithmetic anywhere in fetched source"]

    # ---- S2: backtest module AND submission code, in different files ----
    # A backtest must be a MODULE. An earlier version also accepted "a loop over
    # rows in a file that says 'replay' somewhere", which scored
    # warproxxx/poly-maker a 2 on a websocket client — while that repo's own
    # README says a backtester is "not yet built". The repo was right and the
    # detector was wrong, so the loop heuristic is gone.
    bt = {p for p in paths if BT_SEG.search(p)}
    submit_files = {p for p, t in src if SUBMIT.search(t)}
    distinct = bool(bt) and bool(submit_files) and bool(submit_files - bt)
    s2 = 2 if distinct else 0
    ev["S2"] = ([f"backtest module: {p}" for p in sorted(bt)[:2]]
                + [f"submits orders: {p}" for p in sorted(submit_files)[:2]]) or \
               [f"backtest_files={len(bt)} submit_files={len(submit_files)} — not distinguishable"]

    # ---- S3: >=2 test files, or committed artifacts under a results dir ----
    tests = [p for p in paths if TEST_FILE.search(p)]
    arts = [p for p in paths if ARTIFACT_DIR.search(p) and ARTIFACT.search(p)]
    s3 = 2 if (len(tests) >= 2 or len(arts) >= 1) else 0
    ev["S3"] = ([f"test: {p}" for p in tests[:3]] + [f"artifact: {p}" for p in arts[:3]]) or \
               [f"{len(tests)} test files, {len(arts)} committed artifacts"]

    # ---- S4: README length + mechanism density + a non-install section ----
    n = len(readme or "")
    mech = grep(readme or "", MECH, "README", limit=6)
    heads = HEADER.findall(readme or "")
    s4 = 2 if (n >= 2000 and len(mech) >= 3 and len(heads) >= 2) else 0
    ev["S4"] = mech[:4] or [f"README {n} chars, {len(mech)} mechanism hits, {len(heads)} non-install sections"]

    # ---- S5: unchanged; pinning and an entry point are already objective ----
    return s1, s2, s3, s4, ev


def main():
    con = db.connect()
    con.execute("ALTER TABLE repos ADD COLUMN s_strict INTEGER") if not any(
        r[1] == "s_strict" for r in con.execute("PRAGMA table_info(repos)")) else None
    con.execute("ALTER TABLE repos ADD COLUMN evidence_strict TEXT") if not any(
        r[1] == "evidence_strict" for r in con.execute("PRAGMA table_info(repos)")) else None
    con.commit()

    rows = con.execute("SELECT * FROM repos WHERE fetched>=1").fetchall()
    print(f"rescoring {len(rows)} repos (cache only, zero API spend)", flush=True)
    changed = 0
    for r in rows:
        fn = r["full_name"]
        try:
            ev0 = json.loads(r["evidence"] or "{}")
        except json.JSONDecodeError:
            ev0 = {}
        branch = (ev0.get("branch") or ["main"])[0]
        tr = gh.core(f"/repos/{fn}/git/trees/{branch}?recursive=1", cache_only=True)
        if not tr or not tr.get("data"):
            continue
        paths = [t["path"] for t in tr["data"].get("tree", []) if t.get("type") == "blob"]
        corpus = []
        for p in paths:
            if not p.lower().endswith((".py", ".ts", ".tsx", ".js", ".rs", ".go", ".ipynb")):
                continue
            t = cache_read(fn, branch, p)
            if t:
                corpus.append((p, t))
        readme = ""
        for nm in ("README.md", "readme.md", "README.rst"):
            t = cache_read(fn, branch, nm)
            if t:
                readme = t
                break

        s1, s2, s3, s4, evs = strict_score(fn, branch, paths, corpus, readme)
        s5 = r["s5"] or 0
        total = s1 + s2 + s3 + s4 + s5
        evs["S5"] = (json.loads(r["evidence"] or "{}").get("S5") or [])
        evs["_scores"] = {"s1": s1, "s2": s2, "s3": s3, "s4": s4, "s5": s5}
        con.execute("UPDATE repos SET s_strict=?, evidence_strict=? WHERE full_name=?",
                    (total, json.dumps(evs), fn))
        changed += 1
    con.commit()

    rows = con.execute("SELECT * FROM repos WHERE fetched>=1 AND s_strict IS NOT NULL").fetchall()
    import collections
    d_lit = collections.Counter(r["s_total"] for r in rows)
    d_str = collections.Counter(r["s_strict"] for r in rows)

    out = os.path.join(gh.ROOT, "reports", "step3b_rescore.md")
    with open(out, "w", encoding="utf-8") as fh:
        fh.write("# STEP 3b — does the YouTube S rubric transfer to code?\n\n")
        fh.write(f"Measured {NOW:%Y-%m-%d} UTC over {len(rows)} deep-fetched repos. "
                 "Zero API spend — this reads only cached files.\n\n")
        fh.write("## Answer: the literal port saturates\n\n")
        fh.write("| S | repos (literal rubric) | repos (strict) |\n|---|---|---|\n")
        for s in range(0, 11):
            if d_lit.get(s) or d_str.get(s):
                fh.write(f"| {s} | {d_lit.get(s,0)} | {d_str.get(s,0)} |\n")
        top_lit = sum(v for k, v in d_lit.items() if k >= 9)
        top_str = sum(v for k, v in d_str.items() if k >= 9)
        fh.write(f"\n**{top_lit}/{len(rows)}** repos score 9 or 10 under the literal rubric; "
                 f"**{top_str}/{len(rows)}** do under the strict one.\n\n")
        fh.write("## Which components fail to transfer, and why\n\n")
        fh.write("| component | literal fire rate | strict fire rate | why it over-fires on code |\n")
        fh.write("|---|---|---|---|\n")
        why = {
            "s1": "`spread` is ordinary orderbook vocabulary — every repo that reads a book "
                  "says it. Strict requires a cost term inside an arithmetic expression.",
            "s2": "matching `backtest`/`live`/`order` against FILE PATHS fires on nearly every "
                  "repo. Strict requires a backtest module plus real order-submission calls in a "
                  "different file.",
            "s3": "transfers well — a tests directory and a committed CSV are unambiguous.",
            "s4": "**the worst transfer.** An LLM-written README hits every mechanism keyword "
                  "while explaining nothing. Keyword presence cannot measure explanation.",
            "s5": "transfers well — pinned versions and an entry point are objective facts.",
        }
        lit_fire = {c: sum(1 for r in rows if (r[c] or 0) > 0) for c in ("s1", "s2", "s3", "s4", "s5")}
        strict_fire = {c: 0 for c in ("s1", "s2", "s3", "s4", "s5")}
        for r in rows:
            try:
                sc = (json.loads(r["evidence_strict"] or "{}")).get("_scores") or {}
            except json.JSONDecodeError:
                continue
            for c in strict_fire:
                if (sc.get(c) or 0) > 0:
                    strict_fire[c] += 1
        for c, label in (("s1", "S1 cost side"), ("s2", "S2 backtest vs live"),
                         ("s3", "S3 tests/results"), ("s4", "S4 mechanism"), ("s5", "S5 runnable")):
            fh.write(f"| {label} | {lit_fire[c]}/{len(rows)} ({100*lit_fire[c]/len(rows):.0f}%) "
                     f"| {strict_fire[c]}/{len(rows)} ({100*strict_fire[c]/len(rows):.0f}%) "
                     f"| {why[c]} |\n")
        fh.write("\n## Ranking under the strict score\n\n")
        fh.write("| S_strict | S_literal | stars | repo |\n|---|---|---|---|\n")
        for r in sorted(rows, key=lambda r: (-(r["s_strict"] or 0), -(r["stars"] or 0)))[:40]:
            fh.write(f"| **{r['s_strict']}** | {r['s_total']} | {r['stars']} "
                     f"| [{r['full_name']}]({r['url']}) |\n")
    print(f"wrote {out}; literal>=9: {top_lit}, strict>=9: {top_str}", flush=True)
    db.log(con, "rescore", f"n={len(rows)} literal_top={top_lit} strict_top={top_str}")


if __name__ == "__main__":
    main()

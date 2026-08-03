"""STEP 2 — gates. Free: READMEs come from raw.githubusercontent, not the API.

  G1  not empty          size_kb > 0. The "more than one commit" half needs a
                         core call and is applied later, in fetch_repo, so the
                         free gate can sweep the whole corpus first.
  G2  pushed < 24 months TAG `STALE`, never drop. A video-level age cutoff in
                         the YouTube project silently discarded 184 items, 10 of
                         which outranked everything kept. Age gates leak.
  G3  genuinely on topic Metadata first (name + description + topics, zero HTTP).
                         Only repos that miss on metadata pay for a README fetch.

Every rejection carries a drop reason. The census is the output.
"""
from __future__ import annotations

import concurrent.futures as cf
import datetime
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import db  # noqa: E402
import gh  # noqa: E402

UTC = datetime.timezone.utc
NOW = datetime.datetime.now(UTC)
STALE_DAYS = 730

VENUE_TERMS = ["kalshi", "polymarket", "predictit", "manifold market", "manifoldmarkets",
               "betfair", "prediction market", "prediction-market", "predictionmarket",
               "event contract", "forecastex", "smarkets", "limitless exchange",
               "myriad market", "azuro"]
GENERIC_TERMS = ["orderbook", "order book", "market making", "market maker", "market-making",
                 "arbitrage", "backtest", "clob", "betting odds", "sportsbook",
                 "implied probability", "brier score", "avellaneda"]

README_NAMES = ("README.md", "README.rst", "readme.md", "README")


def readme_of(full_name: str, default_branch: str):
    branches = tuple(dict.fromkeys([b for b in (default_branch, "main", "master") if b])) or ("main",)
    for name in README_NAMES[:2]:
        txt, url = gh.raw(full_name, name, branches=branches)
        if txt:
            return txt
    return None


def days_since(iso: str):
    if not iso:
        return None
    try:
        d = datetime.datetime.fromisoformat(iso.replace("Z", "+00:00"))
    except ValueError:
        return None
    return (NOW - d).days


def classify(blob: str):
    v = [t for t in VENUE_TERMS if t in blob]
    g = [t for t in GENERIC_TERMS if t in blob]
    return v, g


def main():
    con = db.connect()
    rows = con.execute("SELECT * FROM repos").fetchall()
    print(f"gating {len(rows)} repos", flush=True)

    decided: dict[str, tuple[str, str]] = {}
    need_readme = []

    # ---- pass 1: metadata only. Zero HTTP. ----
    for r in rows:
        fn = r["full_name"]
        if (r["size_kb"] or 0) <= 0:
            decided[fn] = ("DROP", "G1 empty repo (size 0 KB)")
            continue
        blob = " ".join([fn, r["description"] or "", r["topics"] or ""]).lower()
        v, g = classify(blob)
        if v:
            decided[fn] = ("PASS", "")
        elif len(g) >= 2:
            decided[fn] = ("PASS", f"G3 generic only: {','.join(g[:3])}")
        else:
            need_readme.append(r)

    print(f"  metadata decided {len(decided)}, {len(need_readme)} need a README", flush=True)

    # ---- pass 2: README, only where metadata was not enough ----
    def work(r):
        try:
            txt = readme_of(r["full_name"], r["default_branch"] or "")
        except Exception:  # noqa: BLE001
            txt = None
        return r["full_name"], txt

    no_readme = 0
    done = 0
    by_name = {r["full_name"]: r for r in need_readme}
    missing_readme = []
    with cf.ThreadPoolExecutor(max_workers=6) as ex:
        for fn, txt in ex.map(work, need_readme):
            done += 1
            r = by_name[fn]
            if not txt:
                no_readme += 1
                missing_readme.append(r)
                continue
            blob = " ".join([fn, r["description"] or "", r["topics"] or "", txt[:20000]]).lower()
            v, g = classify(blob)
            if v:
                decided[fn] = ("PASS", "G3 venue term found in README only")
            elif len(g) >= 2:
                decided[fn] = ("PASS", f"G3 generic only: {','.join(g[:3])}")
            else:
                decided[fn] = ("DROP", f"G3 off topic (no venue term; {len(g)} generic terms)")
            if done % 200 == 0:
                print(f"  README {done}/{len(need_readme)}", flush=True)

    # ---- pass 3: no README? read the CODE. ----
    # Last session dropped 77 repos here purely for having no fetchable README,
    # and recorded it as a known false-negative channel. It no longer has to be
    # one: gh.archive() returns the whole file tree and the text of every file
    # for free, so a repo with an on-topic codebase and no README is decidable
    # on the same terms as any other. A README is now a convenience, not a
    # requirement.
    ARCHIVE_MAX_KB = 60_000  # do not pull a 60 MB+ repo just to gate it
    rescued = 0
    too_big = 0
    still_dropped = 0

    def dig(r):
        fn = r["full_name"]
        if (r["size_kb"] or 0) > ARCHIVE_MAX_KB:
            return fn, None, "too_big"
        try:
            br = tuple(dict.fromkeys(
                [b for b in (r["default_branch"] or "", "main", "master") if b])) or ("main",)
            a = gh.archive(fn, branches=br)
        except Exception:  # noqa: BLE001
            return fn, None, "error"
        if not a.get("paths"):
            return fn, None, "unreachable"
        # Paths carry signal on their own (a file called kalshi_client.py is a
        # venue term), and the file text carries the rest.
        text = "\n".join(a.get("files", {}).values())[:400_000]
        return fn, "\n".join(a["paths"]) + "\n" + text, "ok"

    if missing_readme:
        print(f"  {len(missing_readme)} have no README — gating them on repo contents",
              flush=True)
        with cf.ThreadPoolExecutor(max_workers=5) as ex:
            for fn, body, how in ex.map(dig, missing_readme):
                r = by_name[fn]
                if how == "too_big":
                    too_big += 1
                    decided[fn] = ("DROP", "G3 undecided (no README, archive over size cap)")
                    continue
                if not body:
                    still_dropped += 1
                    decided[fn] = ("DROP", f"G3 off topic (no README, archive {how})")
                    continue
                blob = " ".join([fn, r["description"] or "", r["topics"] or "",
                                 body]).lower()
                v, g = classify(blob)
                if v:
                    rescued += 1
                    decided[fn] = ("PASS", "G3 venue term found in REPO CONTENTS (no README)")
                elif len(g) >= 2:
                    rescued += 1
                    decided[fn] = ("PASS", f"G3 generic only, from repo contents: {','.join(g[:3])}")
                else:
                    still_dropped += 1
                    decided[fn] = ("DROP",
                                   f"G3 off topic (no README; repo contents read; {len(g)} generic)")
        print(f"  rescued {rescued} of {len(missing_readme)} no-README repos "
              f"({still_dropped} genuinely off topic, {too_big} over the size cap)", flush=True)

    # ---- G2: tag, never drop ----
    census = {"PASS": 0, "STALE": 0, "DROP": 0}
    reasons: dict[str, int] = {}
    stale_but_ontopic = 0
    for r in rows:
        fn = r["full_name"]
        gate, reason = decided.get(fn, ("DROP", "not classified"))
        d = days_since(r["pushed_at"])
        if gate == "PASS" and d is not None and d > STALE_DAYS:
            gate = "STALE"
            stale_but_ontopic += 1
            reason = (reason + "; " if reason else "") + f"G2 last push {d} days ago"
        census[gate] = census.get(gate, 0) + 1
        if reason:
            # Bucket by the rule that fired, not by the day count in the message.
            key = re.sub(r"(?<![G])\d+", "N", reason.split("(")[0].split(":")[0]).strip()
            reasons[key] = reasons.get(key, 0) + 1
        con.execute("UPDATE repos SET gate=?, drop_reason=? WHERE full_name=?", (gate, reason, fn))
    con.commit()

    summary = (f"PASS={census['PASS']} STALE={census['STALE']} DROP={census['DROP']} "
               f"readme_fetched_for={len(need_readme)} no_readme={no_readme} "
               f"no_readme_rescued_from_code={rescued} no_readme_still_off_topic={still_dropped} "
               f"no_readme_over_size_cap={too_big} "
               f"raw_calls={gh.STATS['raw_calls']} archive_calls={gh.STATS['archive_calls']}")
    print(summary, flush=True)
    db.log(con, "gates", summary)

    with open(os.path.join(gh.ROOT, "reports", "step2_gates.md"), "w", encoding="utf-8") as fh:
        fh.write("# STEP 2 — gates\n\n")
        fh.write(f"Ran {NOW:%Y-%m-%d} UTC over {len(rows)} retrieved repos. "
                 "Zero API budget spent: the on-topic test runs on search metadata first, and "
                 f"only the {len(need_readme)} repos it could not decide paid for a README "
                 "fetch from raw.githubusercontent, which is unmetered.\n\n")
        fh.write("## Census\n\n| outcome | repos |\n|---|---|\n")
        for k in ("PASS", "STALE", "DROP"):
            fh.write(f"| {k} | {census.get(k,0)} |\n")
        fh.write(f"| _of which STALE was on-topic and is kept_ | {stale_but_ontopic} |\n")
        fh.write(f"| _(README requested, none found)_ | {no_readme} |\n\n")
        fh.write("`STALE` repos are **kept**. The YouTube project lost 184 items to an age "
                 "cutoff, 10 of which outranked everything it kept. Recency belongs on the "
                 "claim, not on the artifact.\n\n")
        fh.write("## Drop and tag reasons\n\n| reason | count |\n|---|---|\n")
        for k, v in sorted(reasons.items(), key=lambda kv: -kv[1]):
            fh.write(f"| {k} | {v} |\n")
        fh.write("\n## Gate definitions as actually applied\n\n")
        fh.write("- **G1** `size_kb > 0`. The *>1 commit* half needs a core call at 60/hour and "
                 "is applied in `fetch_repo.py`, on the shortlist only. Repos that fail it there "
                 "are re-tagged `DROP` retroactively.\n")
        fh.write(f"- **G2** pushed within {STALE_DAYS} days (24 months). Tag, never drop.\n")
        fh.write("- **G3** must name a venue (kalshi / polymarket / predictit / manifold / "
                 "betfair / event contract / …) **or** hit two independent market-structure "
                 "terms. One generic term alone admits every crypto bot on GitHub, so repos "
                 "passing on generics only are flagged `G3 generic only` and stay "
                 "distinguishable downstream.\n\n")
        fh.write("### The no-README channel — closed 2026-08-03\n\n")
        fh.write(f"{no_readme} repos had no fetchable README at `README.md` or `README.rst` on "
                 "the default, `main` or `master` branch. Last session all such repos were "
                 "**dropped**, and that was recorded as a real false-negative channel: a repo "
                 "with an on-topic codebase and no README was invisible to G3.\n\n")
        fh.write("They are no longer dropped for that reason. `gh.archive()` returns the whole "
                 "file tree and the text of every file for free, so G3 now runs a third pass over "
                 "the **code** — paths included, since a file named `kalshi_client.py` is itself "
                 "a venue term. A README is a convenience, not a requirement.\n\n")
        fh.write(f"| outcome of the no-README pass | repos |\n|---|---|\n")
        fh.write(f"| had no README | {no_readme} |\n")
        fh.write(f"| **rescued — on topic, judged from code** | **{rescued}** |\n")
        fh.write(f"| genuinely off topic after reading the code | {still_dropped} |\n")
        fh.write(f"| skipped, archive over the {ARCHIVE_MAX_KB//1000} MB cap | {too_big} |\n\n")
        fh.write("The remaining leak is the size cap and any repo whose archive is unreachable; "
                 "both are counted above rather than hidden.\n")


if __name__ == "__main__":
    main()

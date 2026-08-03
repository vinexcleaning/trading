"""STEP 1 — retrieval. Free. Six axes, provenance kept per repo.

  F1        beginner repo search
  F2        insider repo search
  F2_CODE   sourcegraph code search (substitute; GitHub's own 401s)
  SEED      forks of Jon-Becker/prediction-market-analysis
  LIB_FORK  forks of the Kalshi/Polymarket client libraries
  TOPIC     GitHub topic search

Deduplicated by full_name. Nothing is ever cloned. Every response is cached.
"""
from __future__ import annotations

import os
import re
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import db  # noqa: E402
import gh  # noqa: E402
import queries as Q  # noqa: E402

FOUND: dict[str, dict] = {}


def _record(item: dict, family: str, query: str):
    """item is a GitHub repo object from search or from /forks."""
    fn = item.get("full_name")
    if not fn:
        return
    rec = FOUND.setdefault(fn, {
        "full_name": fn,
        "url": item.get("html_url") or f"https://github.com/{fn}",
        "description": item.get("description") or "",
        "stars": item.get("stargazers_count") or 0,
        "forks": item.get("forks_count") or 0,
        "size_kb": item.get("size") or 0,
        "language": item.get("language") or "",
        "license": ((item.get("license") or {}) or {}).get("spdx_id") or "",
        "created_at": item.get("created_at") or "",
        "pushed_at": item.get("pushed_at") or "",
        "open_issues": item.get("open_issues_count") or 0,
        "is_fork": 1 if item.get("fork") else 0,
        "is_archived": 1 if item.get("archived") else 0,
        "topics": ",".join(item.get("topics") or []),
        "default_branch": item.get("default_branch") or "",
        "families": set(),
        "queries": set(),
    })
    # A later, richer sighting fills blanks left by a thinner one.
    for k in ("description", "language", "created_at", "pushed_at", "default_branch"):
        if not rec[k] and item.get(k.replace("size_kb", "size")):
            rec[k] = item.get(k) or rec[k]
    rec["families"].add(family)
    rec["queries"].add(query)


def repo_search(term: str, family: str, pages: int = 2):
    got = 0
    for page in range(1, pages + 1):
        res = gh.search("repositories", term, per_page=100, page=page)
        items = res.get("items") or []
        for it in items:
            _record(it, family, term)
        got += len(items)
        print(f"  [{family}] {term!r} p{page}: {len(items)} (total_count={res.get('total_count')})", flush=True)
        if len(items) < 100:
            break
    return got


def topic_search(topic: str):
    return repo_search(f"topic:{topic}", "TOPIC", pages=2)


SG_REPO_RE = re.compile(r"^github\.com/([^/]+/[^/]+)$")


def code_search(term: str):
    """Sourcegraph substitute. Yields full_names only; metadata is filled in by a
    follow-up repo search so we never spend core on it."""
    hits = gh.sourcegraph(f'"{term}"', count=40)
    names = []
    for h in hits:
        m = SG_REPO_RE.match(h.get("repository", ""))
        if m:
            names.append((m.group(1), h.get("path", "")))
    uniq = {}
    for fn, path in names:
        uniq.setdefault(fn, path)
    print(f"  [F2_CODE] {term!r}: {len(uniq)} repos", flush=True)
    return uniq


def hydrate_code_hits(pending: dict[str, str]):
    """Turn bare full_names into repo records without spending core calls.

    Repo search with `repo:owner/name` costs one *search* call (600/hour) instead
    of one *core* call (60/hour). Batch as many as the query length allows.
    """
    todo = [fn for fn in pending if fn not in FOUND]
    batch, batches = [], []
    for fn in todo:
        batch.append(fn)
        if len(batch) == 5:
            batches.append(batch)
            batch = []
    if batch:
        batches.append(batch)
    for b in batches:
        q = " ".join(f"repo:{fn}" for fn in b)
        res = gh.search("repositories", q, per_page=100)
        for it in res.get("items") or []:
            _record(it, "F2_CODE", "sourcegraph:" + pending.get(it["full_name"], ""))
        got = {it["full_name"] for it in (res.get("items") or [])}
        for fn in b:
            if fn not in got:
                # Repo is gone, renamed, or not indexed by search. Record the
                # miss rather than dropping it silently.
                FOUND.setdefault(fn, {
                    "full_name": fn, "url": f"https://github.com/{fn}", "description": "",
                    "stars": 0, "forks": 0, "size_kb": 0, "language": "", "license": "",
                    "created_at": "", "pushed_at": "", "open_issues": 0, "is_fork": 0,
                    "is_archived": 0, "topics": "", "default_branch": "",
                    "families": set(), "queries": set(),
                })
                FOUND[fn]["families"].add("F2_CODE")
                FOUND[fn]["queries"].add("sourcegraph:unhydrated")


def forks_of(full_name: str, family: str, max_pages: int = 3):
    """Costs core calls. The seed repo's forks are worth them.

    Skipped outright when core is exhausted and there is no token: one hour of
    sleeping per page is not worth a fork list, and the free axes have already
    been written to the database by the time this runs.
    """
    if not gh.TOKEN and (gh.core_remaining() or 0) <= 1:
        print(f"  [{family}] SKIPPED {full_name} — no core budget, no token", flush=True)
        return 0
    total = 0
    for page in range(1, max_pages + 1):
        r = gh.core(f"/repos/{full_name}/forks?per_page=100&page={page}&sort=stargazers")
        if not r or r.get("_status") != 200 or not r.get("data"):
            break
        items = r["data"]
        for it in items:
            _record(it, family, f"fork_of:{full_name}")
        total += len(items)
        print(f"  [{family}] forks of {full_name} p{page}: {len(items)}", flush=True)
        if len(items) < 100:
            break
    return total


def write(con):
    """Upsert everything found so far. Idempotent, so it is safe to call more
    than once in a run — which is the point: the free axes are persisted before
    the core-spending ones get a chance to stall."""
    for fn, r in FOUND.items():
        con.execute(
            """INSERT INTO repos (full_name,url,description,stars,forks,size_kb,language,
                 license,created_at,pushed_at,open_issues,is_fork,is_archived,topics,
                 default_branch,families,queries)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
               ON CONFLICT(full_name) DO UPDATE SET
                 families=excluded.families, queries=excluded.queries,
                 stars=excluded.stars, pushed_at=excluded.pushed_at""",
            (r["full_name"], r["url"], r["description"], r["stars"], r["forks"], r["size_kb"],
             r["language"], r["license"], r["created_at"], r["pushed_at"], r["open_issues"],
             r["is_fork"], r["is_archived"], r["topics"], r["default_branch"],
             ",".join(sorted(r["families"])), " | ".join(sorted(r["queries"]))[:2000]),
        )
    con.commit()


def main():
    con = db.connect()
    t0 = time.time()

    print("== F1 beginner ==", flush=True)
    for term in Q.F1_BEGINNER:
        repo_search(term, "F1")
    f1_names = set(FOUND)

    print("== F2 insider ==", flush=True)
    for term in Q.F2_INSIDER:
        repo_search(term, "F2")
    f2_names = {fn for fn, r in FOUND.items() if "F2" in r["families"]}

    print("== TOPIC ==", flush=True)
    for t in Q.TOPICS:
        topic_search(t)

    print("== F2_CODE (sourcegraph substitute) ==", flush=True)
    code_hits: dict[str, str] = {}
    for term in Q.F2_CODE:
        code_hits.update(code_search(term))
    hydrate_code_hits(code_hits)
    code_names = set(code_hits)

    # Everything above this line is free (search + sourcegraph). Everything
    # below spends core. Write what we have BEFORE touching core, so that a
    # core stall or an interrupted fork pass cannot discard an entire retrieval
    # run — the previous version wrote only at the very end.
    write(con)
    print(f"-- wrote {len(FOUND)} repos from the free axes --", flush=True)

    left = gh.core_budget()
    print(f"== core budget before the fork axes: {left} ==", flush=True)

    print("== SEED forks ==", flush=True)
    for r in Q.SEED_REPOS:
        if gh.TOKEN or (left or 0) > 1:
            _seed = gh.core(f"/repos/{r}")
            if _seed and _seed.get("data"):
                _record(_seed["data"], "SEED", "seed")
        forks_of(r, "SEED", max_pages=2)

    print("== CLIENT LIB forks ==", flush=True)
    for lib in Q.CLIENT_LIBS:
        forks_of(lib, "LIB_FORK", max_pages=1)

    # ---- write ----
    write(con)

    # ---- the disjointness measurement ----
    inter = len(f1_names & f2_names)
    union = len(f1_names | f2_names)
    jac = inter / union if union else 0.0
    code_only = len(code_names - f1_names - f2_names)

    summary = (
        f"repos={len(FOUND)} F1={len(f1_names)} F2={len(f2_names)} "
        f"shared={inter} jaccard={jac:.3f} code_hits={len(code_names)} "
        f"code_exclusive={code_only} core_calls={gh.STATS['core_calls']} "
        f"search_calls={gh.STATS['search_calls']} sg_calls={gh.STATS['sg_calls']} "
        f"cache_hits={gh.STATS['cache_hits']} secs={time.time()-t0:.0f}"
    )
    print("\n" + summary, flush=True)
    db.log(con, "retrieval", summary)

    with open(os.path.join(gh.ROOT, "reports", "step1_retrieval.md"), "w", encoding="utf-8") as fh:
        fh.write("# STEP 1 — retrieval\n\n")
        fh.write(f"Unique repos: **{len(FOUND)}**. No repo was cloned. "
                 f"API spend: {gh.STATS['core_calls']} core, {gh.STATS['search_calls']} search, "
                 f"{gh.STATS['sg_calls']} sourcegraph.\n\n")
        fh.write("## Family disjointness — the premise under test\n\n")
        fh.write(f"| | |\n|---|---|\n")
        fh.write(f"| F1 beginner repos | {len(f1_names)} |\n")
        fh.write(f"| F2 insider repos | {len(f2_names)} |\n")
        fh.write(f"| in both | {inter} |\n")
        fh.write(f"| union | {union} |\n")
        fh.write(f"| **Jaccard** | **{jac:.3f}** |\n")
        fh.write(f"| F2_CODE hits (sourcegraph) | {len(code_names)} |\n")
        fh.write(f"| F2_CODE found by neither F1 nor F2 | {code_only} |\n\n")
        fh.write("YouTube measured Jaccard 0.037 over 446 videos. "
                 "The comparison is recorded, not assumed to hold.\n\n")
        fh.write("## Per-axis yield\n\n| family | repos |\n|---|---|\n")
        byfam: dict[str, int] = {}
        for r in FOUND.values():
            for f in r["families"]:
                byfam[f] = byfam.get(f, 0) + 1
        for f, n in sorted(byfam.items(), key=lambda kv: -kv[1]):
            fh.write(f"| {f} | {n} |\n")
    print("wrote reports/step1_retrieval.md", flush=True)


if __name__ == "__main__":
    main()

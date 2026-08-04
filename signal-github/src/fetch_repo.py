"""STEP 3a — deep fetch.

**As of 2026-08-03 the cheap level spends NO core budget at all.** It used to
cost one core call per repo for the git tree, which rationed the whole project
to 60 repos/hour. `gh.archive()` now pulls the complete file tree *and the
contents of every text file* from codeload in a single unmetered request.

Two consequences beyond the speed:

  - The source corpus is no longer rationed. It used to be the 30 largest files
    up to 400 KB, because each file was a separate HTTP request. It is now every
    text file in the repo. S1 (cost side in source) and S2 (a live order path)
    were both measured over that truncated 30-file window and are now measured
    over the whole repository.
  - A repo with no README is no longer invisible. 77 repos were dropped last
    session for having no fetchable README; gating can now read their code.

`level='full'` still spends core on commits/contributors/first-commit, which
have no free substitute — but it degrades to `gh.commits_atom()` (free, last ~20
commits) when core is exhausted, instead of stalling for an hour.

Resumable: `fetched>=1` repos are skipped at the cheap level. Nothing is cloned.
"""
from __future__ import annotations

import base64
import datetime
import json
import os
import re
import sqlite3
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import db  # noqa: E402
import gh  # noqa: E402

UTC = datetime.timezone.utc
NOW = datetime.datetime.now(UTC)

SRC_EXT = (".py", ".ts", ".tsx", ".js", ".rs", ".go", ".java", ".rb", ".ipynb",
           ".sol", ".cs", ".cpp", ".sh", ".yaml", ".yml", ".toml", ".cfg")
# These used to be 30 files / 400 KB because every file was its own HTTP
# request. The archive transport delivers them all in one, so the only reason
# for a cap now is to keep a vendored monorepo from dominating the grep.
MAX_SRC_FILES = 400
MAX_SRC_BYTES = 4_000_000

# Set by --skip-issues. See the closed-issues block in fetch_one().
SKIP_ISSUES = False

COST_RE = re.compile(r"\b(fee|fees|slippage|spread|commission|taker|maker|"
                     r"transaction_cost|trading_cost|gas_cost)\b", re.I)
BACKTEST_RE = re.compile(r"\b(backtest|back_test|walk[_ -]?forward|simulate|simulation|"
                         r"replay|historical)\b", re.I)
LIVE_RE = re.compile(r"\b(place_order|post_order|create_order|submit_order|live_trade|"
                     r"paper_trade|execute_trade|dry_run|ClobClient|KalshiHttpClient)\b")


def last_page_from_link(link: str):
    m = re.search(r'[?&]page=(\d+)>; rel="last"', link or "")
    return int(m.group(1)) if m else None


def tree_of(full_name: str, branch: str):
    for b in [x for x in (branch, "main", "master") if x]:
        r = gh.core(f"/repos/{full_name}/git/trees/{b}?recursive=1")
        if r and r.get("_status") == 200 and r.get("data"):
            return r["data"].get("tree") or [], b
    return [], branch


def grep_lines(text: str, rx: re.Pattern, path: str, limit: int = 4):
    out = []
    for n, line in enumerate(text.splitlines(), 1):
        if rx.search(line):
            snippet = line.strip()[:110]
            out.append(f"{path}:{n}  {snippet}")
            if len(out) >= limit:
                break
    return out


def fetch_one(con, row, level: str = "tree"):
    """level='tree'  — 1 core call. Enough for the whole S score. 60 repos/hour.
       level='full'  — 4 core calls. Adds the credibility axis. 15 repos/hour.

    Substance is what ranking needs, so the cheap level runs wide and the
    expensive one runs only on the shortlist that the cheap level produces.
    """
    fn = row["full_name"]
    branch = row["default_branch"] or "main"
    ev: dict[str, list] = {}
    commits, last_sha, last_msg, last_date = row["commits"], "", "", ""
    contributors, first_date, span_days = row["contributors"], "", row["span_days"]

    if level == "full" and gh.core_remaining() == 0 and not gh.TOKEN:
        # Core is exhausted and there is no token. Rather than sleep an hour per
        # repo, take what the free atom feed gives: recency, cadence and the last
        # commit message. It cannot give a total commit count, so `commits` stays
        # NULL and `trust_me_bro` stays undecided — which is the honest result,
        # not a guess. The row is left at level 1 so a later run with core
        # available upgrades it.
        at = gh.commits_atom(fn, branches=(branch, "main", "master"))
        if at.get("dates"):
            last_date = at["dates"][0]
            last_msg = (at["titles"][0] if at.get("titles") else "").strip()[:200]
            ev_atom = f"atom: {len(at['dates'])} recent commits, newest {last_date}"
        else:
            ev_atom = "atom: unavailable"
        con.execute("UPDATE repos SET notes=COALESCE(notes,'')||? WHERE full_name=?",
                    (f" | credibility degraded to atom feed (no core, no token): {ev_atom}", fn))
        level = "tree"  # score it, but do not claim credibility metrics

    if level == "full":
        # --- core: commits (count via Link, plus the last commit itself) ---
        c = gh.core(f"/repos/{fn}/commits?per_page=1")
        if c and c.get("_status") == 200 and c.get("data"):
            commits = last_page_from_link(c.get("_link", "")) or len(c["data"])
            d0 = c["data"][0]
            last_sha = (d0.get("sha") or "")[:10]
            last_msg = ((d0.get("commit") or {}).get("message") or "").splitlines()[0][:200]
            last_date = ((d0.get("commit") or {}).get("committer") or {}).get("date") or ""
        elif c and c.get("_status") == 409:
            commits = 0  # empty repository

        # --- core: contributors ---
        k = gh.core(f"/repos/{fn}/contributors?per_page=1&anon=1")
        if k and k.get("_status") == 200:
            contributors = last_page_from_link(k.get("_link", "")) or len(k.get("data") or [])

        # --- core: first commit, for a real span (not repo created_at) ---
        if commits and commits > 1:
            f = gh.core(f"/repos/{fn}/commits?per_page=1&page={commits}")
            if f and f.get("_status") == 200 and f.get("data"):
                first_date = ((f["data"][0].get("commit") or {}).get("committer") or {}).get("date") or ""
        if first_date and last_date:
            try:
                a = datetime.datetime.fromisoformat(first_date.replace("Z", "+00:00"))
                b = datetime.datetime.fromisoformat(last_date.replace("Z", "+00:00"))
                span_days = (b - a).days
            except ValueError:
                pass

    # --- archive: the whole repo, free. Replaces the git-tree core call. ---
    arch = gh.archive(fn, branches=tuple(x for x in (branch, "main", "master") if x))
    used_branch = arch.get("branch") or branch
    paths = arch.get("paths") or []
    contents: dict[str, str] = arch.get("files") or {}

    if not paths:
        # Fall back to the core tree once, in case codeload is the thing that is
        # broken rather than the repo. Paths only — no contents — so the score
        # from this path is weaker, and `notes` records that.
        tree, used_branch = tree_of(fn, branch)
        paths = [t["path"] for t in tree if t.get("type") == "blob"]
        sizes = {t["path"]: t.get("size", 0) for t in tree if t.get("type") == "blob"}
    else:
        sizes = {p: len(contents.get(p, "")) for p in paths}

    # A repo with real bytes on disk MUST have files. Getting none back from
    # BOTH transports means the fetch failed, not that the repo is empty.
    # Marking it fetched anyway used to poison the row: excluded from retry
    # forever AND counted in the "scored" total with a NULL score. 266 rows were
    # corrupted this way before it was caught. -2 means "retryable failure".
    if not paths and (row["size_kb"] or 0) > 0:
        con.execute("UPDATE repos SET fetched=-2, notes=? WHERE full_name=?",
                    (f"archive+tree both returned nothing for a {row['size_kb']} KB repo "
                     f"(branch {branch!r}, archive status {arch.get('status')}) — retryable", fn))
        con.commit()
        print(f"  [{level}] {fn:48s} FETCH FAILED, will retry  "
              f"(archive {arch.get('status')})", flush=True)
        return

    # --- search: closed issues ---
    # This one call is the pacing bottleneck of the whole credibility pass:
    # search is 30/min even authenticated, so it costs ~2.2s per repo against
    # ~1s for all three core calls combined. Over 2,300 repos that is 3 hours
    # versus 40 minutes.
    #
    # `closed_issues` is NOT used by `trust_me_bro` (claims AND commits<10 AND
    # no artifact) nor by any correlation reported so far. So it is skippable,
    # and skipping it is recorded by leaving the column NULL rather than 0 —
    # "not measured" must not become "measured as none".
    closed_issues = row["closed_issues"]
    if level == "full" and not SKIP_ISSUES:
        ci = gh.search("issues", f"repo:{fn} is:issue is:closed", per_page=1)
        closed_issues = ci.get("total_count")

    def read_file(p: str):
        """Contents from the archive if we have it, else one free raw fetch."""
        if p in contents:
            return contents[p]
        txt, _u = gh.raw(fn, p, branches=(used_branch, "main", "master"))
        return txt

    # --- free: README. Case-insensitive, any extension, top level only. ---
    readme = ""
    readme_path = ""
    for p in paths:
        if "/" in p:
            continue
        if os.path.splitext(p)[0].lower() == "readme":
            txt = read_file(p)
            if txt:
                readme, readme_path = txt, p
                break
    if not readme:
        for name in ("README.md", "readme.md", "README.rst", "README.txt", "README"):
            txt, _u = gh.raw(fn, name, branches=(used_branch, "main", "master"))
            if txt:
                readme, readme_path = txt, name
                break

    # --- free: source files. Every one of them, not the largest 30. ---
    src = [p for p in paths if p.lower().endswith(SRC_EXT)
           and not any(seg in p.lower() for seg in
                       ("node_modules/", "/vendor/", "site-packages", "/dist/", "/.venv/"))]
    src.sort(key=lambda p: -sizes.get(p, 0))
    budget = MAX_SRC_BYTES
    corpus: list[tuple[str, str]] = []
    for p in src[:MAX_SRC_FILES]:
        if budget <= 0:
            break
        txt = read_file(p)
        if txt:
            corpus.append((p, txt))
            budget -= len(txt)

    # ---------- S1: cost side, in SOURCE, not just README ----------
    s1_ev = []
    for p, txt in corpus:
        s1_ev += grep_lines(txt, COST_RE, p, limit=2)
        if len(s1_ev) >= 6:
            break
    s1 = 3 if s1_ev else 0

    # ---------- S2: backtest AND live path, distinguishable ----------
    bt_paths = [p for p in paths if BACKTEST_RE.search(p)]
    live_paths = [p for p in paths if re.search(r"\b(live|trade|trading|execut|order|bot|paper)",
                                                p, re.I)]
    bt_code = [e for p, t in corpus for e in grep_lines(t, BACKTEST_RE, p, limit=1)][:3]
    live_code = [e for p, t in corpus for e in grep_lines(t, LIVE_RE, p, limit=1)][:3]
    has_backtest = bool(bt_paths or bt_code)
    has_live = bool(live_code) or bool([p for p in live_paths if "backtest" not in p.lower()])
    s2 = 2 if (has_backtest and has_live) else 0
    s2_ev = ([f"backtest: {p}" for p in bt_paths[:3]] + bt_code[:2]
             + [f"live: {p}" for p in live_paths[:3]] + live_code[:2])

    # ---------- S3: tests, or a results dir with committed output ----------
    test_paths = [p for p in paths
                  if re.search(r"(^|/)(tests?|spec)/|(^|/)test_[^/]+\.(py|js|ts)$|"
                               r"[^/]+\.(test|spec)\.(js|ts|tsx)$", p, re.I)]
    result_paths = [p for p in paths
                    if re.search(r"(^|/)(results?|output|outputs|reports?|figures?|plots?|"
                                 r"backtest_results|artifacts)/", p, re.I)
                    and p.lower().endswith((".csv", ".json", ".png", ".jpg", ".svg", ".md",
                                            ".parquet", ".txt", ".html"))]
    has_tests = bool(test_paths)
    s3 = 2 if (test_paths or result_paths) else 0
    s3_ev = [f"test: {p}" for p in test_paths[:3]] + [f"result: {p}" for p in result_paths[:3]]

    # ---------- S4: README explains mechanism, not just installation ----------
    mech_rx = re.compile(r"\b(strateg|edge|mechanism|how it works|why |assumption|"
                         r"adverse selection|inventory|expected value|hypothesis|"
                         r"model|signal|thesis|risk)\b", re.I)
    install_only_rx = re.compile(r"\b(pip install|npm install|clone the repo|getting started|"
                                 r"installation)\b", re.I)
    mech_ev = grep_lines(readme, mech_rx, "README", limit=4) if readme else []
    body_len = len(readme or "")
    s4 = 2 if (len(mech_ev) >= 2 and body_len > 1200) else 0
    s4_ev = mech_ev
    if readme and install_only_rx.search(readme) and s4 == 0:
        s4_ev.append("README: install instructions only, no mechanism")

    # ---------- S5: runnable — pinned deps + obvious entry point ----------
    dep_files = [p for p in paths if os.path.basename(p).lower() in
                 ("requirements.txt", "pyproject.toml", "package.json", "cargo.toml",
                  "poetry.lock", "pipfile", "go.mod", "environment.yml", "uv.lock")]
    pinned = []
    for p in dep_files[:4]:
        txt = read_file(p)
        if txt and re.search(r"[=~^><]=?\s*\d+\.\d+|\"\^?\d+\.\d+", txt):
            pinned.append(f"pinned: {p}")
    entry = [p for p in paths if os.path.basename(p).lower() in
             ("main.py", "run.py", "app.py", "cli.py", "__main__.py", "bot.py", "makefile",
              "dockerfile", "docker-compose.yml", "index.ts", "index.js", "main.ts", "main.go",
              "main.rs")]
    s5 = 1 if (pinned and entry) else 0
    s5_ev = pinned[:2] + [f"entry: {p}" for p in entry[:3]]

    ev = {"S1": s1_ev[:6], "S2": s2_ev[:8], "S3": s3_ev[:6], "S4": s4_ev[:5], "S5": s5_ev[:5],
          "commit": [f"last {last_sha}: {last_msg}"] if last_sha else [],
          "branch": [used_branch]}

    # A README that shows results with almost no history is the GitHub
    # equivalent of "trust me bro". Detect the shape, do not judge it.
    claim_rx = re.compile(r"(\d{1,3}(\.\d+)?\s?%|\bROI\b|\bP&?L\b|\bsharpe\b|"
                          r"win\s?rate|profit(?:able|s)?|\breturns?\b|\bPnL\b)", re.I)
    # Shield badges are markdown images whose URLs are full of digits and
    # percent-encoding, so they match every claim pattern. They are decoration,
    # not a claim; drop them before grepping.
    badge_rx = re.compile(r"!\[[^\]]*\]\([^)]*\)|<img\s|img\.shields\.io|badge/|"
                          r"^\s*\[!\[|star-history|<a\s+href", re.I)
    readme_claims = "\n".join(
        ln if not badge_rx.search(ln) else "" for ln in (readme or "").splitlines())
    claims = grep_lines(readme_claims, claim_rx, "README", limit=5) if readme else []
    artifact = bool(result_paths) or bool([p for p in paths if p.lower().endswith(
        (".csv", ".parquet")) and re.search(r"result|backtest|trade|pnl|equity", p, re.I)])
    # Only decidable once the commit count is known, so it stays NULL at the
    # cheap level rather than being guessed.
    trust_me_bro = None
    if commits is not None:
        trust_me_bro = 1 if (claims and commits < 10 and not artifact) else 0

    s_total = s1 + s2 + s3 + s4 + s5
    con.execute(
        """UPDATE repos SET commits=?, span_days=?, contributors=?, first_commit=?,
             last_commit_msg=?, last_commit_sha=?, closed_issues=?, tree_files=?,
             s1=?,s2=?,s3=?,s4=?,s5=?, s_total=?, evidence=?, has_backtest=?, has_tests=?,
             has_live_trading=?, claimed_results=?, artifact_behind_claim=?,
             trust_me_bro=?, fetched=? WHERE full_name=?""",
        (commits, span_days, contributors, first_date or row["first_commit"],
         last_msg or row["last_commit_msg"], last_sha or row["last_commit_sha"],
         closed_issues, len(paths), s1, s2, s3, s4, s5, s_total, json.dumps(ev),
         int(has_backtest), int(has_tests), int(has_live),
         " | ".join(c.split("  ", 1)[-1] for c in claims[:3]),
         "yes: " + ", ".join(result_paths[:2]) if artifact else "no",
         trust_me_bro, 2 if level == "full" else 1, fn))

    # G1 second half, applied only once we actually know the commit count.
    if commits is not None and commits <= 1 and row["gate"] != "DROP":
        con.execute("UPDATE repos SET gate='DROP', drop_reason=? WHERE full_name=?",
                    (f"G1 only {commits} commit(s)", fn))
    con.commit()
    print(f"  [{level}] {fn:48s} S={s_total} ({s1}{s2}{s3}{s4}{s5}) c={commits} "
          f"files={len(paths)} core_left={gh.core_remaining()}", flush=True)


def main():
    global SKIP_ISSUES
    level = sys.argv[1] if len(sys.argv) > 1 else "tree"
    limit = int(sys.argv[2]) if len(sys.argv) > 2 else 50
    SKIP_ISSUES = "--skip-issues" in sys.argv
    if SKIP_ISSUES:
        print("skipping the closed-issues search call: ~3x faster, and "
              "closed_issues stays NULL rather than 0", flush=True)
    con = db.connect()
    if level == "full":
        # Credibility pass: only repos the cheap pass already scored well.
        # `fetched>=1`, not `=1`, so the pass is idempotent: re-running after a
        # scorer or extractor fix revisits repos already at level 2 instead of
        # leaving them frozen with values from an older version of the code.
        # Every core call is cached, so a re-run costs nothing.
        rows = con.execute(
            """SELECT r.* FROM repos r WHERE r.fetched>=1 AND r.gate IN ('PASS','STALE')
               ORDER BY r.s_total DESC, r.stars DESC LIMIT ?""", (limit,)).fetchall()
    else:
        # fetched=0 is "never tried"; -2 is "tried and the tree call failed".
        # Both are eligible, so a rate-limited run is resumed rather than lost.
        rows = con.execute(
            """SELECT r.* FROM repos r LEFT JOIN prescreen p ON p.full_name=r.full_name
               WHERE r.fetched IN (0,-2) AND r.gate IN ('PASS','STALE')
               ORDER BY COALESCE(p.score,-99) DESC, r.stars DESC LIMIT ?""", (limit,)).fetchall()
    print(f"deep-fetching {len(rows)} repos at level={level}", flush=True)

    # The cheap level is now network-bound rather than budget-bound, so warm the
    # archive cache in parallel first. Scoring afterwards is pure CPU over files
    # already on disk, and the database writes stay single-threaded.
    if level != "full" and len(rows) > 1:
        import concurrent.futures as cf

        def warm(r):
            try:
                br = tuple(dict.fromkeys(
                    [b for b in (r["default_branch"] or "", "main", "master") if b])) or ("main",)
                a = gh.archive(r["full_name"], branches=br)
                return r["full_name"], a.get("status"), a.get("n_paths") or 0
            except Exception as e:  # noqa: BLE001
                return r["full_name"], f"ERR {type(e).__name__}", 0

        t0 = time.time()
        ok = 0
        with cf.ThreadPoolExecutor(max_workers=8) as ex:
            for i, (fn, st, n) in enumerate(ex.map(warm, rows), 1):
                if st == 200:
                    ok += 1
                if i % 50 == 0:
                    print(f"  warmed {i}/{len(rows)} archives, {ok} ok, "
                          f"{time.time()-t0:.0f}s", flush=True)
        print(f"  archive prefetch: {ok}/{len(rows)} in {time.time()-t0:.0f}s, "
              f"0 core calls", flush=True)

    for row in rows:
        try:
            fetch_one(con, row, level=level)
        except Exception as e:  # noqa: BLE001 - one bad repo must not end the run
            print(f"  !! {row['full_name']}: {type(e).__name__}: {e}", flush=True)
            # -1 is "failed for a reason specific to this repo" and is NOT
            # retried. A locked database or a dropped connection is neither
            # specific nor permanent, so those get -2, which the selector does
            # pick up again.
            transient = isinstance(e, (sqlite3.OperationalError, OSError, TimeoutError))
            code = -2 if transient else -1
            try:
                con.execute("UPDATE repos SET fetched=?, notes=? WHERE full_name=?",
                            (code, f"fetch error ({'retryable' if transient else 'permanent'}): "
                                   f"{type(e).__name__}: {e}", row["full_name"]))
                con.commit()
            except sqlite3.OperationalError:
                pass  # could not even record it; the row stays at 0 and is retried
    db.log(con, "fetch", f"level={level} n={len(rows)} core={gh.STATS['core_calls']} "
                         f"raw={gh.STATS['raw_calls']} search={gh.STATS['search_calls']} "
                         f"cache={gh.STATS['cache_hits']}")
    print("done", gh.STATS, flush=True)


if __name__ == "__main__":
    main()

"""T1 — the cross-platform join, on the corpora that already exist.

Single-platform signal is weak. A tool praised in a YouTube tutorial and
archived by its own maintainer three months later is a finding neither corpus
produces alone, and it is the cheapest real result available in this programme.

Four sources, none of which has ever been joined to another:

  youtube-signal/data/signal.db               87 tools, 29 videos read
  youtube-signal/data/signal_kalshi_edge.db   10 tools,  4 videos read
  signal-github/data/github.db                4,017 repos, 2,260 scored
  signal-github/cache/*.arch.json             ~2.8 GB of whole-repo source

The fourth is the one that makes this more than a name lookup. Every scored
repo's complete source text is on disk, so "does anyone actually build with the
thing this video is selling?" is answerable by counting, not by asking.

Join discipline, inherited from both siblings because both were burned by the
alternative: match on an exact key or on a URL, never on a free-text name
search. Unmatched is reported as unmatched.

    python src/join_corpora.py            # join + report
    python src/join_corpora.py --no-scan  # skip the 2.8 GB corpus scan
"""
from __future__ import annotations

import argparse
import collections
import datetime
import hashlib
import json
import os
import re
import sqlite3
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import db  # noqa: E402
import norm  # noqa: E402

TRADING = os.path.dirname(db.ROOT)
YT_DBS = [
    ("yt_broad", os.path.join(TRADING, "youtube-signal", "data", "signal.db")),
    ("yt_kalshi_edge", os.path.join(TRADING, "youtube-signal", "data",
                                    "signal_kalshi_edge.db")),
]
GH_DB = os.path.join(TRADING, "signal-github", "data", "github.db")
GH_CACHE = os.path.join(TRADING, "signal-github", "cache")

NOW = datetime.datetime.now(datetime.timezone.utc)

# Things that are venues, institutions or ideas. Asking whether the SEC is a
# scam is not a question this system should spend a request on, and counting
# how many repos mention "Polymarket" measures the corpus, not the tool.
# Ported verbatim in spirit from signal-github/src/crossref.py:NOT_SOFTWARE.
NOT_SOFTWARE_KEYS = {
    norm.key(n): why for n, why in {
        "Kalshi": "exchange", "Polymarket": "exchange", "ForecastEx": "exchange",
        "FanDuel": "sportsbook", "PrizePicks": "sportsbook",
        "Citadel Securities": "institution", "Virtu Financial": "institution",
        "Wintermute / Jump Crypto / GSR Markets": "firms",
        "SEC Rule 606 filings": "regulatory filing",
        "SEC net capital rule / FINRA broker-dealer registration": "regulation",
        "Exchange colocation and direct market data feeds": "infrastructure",
        "Avellaneda-Stoikov model (2008)": "academic model, not a package",
        "VPIN (volume-synchronised probability of informed trading)": "academic metric",
        "Kyle's lambda (Kyle 1985)": "academic metric",
        "Gnosis Conditional Token Framework": "on-chain protocol",
        "UMA optimistic oracle": "on-chain protocol",
        "Broker API key": "not a product",
        "Stonehill Forex / NNFX": "trading system, not software",
        "Binance BTC/USDT order book": "venue data",
        "Polygon (data feed)": "chain / vendor, ambiguous name",
    }.items()
}

# Needles that appear in every repo in a Kalshi/Polymarket corpus. Counting them
# measures the corpus, not the tool, so the scan refuses to run them.
BANNED_NEEDLES = {
    "kalshi", "polymarket", "python", "discord", "github", "vercel", "numpy",
    "streamlit", "duckdb", "pydantic", "metamask", "homebrew", "jupyter",
    "tradingview", "openrouter", "hyperliquid", "alpaca", "grok", "claude",
    "claudecode", "binance", "quantconnect", "polygon", "fanduel",
}

# Three sets, and the distinction between the first two is what stops the
# table crying CONTRADICTION at every ordinary fact.
#
#   ADVOCACY      someone is telling you to use it
#   CORROBORATION independent evidence it exists and works — a repo imports it,
#                 its own artifact answers when fetched, a critic uses it
#   AGAINST       evidence it is dead, broken, flagged or condemned
#
# A CONTRADICTION needs ADVOCACY *and* AGAINST. A stale repo that someone
# merely mentioned in passing is not a contradiction, it is a stale repo.
STANCES_ADVOCACY = {"PROMOTED_WITH_INCENTIVE", "RECOMMENDED"}
STANCES_CORROBORATION = {"BUILT_WITH", "ALIVE", "LIVE", "CORROBORATED",
                         "NEUTRAL_USE"}
STANCES_AGAINST = {"ARCHIVED", "STALE", "GONE", "TRUST_ME_BRO", "CRITICISED",
                   "SCAM_ALLEGED", "BROKEN", "PARKED", "MIXED_REPUTATION"}
# Neither. UNUSED means a needle found nothing, which for a hosted service is
# expected and says nothing; QUIET, BLOCKED, THIN, UNKNOWN and API_ROOT_404 are
# all "we could not tell"; POSTED_ON_REDDIT is a count, and a vendor posting
# nine times produces the same number as nine recommendations. A table that
# scores any of these as evidence is lying.
STANCES_NEUTRAL = {"UNUSED", "QUIET", "BLOCKED", "THIN", "UNKNOWN",
                   "API_ROOT_404", "ALIVE_UNKNOWN", "MENTIONED",
                   "POSTED_ON_REDDIT", "NO_FOOTPRINT", "VENDOR_TALK"}


# --------------------------------------------------------------------------
# 1. YouTube side
# --------------------------------------------------------------------------
def load_youtube(con) -> int:
    """Every tool named in either YouTube corpus, with the promoting video's own
    honesty score attached.

    The score matters: "promoted by a video that scored H = -3" is a materially
    different observation from "used in passing by a video that scored H = +6",
    and a reputation table that flattens the two is worth nothing.
    """
    n = 0
    for corpus, path in YT_DBS:
        if not os.path.exists(path):
            print(f"  [{corpus}] MISSING at {path} — skipped")
            continue
        src = sqlite3.connect(path)
        src.row_factory = sqlite3.Row
        rows = src.execute("""
            SELECT t.*, v.title, v.channel_name, v.view_count, v.upload_date,
                   s.s_total, s.h_total, s.b_total, s.verdict
            FROM tools t
            LEFT JOIN videos v ON v.video_id = t.first_seen_video
            LEFT JOIN scores s ON s.video_id = t.first_seen_video
        """).fetchall()
        for r in rows:
            name = r["name"] or ""
            k = norm.key(name)
            if not k:
                continue
            repo = norm.github_repo(r["url"] or "")
            kind = "concept" if k in NOT_SOFTWARE_KEYS else None
            eid = db.upsert_entity(con, k, norm.compact(name), name, kind=kind,
                                   url=r["url"] or None, repo=repo)

            own = (r["is_creators_own"] or "no").lower()
            referral = bool(r["is_referral_link"])
            if own in ("disclosed", "undisclosed") or referral:
                stance = "PROMOTED_WITH_INCENTIVE"
            elif (r["verdict"] or "").endswith("RECOMMEND"):
                stance = "RECOMMENDED"
            else:
                stance = "MENTIONED"

            h = r["h_total"]
            detail = (f"video H={h if h is not None else '?'} "
                      f"S={r['s_total'] if r['s_total'] is not None else '?'} "
                      f"B={r['b_total'] if r['b_total'] is not None else '?'} "
                      f"verdict={r['verdict'] or '?'} "
                      f"own={own} referral={int(referral)} "
                      f"mentions={r['mention_count']}")
            db.add_observation(
                con, eid, "youtube", corpus, r["first_seen_video"] or "", stance,
                strength=float(r["mention_count"] or 1),
                detail=detail,
                evidence=(r["claimed_purpose"] or "")[:300])
            n += 1
        src.close()
        print(f"  [{corpus}] {len(rows)} tool rows")
    con.commit()
    return n


# --------------------------------------------------------------------------
# 2. GitHub side
# --------------------------------------------------------------------------
def gh_alive(row) -> tuple[str, str]:
    """(stance, note) for a repo's liveness. A tool a recent video recommends
    whose repo is archived or two years cold is the exact conflict this exists
    to surface."""
    pushed = row["pushed_at"] or ""
    days = None
    if pushed:
        try:
            days = (NOW - datetime.datetime.fromisoformat(
                pushed.replace("Z", "+00:00"))).days
        except ValueError:
            pass
    if row["is_archived"]:
        return "ARCHIVED", f"archived by its own maintainer; last push {days}d ago"
    if days is None:
        return "ALIVE_UNKNOWN", "no pushed_at recorded"
    if days > 730:
        return "STALE", f"last push {days}d ago (>24 months)"
    if days > 365:
        return "QUIET", f"last push {days}d ago (>12 months)"
    return "ALIVE", f"last push {days}d ago, {row['stars']}*"


def load_github(con) -> tuple[int, dict]:
    """Attach GitHub evidence to entities that already exist from YouTube.

    Deliberately does NOT create an entity per repo. 4,017 repos would drown
    the 97 tools the reputation question is actually about, and a repo nobody
    on any other platform has ever mentioned has nothing to contradict.
    """
    if not os.path.exists(GH_DB):
        print(f"  GH DB MISSING at {GH_DB}")
        return 0, {}
    src = sqlite3.connect(GH_DB)
    src.row_factory = sqlite3.Row
    repos = src.execute("SELECT * FROM repos").fetchall()

    by_full = {}
    by_compact = collections.defaultdict(list)
    by_owner = collections.defaultdict(list)
    for r in repos:
        fn = (r["full_name"] or "")
        if not fn:
            continue
        by_full[fn.lower()] = r
        owner, _, name = fn.partition("/")
        by_owner[owner.lower()].append(r)
        ck = norm.compact(name)
        if len(ck) >= 5:
            by_compact[ck].append(r)
        ckf = norm.compact(fn)
        if len(ckf) >= 5:
            by_compact[ckf].append(r)

    ents = con.execute("SELECT * FROM entities").fetchall()
    matched = 0
    how = collections.Counter()
    for e in ents:
        cands, via = [], ""
        if e["github_repo"] and e["github_repo"].lower() in by_full:
            cands, via = [by_full[e["github_repo"].lower()]], "url"
        elif e["github_repo"]:
            # A URL was given and the corpus has never seen that repo. That is
            # itself evidence — but it is NOT evidence the repo is gone; this
            # corpus covers 3,252 gated repos, not all of GitHub. Recorded as
            # absence, checked live later only if it matters.
            how["url_not_in_corpus"] += 1
            continue
        else:
            ck = e["compact_key"] or ""
            if len(ck) >= 6 and ck in by_compact:
                cands, via = by_compact[ck], "name"
        if not cands:
            continue
        # If a compact key hits many repos it is a generic word, not an
        # identity. Refuse rather than pick one — picking one is exactly the
        # confident-wrong-project failure both siblings recorded.
        if via == "name" and len(cands) > 3:
            how["name_ambiguous"] += 1
            continue

        for r in cands:
            stance, note = gh_alive(r)
            db.add_observation(
                con, e["entity_id"], "github", "signal-github",
                r["full_name"], stance,
                strength=1.0,
                detail=(f"{r['stars']}* forks={r['forks']} "
                        f"s_strict={r['s_strict']} s_adj={r['s_adj']} "
                        f"commits={r['commits']} kind={r['kind']} "
                        f"venue={r['venue_detected']} "
                        f"submits_orders={r['submits_orders']} "
                        f"pm_client={r['pm_client']} | {note}"
                        + ("  ⚠ matched by NAME, not by a URL anyone gave — "
                           "verify this is the same project before acting on it"
                           if via == "name" else "")),
                evidence=(r["description"] or "")[:300])
            if r["trust_me_bro"]:
                db.add_observation(
                    con, e["entity_id"], "github", "signal-github",
                    r["full_name"], "TRUST_ME_BRO", strength=1.0,
                    detail="results claim in README with <10 commits and no artifact",
                    evidence=(r["claimed_results"] or "")[:300])
            if r["pm_client"] and "v1" in str(r["pm_client"]).lower():
                db.add_observation(
                    con, e["entity_id"], "github", "signal-github",
                    r["full_name"], "BROKEN", strength=1.0,
                    detail=f"pm_client={r['pm_client']} — Polymarket CLOB V1, "
                           "archived upstream and unsupported on production since "
                           "V2 went live 28 Apr 2026",
                    evidence="")
            # Deliberately NOT written back to entities.github_repo. A name
            # match is a hypothesis; writing it back would make the next run
            # treat it as a URL the creator gave, and the run after that would
            # report it missing from the corpus. Provenance has to survive
            # re-running or the join stops being idempotent.
            matched += 1
            how[via] += 1

    # The two hand-curated tables signal-github built and never joined to
    # anything. Small, but they are primary observations about data sources.
    for tbl, stance in (("data_sources", "NEUTRAL_USE"), ("dependencies", "BUILT_WITH")):
        try:
            rows = src.execute(f"SELECT * FROM {tbl}").fetchall()
        except sqlite3.OperationalError:
            continue
        for r in rows:
            name = r["name"] or ""
            k = norm.key(name)
            if not k:
                continue
            eid = db.upsert_entity(con, k, norm.compact(name), name,
                                   url=(r["url"] if "url" in r.keys() else None))
            db.add_observation(con, eid, "github", f"signal-github/{tbl}",
                               (r["seen_in"] if "seen_in" in r.keys() else "") or "",
                               stance, detail=(r["note"] or "")[:300],
                               evidence=(r["what_it_is"] if "what_it_is" in r.keys()
                                         else r["covers"] if "covers" in r.keys()
                                         else "") or "")
    src.close()
    con.commit()
    print(f"  matched {matched} entity-repo pairs; {dict(how)}")
    return matched, dict(how)


# --------------------------------------------------------------------------
# 3. The corpus scan — does anyone actually build with it?
# --------------------------------------------------------------------------
def _arch_path(full_name: str, branch: str) -> str:
    url = f"https://codeload.github.com/{full_name}/tar.gz/{branch}"
    return os.path.join(GH_CACHE, hashlib.sha1(url.encode()).hexdigest()[:20]
                        + ".arch.json")


def build_needles(con) -> dict[str, int]:
    """One needle per entity: its domain if it has one, else its compact name.

    Only needles that could plausibly be typed into source code. A needle that
    is a venue name is refused outright — 991 repos import Polymarket, and
    reporting that as corroboration for a Polymarket-branded product would be
    a measurement of the corpus.
    """
    needles = {}
    for e in con.execute("SELECT * FROM entities"):
        if e["key"] in NOT_SOFTWARE_KEYS:
            continue
        cand = None
        # Several products ARE their domain — "polyreplay.dev", "upside.tools",
        # "moondev.com". youtube-signal records the spoken name and, for these,
        # never a URL, so the compact key silently eats the dot and produces
        # `polyreplaydev`, which appears in no source file on earth. Detect the
        # domain shape in the display name itself.
        stripped_name = norm.strip_descriptor(e["display"] or "").strip()
        if re.fullmatch(r"[a-z0-9][a-z0-9.-]*\.[a-z]{2,10}", stripped_name.lower()):
            needles.setdefault(stripped_name.lower(), e["entity_id"])
            continue
        d = norm.domain(e["canonical_url"] or "")
        if d and d not in ("github.com", "docs.polymarket.com", "polymarket.com",
                           "kalshi.com", "docs.kalshi.com"):
            cand = d
        elif e["github_repo"]:
            cand = e["github_repo"].split("/")[1].lower()
        else:
            # A compact key is only an identifier if the name was one. "PolyCop"
            # is something a developer types; "Polymarket Gamma API / Data API"
            # compacts to a 24-character string that appears in no source file
            # anywhere, and reporting it as UNUSED would be an artefact of the
            # needle, not a fact about the tool.
            stripped = norm.strip_descriptor(e["display"] or "")
            ck = e["compact_key"] or ""
            if " " not in stripped and 7 <= len(ck) <= 24:
                cand = ck
        if not cand:
            continue
        c = cand.lower()
        if c in BANNED_NEEDLES or len(c) < 6:
            continue
        needles[c] = e["entity_id"]
    return needles


def scan_corpus(con, needles: dict[str, int], limit: int | None = None):
    """Stream every cached repo archive once, counting needle hits.

    ~2.8 GB on disk. Read once, all needles tested per repo, so the cost is one
    pass regardless of how many tools are being checked.
    """
    if not os.path.isdir(GH_CACHE):
        print("  no signal-github/cache — scan skipped")
        return {}
    src = sqlite3.connect(GH_DB)
    src.row_factory = sqlite3.Row
    # fetched is 1 (archive pulled) or 2 (archive + credibility tier). Both have
    # a cached archive; only using 1 silently dropped the 862 deepest-covered
    # repos in the corpus, which are exactly the ones most likely to import a
    # named library.
    repos = src.execute(
        "SELECT full_name, default_branch FROM repos WHERE fetched IN (1,2)"
    ).fetchall()
    src.close()
    if limit:
        repos = repos[:limit]

    hits: dict[str, set] = {n: set() for n in needles}
    scanned = missing = 0
    t0 = time.time()
    for i, r in enumerate(repos):
        branches = [r["default_branch"] or "main", "main", "master"]
        doc = None
        for br in branches:
            p = _arch_path(r["full_name"], br)
            if os.path.exists(p):
                try:
                    with open(p, "r", encoding="utf-8") as fh:
                        doc = json.load(fh)
                except (json.JSONDecodeError, OSError):
                    doc = None
                if doc and doc.get("status") == 200:
                    break
                doc = None
        if not doc:
            missing += 1
            continue
        blob = ("\n".join(doc.get("paths") or []) + "\n" +
                "\n".join((doc.get("files") or {}).values())).lower()
        for n in needles:
            if n in blob:
                hits[n].add(r["full_name"])
        scanned += 1
        if (i + 1) % 250 == 0:
            print(f"    scanned {i+1}/{len(repos)} "
                  f"({time.time()-t0:.0f}s, {missing} archives absent)", flush=True)

    print(f"  corpus scan: {scanned} repos read, {missing} archives absent, "
          f"{time.time()-t0:.0f}s")
    for n, eid in needles.items():
        repos_hit = sorted(hits[n])
        # corpus/source_id are fixed strings so the UNIQUE key does not change
        # when the corpus grows; the count lives in detail, which is updated.
        stance = "BUILT_WITH" if repos_hit else "UNUSED"
        detail = (f"needle '{n}' appears in {len(repos_hit)} of {scanned} "
                  "whole-repo source archives")
        db.add_observation(con, eid, "github_corpus", "archives", "scan",
                           stance, strength=float(len(repos_hit)),
                           detail=detail,
                           evidence=", ".join(repos_hit[:8]))
        con.execute("""UPDATE observations SET strength=?, detail=?, evidence=?
                       WHERE entity_id=? AND platform='github_corpus'
                         AND stance=?""",
                    (float(len(repos_hit)), detail, ", ".join(repos_hit[:8]),
                     eid, stance))
    con.commit()
    return {n: len(v) for n, v in hits.items()}


# --------------------------------------------------------------------------
# 4. Verdicts
# --------------------------------------------------------------------------
VERDICTS = """
CONTRADICTION    someone ADVOCATES it and another source shows it dead, broken,
                 flagged or condemned. Mere mention is not advocacy.
AGREE_NEGATIVE   evidence against it, and nobody advocating
UNDISCLOSED      advocated with an incentive and corroborated by nobody independent
AGREE_POSITIVE   two or more platforms, independently corroborated, nothing against
SINGLE_SOURCE    exactly one platform has ever mentioned it
NOT_SOFTWARE     an exchange, an institution or an idea; not a thing to verify
"""


def decide(con):
    con.execute("DELETE FROM verdicts")
    for e in con.execute("SELECT * FROM entities"):
        obs = con.execute("SELECT * FROM observations WHERE entity_id=?",
                          (e["entity_id"],)).fetchall()
        plats = {o["platform"] for o in obs}
        stances = [o["stance"] for o in obs]
        advocacy = [s for s in stances if s in STANCES_ADVOCACY]
        against = [s for s in stances if s in STANCES_AGAINST]
        # Corroboration means a source with no incentive to sell it says it is
        # there: a repo imports it, or its own artifact answers when fetched.
        # Vendor copy is the vendor talking and is never corroboration.
        corrob = [o for o in obs if o["stance"] in STANCES_CORROBORATION]
        corroborated = bool(corrob)
        incentive = any("own=undisclosed" in (o["detail"] or "") or
                        "referral=1" in (o["detail"] or "") for o in obs)

        if e["key"] in NOT_SOFTWARE_KEYS:
            v, why = "NOT_SOFTWARE", NOT_SOFTWARE_KEYS[e["key"]]
        elif advocacy and against:
            v = "CONTRADICTION"
            why = (f"advocated ({'/'.join(sorted(set(advocacy)))}) and "
                   f"contradicted ({'/'.join(sorted(set(against)))})")
        elif against and not advocacy:
            v, why = "AGREE_NEGATIVE", "/".join(sorted(set(against)))
        elif incentive and not corroborated:
            v = "UNDISCLOSED"
            why = ("advocated with an incentive and corroborated by no "
                   "independent source in any corpus here")
        elif len(plats) >= 2 and corroborated:
            v, why = "AGREE_POSITIVE", "+".join(sorted(plats))
        else:
            v, why = "SINGLE_SOURCE", "+".join(sorted(plats)) or "none"

        con.execute(
            """INSERT INTO verdicts (entity_id, verdict, n_platforms, promo_score,
                                     critic_score, reason, decided_utc)
               VALUES (?,?,?,?,?,?,?)""",
            (e["entity_id"], v, len(plats), float(len(advocacy)),
             float(len(against)), why, db.now()))
    con.commit()


def report(con, scan_counts):
    out = os.path.join(db.REPORTS, "T1_cross_platform.md")
    rows = con.execute("""
        SELECT e.*, v.verdict, v.n_platforms, v.reason
        FROM entities e JOIN verdicts v ON v.entity_id = e.entity_id
        ORDER BY CASE v.verdict
                   WHEN 'CONTRADICTION' THEN 0 WHEN 'AGREE_NEGATIVE' THEN 1
                   WHEN 'UNDISCLOSED' THEN 2 WHEN 'AGREE_POSITIVE' THEN 3
                   WHEN 'SINGLE_SOURCE' THEN 4 ELSE 5 END,
                 e.display
    """).fetchall()
    counts = collections.Counter(r["verdict"] for r in rows)

    with open(out, "w", encoding="utf-8") as fh:
        fh.write("# T1 — cross-platform tool reputation\n\n")
        fh.write(f"Joined {NOW:%Y-%m-%d} UTC. "
                 "`youtube-signal` (2 corpora) x `signal-github` "
                 "(4,017 repos, 2,260 whole-repo archives).\n\n")
        fh.write("```\n" + VERDICTS.strip() + "\n```\n\n")
        fh.write("| verdict | entities |\n|---|---|\n")
        for k, n in counts.most_common():
            fh.write(f"| {k} | {n} |\n")
        fh.write("\n---\n\n")
        for r in rows:
            if r["verdict"] in ("NOT_SOFTWARE",):
                continue
            obs = con.execute(
                "SELECT * FROM observations WHERE entity_id=? ORDER BY platform",
                (r["entity_id"],)).fetchall()
            fh.write(f"## {r['display']}  —  **{r['verdict']}**\n\n")
            if r["canonical_url"]:
                fh.write(f"`{r['canonical_url']}` ")
            if r["github_repo"]:
                fh.write(f"repo `{r['github_repo']}`")
            fh.write(f"\n\n_{r['reason']}_\n\n")
            fh.write("| platform | source | stance | detail |\n|---|---|---|---|\n")
            for o in obs:
                fh.write(f"| {o['platform']}/{o['corpus']} | `{o['source_id']}` | "
                         f"**{o['stance']}** | {(o['detail'] or '')[:220]} |\n")
            fh.write("\n")
    print(f"\n  wrote {out}")
    return counts


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-scan", action="store_true",
                    help="skip the 2.8 GB whole-repo corpus scan")
    ap.add_argument("--scan-limit", type=int, default=None)
    ap.add_argument("--print-needles", action="store_true",
                    help="show what the corpus scan would search for, then exit")
    ap.add_argument("--decide-only", action="store_true",
                    help="re-run verdicts and the report over existing "
                         "observations; load nothing")
    args = ap.parse_args()

    con = db.connect()
    if args.decide_only:
        decide(con)
        counts = report(con, {})
        for k, v in counts.most_common():
            print(f"    {k:<16} {v}")
        con.close()
        return

    print("YouTube corpora:")
    n_yt = load_youtube(con)
    print("GitHub corpus:")
    n_gh, how = load_github(con)

    if args.print_needles:
        needles = build_needles(con)
        for n, eid in sorted(needles.items()):
            e = con.execute("SELECT display FROM entities WHERE entity_id=?",
                            (eid,)).fetchone()
            print(f"  {n:<28} <- {e['display']}")
        print(f"  {len(needles)} needles")
        con.close()
        return

    scan_counts = {}
    if not args.no_scan:
        needles = build_needles(con)
        print(f"Corpus scan: {len(needles)} needles")
        scan_counts = scan_corpus(con, needles, limit=args.scan_limit)

    decide(con)
    counts = report(con, scan_counts)

    n_ent = con.execute("SELECT COUNT(*) c FROM entities").fetchone()["c"]
    n_obs = con.execute("SELECT COUNT(*) c FROM observations").fetchone()["c"]
    print(f"\n  entities {n_ent} | observations {n_obs} | "
          f"yt rows {n_yt} | gh pairs {n_gh}")
    for k, v in counts.most_common():
        print(f"    {k:<16} {v}")
    db.log(con, "join_corpora",
           f"entities={n_ent} obs={n_obs} " +
           " ".join(f"{k}={v}" for k, v in counts.most_common()))
    con.close()


if __name__ == "__main__":
    main()

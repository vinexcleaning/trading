"""Read-only access to the four sibling corpora, and read-only is enforced.

Two sibling sessions have already lost work to SQLite lock contention in this
tree (social-signal's Reddit collector died after 45 minutes holding
`database is locked`). Every connection here is opened with `mode=ro` in the
URI, so this project cannot be the cause of a third.

Nothing in this module reimplements a sibling's logic. The rubrics are IMPORTED
from where they live:

    youtube-signal/src/read_video.py   the LLM rubric + verdict routing
    social-signal/src/rubric.py        the mechanical lexicon

If either moves, this fails loudly rather than drifting into a private copy.
"""
from __future__ import annotations

import importlib.util
import json
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent   # trading/
HERE = Path(__file__).resolve().parent
REPORTS = HERE.parent / "reports"
DATA = HERE.parent / "data"

DBS = {
    "yt":        ROOT / "youtube-signal" / "data" / "signal.db",
    "yt_kalshi": ROOT / "youtube-signal" / "data" / "signal_kalshi_edge.db",
    "reddit":    ROOT / "social-signal" / "data" / "social.db",
    "github":    ROOT / "signal-github" / "data" / "github.db",
}


def ro(corpus: str) -> sqlite3.Connection:
    p = DBS[corpus]
    if not p.exists():
        raise FileNotFoundError(f"{corpus}: {p} does not exist")
    con = sqlite3.connect(f"file:{p.as_posix()}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    return con


def _load(name: str, path: Path):
    """Import a sibling module by path without putting its whole src/ on
    sys.path, which would shadow this project's own modules."""
    if not path.exists():
        raise FileNotFoundError(f"sibling rubric moved: {path}")
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def lexicon():
    """social-signal's mechanical rubric: score(text) -> (s, b, h, comps)."""
    return _load("_ss_rubric", ROOT / "social-signal" / "src" / "rubric.py")


def llm_rubric():
    """youtube-signal's read_video: RUBRIC prompt, weights, verdict routing.

    read_video imports db_phase2 and ncheck as siblings, so its own src/ has to
    be importable for the duration of the load.
    """
    src = ROOT / "youtube-signal" / "src"
    sys.path.insert(0, str(src))
    try:
        return _load("_ys_read_video", src / "read_video.py")
    finally:
        sys.path.remove(str(src))


# ---------------------------------------------------------------- case text

def text_for(corpus: str, key: str) -> str:
    """The artifact a rubric reads, as one string."""
    if corpus in ("yt", "yt_kalshi"):
        con = ro(corpus)
        r = con.execute("SELECT v.title, v.description, t.snippets_json "
                        "FROM videos v LEFT JOIN transcripts t "
                        "  ON t.video_id = v.video_id "
                        "WHERE v.video_id = ?", (key,)).fetchone()
        con.close()
        if r is None:
            raise KeyError(f"{corpus}:{key} not found")
        body = ""
        if r["snippets_json"]:
            body = " ".join(s["text"] for s in json.loads(r["snippets_json"]))
        return f"{r['title'] or ''}\n{r['description'] or ''}\n{body}".strip()

    if corpus == "reddit":
        con = ro(corpus)
        r = con.execute("SELECT title, selftext FROM rd_posts WHERE post_id = ?",
                        (key,)).fetchone()
        con.close()
        if r is None:
            raise KeyError(f"reddit:{key} not found")
        return f"{r['title']}\n{r['selftext'] or ''}"

    if corpus == "github":
        con = ro(corpus)
        r = con.execute("SELECT full_name, description, evidence, what_it_does, "
                        "claimed_results, notes, license, stars, commits, "
                        "is_archived, pushed_at FROM repos WHERE full_name = ?",
                        (key,)).fetchone()
        con.close()
        if r is None:
            raise KeyError(f"github:{key} not found")
        return "\n".join(str(r[c] or "") for c in
                         ("full_name", "description", "what_it_does",
                          "claimed_results", "evidence", "notes"))
    raise ValueError(corpus)


def meta_for(corpus: str, key: str) -> dict:
    """Non-text facts a staleness or authority component needs."""
    if corpus in ("yt", "yt_kalshi"):
        con = ro(corpus)
        r = con.execute("SELECT upload_date, age_months, duration_s, "
                        "view_count, is_stale FROM videos WHERE video_id = ?",
                        (key,)).fetchone()
        con.close()
        return dict(r) if r else {}
    if corpus == "reddit":
        con = ro(corpus)
        r = con.execute("SELECT created_utc, score, num_comments, subreddit "
                        "FROM rd_posts WHERE post_id = ?", (key,)).fetchone()
        con.close()
        return dict(r) if r else {}
    if corpus == "github":
        con = ro(corpus)
        r = con.execute("SELECT stars, commits, is_archived, pushed_at, license "
                        "FROM repos WHERE full_name = ?", (key,)).fetchone()
        con.close()
        return dict(r) if r else {}
    return {}


def stored_verdict(corpus: str, key: str):
    """What the CURRENT pipeline actually recorded. This is the instrument's
    real output, not a re-derivation - see the note in validate_rubric.py on
    why the youtube verdict cannot be recomputed from the database at all."""
    if corpus in ("yt", "yt_kalshi"):
        con = ro(corpus)
        r = con.execute("SELECT s_total, b_total, h_total, verdict "
                        "FROM scores WHERE video_id = ?", (key,)).fetchone()
        con.close()
        return dict(r) if r else None
    if corpus == "reddit":
        con = ro(corpus)
        r = con.execute("SELECT s_total, b_total, h_total, verdict "
                        "FROM rd_scores WHERE post_id = ?", (key,)).fetchone()
        con.close()
        return dict(r) if r else None
    if corpus == "github":
        con = ro(corpus)
        r = con.execute("SELECT s_total, s_strict, s_adj, verdict, trust_me_bro "
                        "FROM repos WHERE full_name = ?", (key,)).fetchone()
        con.close()
        return dict(r) if r else None
    return None


def all_scored_components():
    """(corpus, key, set(components)) for every video the LLM rubric has read.

    This is the population the component diagnostics run on - 38 videos, not
    the 24 test cases, because a fire-rate measured on cases chosen for being
    interesting is not a fire rate.
    """
    out = []
    for corpus in ("yt", "yt_kalshi"):
        con = ro(corpus)
        for (vid,) in con.execute("SELECT video_id FROM scores"):
            comps = {r[0] for r in con.execute(
                "SELECT component FROM score_evidence WHERE video_id = ?",
                (vid,))}
            out.append((corpus, vid, comps))
        con.close()
    return out

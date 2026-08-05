"""social.db — one entity table, one observation table, one verdict per entity.

Schema note carried over from youtube-signal's bug #4 and #5, which between them
made that project un-runnable on any machine but the one it was written on:

    `CREATE TABLE IF NOT EXISTS` is a no-op against a table that already exists,
    so a column added to SCHEMA alone reaches new databases and never old ones,
    and a column added by ALTER alone reaches old databases and never new ones.
    **Both halves are always required.**

So every column lives in SCHEMA *and* every column added after the first release
also gets a line in MIGRATIONS, which is applied idempotently at connect().
"""
from __future__ import annotations

import datetime
import os
import sqlite3

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
REPORTS = os.path.join(ROOT, "reports")
os.makedirs(DATA, exist_ok=True)
os.makedirs(REPORTS, exist_ok=True)

DB = os.path.join(DATA, "social.db")

SCHEMA = """
CREATE TABLE IF NOT EXISTS entities (
    entity_id      INTEGER PRIMARY KEY AUTOINCREMENT,
    key            TEXT UNIQUE NOT NULL,   -- norm.key()
    compact_key    TEXT,                   -- norm.compact(), secondary join
    display        TEXT NOT NULL,
    kind           TEXT,        -- library|service|site|exchange|repo|concept|institution|unknown
    canonical_url  TEXT,
    github_repo    TEXT,        -- owner/name once resolved
    first_seen_utc TEXT
);
CREATE INDEX IF NOT EXISTS ix_entities_compact ON entities(compact_key);

-- One row per (entity, platform, source). This is the evidence layer; nothing
-- here is a judgement, only what a named source was observed to say.
CREATE TABLE IF NOT EXISTS observations (
    obs_id       INTEGER PRIMARY KEY AUTOINCREMENT,
    entity_id    INTEGER NOT NULL,
    platform     TEXT NOT NULL,   -- youtube|github|github_corpus|reddit|discord
    corpus       TEXT,            -- which DB / subreddit / channel it came from
    source_id    TEXT,            -- video_id | owner/repo | permalink
    stance       TEXT NOT NULL,   -- PROMOTED|RECOMMENDED|NEUTRAL_USE|CRITICISED|SCAM_ALLEGED|DEAD|BROKEN
    strength     REAL DEFAULT 1.0,
    detail       TEXT,
    evidence     TEXT,            -- verbatim, short
    observed_utc TEXT,
    UNIQUE(entity_id, platform, corpus, source_id, stance)
);
CREATE INDEX IF NOT EXISTS ix_obs_entity ON observations(entity_id);

CREATE TABLE IF NOT EXISTS verdicts (
    entity_id      INTEGER PRIMARY KEY,
    verdict        TEXT,   -- see join_corpora.VERDICTS
    n_platforms    INTEGER,
    promo_score    REAL,
    critic_score   REAL,
    reason         TEXT,
    decided_utc    TEXT
);

CREATE TABLE IF NOT EXISTS runlog (
    id     INTEGER PRIMARY KEY AUTOINCREMENT,
    ts_utc TEXT,
    step   TEXT,
    detail TEXT
);

-- ---------------- Reddit (T2) ----------------
CREATE TABLE IF NOT EXISTS rd_posts (
    post_id     TEXT PRIMARY KEY,
    subreddit   TEXT,
    title       TEXT,
    selftext    TEXT,
    author      TEXT,
    created_utc REAL,
    score       INTEGER,
    upvote_ratio REAL,
    num_comments INTEGER,
    permalink   TEXT,
    is_self     INTEGER,
    url         TEXT,
    link_flair  TEXT,
    over_18     INTEGER,
    query       TEXT,
    fetched_utc TEXT,
    gate_status TEXT,
    gate_reason TEXT,
    platform    TEXT DEFAULT 'reddit'
);
CREATE INDEX IF NOT EXISTS ix_rd_posts_sub ON rd_posts(subreddit);
-- NOTE: the index on `platform` is deliberately NOT here. See MIGRATIONS.

CREATE TABLE IF NOT EXISTS rd_comments (
    comment_id  TEXT PRIMARY KEY,
    post_id     TEXT,
    parent_id   TEXT,
    author      TEXT,
    body        TEXT,
    created_utc REAL,
    score       INTEGER,
    depth       INTEGER,
    permalink   TEXT,
    fetched_utc TEXT
);
CREATE INDEX IF NOT EXISTS ix_rd_comments_post ON rd_comments(post_id);

CREATE TABLE IF NOT EXISTS rd_scores (
    post_id      TEXT PRIMARY KEY,
    s_total      INTEGER,
    b_total      INTEGER,
    h_total      INTEGER,
    verdict      TEXT,
    components   TEXT,   -- JSON: [{axis,component,weight,quote}]
    scored_utc   TEXT
);

CREATE TABLE IF NOT EXISTS rd_log (
    id      INTEGER PRIMARY KEY AUTOINCREMENT,
    ts_utc  TEXT,
    kind    TEXT,
    target  TEXT,
    n       INTEGER,
    seconds REAL,
    ok      INTEGER,
    error   TEXT
);
"""

# Columns added after first release. Every one must ALSO be in SCHEMA above.
#
# `platform` was added when the second platform (Mastodon) arrived. The table is
# still called `rd_posts` — renaming it would break every sibling script for a
# cosmetic gain. Column mapping for non-Reddit platforms is documented in the
# fetcher that writes them; for Mastodon: subreddit->"instance/tag",
# score->favourites_count, num_comments->replies_count, permalink->url.
# **An index on a migrated column must NOT live in SCHEMA.** `executescript`
# runs SCHEMA first, and against an existing database `CREATE TABLE IF NOT
# EXISTS` is a no-op — so the CREATE INDEX fires before the ALTER has added the
# column and the whole connect() raises `no such column: platform`. This is
# youtube-signal's recorded bug #4/#5 in a third costume: the column reaches new
# databases via SCHEMA and old ones via ALTER, but anything DEPENDING on that
# column has to run after both. Order is: SCHEMA, then MIGRATIONS, in this list.
MIGRATIONS: tuple[str, ...] = (
    "ALTER TABLE rd_posts ADD COLUMN platform TEXT DEFAULT 'reddit'",
    "CREATE INDEX IF NOT EXISTS ix_rd_posts_platform ON rd_posts(platform)",
    "UPDATE rd_posts SET platform='reddit' WHERE platform IS NULL",
)


def now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")


def connect(path: str = DB, timeout: float = 120.0) -> sqlite3.Connection:
    """One connection, configured to survive a concurrent writer.

    This project runs a long collector in the background while analysis passes
    run in the foreground, and SQLite's **default busy timeout is 5 seconds**.
    A 45-minute Reddit collection died with `database is locked` because an
    analysis pass held a write lock for six seconds — the collector was the
    long, expensive, irreplaceable job and the cheap one killed it.

    Two changes, both required:
      * `timeout` raises the busy wait to two minutes, so a writer queues
        instead of failing.
      * WAL lets readers proceed while a writer holds the file, which is the
        normal case here — the analysis passes are overwhelmingly reads.
    """
    con = sqlite3.connect(path, timeout=timeout)
    con.row_factory = sqlite3.Row
    try:
        con.execute("PRAGMA journal_mode=WAL")
        con.execute("PRAGMA synchronous=NORMAL")
    except sqlite3.OperationalError:
        pass  # a concurrent writer may hold the file; the timeout covers us
    con.executescript(SCHEMA)
    for stmt in MIGRATIONS:
        try:
            con.execute(stmt)
        except sqlite3.OperationalError:
            pass  # already applied
    con.commit()
    return con


def log(con: sqlite3.Connection, step: str, detail: str) -> None:
    con.execute("INSERT INTO runlog (ts_utc, step, detail) VALUES (?,?,?)",
                (now(), step, detail))
    con.commit()


def upsert_entity(con, key, compact_key, display, kind=None, url=None, repo=None):
    row = con.execute("SELECT entity_id, display, kind, canonical_url, github_repo"
                      " FROM entities WHERE key=?", (key,)).fetchone()
    if row is None:
        cur = con.execute(
            """INSERT INTO entities (key, compact_key, display, kind,
                                     canonical_url, github_repo, first_seen_utc)
               VALUES (?,?,?,?,?,?,?)""",
            (key, compact_key, display, kind, url, repo, now()))
        return cur.lastrowid
    eid = row["entity_id"]
    # Fill blanks only; never overwrite a resolved fact with a vaguer one.
    if kind and not row["kind"]:
        con.execute("UPDATE entities SET kind=? WHERE entity_id=?", (kind, eid))
    if url and not row["canonical_url"]:
        con.execute("UPDATE entities SET canonical_url=? WHERE entity_id=?", (url, eid))
    if repo and not row["github_repo"]:
        con.execute("UPDATE entities SET github_repo=? WHERE entity_id=?", (repo, eid))
    # Prefer the longer display name: it carries the creator's own gloss.
    if display and len(display) > len(row["display"] or ""):
        con.execute("UPDATE entities SET display=? WHERE entity_id=?", (display, eid))
    return eid


def add_observation(con, entity_id, platform, corpus, source_id, stance,
                    strength=1.0, detail=None, evidence=None):
    con.execute(
        """INSERT OR IGNORE INTO observations
           (entity_id, platform, corpus, source_id, stance, strength, detail,
            evidence, observed_utc)
           VALUES (?,?,?,?,?,?,?,?,?)""",
        (entity_id, platform, corpus or "", source_id or "", stance, strength,
         detail, evidence, now()))

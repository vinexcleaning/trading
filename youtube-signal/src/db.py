"""SQLite schema for youtube-signal.

One row per video, one per channel, and a full audit trail: every search call
logged, every per-run hit recorded (so retrieval_stability and Jaccard are
computable), every gate rejection given a reason.
"""

import datetime as dt
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "signal.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS channels (
    channel_id      TEXT PRIMARY KEY,
    name            TEXT,
    subscribers     INTEGER,
    median_views    INTEGER,
    upload_count    INTEGER,
    is_seed         INTEGER DEFAULT 0,
    expanded        INTEGER DEFAULT 0,
    stats_flag      TEXT,          -- set when a refresh moves stats >5x
    first_seen_utc  TEXT,
    last_refresh_utc TEXT
);

CREATE TABLE IF NOT EXISTS videos (
    video_id        TEXT PRIMARY KEY,
    channel_id      TEXT,
    channel_name    TEXT,
    title           TEXT,
    view_count      INTEGER,
    duration_s      INTEGER,
    upload_date     TEXT,
    age_months      REAL,
    source          TEXT,          -- 'search' or 'channel_expansion'
    transcript_words INTEGER,
    transcript_via  TEXT,
    is_stale        INTEGER,
    gate_status     TEXT,          -- 'PASS', or the gate that dropped it
    metadata_fetched INTEGER DEFAULT 0,
    created_utc     TEXT,
    -- The transcript is auto-captioned SPEECH; the description is TYPED, and it
    -- is where the literal URLs and the undisclosed referral links live. Added
    -- in Phase 2. run_gates.py writes `description` on every video it gates, so
    -- these must exist in the base schema and not only as a later ALTER.
    description     TEXT,
    description_urls TEXT,
    description_has_affiliate INTEGER,
    description_fetched_utc TEXT
);

-- One row per (video, family, query, run). This is what makes stability and
-- Jaccard computable after the fact instead of only during the run.
CREATE TABLE IF NOT EXISTS retrieval_hits (
    video_id   TEXT,
    family     TEXT,
    query      TEXT,
    run_idx    INTEGER,
    rank       INTEGER,
    PRIMARY KEY (video_id, family, query, run_idx)
);

CREATE TABLE IF NOT EXISTS retrieval_log (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    ts_utc     TEXT,
    family     TEXT,
    query      TEXT,
    run_idx    INTEGER,
    n_results  INTEGER,
    seconds    REAL,
    ok         INTEGER,
    error      TEXT
);

-- Transcript text is cached at gate time. G1 fetches it anyway, and Phase 2
-- scoring needs the timestamped snippets for its evidence requirement; refetching
-- 470 transcripts later would cost ~35 minutes for nothing.
CREATE TABLE IF NOT EXISTS transcripts (
    video_id      TEXT PRIMARY KEY,
    via           TEXT,
    n_snippets    INTEGER,
    n_words       INTEGER,
    snippets_json TEXT,
    fetched_utc   TEXT
);

CREATE TABLE IF NOT EXISTS drops (
    video_id  TEXT,
    gate      TEXT,
    reason    TEXT,
    ts_utc    TEXT,
    PRIMARY KEY (video_id, gate)
);

CREATE INDEX IF NOT EXISTS idx_hits_family ON retrieval_hits(family);
CREATE INDEX IF NOT EXISTS idx_videos_gate ON videos(gate_status);
"""


# Columns added after databases already existed. See db_phase2.MIGRATIONS for the
# full reasoning: CREATE TABLE IF NOT EXISTS is a no-op against an existing
# table, so a column added to SCHEMA alone reaches new DBs and never old ones,
# and a column added by ALTER alone reaches old DBs and never new ones. Both
# halves are required. Two bugs of exactly this shape have now been found.
MIGRATIONS = (
    "ALTER TABLE videos ADD COLUMN description TEXT",
    "ALTER TABLE videos ADD COLUMN description_urls TEXT",
    "ALTER TABLE videos ADD COLUMN description_has_affiliate INTEGER",
    "ALTER TABLE videos ADD COLUMN description_fetched_utc TEXT",
)


def now():
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")


def connect(path=DB_PATH):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(path)
    con.row_factory = sqlite3.Row
    con.executescript(SCHEMA)
    for stmt in MIGRATIONS:
        try:
            con.execute(stmt)
        except sqlite3.OperationalError:
            pass  # already present
    con.commit()
    return con

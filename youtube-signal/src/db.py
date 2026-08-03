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
    created_utc     TEXT
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


def now():
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")


def connect(path=DB_PATH):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(path)
    con.row_factory = sqlite3.Row
    con.executescript(SCHEMA)
    con.commit()
    return con

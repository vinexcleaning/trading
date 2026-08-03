"""SQLite schema. One row per repo, plus the four extraction tables.

NULL != NULL in SQLite, so every UNIQUE constraint that can see a null column
wraps it in COALESCE. This bit the YouTube project already.
"""
from __future__ import annotations

import os
import sqlite3

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(ROOT, "data", "github.db")

SCHEMA = """
CREATE TABLE IF NOT EXISTS repos (
    full_name       TEXT PRIMARY KEY,
    url             TEXT,
    description     TEXT,
    stars           INTEGER,
    forks           INTEGER,
    size_kb         INTEGER,
    language        TEXT,
    license         TEXT,
    created_at      TEXT,
    pushed_at       TEXT,
    open_issues     INTEGER,
    is_fork         INTEGER,
    is_archived     INTEGER,
    topics          TEXT,
    default_branch  TEXT,
    -- retrieval provenance
    families        TEXT,   -- comma list of F1/F2/F2_CODE/SEED/LIB_FORK/TOPIC
    queries         TEXT,   -- comma list of the actual query strings
    -- gates
    gate            TEXT,   -- PASS / DROP / STALE
    drop_reason     TEXT,
    -- deep fetch
    commits         INTEGER,
    span_days       INTEGER,
    contributors    INTEGER,
    first_commit    TEXT,
    last_commit_msg TEXT,
    last_commit_sha TEXT,
    closed_issues   INTEGER,
    tree_files      INTEGER,
    fetched         INTEGER DEFAULT 0,
    -- scoring
    s1 INTEGER, s2 INTEGER, s3 INTEGER, s4 INTEGER, s5 INTEGER,
    s_total INTEGER,
    evidence        TEXT,   -- JSON: component -> [path:line or sha, ...]
    -- extraction
    what_it_does        TEXT,
    strategy_type       TEXT,
    venue               TEXT,
    has_backtest        INTEGER,
    has_tests           INTEGER,
    has_live_trading    INTEGER,
    claimed_results     TEXT,
    artifact_behind_claim TEXT,
    verdict             TEXT,
    trust_me_bro        INTEGER,
    notes               TEXT,
    read_at             TEXT
);

CREATE TABLE IF NOT EXISTS strategies (
    id INTEGER PRIMARY KEY,
    repo TEXT, name TEXT, description TEXT,
    entry_logic TEXT, exit_logic TEXT, parameters TEXT,
    costs_modelled INTEGER, backtest_evidence TEXT, file_path TEXT
);
CREATE UNIQUE INDEX IF NOT EXISTS ix_strategies
    ON strategies(COALESCE(repo,''), COALESCE(name,''));

CREATE TABLE IF NOT EXISTS dependencies (
    id INTEGER PRIMARY KEY,
    name TEXT, kind TEXT, what_it_is TEXT, repo_count INTEGER DEFAULT 0,
    seen_in TEXT, url TEXT, note TEXT
);
CREATE UNIQUE INDEX IF NOT EXISTS ix_dependencies ON dependencies(COALESCE(name,''));

CREATE TABLE IF NOT EXISTS data_sources (
    id INTEGER PRIMARY KEY,
    name TEXT, url TEXT, free TEXT, covers TEXT, venue TEXT,
    seen_in TEXT, note TEXT
);
CREATE UNIQUE INDEX IF NOT EXISTS ix_data_sources
    ON data_sources(COALESCE(name,''), COALESCE(url,''));

CREATE TABLE IF NOT EXISTS crossref (
    id INTEGER PRIMARY KEY,
    tool TEXT, yt_claim TEXT, repo TEXT, alive TEXT, verdict TEXT, note TEXT
);
CREATE UNIQUE INDEX IF NOT EXISTS ix_crossref ON crossref(COALESCE(tool,''));

CREATE TABLE IF NOT EXISTS runlog (
    id INTEGER PRIMARY KEY,
    ts TEXT, step TEXT, detail TEXT
);
"""


def connect():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    con.executescript(SCHEMA)
    return con


def log(con, step: str, detail: str):
    import datetime
    con.execute(
        "INSERT INTO runlog (ts, step, detail) VALUES (?,?,?)",
        (datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"), step, detail),
    )
    con.commit()

"""Phase 2 schema: scores, evidence, and the extraction tables.

Design point that matters: score_evidence is a separate table with a NOT NULL
quote and timestamp, and a score component may only be written if it has a row
there. "No evidence, no score" is enforced by the schema, not by remembering to
check. A component that cannot cite did not fire.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import db  # noqa: E402

SCHEMA = """
-- Which videos were chosen for the read, and by which rule.
CREATE TABLE IF NOT EXISTS read_set (
    video_id     TEXT PRIMARY KEY,
    selection_rule TEXT NOT NULL,   -- 'anchor' | 'longest' | 'stratified'
    view_band    TEXT,
    family_bucket TEXT,
    selected_utc TEXT
);

CREATE TABLE IF NOT EXISTS scores (
    video_id     TEXT PRIMARY KEY,
    s_total      INTEGER,
    h_total      INTEGER,
    verdict      TEXT,              -- WATCH | EXTRACT | EXTRACT_RESULTS_DISCOUNTED | SKIP
    visual_dependent INTEGER,
    model        TEXT,
    input_tokens INTEGER,
    output_tokens INTEGER,
    cost_usd     REAL,
    scored_utc   TEXT
);

-- One row per component that FIRED. Absence is a zero; there is no null score.
CREATE TABLE IF NOT EXISTS score_evidence (
    video_id   TEXT NOT NULL,
    axis       TEXT NOT NULL,       -- 'S' | 'H'
    component  TEXT NOT NULL,       -- S1..S5, H1..H10
    weight     INTEGER NOT NULL,
    timestamp_s REAL NOT NULL,
    quote      TEXT NOT NULL,       -- verbatim, < 15 words
    PRIMARY KEY (video_id, component)
);

CREATE TABLE IF NOT EXISTS tools (
    tool_id         INTEGER PRIMARY KEY AUTOINCREMENT,
    name            TEXT NOT NULL,
    url             TEXT,
    claimed_purpose TEXT,
    is_creators_own TEXT,           -- disclosed | undisclosed | no
    is_referral_link INTEGER,
    first_seen_video TEXT,
    mention_count   INTEGER DEFAULT 1,
    resolution      TEXT,           -- resolved | dead | unreachable | not_checked
    resolution_detail TEXT,
    resolved_utc    TEXT
);

-- NOT `UNIQUE (name, url)`. In SQL, NULL != NULL, so a plain unique constraint
-- never fires for a tool with no URL -- every reload inserted a duplicate row
-- instead of bumping mention_count. Grok and Perplexity each reached 3 rows
-- before this was caught. COALESCE makes the null case compare equal.
CREATE UNIQUE INDEX IF NOT EXISTS idx_tools_uniq
    ON tools(name, COALESCE(url, ''));

CREATE TABLE IF NOT EXISTS claims (
    claim_id        INTEGER PRIMARY KEY AUTOINCREMENT,
    video_id        TEXT NOT NULL,
    timestamp_s     REAL,
    claim_text      TEXT NOT NULL,
    claim_type      TEXT,           -- mechanism | procedure | tool_rec | spec | result
    stated_n        INTEGER,
    stated_period   TEXT,
    stated_capital  TEXT,
    stated_win_rate REAL,
    n_check_verdict TEXT,
    n_check_detail  TEXT,
    expires_after_months INTEGER,   -- NULL means never
    confidence      TEXT
);

CREATE TABLE IF NOT EXISTS methods (
    method_id    INTEGER PRIMARY KEY AUTOINCREMENT,
    video_id     TEXT NOT NULL,
    title        TEXT,
    steps_json   TEXT NOT NULL,     -- [{"n":1,"step":"...","t":123.4}, ...]
    ts_start     REAL,
    ts_end       REAL
);

CREATE TABLE IF NOT EXISTS watch_segments (
    segment_id  INTEGER PRIMARY KEY AUTOINCREMENT,
    video_id    TEXT NOT NULL,
    ts_start    REAL NOT NULL,
    ts_end      REAL NOT NULL,
    why         TEXT
);

CREATE INDEX IF NOT EXISTS idx_claims_video ON claims(video_id);
CREATE INDEX IF NOT EXISTS idx_ev_video ON score_evidence(video_id);
"""

# claim_type -> shelf life in months. Replaces the video-level staleness cutoff,
# because one video carries claims of several kinds: the mechanism it explains
# does not expire, the API spec it quotes expires in a quarter.
EXPIRY_MONTHS = {
    "mechanism": None,
    "concept": None,
    "math": None,
    "procedure": 12,
    "tool_rec": 4,
    "spec": 3,
    "result": 3,
}


def connect(path=db.DB_PATH):
    con = db.connect(path)
    con.executescript(SCHEMA)
    con.commit()
    return con


if __name__ == "__main__":
    con = connect()
    tables = [r["name"] for r in con.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
    print("tables:", ", ".join(tables))
    con.close()

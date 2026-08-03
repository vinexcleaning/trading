"""YouTube Data API quota ledger.

Every API call is logged with its documented unit cost before it is made. The
ledger hard-halts the run at HALT_AT units so the 10,000/day allowance cannot be
burned by accident. Quota resets at midnight US/Pacific, so the ledger accounts
by Pacific date, not local date.
"""

import datetime as _dt
import sqlite3
from pathlib import Path

DAILY_LIMIT = 10_000
HALT_AT = 9_500

# Documented unit costs. search.list is 100x everything else -- that asymmetry is
# the whole reason this file exists.
COSTS = {
    "search.list": 100,
    "videos.list": 1,
    "channels.list": 1,
    "playlistItems.list": 1,
    "playlists.list": 1,
}

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "signal.db"


class QuotaExceeded(RuntimeError):
    pass


def pacific_date(now=None):
    """Quota resets midnight US/Pacific. Pacific is UTC-8 (PST) or UTC-7 (PDT);
    we use -8 as the conservative choice -- it rolls the day over later, so we
    keep counting against the old day for an extra hour rather than resetting
    early and overspending."""
    now = now or _dt.datetime.now(_dt.timezone.utc)
    return (now - _dt.timedelta(hours=8)).date().isoformat()


def connect(db_path=DB_PATH):
    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(db_path)
    con.execute(
        """CREATE TABLE IF NOT EXISTS quota_ledger (
               id           INTEGER PRIMARY KEY AUTOINCREMENT,
               ts_utc       TEXT NOT NULL,
               pacific_date TEXT NOT NULL,
               endpoint     TEXT NOT NULL,
               cost         INTEGER NOT NULL,
               phase        TEXT,
               detail       TEXT
           )"""
    )
    con.commit()
    return con


def spent(con, day=None):
    day = day or pacific_date()
    row = con.execute(
        "SELECT COALESCE(SUM(cost), 0) FROM quota_ledger WHERE pacific_date = ?", (day,)
    ).fetchone()
    return row[0]


def charge(con, endpoint, phase=None, detail=None, n_calls=1):
    """Log and charge a call. Raises QuotaExceeded *before* the call is made if
    it would cross HALT_AT."""
    if endpoint not in COSTS:
        raise ValueError(f"unknown endpoint {endpoint!r}; add its cost to COSTS")
    cost = COSTS[endpoint] * n_calls
    already = spent(con)
    if already + cost > HALT_AT:
        raise QuotaExceeded(
            f"HALTED: {already} units already spent today (Pacific {pacific_date()}). "
            f"This {endpoint} call would cost {cost}, crossing the {HALT_AT} safety "
            f"limit (daily cap {DAILY_LIMIT}). Quota resets at midnight US/Pacific. "
            f"Nothing was called."
        )
    con.execute(
        "INSERT INTO quota_ledger (ts_utc, pacific_date, endpoint, cost, phase, detail)"
        " VALUES (?, ?, ?, ?, ?, ?)",
        (
            _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds"),
            pacific_date(),
            endpoint,
            cost,
            phase,
            detail,
        ),
    )
    con.commit()
    return cost


def report(con, day=None):
    day = day or pacific_date()
    rows = con.execute(
        "SELECT endpoint, COUNT(*), SUM(cost) FROM quota_ledger WHERE pacific_date = ?"
        " GROUP BY endpoint ORDER BY SUM(cost) DESC",
        (day,),
    ).fetchall()
    lines = [f"QUOTA LEDGER  (Pacific date {day})", ""]
    if not rows:
        lines.append("  no API calls logged")
    else:
        lines.append(f"  {'endpoint':<22}{'calls':>7}{'units':>8}")
        for ep, n, c in rows:
            lines.append(f"  {ep:<22}{n:>7}{c:>8}")
    total = spent(con, day)
    lines += [
        "",
        f"  {'TOTAL':<22}{'':>7}{total:>8} / {DAILY_LIMIT} "
        f"(halt at {HALT_AT}, {max(0, HALT_AT - total)} left)",
    ]
    return "\n".join(lines)

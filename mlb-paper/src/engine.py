"""The paper engine: 16 bots, 3 exit modes, one shared game pool, no money.

### Paper only, structurally

This module imports no signing code, reads no credential, opens no key file and
never issues a non-GET request. `tests/test_paper_only.py` walks every source
file in this package and fails the build if order-shaped code appears anywhere.
Fills are simulated against a book that was recorded on a LATER tick than the
decision.

### The fill model, and the three ways this repo has already faked a profit

1. **Never the mid.** Fills are at the ask for YES and at (100 - bid) for NO.
   A tennis result of +14.4% to +24.6% became -24.3% to -30.9% when this was
   fixed. `_mid_for` exists in `mentalities.py` for reporting and
   `tests/test_no_mid_fill.py` asserts no fill path reads it.
2. **Never the tick that triggered.** A decision taken on tick N fills against
   tick N+1's book. Without latency, most strategies are profitable.
3. **Never more size than the book showed.** Capped at 25% of the displayed
   top-of-book size at fill time.

### Shadow decisions -- why they exist and what they are not

A mentality whose stated adjustment fails the cost bar produces a SHADOW
record: the full reasoning, the price it would have paid, and no position, no
stake and no P&L. Shadows exist because the primary endpoint is closing-line
value (PREREGISTRATION section 5/P1), CLV is measurable on a decision that was
never executed, and the real bots will fire too rarely to power it alone.

**A shadow is never a trade.** It never enters a bankroll, never appears in a
P&L table, and is reported in its own section labelled as decisions that were
NOT taken. Treating shadows as trades would be exactly the "assume you always
get filled" error this repo already labels FAKE.

### The unit of observation

A settled GAME. Not a fill, not a tick, not a ladder rung. Every interval is
clustered on the game.
"""
from __future__ import annotations

import json
import sqlite3
import sys
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
# The repo root, derived from this file. NEVER a hardcoded home
# directory: this package is meant to run on the laptop, whose paths
# live under a different user, and a hardcoded desktop path would
# import nothing and fail at the first shared-fee call.
TRADING_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(TRADING_ROOT))

import mentalities as MEN                      # noqa: E402
from common.kalshi_fees import fee_order_cents  # noqa: E402

DB = HERE.parent / "data" / "paper.db"

BANKROLL_START = 500.00
STAKE_MIN_FRAC = 0.005
STAKE_MAX_FRAC = 0.06
KELLY_FRACTION = 0.25
MAX_CONTRACTS = 25
DEPTH_CAP_FRAC = 0.25
TAKE_PROFIT_C = 12
STOP_LOSS_C = 12
REENTRY_COOLDOWN_S = 3600
MAX_ENTRIES_PER_GAME = {"hold": 1, "exit-once": 1, "free": 2}
PENDING_MAX_AGE_S = 900
SHADOW_MIN_ADJUSTMENT_C = 1.5   # below this it is not even a view


SCHEMA = """
CREATE TABLE IF NOT EXISTS decisions (
  id TEXT PRIMARY KEY,
  ts_utc TEXT NOT NULL,
  bot TEXT NOT NULL,
  mentality TEXT NOT NULL,
  exit_mode TEXT NOT NULL,
  game_key TEXT NOT NULL,
  game_pk INTEGER,
  starts_utc TEXT NOT NULL,
  window TEXT NOT NULL,
  kind TEXT NOT NULL,          -- 'entry' | 'shadow' | 'decline' | 'control'
  ticker TEXT,
  side TEXT,
  quoted_price_c INTEGER,
  conviction REAL,
  stated_prob_c REAL,
  edge_c REAL,
  stake_usd REAL,
  reasoning_json TEXT NOT NULL,
  reasoning_sha1 TEXT NOT NULL,
  outcome_known INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS fills (
  id TEXT PRIMARY KEY,
  decision_id TEXT NOT NULL,
  ts_utc TEXT NOT NULL,
  bot TEXT NOT NULL,
  game_key TEXT NOT NULL,
  ticker TEXT NOT NULL,
  side TEXT NOT NULL,
  action TEXT NOT NULL,        -- 'open' | 'close'
  price_c INTEGER NOT NULL,
  contracts INTEGER NOT NULL,
  fee_c REAL NOT NULL,
  slippage_c REAL NOT NULL,
  book_size_at_fill REAL,
  FOREIGN KEY (decision_id) REFERENCES decisions(id)
);
CREATE TABLE IF NOT EXISTS positions (
  id TEXT PRIMARY KEY,
  bot TEXT NOT NULL,
  game_key TEXT NOT NULL,
  game_pk INTEGER,
  ticker TEXT NOT NULL,
  side TEXT NOT NULL,
  contracts INTEGER NOT NULL,
  entry_price_c INTEGER NOT NULL,
  entry_fee_c REAL NOT NULL,
  opened_utc TEXT NOT NULL,
  exit_mode TEXT NOT NULL,
  status TEXT NOT NULL,        -- 'open' | 'closed' | 'settled'
  closed_utc TEXT,
  exit_price_c INTEGER,
  exit_fee_c REAL,
  settle_value_c INTEGER,
  pnl_c REAL,
  decision_id TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS pending (
  id TEXT PRIMARY KEY,
  created_utc TEXT NOT NULL,
  bot TEXT NOT NULL,
  decision_id TEXT NOT NULL,
  game_key TEXT NOT NULL,
  ticker TEXT NOT NULL,
  side TEXT NOT NULL,
  intent TEXT NOT NULL,        -- 'open' | 'close'
  contracts INTEGER NOT NULL,
  max_price_c INTEGER,
  min_price_c INTEGER,
  position_id TEXT
);
CREATE TABLE IF NOT EXISTS marks (
  ts_utc TEXT NOT NULL,
  game_key TEXT NOT NULL,
  ticker TEXT NOT NULL,
  bid INTEGER, ask INTEGER, bid_size REAL, ask_size REAL,
  hours_to_start REAL,
  sharp_fair_yes_c REAL,
  PRIMARY KEY (ts_utc, ticker)
);
CREATE TABLE IF NOT EXISTS ticks (
  ts_utc TEXT PRIMARY KEY,
  games_in_pool INTEGER, markets_seen INTEGER,
  markets_with_ask INTEGER, zero_ask INTEGER,
  leaked_filtered INTEGER, entries INTEGER, shadows INTEGER,
  closes INTEGER, errors INTEGER, notes TEXT
);
CREATE TABLE IF NOT EXISTS settlements (
  game_pk INTEGER PRIMARY KEY, game_key TEXT NOT NULL,
  settled_utc TEXT NOT NULL, away_runs INTEGER, home_runs INTEGER,
  total_runs INTEGER, first_inning_runs INTEGER, raw_json TEXT
);
CREATE TABLE IF NOT EXISTS heartbeat (
  k TEXT PRIMARY KEY, v TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_dec_game ON decisions(game_key, bot);
CREATE INDEX IF NOT EXISTS ix_pos_bot ON positions(bot, status);
"""


def connect(path=None):
    p = Path(path or DB)
    p.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(p, timeout=30)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA journal_mode=WAL")
    con.executescript(SCHEMA)
    return con


def now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _sha1(s):
    import hashlib
    return hashlib.sha1(s.encode("utf-8")).hexdigest()


# ------------------------------------------------------------------- sizing

def stake_for(bankroll, edge_c, price_c):
    """Quarter-Kelly on the bot's own stated edge, clamped.

    Sizing is by CONTRACTS derived from a dollar stake, and the re-entry cap in
    `may_enter` is what stops the emergent martingale: a fixed dollar stake buys
    more contracts as the price falls, which is how 12 -> 20 -> 32 contracts
    cost -$7.56 on one tennis match in 50 minutes. Nobody designed that; it was
    a property of sizing by dollars.
    """
    p = max(1, min(99, int(price_c))) / 100.0
    b = (1.0 - p) / p
    edge_p = max(0.0, edge_c) / 100.0
    q_win = min(0.99, max(0.01, p + edge_p))
    kelly = (b * q_win - (1 - q_win)) / b if b > 0 else 0.0
    frac = max(0.0, kelly) * KELLY_FRACTION
    frac = min(STAKE_MAX_FRAC, max(STAKE_MIN_FRAC, frac)) if frac > 0 else 0.0
    return round(bankroll * frac, 2)


def contracts_for(stake_usd, price_c, book_size):
    if stake_usd <= 0 or price_c <= 0:
        return 0
    n = int(stake_usd / (price_c / 100.0))
    n = min(n, MAX_CONTRACTS)
    n = min(n, int(max(0.0, book_size) * DEPTH_CAP_FRAC))
    return max(0, n)


# -------------------------------------------------------------- bookkeeping

def bankroll(con, bot):
    row = con.execute(
        "SELECT COALESCE(SUM(pnl_c),0)/100.0 AS p FROM positions "
        "WHERE bot=? AND status IN ('closed','settled')", (bot,)).fetchone()
    open_cost = con.execute(
        "SELECT COALESCE(SUM(contracts*entry_price_c + entry_fee_c),0)/100.0 AS c "
        "FROM positions WHERE bot=? AND status='open'", (bot,)).fetchone()
    return BANKROLL_START + (row["p"] or 0.0) - (open_cost["c"] or 0.0)


def may_enter(con, bot, game_key, exit_mode, first_entry_contracts=None):
    """Entry permission, and the martingale refusal."""
    n = con.execute(
        "SELECT COUNT(*) c FROM positions WHERE bot=? AND game_key=?",
        (bot, game_key)).fetchone()["c"]
    cap = MAX_ENTRIES_PER_GAME[exit_mode]
    if n >= cap:
        return False, f"already {n} entries on this game (cap {cap})"
    if n > 0:
        last = con.execute(
            "SELECT closed_utc, contracts FROM positions WHERE bot=? AND "
            "game_key=? ORDER BY opened_utc DESC LIMIT 1",
            (bot, game_key)).fetchone()
        if last and last["closed_utc"]:
            dt = (datetime.now(timezone.utc)
                  - datetime.fromisoformat(last["closed_utc"])).total_seconds()
            if dt < REENTRY_COOLDOWN_S:
                return False, (f"re-entry cooldown ({int(dt)}s of "
                               f"{REENTRY_COOLDOWN_S}s)")
    return True, None


def reentry_size_cap(con, bot, game_key):
    """A re-entry may never be larger than the first entry. GUARDS: this alone
    refuses the 12 -> 20 -> 32 martingale."""
    row = con.execute(
        "SELECT contracts FROM positions WHERE bot=? AND game_key=? "
        "ORDER BY opened_utc ASC LIMIT 1", (bot, game_key)).fetchone()
    return row["contracts"] if row else None


# ---------------------------------------------------------------- decisions

def record_decision(con, *, bot, mentality, exit_mode, brief, window, kind,
                    intent=None, decline=None, stake_usd=None):
    """Write the reasoning to disk. ALWAYS before the outcome exists.

    The row carries a sha1 of the reasoning JSON so that a later read can prove
    the text was not edited after settlement. `outcome_known` is 0 at write
    time and is only ever set to 1 by the settlement pass, never by the
    decision pass.
    """
    payload = intent.to_dict() if intent is not None else decline.to_dict()
    payload["_brief_built_at_utc"] = brief.get("built_at_utc")
    payload["_hours_to_first_pitch"] = brief.get("hours_to_first_pitch")
    js = json.dumps(payload, sort_keys=True, default=str)
    did = str(uuid.uuid4())
    con.execute(
        "INSERT INTO decisions (id, ts_utc, bot, mentality, exit_mode, "
        "game_key, game_pk, starts_utc, window, kind, ticker, side, "
        "quoted_price_c, conviction, stated_prob_c, edge_c, stake_usd, "
        "reasoning_json, reasoning_sha1, outcome_known) "
        "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,0)",
        (did, now(), bot, mentality, exit_mode,
         brief.get("kalshi_game_key") or f"pk{brief.get('game_pk')}",
         brief.get("game_pk"), brief.get("starts_utc"), window, kind,
         getattr(intent, "ticker", None), getattr(intent, "side", None),
         getattr(intent, "entry_price_c", None),
         getattr(intent, "conviction", None),
         getattr(intent, "stated_prob_c", None),
         getattr(intent, "edge_c", None), stake_usd, js, _sha1(js)))
    return did


def queue_open(con, *, decision_id, bot, brief, intent, contracts):
    """An intention to open, which fills against the NEXT tick's book."""
    pid = str(uuid.uuid4())
    con.execute(
        "INSERT INTO pending (id, created_utc, bot, decision_id, game_key, "
        "ticker, side, intent, contracts, max_price_c, min_price_c, "
        "position_id) VALUES (?,?,?,?,?,?,?, 'open', ?,?,NULL,NULL)",
        (pid, now(), bot, decision_id,
         brief.get("kalshi_game_key") or f"pk{brief.get('game_pk')}",
         intent.ticker, intent.side, contracts,
         intent.entry_price_c + 1))     # allow one tick of adverse move
    return pid


def queue_close(con, *, position, reason_decision_id, min_price_c=None,
                max_price_c=None):
    pid = str(uuid.uuid4())
    con.execute(
        "INSERT INTO pending (id, created_utc, bot, decision_id, game_key, "
        "ticker, side, intent, contracts, max_price_c, min_price_c, "
        "position_id) VALUES (?,?,?,?,?,?,?, 'close', ?,?,?,?)",
        (pid, now(), position["bot"], reason_decision_id,
         position["game_key"], position["ticker"], position["side"],
         position["contracts"], max_price_c, min_price_c, position["id"]))
    return pid


# --------------------------------------------------------------- the fills

def _exec_price(row, side, action):
    """What a taker pays or receives. There is no mid here, ever."""
    if action == "open":
        return (row["ask"], row["ask_size"]) if side == "YES" \
            else (100 - row["bid"], row["bid_size"])
    # closing a YES means selling YES, i.e. hitting the bid
    return (row["bid"], row["bid_size"]) if side == "YES" \
        else (100 - row["ask"], row["ask_size"])


def fill_pending(con, book_by_ticker):
    """Fill every pending intention against THIS tick's book.

    A pending row was written on an earlier tick, so this is the latency model:
    a decision can never fill at the price that triggered it.
    """
    filled, expired = 0, 0
    for p in con.execute("SELECT * FROM pending").fetchall():
        age = (datetime.now(timezone.utc)
               - datetime.fromisoformat(p["created_utc"])).total_seconds()
        if age > PENDING_MAX_AGE_S:
            con.execute("DELETE FROM pending WHERE id=?", (p["id"],))
            expired += 1
            continue
        row = book_by_ticker.get(p["ticker"])
        if not row:
            continue
        price, size = _exec_price(row, p["side"], p["intent"])
        if price <= 0 or price >= 100:
            continue
        if p["intent"] == "open":
            if p["max_price_c"] is not None and price > p["max_price_c"]:
                continue        # the book moved against the intention
            n = min(p["contracts"], int(max(0.0, size) * DEPTH_CAP_FRAC))
            if n < 1:
                continue
            fee = float(fee_order_cents(price, n))
            posid = str(uuid.uuid4())
            con.execute(
                "INSERT INTO positions (id, bot, game_key, game_pk, ticker, "
                "side, contracts, entry_price_c, entry_fee_c, opened_utc, "
                "exit_mode, status, decision_id) "
                "VALUES (?,?,?,?,?,?,?,?,?,?,?, 'open', ?)",
                (posid, p["bot"], p["game_key"],
                 con.execute("SELECT game_pk FROM decisions WHERE id=?",
                             (p["decision_id"],)).fetchone()["game_pk"],
                 p["ticker"], p["side"], n, price, fee, now(),
                 p["bot"].split("__")[1], p["decision_id"]))
            con.execute(
                "INSERT INTO fills (id, decision_id, ts_utc, bot, game_key, "
                "ticker, side, action, price_c, contracts, fee_c, slippage_c, "
                "book_size_at_fill) VALUES (?,?,?,?,?,?,?, 'open', ?,?,?,?,?)",
                (str(uuid.uuid4()), p["decision_id"], now(), p["bot"],
                 p["game_key"], p["ticker"], p["side"], price, n, fee,
                 0.0, size))
        else:
            pos = con.execute("SELECT * FROM positions WHERE id=?",
                              (p["position_id"],)).fetchone()
            if not pos or pos["status"] != "open":
                con.execute("DELETE FROM pending WHERE id=?", (p["id"],))
                continue
            n = pos["contracts"]
            fee = float(fee_order_cents(price, n))
            gross = (price - pos["entry_price_c"]) * n
            pnl = gross - pos["entry_fee_c"] - fee
            con.execute(
                "UPDATE positions SET status='closed', closed_utc=?, "
                "exit_price_c=?, exit_fee_c=?, pnl_c=? WHERE id=?",
                (now(), price, fee, pnl, pos["id"]))
            con.execute(
                "INSERT INTO fills (id, decision_id, ts_utc, bot, game_key, "
                "ticker, side, action, price_c, contracts, fee_c, slippage_c, "
                "book_size_at_fill) VALUES (?,?,?,?,?,?,?, 'close', ?,?,?,?,?)",
                (str(uuid.uuid4()), p["decision_id"], now(), p["bot"],
                 p["game_key"], p["ticker"], p["side"], price, n, fee,
                 0.0, size))
        con.execute("DELETE FROM pending WHERE id=?", (p["id"],))
        filled += 1
    con.commit()
    return filled, expired


# ----------------------------------------------------------------- the exits

def manage_exits(con, book_by_ticker):
    """Exit-mode behaviour. `hold` never exits; the other two use +/-12c.

    Symmetric take-profit and stop-loss, so the exit modes are not secretly
    directional. The archive measured a stop-loss alone moving one tennis test
    from +0.62c to -3.77c, which is why `hold` is expected to win.
    """
    n = 0
    for pos in con.execute(
            "SELECT * FROM positions WHERE status='open'").fetchall():
        mode = pos["exit_mode"]
        if mode == "hold":
            continue
        row = book_by_ticker.get(pos["ticker"])
        if not row:
            continue
        mark, _ = _exec_price(row, pos["side"], "close")
        move = mark - pos["entry_price_c"]
        if move >= TAKE_PROFIT_C or move <= -STOP_LOSS_C:
            already = con.execute(
                "SELECT COUNT(*) c FROM pending WHERE position_id=?",
                (pos["id"],)).fetchone()["c"]
            if already:
                continue
            queue_close(con, position=pos, reason_decision_id=pos["decision_id"])
            n += 1
    con.commit()
    return n


def settle_open_positions(con, settlements):
    """Settle at 100 or 0. Kalshi charges its fee on the TRADE, so a position
    held to settlement pays ONE fee, not two -- which is exactly why the
    `hold` arm has a lower cost bar than the others and why that must not be
    quietly reversed."""
    n = 0
    for pos in con.execute(
            "SELECT * FROM positions WHERE status='open'").fetchall():
        s = settlements.get(pos["game_pk"])
        if not s:
            continue
        val = settle_value_c(pos, s)
        if val is None:
            continue
        pnl = (val - pos["entry_price_c"]) * pos["contracts"] - pos["entry_fee_c"]
        con.execute(
            "UPDATE positions SET status='settled', closed_utc=?, "
            "settle_value_c=?, pnl_c=? WHERE id=?",
            (now(), val, pnl, pos["id"]))
        n += 1
    con.commit()
    return n


def settle_value_c(pos, s):
    """100 if the contract's YES condition happened, else 0, from the ticker.

    KXMLBGAME-...-<CLUB>  : YES iff that club won.
    KXMLBTOTAL-...-<k>    : YES iff total runs > floor_strike. The strike is
                            recovered from the decision's own reasoning rather
                            than from the suffix, because the suffix is an
                            index and NOT the strike (rung '-9' is 'Over 8.5').
    """
    import kalshi as K
    parts = K.ticker_parts(pos["ticker"])
    if not parts:
        return None
    suffix = (parts.get("suffix") or "").upper()
    if parts["series"] == "KXMLBGAME":
        club = K.CODE.get(suffix)
        if not club:
            return None
        # ⚠ A TIE IS NOT A RESULT. Baseball games do not end level, so a tied
        # settlement row means the score was read before the game finished.
        # `home_won = home > away` silently turned every one of those into
        # "the away team won" -- 18 such rows existed and settled 107
        # positions. Refuse instead: an unsettled position is settled
        # correctly on a later tick, a wrongly settled one never is.
        if s["home_runs"] == s["away_runs"]:
            return None
        home_won = s["home_runs"] > s["away_runs"]
        is_home = (suffix == parts["home"])
        yes = (home_won == is_home)
        return (100 if yes else 0) if pos["side"] == "YES" else (0 if yes else 100)
    if parts["series"] == "KXMLBTOTAL":
        strike = _strike_for(pos["ticker"])
        if strike is None:
            return None
        yes = s["total_runs"] > strike
        return (100 if yes else 0) if pos["side"] == "YES" else (0 if yes else 100)
    return None


_STRIKE_CACHE: dict[str, float] = {}
STRIKES_FILE = DB.parent / "strikes.json"


def _strike_for(ticker):
    """The rung's `floor_strike`, recorded while the market was still open.

    Deliberately NOT parsed from the ticker suffix. 'KXMLBTOTAL-...-9' is the
    NINTH RUNG and its strike is 8.5; reading the suffix as the strike would
    settle every totals position exactly half a run high, which is a full tick
    of the ladder and would silently invert close calls. Kalshi's window is
    ~69 days and closed markets 404, so the strike has to be captured before
    settlement, not looked up after it.
    """
    if not _STRIKE_CACHE and STRIKES_FILE.exists():
        try:
            _STRIKE_CACHE.update({k: float(v) for k, v in
                                  json.loads(STRIKES_FILE.read_text()).items()})
        except (json.JSONDecodeError, ValueError, TypeError):
            pass
    return _STRIKE_CACHE.get(ticker)


def load_strikes(rows):
    """Record every live rung's strike to disk. Called on every tick."""
    if STRIKES_FILE.exists():
        try:
            _STRIKE_CACHE.update({k: float(v) for k, v in
                                  json.loads(STRIKES_FILE.read_text()).items()})
        except (json.JSONDecodeError, ValueError, TypeError):
            pass
    for r in rows:
        if r.get("floor_strike") is not None:
            _STRIKE_CACHE[r["ticker"]] = float(r["floor_strike"])
    STRIKES_FILE.parent.mkdir(parents=True, exist_ok=True)
    STRIKES_FILE.write_text(json.dumps(_STRIKE_CACHE, sort_keys=True))
    return len(_STRIKE_CACHE)

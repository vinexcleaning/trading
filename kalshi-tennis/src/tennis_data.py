"""Shared loading and name-normalisation utilities for the Sackmann + Kalshi data.

Kept in one place because every stage needs the same player-name matching; if
matching is sloppy the coverage audit understates coverage and every later
stage inherits the error.
"""
import functools
import glob
import json
import pathlib
import re
import unicodedata

import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[1]
SACK = ROOT / "data" / "sackmann"
KALSHI = ROOT / "data" / "kalshi"
CACHE = ROOT / "data" / "cache"

# Sackmann file groups -> (tour, tier). "tier" is the level we care about for
# population rates and for the Stage 0 split.
FILE_GROUPS = {
    "atp/atp_matches_[12]*.csv": ("ATP", "main"),
    "atp/atp_matches_qual_chall_*.csv": ("ATP", "chall"),
    "atp/atp_matches_futures_*.csv": ("ATP", "itf"),
    "wta/wta_matches_[12]*.csv": ("WTA", "main"),
    "wta/wta_matches_qual_itf_*.csv": ("WTA", "itf"),
}

SUFFIXES = {"jr", "jr.", "sr", "ii", "iii", "iv"}


def strip_accents(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", s)
                   if not unicodedata.combining(c))


@functools.lru_cache(maxsize=200_000)
def norm_name(name) -> str:
    """Aggressive but order-preserving normalisation of a player name."""
    if not isinstance(name, str):
        return ""
    s = strip_accents(name).lower()
    s = s.replace("-", " ").replace("'", "").replace(".", " ").replace("`", "")
    s = re.sub(r"[^a-z ]", " ", s)
    toks = [t for t in s.split() if t and t not in SUFFIXES]
    return " ".join(toks)


def name_key(name) -> str:
    """Order-insensitive key, for 'Si Yu Dong' vs 'Dong Si Yu' style flips."""
    return " ".join(sorted(norm_name(name).split()))


def last_initial_key(name) -> str:
    """Last token + first initial, e.g. 'Ben Shelton' -> 'shelton|b'."""
    toks = norm_name(name).split()
    if not toks:
        return ""
    return f"{toks[-1]}|{toks[0][0]}"


# --------------------------------------------------------------------------
# Sackmann matches
# --------------------------------------------------------------------------

def _read_group(pattern, tour, tier):
    frames = []
    for f in sorted(glob.glob(str(SACK / pattern))):
        df = pd.read_csv(f, low_memory=False, encoding="utf-8",
                         encoding_errors="replace")
        frames.append(df)
    if not frames:
        return pd.DataFrame()
    df = pd.concat(frames, ignore_index=True)
    df["tour"] = tour
    df["tier"] = tier
    return df


def load_matches(force=False) -> pd.DataFrame:
    """All singles matches, one row per match, with tour/tier tags."""
    CACHE.mkdir(parents=True, exist_ok=True)
    cache = CACHE / "matches.parquet"
    if cache.exists() and not force:
        return pd.read_parquet(cache)

    parts = [_read_group(pat, tour, tier)
             for pat, (tour, tier) in FILE_GROUPS.items()]
    df = pd.concat(parts, ignore_index=True)

    df["date"] = pd.to_datetime(df["tourney_date"], format="%Y%m%d",
                                errors="coerce")
    df = df[df["date"].notna()].copy()

    # Surface casing is inconsistent in the futures/itf files ('clay' vs 'Clay')
    df["surface"] = df["surface"].astype("string").str.strip().str.capitalize()
    df.loc[~df["surface"].isin(["Hard", "Clay", "Grass", "Carpet"]), "surface"] = pd.NA

    for col in ("winner_name", "loser_name"):
        df[col] = df[col].astype("string")

    # Year files disagree on dtypes (e.g. draw_size is str in some, int in
    # others). Force numerics numeric and everything else to string so the
    # concatenated frame is round-trippable through parquet.
    numeric = [
        "draw_size", "match_num", "winner_id", "loser_id", "winner_ht",
        "loser_ht", "winner_age", "loser_age", "best_of", "minutes",
        "w_ace", "w_df", "w_svpt", "w_1stIn", "w_1stWon", "w_2ndWon",
        "w_SvGms", "w_bpSaved", "w_bpFaced", "l_ace", "l_df", "l_svpt",
        "l_1stIn", "l_1stWon", "l_2ndWon", "l_SvGms", "l_bpSaved",
        "l_bpFaced", "winner_rank", "winner_rank_points", "loser_rank",
        "loser_rank_points", "winner_seed", "loser_seed",
    ]
    for col in numeric:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    for col in df.columns:
        if df[col].dtype == object:
            df[col] = df[col].astype("string")

    # A match has usable serve stats only if service points were recorded for
    # BOTH players -- a one-sided row cannot produce return stats.
    df["has_serve"] = (
        df["w_svpt"].notna() & (df["w_svpt"] > 0)
        & df["l_svpt"].notna() & (df["l_svpt"] > 0)
    )

    df.to_parquet(cache, index=False)
    return df


def to_long(matches: pd.DataFrame) -> pd.DataFrame:
    """One row per (player, match) -- the natural shape for per-player counts."""
    base = ["date", "surface", "tour", "tier", "has_serve", "tourney_name",
            "tourney_level", "round", "best_of", "minutes"]
    w = matches[base + ["winner_name", "winner_id"]].rename(
        columns={"winner_name": "player", "winner_id": "player_id"})
    w["won"] = 1
    l = matches[base + ["loser_name", "loser_id"]].rename(
        columns={"loser_name": "player", "loser_id": "player_id"})
    l["won"] = 0
    out = pd.concat([w, l], ignore_index=True)
    out["player"] = out["player"].astype("string")
    return out[out["player"].notna()]


# --------------------------------------------------------------------------
# Kalshi markets
# --------------------------------------------------------------------------

_TOURNEY_RE = re.compile(
    r"\bin the (\d{4} .+?)\s+"
    r"((?:Qualification|Qualifying)(?:\s+Round\s*\d*)?|Round Of \d+|"
    r"Quarterfinals?|Semifinals?|Finals?|Round Robin|"
    r"\d(?:st|nd|rd|th) Round)\b",
    re.I,
)

# Kalshi head-to-head SINGLES series -> (tour, tier).
# Tiers map onto the Sackmann file groups: 'itf' is atp_matches_futures_* for
# men and wta_matches_qual_itf_* for women.
SERIES_TIER = {
    "KXATPMATCH": ("ATP", "main"),
    "KXWTAMATCH": ("WTA", "main"),
    "KXATPCHALLENGERMATCH": ("ATP", "chall"),
    "KXCHALLENGERMATCH": ("ATP", "chall"),
    "KXWTACHALLENGERMATCH": ("WTA", "chall"),
    "KXITFMATCH": ("ATP", "itf"),
    "KXITFWMATCH": ("WTA", "itf"),
    "KXDAVISCUPMATCH": ("ATP", "main"),
    "KXUNITEDCUPMATCH": ("MIX", "main"),
}


def load_kalshi_events(force=False) -> pd.DataFrame:
    """One row per Kalshi match (event), with both players and both prices."""
    CACHE.mkdir(parents=True, exist_ok=True)
    cache = CACHE / "kalshi_events.parquet"
    if cache.exists() and not force:
        return pd.read_parquet(cache)

    raw = json.loads((KALSHI / "tennis_markets.json").read_text(encoding="utf-8"))
    by_event = {}
    for series, rows in raw.items():
        if series not in SERIES_TIER:
            continue
        for m in rows:
            by_event.setdefault(m["event_ticker"], []).append((series, m))

    recs = []
    for ev, pairs in by_event.items():
        if len(pairs) != 2:
            continue
        series = pairs[0][0]
        tour, tier = SERIES_TIER[series]
        a, b = pairs[0][1], pairs[1][1]

        rules = a.get("rules_primary") or ""
        g = _TOURNEY_RE.search(rules)
        tourney_raw, rnd = (g.group(1), g.group(2)) if g else (None, None)

        recs.append({
            "event_ticker": ev,
            "series": series,
            "tour": tour,
            "tier": tier,
            "tourney_raw": tourney_raw,
            "round": rnd,
            "player_a": a.get("yes_sub_title"),
            "player_b": b.get("yes_sub_title"),
            "ticker_a": a.get("ticker"),
            "ticker_b": b.get("ticker"),
            "status": a.get("status"),
            "result_a": a.get("result"),
            "result_b": b.get("result"),
            "open_time": a.get("open_time"),
            "close_time": a.get("close_time"),
            "occurrence": a.get("occurrence_datetime"),
            "last_price_a": _f(a.get("last_price_dollars")),
            "yes_bid_a": _f(a.get("yes_bid_dollars")),
            "yes_ask_a": _f(a.get("yes_ask_dollars")),
            "volume_a": _f(a.get("volume_fp")),
            "open_interest_a": _f(a.get("open_interest_fp")),
        })

    df = pd.DataFrame(recs)
    df["date"] = pd.to_datetime(df["occurrence"], errors="coerce", utc=True)
    df["open_dt"] = pd.to_datetime(df["open_time"], errors="coerce", utc=True)
    df["venue"] = df["tourney_raw"].map(parse_venue)
    df = df[df["player_a"].notna() & df["player_b"].notna()]
    df.to_parquet(cache, index=False)
    return df


def _f(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return float("nan")


_VENUE_STRIP = re.compile(
    r"^\d{4}\s+|"
    r"\b(ATP|WTA)\b\s*(Challenger)?\s*|"
    r"\b125K?\b\s*|"
    r"\b(Men|Women)('s)?\s+Singles\b\s*|"
    r"\bQualification\b\s*|"
    r"\bpresented by.*$",
    re.I,
)


def parse_venue(s):
    """'2026 ATP Challenger Vancouver' -> 'vancouver', '2026 M25 Pitesti' -> 'pitesti'."""
    if not isinstance(s, str):
        return None
    v = _VENUE_STRIP.sub(" ", s)
    v = re.sub(r"\(([^)]*)\)", " ", v)     # 'Lincoln (NE)' -> 'Lincoln'
    # ITF events are prize-level coded: 'M15', 'M25', 'W35'. norm_name strips
    # the digits and would otherwise leave a stray 'm'/'w' token glued to the
    # venue, which never matches the Sackmann key.
    v = re.sub(r"\b[MW]\d{2,3}\b", " ", v, flags=re.I)
    v = re.sub(r"\s+", " ", v).strip()
    v = re.sub(r"\s+\d+$", "", v)          # 'Nottingham 2' -> 'Nottingham'
    v = norm_name(v)
    v = re.sub(r"^(m|w)\s+", "", v).strip()
    return v or None


# --------------------------------------------------------------------------
# surface inference for Kalshi tournaments
# --------------------------------------------------------------------------

# Kalshi names some events by city where Sackmann names them by club/label.
MANUAL_SURFACE = {
    "wimbledon": "Grass",
    "french open": "Clay",
    "us open": "Hard",
    "australian open": "Hard",
    "roland garros": "Clay",
    "london": "Grass",      # 'ATP London' is the Queen's Club grass event
}

# Sackmann ITF/Challenger rows carry tier markers in tourney_name:
#   'M-ITF' style 'm foggia' / 'w dublin' prefixes, ' k' and ' ch'/' q' suffixes
_TOURNEY_MARKERS = re.compile(r"^(m|w)\s+|\s+(k|ch|q)$", re.I)

_TIER_PRIORITY = {"main": 0, "chall": 1, "itf": 2}


def sack_venue_key(name: str) -> str:
    """Reduce a Sackmann tourney_name to a comparable venue key."""
    if not isinstance(name, str):
        return ""
    v = re.sub(r"\s+(CH|Q)$", "", name, flags=re.I)
    v = re.sub(r"\s+\d+$", "", v)
    v = norm_name(v)
    prev = None
    while prev != v:                       # 'm plovdiv k' -> 'plovdiv'
        prev = v
        v = _TOURNEY_MARKERS.sub("", v).strip()
    return v


def build_surface_map(matches: pd.DataFrame) -> dict:
    """venue key -> {tier: surface}, from recent events, per tier.

    Kept per-tier rather than collapsed to a single modal surface: a venue can
    host a legacy ITF carpet event and a modern hard-court Challenger, and
    letting the ITF row answer for the Challenger market is how 2026 Dublin
    ends up labelled Carpet.
    """
    recent = matches[matches["date"] >= "2015-01-01"].copy()
    recent = recent[recent["surface"].notna()]
    recent["venue"] = [sack_venue_key(x) for x in
                       recent["tourney_name"].astype("string").fillna("")]
    recent = recent[recent["venue"] != ""]

    agg = (recent.groupby(["venue", "tier", "surface"], observed=True)
           .size().reset_index(name="n")
           .sort_values("n", ascending=False)
           .drop_duplicates(["venue", "tier"]))
    out = {}
    for _, r in agg.iterrows():
        out.setdefault(r["venue"], {})[r["tier"]] = r["surface"]
    return out


# Carpet is effectively extinct above ITF level; inferring it for a 2026 main
# or Challenger market from a legacy ITF row is a mapping error, not a finding.
_LOOKUP_ORDER = {
    "main": ("main", "chall", "itf"),
    "chall": ("chall", "main", "itf"),
    "itf": ("itf", "chall", "main"),
}


def surface_for(venue, smap, tier="main", cutoff=90):
    if not isinstance(venue, str) or not venue:
        return None
    if venue in MANUAL_SURFACE:
        return MANUAL_SURFACE[venue]
    entry = smap.get(venue)
    if entry is None:
        from rapidfuzz import fuzz, process
        hit = process.extractOne(venue, smap.keys(), scorer=fuzz.ratio,
                                 score_cutoff=cutoff)
        if not hit:
            return None
        entry = smap[hit[0]]
    for t in _LOOKUP_ORDER.get(tier, ("main", "chall", "itf")):
        if t in entry:
            s = entry[t]
            if s == "Carpet" and tier in ("main", "chall") and t == "itf":
                return None      # legacy ITF carpet cannot speak for a 2026 event
            return s
    return None


# --------------------------------------------------------------------------
# player name resolution
# --------------------------------------------------------------------------

FUZZ_THRESHOLD = 92


def build_player_index(long: pd.DataFrame):
    """Lookup structures mapping normalised names -> canonical Sackmann name."""
    from collections import defaultdict
    names = long["player"].dropna().unique().tolist()
    exact, key, li = {}, {}, {}
    by_token = defaultdict(set)
    for n in names:
        toks = norm_name(n)
        exact.setdefault(toks, n)
        key.setdefault(name_key(n), n)
        li.setdefault(last_initial_key(n), []).append(n)
        for t in toks.split():
            by_token[t].add(n)
    return {"names": names, "exact": exact, "key": key, "li": li,
            "by_token": by_token}


def _subset_match(kalshi_name, idx):
    """Handle multi-part surnames: 'Daniel Merida' vs 'Daniel Merida Aguilar'.

    Accepts only when one token set contains the other AND the first or last
    token agrees AND exactly one Sackmann name qualifies.
    """
    from rapidfuzz import fuzz
    toks = norm_name(kalshi_name).split()
    if len(toks) < 2:
        return None
    tset = set(toks)
    cand = set()
    for t in tset:
        cand |= idx["by_token"].get(t, set())

    hits = []
    for c in cand:
        ctoks = norm_name(c).split()
        cset = set(ctoks)
        if not (tset <= cset or cset <= tset):
            continue
        first_ok = fuzz.ratio(toks[0], ctoks[0]) >= 78
        last_ok = toks[-1] == ctoks[-1]
        if first_ok or last_ok:
            hits.append(c)
    return hits[0] if len(hits) == 1 else None


def resolve(kalshi_name, idx):
    """Return (canonical_sackmann_name | None, how)."""
    from rapidfuzz import fuzz, process
    n = norm_name(kalshi_name)
    if not n:
        return None, "empty"
    if n in idx["exact"]:
        return idx["exact"][n], "exact"
    k = name_key(kalshi_name)
    if k in idx["key"]:
        return idx["key"][k], "token"
    cand = idx["li"].get(last_initial_key(kalshi_name), [])
    if len(cand) == 1:
        return cand[0], "last+initial"
    if len(cand) > 1:
        hit = process.extractOne(n, [norm_name(c) for c in cand],
                                 scorer=fuzz.ratio, score_cutoff=FUZZ_THRESHOLD)
        if hit:
            return cand[hit[2]], "last+initial-fuzzy"
    sub = _subset_match(kalshi_name, idx)
    if sub:
        return sub, "subset"
    hit = process.extractOne(n, idx["exact"].keys(), scorer=fuzz.WRatio,
                             score_cutoff=FUZZ_THRESHOLD)
    if hit:
        return idx["exact"][hit[0]], "fuzzy"
    return None, "unmatched"

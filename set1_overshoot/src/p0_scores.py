"""Phase 0d -- build a scoreline truth table for detector validation.

Kalshi publishes no scoreline, so the Phase 1 detector cannot be validated from
Kalshi data alone. Two external sources are joined in:

  * Sackmann (frozen local mirror, tourney weeks up to 2026-06-02) -- covers
    ATP/WTA/Challenger/ITF, i.e. the whole Kalshi book, but only the first
    ~9 days of the Kalshi window.
  * tennis-data.co.uk (local xlsx, to 2026-07-26) -- covers only ATP/WTA main
    tour, but spans almost the whole window.

Together they give a validation set that is both broad in tier and broad in
time; neither alone is. Matching is on (unordered pair of surname+initial keys)
within a date tolerance.
"""
import datetime as dt
import json
import pathlib
import sys

import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
OLD = ROOT.parent / "data"
sys.path.insert(0, str(ROOT.parent / "src"))
import tennis_data as td  # noqa: E402


def pair_key(a, b, keyfn=None):
    keyfn = keyfn or td.last_initial_key
    ka, kb = keyfn(a), keyfn(b)
    if not ka or not kb:
        return None
    return "|".join(sorted([ka, kb]))


def td_key(name):
    """tennis-data writes names surname-first: 'Valentova T.', 'De Minaur A.'.

    td.last_initial_key assumes given-name-first and would key that as 't|v'.
    Here the surname is everything before the trailing initial token.
    """
    toks = td.norm_name(name).split()
    if len(toks) < 2:
        return ""
    initial = toks[-1][0]
    surname = toks[-2] if len(toks[-1]) == 1 else toks[-1]
    if len(toks[-1]) > 1:          # no trailing initial -- fall back
        return td.last_initial_key(name)
    return f"{surname}|{initial}"


# ---------------------------------------------------------------- Kalshi side
def kalshi_events():
    raw = json.loads((DATA / "markets_raw.json").read_text(encoding="utf-8"))
    by_event = {}
    for series, mkts in raw.items():
        for m in mkts:
            by_event.setdefault(m["event_ticker"], []).append(m)

    uni = pd.read_parquet(DATA / "universe.parquet")
    keep_ticker = dict(zip(uni["event_ticker"], uni["ticker"]))

    rows = []
    for ev, tick in keep_ticker.items():
        ms = by_event.get(ev, [])
        if len(ms) != 2:
            continue
        kept = next((m for m in ms if m["ticker"] == tick), None)
        other = next((m for m in ms if m["ticker"] != tick), None)
        if kept is None or other is None:
            continue
        rows.append({
            "event_ticker": ev,
            "ticker": tick,
            "player": kept.get("yes_sub_title"),
            "opponent": other.get("yes_sub_title"),
            "player_won": kept.get("result") == "yes",
        })
    df = pd.DataFrame(rows)
    df = df.merge(uni[["event_ticker", "tour", "close_time", "open_time"]],
                  on="event_ticker", how="left")
    df["pair"] = [pair_key(a, b) for a, b in zip(df["player"], df["opponent"])]
    df["kdate"] = pd.to_datetime(df["close_time"]).dt.tz_convert("UTC").dt.date
    return df


# ------------------------------------------------------------- truth sources
def parse_sackmann_score(score):
    """'6-4 3-6 7-5' -> (set1_games_winner, set1_games_loser) or None.

    Returned from the perspective of the MATCH winner. Retirements, walkovers
    and unparseable strings return None rather than a guess.
    """
    if not isinstance(score, str):
        return None
    s = score.strip()
    low = s.lower()
    if any(w in low for w in ("ret", "w/o", "walkover", "def", "abd",
                              "unfinished", "in progress")):
        return None
    first = s.split()[0] if s.split() else ""
    first = first.split("(")[0]
    if "-" not in first:
        return None
    a, _, b = first.partition("-")
    try:
        return int(a), int(b)
    except ValueError:
        return None


def sackmann_truth():
    m = pd.read_parquet(OLD / "cache" / "matches.parquet",
                        columns=["date", "winner_name", "loser_name", "score",
                                 "tour", "tier", "minutes"])
    m = m[m["date"] >= "2026-05-15"].copy()
    out = []
    for r in m.itertuples():
        g = parse_sackmann_score(r.score)
        if g is None:
            continue
        pk = pair_key(r.winner_name, r.loser_name)
        if pk is None:
            continue
        out.append({"pair": pk, "sdate": r.date.date(),
                    "winner": r.winner_name, "loser": r.loser_name,
                    "winner_key": td.last_initial_key(r.winner_name),
                    "loser_key": td.last_initial_key(r.loser_name),
                    "s1_w": g[0], "s1_l": g[1], "minutes": r.minutes,
                    "src": "sackmann", "score": r.score})
    df = pd.DataFrame(out)
    # tourney_date is the tournament START, so a match can be up to ~13 days later
    df["lo"] = df["sdate"]
    df["hi"] = [d + dt.timedelta(days=13) for d in df["sdate"]]
    return df


def tennisdata_truth():
    t = pd.read_parquet(OLD / "tennisdata" / "tennisdata_all.parquet")
    t = t[t["Date"] >= "2026-05-15"].copy()
    t = t[t["Comment"].astype(str).str.strip().str.lower() == "completed"]
    out = []
    for r in t.itertuples():
        try:
            w1, l1 = int(r.W1), int(r.L1)
        except (TypeError, ValueError):
            continue
        pk = pair_key(r.Winner, r.Loser, td_key)
        if pk is None:
            continue
        out.append({"pair": pk, "sdate": r.Date.date(),
                    "winner": r.Winner, "loser": r.Loser,
                    "winner_key": td_key(r.Winner),
                    "loser_key": td_key(r.Loser),
                    "s1_w": w1, "s1_l": l1, "minutes": float("nan"),
                    "src": "tennisdata", "score": f"{w1}-{l1}"})
    df = pd.DataFrame(out)
    df["lo"] = [d - dt.timedelta(days=2) for d in df["sdate"]]
    df["hi"] = [d + dt.timedelta(days=2) for d in df["sdate"]]
    return df


def main():
    ke = kalshi_events()
    ke[["event_ticker", "ticker", "player", "opponent", "player_won",
        "tour"]].to_parquet(DATA / "players.parquet", index=False)
    print(f"kalshi events                   {len(ke):,}")
    print(f"  with a usable pair key        {ke['pair'].notna().sum():,}")

    truth = pd.concat([sackmann_truth(), tennisdata_truth()], ignore_index=True)
    print(f"\ntruth rows (set-1 parsed)       {len(truth):,}")
    print(truth.groupby("src").size().to_string())

    # join on pair, then filter by date window; drop ambiguous multi-hits
    j = ke.merge(truth, on="pair", how="inner")
    j = j[(j["kdate"] >= j["lo"]) & (j["kdate"] <= j["hi"])]
    n_before = j["event_ticker"].nunique()
    cnt = j.groupby("event_ticker").size()
    amb = set(cnt[cnt > 1].index)
    # a duplicate is only a problem if the sources disagree on who won set 1
    j["s1_key"] = j["winner_key"].where(j["s1_w"] > j["s1_l"], j["loser_key"])
    agree = j.groupby("event_ticker")["s1_key"].nunique()
    conflict = set(agree[agree > 1].index)
    j = j[~j["event_ticker"].isin(conflict)]
    j = j.sort_values(["event_ticker", "src"]).groupby(
        "event_ticker", as_index=False).head(1)

    print(f"\nmatched kalshi events           {n_before:,}")
    print(f"  multi-hit (deduped)           {len(amb):,}")
    print(f"  source conflict (dropped)     {len(conflict):,}")
    print(f"  final truth rows              {len(j):,}")

    # who won set 1, expressed as: did the KEPT market's player win set 1?
    j["player_key"] = j["player"].map(td.last_initial_key)
    j["opp_key"] = j["opponent"].map(td.last_initial_key)
    ok = (j["s1_key"] == j["player_key"]) | (j["s1_key"] == j["opp_key"])
    print(f"  set-1 winner resolvable       {ok.sum():,}")
    j = j[ok].copy()
    j["player_won_s1"] = j["s1_key"] == j["player_key"]

    # sanity: Kalshi's own settlement must agree with the truth source's winner
    j["truth_player_won"] = j["winner_key"] == j["player_key"]
    agree_match = (j["truth_player_won"] == j["player_won"]).mean()
    print(f"\n  match-winner agreement with Kalshi settlement: {agree_match:.4f}")
    print("  (this is the join-quality check -- anything below ~0.99 means "
          "the name match is wrong, not the detector)")
    j = j[j["truth_player_won"] == j["player_won"]].copy()
    print(f"  after dropping disagreements  {len(j):,}")

    print("\nby tour:")
    print(j.groupby("tour").size().to_string())
    print("\nby source:")
    print(j.groupby("src").size().to_string())
    print("\nby month:")
    print(j.groupby(pd.to_datetime(j["kdate"]).dt.to_period("M")
                    .astype(str)).size().to_string())

    cols = ["event_ticker", "ticker", "tour", "player", "opponent",
            "player_won", "player_won_s1", "s1_w", "s1_l", "minutes", "score",
            "src", "kdate"]
    j[cols].to_parquet(DATA / "truth_set1.parquet", index=False)
    print(f"\n-> {DATA / 'truth_set1.parquet'}")


if __name__ == "__main__":
    main()

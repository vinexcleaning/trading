"""Stage 1 -- feature pipeline.

One chronological pass over every match. For each match we EMIT features from
the current state, THEN update the state with the result. That ordering is the
whole game: it guarantees every feature is strictly pre-match, so nothing the
model sees could have been known only after the match finished.

Rates are emitted as weighted numerator/denominator pairs rather than finished
ratios, because Stage 2 has to shrink them toward tier-and-surface population
means and needs the effective sample size to do it.

Time weighting is exponential decay with a 182-day half-life: a match 12 months
old carries a quarter the weight of today's. That approximates the spec's
"12-month window" without a hard cliff at 365 days.

Features are written into preallocated float32 arrays rather than a list of
dicts -- at 1.75M matches x ~80 features the dict form needs tens of GB and
dies. Static/metadata columns are copied straight off the source frame at the
end, since the loop preserves row order.
"""
import math
import pathlib
import re
import sys
from collections import defaultdict, deque

import numpy as np
import pandas as pd

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import tennis_data as td  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[1]
CACHE = ROOT / "data" / "cache"

HALFLIFE_DAYS = 182.0
DECAY_LN2 = math.log(2.0)
ELO_START = 1500.0
SURFACES = ("Hard", "Clay", "Grass", "Carpet")

ACC_FIELDS = (
    "n", "svpt", "first_in", "first_won", "second_won", "sv_gms",
    "breaks_suffered", "ace", "df", "rtn_pt", "rtn_won", "rtn_gms",
    "breaks_made", "minutes",
)
FATIGUE = ("matches_7d", "matches_14d", "minutes_14d", "days_since",
           "back_to_back")
H2H_COLS = ("h2h_w_wins", "h2h_l_wins", "h2h_played", "h2h_w_wins_surf",
            "h2h_l_wins_surf", "h2h_played_surf", "h2h_days_since")


class Acc:
    __slots__ = ("v", "last_day")

    def __init__(self):
        self.v = np.zeros(len(ACC_FIELDS), dtype=np.float64)
        self.last_day = None

    def decay_to(self, day):
        if self.last_day is None:
            self.last_day = day
            return
        dt = day - self.last_day
        if dt > 0:
            fct = math.exp(-DECAY_LN2 * dt / HALFLIFE_DAYS)
            self.v *= 0.0 if fct < 1e-9 else fct
            self.last_day = day


def elo_k(n):
    """FiveThirtyEight-style decaying K: fast early, stable later."""
    return 250.0 / ((n + 5.0) ** 0.4)


def elo_expected(ra, rb):
    return 1.0 / (1.0 + 10.0 ** ((rb - ra) / 400.0))


_SET_RE = re.compile(r"^(\d+)-(\d+)")


def lost_first_set(score):
    """From the winner's perspective: did the eventual winner drop set 1?"""
    if not isinstance(score, str):
        return np.nan
    s = score.strip()
    if not s or "W/O" in s.upper() or "DEF" in s.upper():
        return np.nan
    m = _SET_RE.match(s.split()[0])
    if not m:
        return np.nan
    a, b = int(m.group(1)), int(m.group(2))
    if a == b:
        return np.nan
    return 0.0 if a > b else 1.0


def n_sets(score):
    if not isinstance(score, str):
        return np.nan
    return float(sum(1 for t in score.split() if _SET_RE.match(t)))


def main():
    print("loading matches ...", flush=True)
    m = td.load_matches()
    m = m.sort_values(["date", "tourney_id", "match_num"],
                      kind="mergesort").reset_index(drop=True)

    wn = m["winner_name"].astype(object).where(m["winner_name"].notna(), None)
    ln = m["loser_name"].astype(object).where(m["loser_name"].notna(), None)
    keep = (wn.map(lambda x: isinstance(x, str))
            & ln.map(lambda x: isinstance(x, str))).to_numpy()
    m = m[keep].reset_index(drop=True)
    N = len(m)
    print(f"  {N:,} matches, {m['date'].min().date()} .. {m['date'].max().date()}")

    day = (m["date"] - pd.Timestamp("1900-01-01")).dt.days.to_numpy()

    str_cols = ["winner_name", "loser_name", "surface", "tier", "score"]
    num_cols = ["minutes",
                "w_ace", "w_df", "w_svpt", "w_1stIn", "w_1stWon", "w_2ndWon",
                "w_SvGms", "w_bpSaved", "w_bpFaced",
                "l_ace", "l_df", "l_svpt", "l_1stIn", "l_1stWon", "l_2ndWon",
                "l_SvGms", "l_bpSaved", "l_bpFaced"]
    C = {}
    for c in str_cols:
        s = m[c]
        C[c] = s.astype(object).where(s.notna(), None).to_numpy()
    for c in num_cols:
        C[c] = pd.to_numeric(m[c], errors="coerce").astype(float).to_numpy()
    has_serve = m["has_serve"].fillna(False).astype(bool).to_numpy()

    # ---- preallocate output columns --------------------------------------
    names = []
    for side in ("w", "l"):
        names += [f"{side}_elo", f"{side}_elo_n", f"{side}_elo_surf",
                  f"{side}_elo_surf_n"]
        for bucket in ("all", "surf"):
            names += [f"{side}_{bucket}_{f}" for f in ACC_FIELDS]
        names += [f"{side}_{c}" for c in FATIGUE]
    names += list(H2H_COLS)
    A = {n: np.full(N, np.nan, dtype=np.float32) for n in names}
    col = {n: A[n] for n in names}
    print(f"  {len(names)} numeric feature columns "
          f"({N * len(names) * 4 / 1e9:.2f} GB)")

    # ---- rolling state ----------------------------------------------------
    elo = defaultdict(lambda: ELO_START)
    elo_n = defaultdict(int)
    elo_s = {s: defaultdict(lambda: ELO_START) for s in SURFACES}
    elo_sn = {s: defaultdict(int) for s in SURFACES}
    acc = defaultdict(Acc)
    h2h = defaultdict(lambda: [0, 0])
    h2h_s = defaultdict(lambda: [0, 0])
    h2h_last = {}
    hist = defaultdict(deque)

    for i in range(N):
        if i % 250_000 == 0:
            print(f"  {i:,}/{N:,}", flush=True)

        w, l = C["winner_name"][i], C["loser_name"][i]
        d = int(day[i])
        surf = C["surface"][i]
        surf = surf if surf in SURFACES else None

        # ---------- EMIT (state is strictly pre-match) --------------------
        for side, p in (("w", w), ("l", l)):
            col[f"{side}_elo"][i] = elo[p]
            col[f"{side}_elo_n"][i] = elo_n[p]
            if surf is not None:
                col[f"{side}_elo_surf"][i] = elo_s[surf][p]
                col[f"{side}_elo_surf_n"][i] = elo_sn[surf][p]

            for bucket, key in (("all", (p, "ALL")),
                                ("surf", (p, surf) if surf else None)):
                if key is None:
                    continue
                a = acc[key]
                a.decay_to(d)
                v = a.v
                for j, fld in enumerate(ACC_FIELDS):
                    col[f"{side}_{bucket}_{fld}"][i] = v[j]

            dq = hist[p]
            while dq and d - dq[0][0] > 60:
                dq.popleft()
            m7 = m14 = 0
            min14 = 0.0
            for dd, mm in dq:
                gap = d - dd
                if 0 <= gap <= 14:
                    m14 += 1
                    min14 += mm
                    if gap <= 7:
                        m7 += 1
            last = dq[-1][0] if dq else None
            col[f"{side}_matches_7d"][i] = m7
            col[f"{side}_matches_14d"][i] = m14
            col[f"{side}_minutes_14d"][i] = min14
            if last is not None:
                col[f"{side}_days_since"][i] = d - last
                col[f"{side}_back_to_back"][i] = 1.0 if d - last <= 1 else 0.0
            else:
                col[f"{side}_back_to_back"][i] = 0.0

        first = w <= l
        key = (w, l) if first else (l, w)
        rec = h2h[key]
        recs = h2h_s[(key, surf)] if surf else (0, 0)
        col["h2h_w_wins"][i] = rec[0] if first else rec[1]
        col["h2h_l_wins"][i] = rec[1] if first else rec[0]
        col["h2h_played"][i] = rec[0] + rec[1]
        col["h2h_w_wins_surf"][i] = recs[0] if first else recs[1]
        col["h2h_l_wins_surf"][i] = recs[1] if first else recs[0]
        col["h2h_played_surf"][i] = recs[0] + recs[1]
        lastd = h2h_last.get(key)
        if lastd is not None:
            col["h2h_days_since"][i] = d - lastd

        # ---------- UPDATE (result now visible) ---------------------------
        ew = elo_expected(elo[w], elo[l])
        elo[w] += elo_k(elo_n[w]) * (1.0 - ew)
        elo[l] -= elo_k(elo_n[l]) * (1.0 - ew)
        elo_n[w] += 1
        elo_n[l] += 1
        if surf is not None:
            es = elo_expected(elo_s[surf][w], elo_s[surf][l])
            elo_s[surf][w] += elo_k(elo_sn[surf][w]) * (1.0 - es)
            elo_s[surf][l] -= elo_k(elo_sn[surf][l]) * (1.0 - es)
            elo_sn[surf][w] += 1
            elo_sn[surf][l] += 1

        if first:
            rec[0] += 1
            if surf:
                h2h_s[(key, surf)][0] += 1
        else:
            rec[1] += 1
            if surf:
                h2h_s[(key, surf)][1] += 1
        h2h_last[key] = d

        mins = C["minutes"][i]
        mins = 0.0 if mins != mins else float(mins)
        hist[w].append((d, mins))
        hist[l].append((d, mins))

        if has_serve[i]:
            wsv, lsv = C["w_svpt"][i], C["l_svpt"][i]
            for p, pre, opre, osv in ((w, "w_", "l_", lsv), (l, "l_", "w_", wsv)):
                bpf, bps = C[f"{pre}bpFaced"][i], C[f"{pre}bpSaved"][i]
                obpf, obps = C[f"{opre}bpFaced"][i], C[f"{opre}bpSaved"][i]
                opp_won = C[f"{opre}1stWon"][i] + C[f"{opre}2ndWon"][i]
                vals = np.array([
                    1.0, C[f"{pre}svpt"][i], C[f"{pre}1stIn"][i],
                    C[f"{pre}1stWon"][i], C[f"{pre}2ndWon"][i],
                    C[f"{pre}SvGms"][i], bpf - bps, C[f"{pre}ace"][i],
                    C[f"{pre}df"][i], osv, osv - opp_won,
                    C[f"{opre}SvGms"][i], obpf - obps, mins,
                ], dtype=np.float64)
                np.nan_to_num(vals, copy=False, nan=0.0)
                for bucket_key in ((p, "ALL"),) + (((p, surf),) if surf else ()):
                    a = acc[bucket_key]
                    a.decay_to(d)
                    a.v += vals

    print("assembling frame ...", flush=True)
    out = pd.DataFrame(A)
    out.insert(0, "date", m["date"].to_numpy())
    for c in ("surface", "tier", "tour", "tourney_name", "tourney_level",
              "round", "winner_name", "loser_name", "score"):
        out[c] = m[c].to_numpy()
    for c, src in (("best_of", "best_of"), ("minutes", "minutes"),
                   ("w_ht", "winner_ht"), ("l_ht", "loser_ht"),
                   ("w_age", "winner_age"), ("l_age", "loser_age"),
                   ("w_rank", "winner_rank"), ("l_rank", "loser_rank")):
        out[c] = pd.to_numeric(m[src], errors="coerce").astype(np.float32)
    out["w_hand"] = m["winner_hand"].to_numpy()
    out["l_hand"] = m["loser_hand"].to_numpy()
    for c, src in (("w_qualifier", "winner_entry"), ("l_qualifier", "loser_entry")):
        out[c] = m[src].isin(["Q", "LL"]).astype(np.int8)
    out["has_serve"] = has_serve
    sc = m["score"].astype(object).where(m["score"].notna(), None).to_numpy()
    out["winner_lost_set1"] = np.array([lost_first_set(s) for s in sc],
                                       dtype=np.float32)
    out["n_sets"] = np.array([n_sets(s) for s in sc], dtype=np.float32)

    CACHE.mkdir(parents=True, exist_ok=True)
    path = CACHE / "stage1_features.parquet"
    out.to_parquet(path, index=False)
    print(f"  {len(out):,} rows x {len(out.columns)} cols -> {path}")
    print(f"  {path.stat().st_size / 1e6:.0f} MB")


if __name__ == "__main__":
    main()

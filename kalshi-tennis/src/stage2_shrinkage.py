"""Stage 2 -- shrinkage.

    adjusted = (n * player_rate + k * population_rate) / (n + k)

Implemented as (numerator + k*pop) / (denominator + k), which is the same thing
but avoids dividing by zero for players with no history.

  * population_rate is computed within tier AND surface, never globally
  * k is tuned separately per statistic, on a chronological validation split,
    by how well the shrunk pre-match estimate predicts what the player actually
    did in that match
  * n (the denominator -- points or games, not matches) is carried alongside
    every shrunk feature so the model knows how much to trust it

Splits are chronological throughout: hypotheses on early data, one pass on late.
"""
import pathlib
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import tennis_data as td  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[1]
CACHE = ROOT / "data" / "cache"
REPORT = ROOT / "reports"

TRAIN_END = pd.Timestamp("2023-01-01")
VAL_END = pd.Timestamp("2025-01-01")      # val = [TRAIN_END, VAL_END)
# test = [VAL_END, end of data) -- untouched until Stage 4

K_GRID = np.array([0, 10, 25, 50, 100, 200, 400, 800, 1600, 3200, 6400, 12800],
                  dtype=float)

# rate -> (accumulator numerator, accumulator denominator, per-match numerator,
#          per-match denominator).  Per-match fields are prefixed w_/l_ later.
RATES = {
    "serve_pts_won": (("first_won", "second_won"), ("svpt",),
                      ("1stWon", "2ndWon"), ("svpt",)),
    "first_in":      (("first_in",), ("svpt",), ("1stIn",), ("svpt",)),
    "first_won":     (("first_won",), ("first_in",), ("1stWon",), ("1stIn",)),
    "ace":           (("ace",), ("svpt",), ("ace",), ("svpt",)),
    "df":            (("df",), ("svpt",), ("df",), ("svpt",)),
    "hold":          (("sv_gms", "-breaks_suffered"), ("sv_gms",),
                      ("SvGms", "-bpFaced", "+bpSaved"), ("SvGms",)),
    "rtn_pts_won":   (("rtn_won",), ("rtn_pt",), None, None),
    "break":         (("breaks_made",), ("rtn_gms",), None, None),
}


def combine(df, fields, prefix):
    """Sum accumulator fields, honouring leading -/+ signs."""
    total = None
    for f in fields:
        sign = 1.0
        if f.startswith("-"):
            sign, f = -1.0, f[1:]
        elif f.startswith("+"):
            f = f[1:]
        col = df[f"{prefix}{f}"].astype(float)
        total = sign * col if total is None else total + sign * col
    return total


def observed(mt, fields, side):
    """Per-match observed value for one player ('w' or 'l')."""
    total = None
    for f in fields:
        sign = 1.0
        if f.startswith("-"):
            sign, f = -1.0, f[1:]
        elif f.startswith("+"):
            f = f[1:]
        col = pd.to_numeric(mt[f"{side}_{f}"], errors="coerce").astype(float)
        total = sign * col if total is None else total + sign * col
    return total


def observed_return(mt, side, which):
    """Return-side observables have to come from the OPPONENT's serve rows."""
    opp = "l" if side == "w" else "w"
    svpt = pd.to_numeric(mt[f"{opp}_svpt"], errors="coerce").astype(float)
    won = (pd.to_numeric(mt[f"{opp}_1stWon"], errors="coerce").astype(float)
           + pd.to_numeric(mt[f"{opp}_2ndWon"], errors="coerce").astype(float))
    svgms = pd.to_numeric(mt[f"{opp}_SvGms"], errors="coerce").astype(float)
    bpf = pd.to_numeric(mt[f"{opp}_bpFaced"], errors="coerce").astype(float)
    bps = pd.to_numeric(mt[f"{opp}_bpSaved"], errors="coerce").astype(float)
    if which == "rtn_pts_won":
        return svpt - won, svpt
    return bpf - bps, svgms          # breaks made / return games


def aligned_matches(n_expected):
    """Reload matches under Stage 1's exact sort and row filter, so positions line up."""
    m = td.load_matches()
    m = m.sort_values(["date", "tourney_id", "match_num"],
                      kind="mergesort").reset_index(drop=True)
    w = m["winner_name"].astype(object).where(m["winner_name"].notna(), None)
    l = m["loser_name"].astype(object).where(m["loser_name"].notna(), None)
    keep = w.map(lambda x: isinstance(x, str)) & l.map(lambda x: isinstance(x, str))
    m = m[keep].reset_index(drop=True)
    assert len(m) == n_expected, f"alignment failed: {len(m)} vs {n_expected}"
    return m


def main():
    print("loading Stage 1 features ...", flush=True)
    f = pd.read_parquet(CACHE / "stage1_features.parquet")
    print(f"  {len(f):,} rows x {len(f.columns)} cols")
    mt = aligned_matches(len(f))
    print("  aligned to raw match stats OK")

    f["date"] = pd.to_datetime(f["date"])
    train = f["date"] < TRAIN_END
    val = (f["date"] >= TRAIN_END) & (f["date"] < VAL_END)
    print(f"  train {train.sum():,} | val {val.sum():,} | test {(~train & ~val).sum():,}")

    # ---- population rates by tier AND surface, from TRAIN only ------------
    print("\ncomputing population rates (tier x surface, train only) ...")
    pop = {}
    for rate, (num_f, den_f, mnum, mden) in RATES.items():
        rows = []
        for (tier, surf), g in mt[train.to_numpy()].groupby(
                ["tier", "surface"], observed=True):
            if rate in ("rtn_pts_won", "break"):
                n_w, d_w = observed_return(g, "w", rate)
                n_l, d_l = observed_return(g, "l", rate)
            else:
                n_w, d_w = observed(g, mnum, "w"), observed(g, mden, "w")
                n_l, d_l = observed(g, mnum, "l"), observed(g, mden, "l")
            num = np.nansum(n_w) + np.nansum(n_l)
            den = np.nansum(d_w) + np.nansum(d_l)
            if den > 0:
                rows.append((tier, surf, num / den, den))
        for tier, surf, r, den in rows:
            pop[(rate, tier, surf)] = r
        # tier-level fallback for surfaces with no train data
        for tier in mt["tier"].dropna().unique():
            vals = [(r, d) for (t, s, r, d) in rows if t == tier]
            if vals:
                pop[(rate, tier, None)] = (sum(r * d for r, d in vals)
                                           / sum(d for _, d in vals))
    print(f"  {len(pop)} population rates")

    # ---- tune k per statistic on VALIDATION -------------------------------
    print("\ntuning k per statistic (validation split) ...")
    tier_arr = f["tier"].to_numpy()
    surf_arr = f["surface"].to_numpy()

    def pop_vec(rate, use_surface):
        out = np.empty(len(f), dtype=float)
        for i in range(len(f)):
            s = surf_arr[i] if use_surface else None
            v = pop.get((rate, tier_arr[i], s))
            if v is None:
                v = pop.get((rate, tier_arr[i], None), np.nan)
            out[i] = v
        return out

    chosen_k, tuning_rows = {}, []
    for rate, (num_f, den_f, mnum, mden) in RATES.items():
        for bucket in ("all", "surf"):
            prefix_w, prefix_l = f"w_{bucket}_", f"l_{bucket}_"
            num_w = combine(f, num_f, prefix_w)
            den_w = combine(f, den_f, prefix_w)
            num_l = combine(f, num_f, prefix_l)
            den_l = combine(f, den_f, prefix_l)
            pv = pop_vec(rate, bucket == "surf")

            if rate in ("rtn_pts_won", "break"):
                on_w, od_w = observed_return(mt, "w", rate)
                on_l, od_l = observed_return(mt, "l", rate)
            else:
                on_w, od_w = observed(mt, mnum, "w"), observed(mt, mden, "w")
                on_l, od_l = observed(mt, mnum, "l"), observed(mt, mden, "l")

            obs_num = pd.concat([on_w, on_l]).to_numpy()
            obs_den = pd.concat([od_w, od_l]).to_numpy()
            acc_num = pd.concat([num_w, num_l]).to_numpy()
            acc_den = pd.concat([den_w, den_l]).to_numpy()
            popv = np.concatenate([pv, pv])
            vmask = np.concatenate([val.to_numpy(), val.to_numpy()])

            ok = (vmask & np.isfinite(obs_num) & np.isfinite(obs_den)
                  & (obs_den > 0) & np.isfinite(acc_den) & np.isfinite(popv)
                  & np.isfinite(acc_num))
            if ok.sum() < 500:
                chosen_k[(rate, bucket)] = 200.0
                continue
            o = obs_num[ok] / obs_den[ok]
            wgt = obs_den[ok]
            an, ad, pp = acc_num[ok], acc_den[ok], popv[ok]

            best, best_mse = None, np.inf
            for k in K_GRID:
                est = (an + k * pp) / (ad + k) if k > 0 else np.where(
                    ad > 0, an / np.maximum(ad, 1e-9), pp)
                mse = np.average((est - o) ** 2, weights=wgt)
                tuning_rows.append((rate, bucket, k, mse, int(ok.sum())))
                if mse < best_mse:
                    best, best_mse = k, mse
            chosen_k[(rate, bucket)] = float(best)
            print(f"  {rate:<14} {bucket:<5} k={best:<7.0f} "
                  f"wMSE={best_mse:.6f}  n={ok.sum():,}")

    # ---- apply shrinkage --------------------------------------------------
    print("\napplying shrinkage ...")
    out = f[["date", "surface", "tier", "tour", "tourney_name", "round",
             "best_of", "winner_name", "loser_name", "score",
             "winner_lost_set1", "n_sets", "minutes", "has_serve"]].copy()

    for side in ("w", "l"):
        out[f"{side}_elo"] = f[f"{side}_elo"]
        out[f"{side}_elo_n"] = f[f"{side}_elo_n"]
        out[f"{side}_elo_surf"] = f[f"{side}_elo_surf"]
        out[f"{side}_elo_surf_n"] = f[f"{side}_elo_surf_n"]
        for c in ("matches_7d", "matches_14d", "minutes_14d", "days_since",
                  "back_to_back"):
            out[f"{side}_{c}"] = f[f"{side}_{c}"]
        out[f"{side}_hand"] = f[f"{side}_hand"]
        out[f"{side}_ht"] = f[f"{side}_ht"]
        out[f"{side}_age"] = f[f"{side}_age"]
        out[f"{side}_rank"] = f[f"{side}_rank"]
        out[f"{side}_qualifier"] = f[f"{side}_qualifier"]

    for c in ("h2h_w_wins", "h2h_l_wins", "h2h_played", "h2h_w_wins_surf",
              "h2h_l_wins_surf", "h2h_played_surf", "h2h_days_since"):
        out[c] = f[c]

    for rate, (num_f, den_f, _, _) in RATES.items():
        for bucket in ("all", "surf"):
            k = chosen_k[(rate, bucket)]
            pv = pop_vec(rate, bucket == "surf")
            for side in ("w", "l"):
                p = f"{side}_{bucket}_"
                num = combine(f, num_f, p).to_numpy()
                den = combine(f, den_f, p).to_numpy()
                est = (np.nan_to_num(num) + k * pv) / (np.nan_to_num(den) + k)
                est[~np.isfinite(pv)] = np.nan
                out[f"{side}_{bucket}_{rate}"] = est
                out[f"{side}_{bucket}_{rate}_n"] = den
    out["_k_used"] = ""      # documented separately; keeps the frame tidy

    CACHE.mkdir(parents=True, exist_ok=True)
    path = CACHE / "stage2_features.parquet"
    out.drop(columns=["_k_used"]).to_parquet(path, index=False)
    pd.DataFrame(tuning_rows,
                 columns=["rate", "bucket", "k", "weighted_mse", "n"]
                 ).to_csv(CACHE / "stage2_k_tuning.csv", index=False)
    pd.Series({f"{r}|{b}": v for (r, b), v in chosen_k.items()}
              ).to_csv(CACHE / "stage2_chosen_k.csv")
    print(f"  wrote {len(out):,} rows x {len(out.columns) - 1} cols -> {path}")

    # ---- sanity check: do tiny-sample players sit near the population? ----
    REPORT.mkdir(parents=True, exist_ok=True)
    lines = []

    def emit(s=""):
        print(s)
        lines.append(s)

    emit()
    emit("=" * 78)
    emit("STAGE 2 -- SHRINKAGE SANITY CHECK")
    emit("=" * 78)
    emit(f"{'statistic':<16}{'bucket':<7}{'k':>7}   "
         f"{'raw sd (n<100)':>15}{'shrunk sd':>12}{'pop sd':>9}")
    for rate, (num_f, den_f, _, _) in RATES.items():
        for bucket in ("all", "surf"):
            k = chosen_k[(rate, bucket)]
            pv = pop_vec(rate, bucket == "surf")
            num = combine(f, num_f, f"w_{bucket}_").to_numpy()
            den = combine(f, den_f, f"w_{bucket}_").to_numpy()
            thin = np.isfinite(den) & (den > 0) & (den < 100) & np.isfinite(pv)
            if thin.sum() < 50:
                continue
            raw = num[thin] / den[thin]
            shr = (num[thin] + k * pv[thin]) / (den[thin] + k)
            emit(f"{rate:<16}{bucket:<7}{k:>7.0f}   "
                 f"{np.nanstd(raw):>15.4f}{np.nanstd(shr):>12.4f}"
                 f"{np.nanstd(pv[thin]):>9.4f}")
    emit()
    emit("Raw sd should collapse toward the population sd after shrinking;")
    emit("if a 4-match player still shows an extreme rate, k is too small.")
    (REPORT / "stage2_shrinkage.txt").write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    main()

"""Stage 3 -- split-half reliability of claimed player "tendencies".

Settles whether "known for comebacks" is a measurable trait or a story we tell
about noise. Method, per the spec:

  1. players with >=20 qualifying matches
  2. split each player's matches into halves by ALTERNATING date order
     (alternating, not first-half/second-half, so form trends don't inflate r)
  3. compute the rate within each half
  4. correlate the halves across players

Two controls make the number interpretable, because a bare r is not:

  * a POSITIVE control -- serve points won %, which is unquestionably a stable
    skill. If the method can't detect that, the method is broken.
  * a NULL simulation -- resample every player's matches from a single league
    -wide rate, so every player is truly identical, and see what r the binomial
    noise alone produces. That is the floor any real trait must clear.

Split-half r is also attenuated because each half holds half the data, so the
Spearman-Brown corrected value is reported alongside the raw one.
"""
import pathlib
import re
import sys

import numpy as np
import pandas as pd
from scipy import stats

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import tennis_data as td  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[1]
REPORT = ROOT / "reports"
CACHE = ROOT / "data" / "cache"

MIN_N = 20
RNG = np.random.default_rng(20260729)

_SET = re.compile(r"^(\d+)-(\d+)(?:\((\d+)\))?$")


def parse_sets(score):
    """['7-6(5)', '4-6'] -> [(7,6,True), (4,6,False)] from the WINNER's side."""
    if not isinstance(score, str):
        return None
    s = score.strip()
    if not s or any(t in s.upper() for t in ("W/O", "DEF", "WALKOVER")):
        return None
    sets = []
    for tok in s.split():
        m = _SET.match(tok)
        if not m:
            if tok.upper().startswith(("RET", "ABN")):
                break
            continue
        a, b = int(m.group(1)), int(m.group(2))
        tb = m.group(3) is not None or (max(a, b) == 7 and min(a, b) == 6)
        sets.append((a, b, tb))
    return sets or None


def build_records(matches):
    """One row per (player, match) with the flags every trait needs."""
    recs = []
    cols = matches[["date", "score", "best_of", "winner_name", "loser_name",
                    "surface", "tier"]].to_dict("list")
    n = len(matches)
    for i in range(n):
        if i % 300_000 == 0:
            print(f"  parsing {i:,}/{n:,}", flush=True)
        sets = parse_sets(cols["score"][i])
        if not sets:
            continue
        bo = cols["best_of"][i]
        bo = int(bo) if bo == bo and bo is not None else 3
        complete = len(sets) >= 2
        if not complete:
            continue

        s1w, s1l, _ = sets[0]
        lost_s1_winner = s1w < s1l
        decided = len(sets) == bo            # went the distance
        tb_w = sum(1 for a, b, tb in sets if tb and a > b)
        tb_l = sum(1 for a, b, tb in sets if tb and b > a)
        tb_total = tb_w + tb_l

        for side, name in (("w", cols["winner_name"][i]),
                           ("l", cols["loser_name"][i])):
            if not isinstance(name, str):
                continue
            won = side == "w"
            lost_s1 = lost_s1_winner if won else (not lost_s1_winner)
            recs.append((
                name, cols["date"][i], cols["tier"][i], cols["surface"][i],
                int(won), int(lost_s1), int(decided),
                tb_w if won else tb_l, tb_total,
            ))
    return pd.DataFrame(recs, columns=[
        "player", "date", "tier", "surface", "won", "lost_set1",
        "decided", "tb_won", "tb_played"])


# trait -> (numerator, denominator) as callables on the record frame
TRAITS = {
    "comeback (win | lost set 1)":
        (lambda d: d["won"] * d["lost_set1"], lambda d: d["lost_set1"]),
    "slow starter (lose set 1)":
        (lambda d: d["lost_set1"], lambda d: pd.Series(1, index=d.index)),
    "tiebreak win rate":
        (lambda d: d["tb_won"], lambda d: d["tb_played"]),
    "decider win rate":
        (lambda d: d["won"] * d["decided"], lambda d: d["decided"]),
    "POSITIVE CONTROL: match win rate":
        (lambda d: d["won"], lambda d: pd.Series(1, index=d.index)),
}


def split_half_r(df, num, den, min_n=MIN_N):
    """Alternate-split each player's qualifying matches; correlate the halves."""
    d = df.copy()
    d["_num"] = num(d)
    d["_den"] = den(d)
    d = d[d["_den"] > 0].sort_values(["player", "date"], kind="mergesort")
    d["_i"] = d.groupby("player", observed=True).cumcount()

    tot = d.groupby("player", observed=True)["_den"].sum()
    keep = tot[tot >= min_n].index
    d = d[d["player"].isin(keep)]
    if d.empty:
        return None

    g = d.groupby(["player", d["_i"] % 2], observed=True)[["_num", "_den"]].sum()
    g = g.unstack(level=-1)
    need = [("_num", 0), ("_num", 1), ("_den", 0), ("_den", 1)]
    if any(c not in g.columns for c in need):
        return None
    g = g.dropna(subset=need)
    g = g[(g[("_den", 0)] > 0) & (g[("_den", 1)] > 0)]
    if len(g) < 30:
        return None

    a = g[("_num", 0)] / g[("_den", 0)]
    b = g[("_num", 1)] / g[("_den", 1)]
    r, p = stats.pearsonr(a, b)
    n = len(g)
    z = np.arctanh(r)
    se = 1.0 / np.sqrt(n - 3)
    lo, hi = np.tanh(z - 1.96 * se), np.tanh(z + 1.96 * se)
    sb = 2 * r / (1 + r) if r > -1 else np.nan
    return dict(r=r, lo=lo, hi=hi, p=p, n_players=n, spearman_brown=sb,
                median_den=float(tot.loc[g.index].median()))


def null_r(df, num, den, min_n=MIN_N):
    """Same test, but with every player's outcomes resampled from ONE rate.

    Whatever r this produces is pure binomial noise -- the floor.
    """
    d = df.copy()
    d["_num"] = num(d)
    d["_den"] = den(d)
    d = d[d["_den"] > 0]
    if d.empty or d["_den"].sum() == 0:
        return None
    p_bar = d["_num"].sum() / d["_den"].sum()
    sim = d.copy()
    sim["_num"] = RNG.binomial(d["_den"].astype(int).to_numpy(), p_bar)
    return split_half_r(sim, lambda x: x["_num"], lambda x: x["_den"], min_n)


def split_half_r_residual(df, num, den, min_n=MIN_N):
    """Split-half reliability of a trait AFTER removing overall player strength.

    A strong player both loses set 1 less often and wins more often when they
    do, so a raw comeback correlation can be nothing more than skill measured
    twice. Within each half we regress the trait on that half's overall win
    rate and correlate the residuals: what survives is comeback ability that
    Elo does not already know about.
    """
    d = df.copy()
    d["_num"] = num(d)
    d["_den"] = den(d)
    d = d.sort_values(["player", "date"], kind="mergesort")
    d["_i"] = d.groupby("player", observed=True).cumcount()
    d["_half"] = d["_i"] % 2

    q = d[d["_den"] > 0]
    tot = q.groupby("player", observed=True)["_den"].sum()
    keep = tot[tot >= min_n].index

    trait = (q[q["player"].isin(keep)]
             .groupby(["player", "_half"], observed=True)[["_num", "_den"]].sum())
    # overall strength uses EVERY match in that half, not just qualifying ones
    strength = (d[d["player"].isin(keep)]
                .groupby(["player", "_half"], observed=True)
                .agg(wins=("won", "sum"), played=("won", "size")))

    j = trait.join(strength, how="inner").reset_index()
    j = j[(j["_den"] > 0) & (j["played"] >= 5)]
    j["rate"] = j["_num"] / j["_den"]
    j["winrate"] = j["wins"] / j["played"]

    resid = {}
    for h in (0, 1):
        g = j[j["_half"] == h]
        if len(g) < 30:
            return None
        slope, intercept, *_ = stats.linregress(g["winrate"], g["rate"])
        resid[h] = pd.Series(
            (g["rate"] - (intercept + slope * g["winrate"])).to_numpy(),
            index=g["player"].to_numpy())

    common = resid[0].index.intersection(resid[1].index)
    if len(common) < 30:
        return None
    a, b = resid[0].loc[common], resid[1].loc[common]
    r, p = stats.pearsonr(a, b)
    n = len(common)
    z, se = np.arctanh(r), 1.0 / np.sqrt(n - 3)
    return dict(r=r, lo=np.tanh(z - 1.96 * se), hi=np.tanh(z + 1.96 * se),
                p=p, n_players=n,
                spearman_brown=2 * r / (1 + r) if r > -1 else np.nan)


def main():
    REPORT.mkdir(parents=True, exist_ok=True)
    print("loading matches ...", flush=True)
    m = td.load_matches()
    print(f"  {len(m):,} matches")

    cache = CACHE / "stage3_records.parquet"
    if cache.exists():
        recs = pd.read_parquet(cache)
        print(f"  cached records: {len(recs):,}")
    else:
        recs = build_records(m)
        recs.to_parquet(cache, index=False)
        print(f"  built {len(recs):,} player-match records")

    lines = []

    def emit(s=""):
        print(s)
        lines.append(s)

    emit("=" * 86)
    emit("STAGE 3 -- SPLIT-HALF RELIABILITY OF PLAYER TENDENCIES")
    emit("=" * 86)
    emit(f"records: {len(recs):,} player-match rows | "
         f"min qualifying n per player: {MIN_N}")
    emit("r is the raw split-half correlation; SB is Spearman-Brown corrected;")
    emit("null is the same statistic when all players are secretly identical.")
    emit()

    segments = [("ALL TIERS", recs)]
    for tier in ("main", "chall"):
        segments.append((f"tier={tier}", recs[recs["tier"] == tier]))

    for label, sub in segments:
        emit("-" * 86)
        emit(label)
        emit("-" * 86)
        emit(f"{'trait':<36}{'players':>8}{'r':>8}{'95% CI':>18}"
             f"{'SB':>7}{'null r':>8}")
        for name, (num, den) in TRAITS.items():
            res = split_half_r(sub, num, den)
            if res is None:
                emit(f"{name:<36}{'insufficient data':>49}")
                continue
            nul = null_r(sub, num, den)
            nr = f"{nul['r']:+.3f}" if nul else "n/a"
            ci = f"[{res['lo']:+.3f}, {res['hi']:+.3f}]"
            emit(f"{name:<36}{res['n_players']:>8,}{res['r']:>+8.3f}"
                 f"{ci:>18}{res['spearman_brown']:>+7.3f}{nr:>8}")
        emit()

    emit("=" * 86)
    emit("CONTROLLING FOR OVERALL STRENGTH")
    emit("=" * 86)
    emit("Same test, but the trait is residualised against the player's own win")
    emit("rate in that half. This asks whether the tendency carries information")
    emit("Elo does not already have. A trait that is real but collapses here is")
    emit("not worth a feature -- it is strength, relabelled.")
    emit()
    emit(f"{'trait':<36}{'players':>8}{'raw r':>8}{'resid r':>9}"
         f"{'95% CI':>18}{'SB':>7}")
    for name, (num, den) in TRAITS.items():
        raw = split_half_r(recs, num, den)
        res = split_half_r_residual(recs, num, den)
        if raw is None or res is None:
            emit(f"{name:<36}{'insufficient data':>50}")
            continue
        ci = f"[{res['lo']:+.3f}, {res['hi']:+.3f}]"
        emit(f"{name:<36}{res['n_players']:>8,}{raw['r']:>+8.3f}"
             f"{res['r']:>+9.3f}{ci:>18}{res['spearman_brown']:>+7.3f}")
    emit()

    emit("=" * 86)
    emit("READING THIS")
    emit("=" * 86)
    emit("The positive control must show a clearly non-zero r -- match win rate")
    emit("is a real, stable skill. If a trait's r is not meaningfully above its")
    emit("null, there are no stable individual differences to model: the")
    emit("variation between players is what binomial noise produces on its own,")
    emit("and the feature should be dropped rather than shrunk.")

    (REPORT / "stage3_traits.txt").write_text("\n".join(lines), encoding="utf-8")
    emit()
    emit(f"report -> {REPORT / 'stage3_traits.txt'}")


if __name__ == "__main__":
    main()

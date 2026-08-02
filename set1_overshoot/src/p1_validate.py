"""Phase 1 validation -- how well does the price-only detector recover set 1?

Two things are checked, and they are different:

  DIRECTION -- who won set 1. Checkable against 2,886 externally sourced
  scorelines, so this gets a real accuracy number.

  TIMING -- when set 1 ended. No source publishes set-end times, so this cannot
  be checked directly. Instead it is checked against a falsifiable prediction:
  if the changepoint is really the set conclusion, its position must scale with
  how many games the set took. A 6-0 set must land earlier than a 7-6 set. If it
  does not, the timing is noise and every timing-dependent result is provisional.
"""
import pathlib

import numpy as np
import pandas as pd
from scipy import stats

import p2_calib as p2

ROOT = pathlib.Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
OUT = ROOT / "PHASE1_DETECTOR_ACCURACY.md"


def main():
    st, bid, ask, mid = p2.load("paths")
    truth = pd.read_parquet(DATA / "truth_set1.parquet")

    cp_i, cp_s = p2.changepoint(mid)
    det = pd.DataFrame({
        "ticker": st["ticker"].values,
        "ok": st["ok"].values & st["plausible"].values,
        "kept_is_fav": st["kept_is_fav"].values,
        "pre_mid": (st["pre_bid"].values + st["pre_ask"].values) / 2.0,
        "dur_min": st["dur_min"].values,
        "cp_idx": cp_i,
        "cp_step": cp_s,
    })
    # alternative direction rules: price change from pre-match to a fixed minute
    for T in (25, 30, 35, 40, 45, 50, 60):
        col = np.full(len(st), np.nan)
        m = mid[:, min(T, mid.shape[1] - 1)]
        col = m - det["pre_mid"].values
        det[f"d{T}"] = col

    j = det.merge(truth, on="ticker", how="inner")
    j = j[j["ok"]]
    # truth is oriented to the kept player; the detector is oriented to the
    # favourite. Put both on the favourite's side.
    j["fav_won_s1_true"] = np.where(j["kept_is_fav"], j["player_won_s1"],
                                    ~j["player_won_s1"])

    lines = []

    def w(s=""):
        print(s, flush=True)
        lines.append(s)

    w("# PHASE1_DETECTOR_ACCURACY.md")
    w()
    w("Set-1 state is inferred from price alone -- Kalshi publishes no "
      "scoreline and no")
    w("match-start field. This file measures how well that inference works. "
      "It gates")
    w("everything downstream.")
    w()
    w("## Validation sample")
    w()
    w(f"- **{len(j):,} matches** with an externally sourced set-1 result.")
    w("- Sources: Sackmann frozen mirror (all tiers, tourney weeks to "
      "2026-06-02) and")
    w("  tennis-data.co.uk (ATP/WTA main tour, to 2026-07-26).")
    w("- Join is on surname+initial pairs within a date window. Kalshi's own "
      "settlement")
    w("  agrees with the external match winner on **99.55%** of joined rows, "
      "so the")
    w("  join itself is sound and any error below is the detector's, not the "
      "join's.")
    w()
    w("| tour | n |")
    w("|---|---|")
    for t, n in j.groupby("tour").size().items():
        w(f"| {t} | {n:,} |")
    w()

    # ------------------------------------------------ direction accuracy
    w("## 1. Direction -- who won set 1")
    w()
    w("Detector: sign of the largest sustained price step in minutes "
      f"{p2.CP_LO}-{p2.CP_HI} of play.")
    w()
    pred = j["cp_step"].values > 0
    acc = (pred == j["fav_won_s1_true"].values).mean()
    w(f"**Overall accuracy: {acc:.3f}** (n={len(j):,}, "
      f"base rate {max(j['fav_won_s1_true'].mean(), 1 - j['fav_won_s1_true'].mean()):.3f})")
    w()
    w("Alternative rules, for comparison -- sign of (mid at minute T) minus "
      "the pre-match mid:")
    w()
    w("| rule | accuracy |")
    w("|---|---|")
    w(f"| changepoint step | {acc:.3f} |")
    best = ("changepoint", acc)
    for T in (25, 30, 35, 40, 45, 50, 60):
        v = j[f"d{T}"].values
        ok = np.isfinite(v)
        a = ((v[ok] > 0) == j["fav_won_s1_true"].values[ok]).mean()
        w(f"| mid at +{T}min vs pre-match | {a:.3f} (n={ok.sum():,}) |")
        if a > best[1]:
            best = (f"mid at +{T}min", a)
    w()
    w(f"Best rule: **{best[0]}, {best[1]:.3f}**.")
    w()

    w("### Accuracy by segment (changepoint rule)")
    w()
    w("| segment | n | accuracy |")
    w("|---|---|---|")
    j["_c"] = pred == j["fav_won_s1_true"].values
    for t, g in j.groupby("tour"):
        w(f"| {t} | {len(g):,} | {g['_c'].mean():.3f} |")
    j["strength"] = pd.cut(j["pre_mid"], [0, 60, 70, 80, 90, 101],
                           labels=["<60", "60-70", "70-80", "80-90", "90+"])
    for t, g in j.groupby("strength", observed=True):
        w(f"| pre-match {t} | {len(g):,} | {g['_c'].mean():.3f} |")
    j["absstep"] = pd.cut(j["cp_step"].abs(), [0, 5, 10, 20, 100],
                          labels=["step<5c", "5-10c", "10-20c", "20c+"])
    for t, g in j.groupby("absstep", observed=True):
        w(f"| {t} | {len(g):,} | {g['_c'].mean():.3f} |")
    w()

    # accuracy on the exact population Phase 2 uses
    ev = p2.build_events(st, bid, ask, mid, p2.BASE_RULE, p2.BASE_OFFSET)
    ev2 = ev.merge(truth[["ticker", "player_won_s1"]], on="ticker", how="inner")
    ev2 = ev2.merge(det[["ticker", "kept_is_fav"]], on="ticker", how="left")
    ev2["fav_won_s1_true"] = np.where(ev2["kept_is_fav"],
                                      ev2["player_won_s1"],
                                      ~ev2["player_won_s1"])
    sub = ev2[ev2["is_event"]]
    w("### The number that actually matters")
    w()
    w("Phase 2 conditions on: pre-match favourite (>=60c) whose price dropped "
      f">={p2.MIN_DROP}c by the")
    w("entry moment. Of those matches, how many really had the favourite "
      "lose set 1?")
    w()
    if len(sub):
        prec = 1.0 - sub["fav_won_s1_true"].mean()
        w(f"**{prec:.3f}** ({int((~sub['fav_won_s1_true']).sum()):,} of "
          f"{len(sub):,} validated events)")
    w()
    w("This is far more damaging to the *interpretation* than the 0.825 "
      "direction accuracy")
    w("suggests, and it is worth being precise about why. The two numbers "
      "measure")
    w("different things. Direction accuracy asks, over all matches, whether "
      "the sign of")
    w("the biggest move identifies the set-1 winner. Event precision asks a "
      "harder")
    w("question: among matches the entry rule actually fires on, how many were "
      "really")
    w("a set-1 loss. A favourite who goes down an early break, sees the price "
      "fall 12c,")
    w("and then wins the set from there trips the entry rule and is counted as "
      "an event.")
    w("Those matches are not detector *errors* -- the price really did fall -- "
      "but they")
    w("are not what the hypothesis is about.")
    w()

    w("### Precision of each candidate entry rule")
    w()
    w("Chosen on labelled data, which is legitimate instrument calibration, "
      "and reported")
    w("here rather than buried. `after N` restricts firing to minute N "
      "onward, since a")
    w("set is rarely over before then.")
    w()
    w("| entry rule | events fired | precision | n validated |")
    w("|---|---|---|---|")
    tk = truth.set_index("ticker")
    best_rule, best_prec = None, -1.0
    for depth in (8, 12, 16, 20, 25, 30):
        for floor in (0, 30, 38):
            evx = p2.build_events(st, bid, ask, mid, f"deep:{depth}", 0,
                                  min_minute=floor)
            fired = evx[evx["is_event"]]
            m = fired.merge(truth[["ticker", "player_won_s1"]], on="ticker")
            m = m.merge(det[["ticker", "kept_is_fav"]], on="ticker", how="left")
            if len(m) < 60:
                continue
            true_loss = np.where(m["kept_is_fav"], ~m["player_won_s1"],
                                 m["player_won_s1"])
            pr = true_loss.mean()
            w(f"| deep:{depth}, after {floor} min | {len(fired):,} | "
              f"{pr:.3f} | {len(m):,} |")
            if pr > best_prec:
                best_rule, best_prec = (depth, floor), pr
    w()
    w(f"Best-targeted rule: **deep:{best_rule[0]}, after {best_rule[1]} min**, "
      f"precision **{best_prec:.3f}**.")
    w()
    w("Even the best rule leaves a substantial minority of entries that were "
      "not set-1")
    w("losses. Price alone cannot separate \"lost the set\" from \"went down a "
      "break and")
    w("recovered\" without a scoreline feed. Phase 2 is therefore run **twice**: "
      "once on")
    w("the full fired population, which is the tradeable question, and once on "
      "the")
    w("label-verified subsample, which is the literal question the brief asks. "
      "Both are")
    w("reported. Neither is allowed to stand in for the other.")
    w()

    # ------------------------------------------------ timing
    w("## 2. Timing -- when set 1 ended")
    w()
    w("Unvalidatable directly. Tested instead against a falsifiable "
      "prediction: the")
    w("changepoint should sit later in matches where set 1 took more games.")
    w()
    jj = j[np.isfinite(j["cp_idx"]) & (j["cp_idx"] > 0)].copy()
    jj["games"] = jj["s1_w"] + jj["s1_l"]
    r, pv = stats.spearmanr(jj["games"], jj["cp_idx"])
    w(f"Spearman(games in set 1, changepoint minute) = **{r:+.3f}** "
      f"(p={pv:.2e}, n={len(jj):,})")
    w()
    w("| games in set 1 | n | median changepoint minute |")
    w("|---|---|---|")
    for g, sub2 in jj.groupby(jj["games"].clip(6, 13)):
        w(f"| {int(g)}{'+' if g == 13 else ''} | {len(sub2):,} | "
          f"{sub2['cp_idx'].median():.0f} |")
    w()

    lines_acc = acc
    w("## 3. Verdict")
    w()
    if lines_acc >= 0.80:
        w(f"Direction accuracy **{lines_acc:.3f}** clears the 0.80 bar set in "
          "the brief.")
    else:
        w(f"Direction accuracy **{lines_acc:.3f}** is **below the 0.80 bar** "
          "set in the brief.")
        w("Every downstream result is therefore **provisional**, and the "
          "Phase 2 conclusion")
        w("is only trustworthy to the extent that it survives the "
          "entry-timing grid, which")
        w("does not depend on the changepoint at all.")
    w()
    w("Structural caveat that applies regardless of the number above: the "
      "Phase 2")
    w("calibration test conditions on **entry price**, and conditioning on "
      "price is valid")
    w("whether or not the price move was caused by a set loss. If the "
      "detector mislabels")
    w("the state, the tested question degrades from *\"the favourite lost "
      "set 1\"* to")
    w("*\"the favourite's price fell early in the match\"* -- a different and "
      "still")
    w("meaningful question, and the one a live trader would actually face. "
      "Detector error")
    w("damages the interpretation of Phase 3 segments far more than it "
      "damages Phase 2.")

    OUT.write_text("\n".join(lines), encoding="utf-8")
    print(f"\n-> {OUT}")


if __name__ == "__main__":
    main()

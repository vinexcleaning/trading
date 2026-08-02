"""Stage 0 -- coverage audit.

Question: of the players Kalshi actually offers tennis markets on, how many can
we model from Sackmann's data at all?

Reported per the build spec:
  * % of Kalshi-market players present in the data
  * % with >=20 career matches
  * % with >=20 matches with serve statistics
  * % with >=10 matches on the surface being played
  * the same split by tier

Reported two ways, because they answer different questions:
  PLAYER-level  -- what fraction of distinct players are modelable
  MARKET-level  -- what fraction of markets have BOTH players modelable,
                   which is what the spec's ~15% decision rule is about.
"""
import pathlib
import sys
from collections import Counter

import pandas as pd

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import tennis_data as td  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[1]
REPORT = ROOT / "reports"

CAREER_MIN = 20
SERVE_MIN = 20
SURFACE_MIN = 10


# --------------------------------------------------------------------------

def pct(x, n):
    return f"{100.0 * x / n:5.1f}%" if n else "  n/a"


def main():
    REPORT.mkdir(parents=True, exist_ok=True)
    print("loading Sackmann matches ...", flush=True)
    matches = td.load_matches()
    long = td.to_long(matches)
    print(f"  {len(matches):,} matches, {len(long):,} player-match rows")
    print(f"  data ends {matches['date'].max().date()}")

    print("loading Kalshi events ...", flush=True)
    ev = td.load_kalshi_events()
    print(f"  {len(ev):,} Kalshi matches")

    # ---- surface inference -------------------------------------------------
    smap = td.build_surface_map(matches)
    ev["surface"] = [td.surface_for(v, smap, t)
                     for v, t in zip(ev["venue"], ev["tier"])]
    unmapped = sorted(set(ev.loc[ev["surface"].isna(), "venue"].dropna()))
    print(f"  surface resolved for {ev['surface'].notna().mean() * 100:.1f}% "
          f"of markets ({len(unmapped)} venues unmapped)")
    if unmapped:
        print(f"    unmapped venues: {unmapped[:15]}")

    # ---- player resolution -------------------------------------------------
    print("resolving player names ...", flush=True)
    idx = td.build_player_index(long)
    kalshi_players = pd.unique(pd.concat([ev["player_a"], ev["player_b"]]).dropna())
    print(f"  {len(kalshi_players):,} distinct Kalshi players "
          f"vs {len(idx['names']):,} Sackmann players")

    res = {}
    how = Counter()
    for p in kalshi_players:
        canon, h = td.resolve(p, idx)
        res[p] = canon
        how[h] += 1
    print(f"  match methods: {dict(how)}")

    unmatched = [p for p, c in res.items() if c is None]

    # ---- per-player stats --------------------------------------------------
    print("computing per-player counts ...", flush=True)
    long = long.copy()
    career = long.groupby("player", observed=True).size()
    serve = long[long["has_serve"]].groupby("player", observed=True).size()
    by_surf = long.groupby(["player", "surface"], observed=True).size()

    ev["canon_a"] = ev["player_a"].map(res)
    ev["canon_b"] = ev["player_b"].map(res)

    def stats_for(canon, surface):
        if canon is None or (isinstance(canon, float)):
            return dict(present=False, career=0, serve=0, surf=0)
        c = int(career.get(canon, 0))
        s = int(serve.get(canon, 0))
        sf = int(by_surf.get((canon, surface), 0)) if surface else 0
        return dict(present=True, career=c, serve=s, surf=sf)

    rows = []
    for _, r in ev.iterrows():
        for side in ("a", "b"):
            st = stats_for(r[f"canon_{side}"], r["surface"])
            rows.append({
                "event_ticker": r["event_ticker"], "side": side,
                "tour": r["tour"], "tier": r["tier"], "status": r["status"],
                "surface": r["surface"], "kalshi_name": r[f"player_{side}"],
                "canon": r[f"canon_{side}"], **st,
            })
    pm = pd.DataFrame(rows)
    pm["ok_career"] = pm["present"] & (pm["career"] >= CAREER_MIN)
    pm["ok_serve"] = pm["present"] & (pm["serve"] >= SERVE_MIN)
    pm["ok_surface"] = pm["present"] & (pm["surf"] >= SURFACE_MIN)
    pm["modelable"] = pm["ok_career"] & pm["ok_serve"] & pm["ok_surface"]

    pm.to_parquet(ROOT / "data" / "cache" / "stage0_player_market.parquet",
                  index=False)

    # ---- report ------------------------------------------------------------
    out = []

    def emit(s=""):
        print(s)
        out.append(s)

    emit()
    emit("=" * 78)
    emit("STAGE 0 -- COVERAGE AUDIT")
    emit("=" * 78)
    emit(f"Sackmann data through   : {matches['date'].max().date()}")
    emit(f"Kalshi markets pulled   : {len(ev):,} matches "
         f"({ev['open_dt'].min().date()} .. {ev['open_dt'].max().date()})")
    emit(f"Distinct Kalshi players : {len(kalshi_players):,}")
    emit(f"Thresholds              : career>={CAREER_MIN}, "
         f"serve>={SERVE_MIN}, surface>={SURFACE_MIN}")
    emit()

    # PLAYER level -- dedupe to one row per (player, surface-context)
    emit("-" * 78)
    emit("PLAYER LEVEL  (distinct players; surface = the one they were listed on)")
    emit("-" * 78)
    ply = pm.drop_duplicates(subset=["kalshi_name", "surface"])
    tiers = [("ALL", ply)]
    for (tour, tier), g in ply.groupby(["tour", "tier"], observed=True):
        tiers.append((f"{tour} {tier}", g))
    emit(f"{'segment':<16}{'n':>7}{'in data':>10}{'>=20 car':>10}"
         f"{'>=20 srv':>10}{'>=10 surf':>11}{'all three':>11}")
    for label, g in tiers:
        n = len(g)
        emit(f"{label:<16}{n:>7}{pct(g['present'].sum(), n):>10}"
             f"{pct(g['ok_career'].sum(), n):>10}{pct(g['ok_serve'].sum(), n):>10}"
             f"{pct(g['ok_surface'].sum(), n):>11}{pct(g['modelable'].sum(), n):>11}")

    # MARKET level -- both players must qualify
    emit()
    emit("-" * 78)
    emit("MARKET LEVEL  (both players must clear the bar -- the decision rule)")
    emit("-" * 78)
    mk = pm.groupby("event_ticker", observed=True).agg(
        tour=("tour", "first"), tier=("tier", "first"),
        surface=("surface", "first"), status=("status", "first"),
        present=("present", "all"), ok_career=("ok_career", "all"),
        ok_serve=("ok_serve", "all"), ok_surface=("ok_surface", "all"),
        modelable=("modelable", "all"),
    )
    emit(f"{'segment':<16}{'n':>7}{'in data':>10}{'>=20 car':>10}"
         f"{'>=20 srv':>10}{'>=10 surf':>11}{'all three':>11}")
    segs = [("ALL", mk)]
    for (tour, tier), g in mk.groupby(["tour", "tier"], observed=True):
        segs.append((f"{tour} {tier}", g))
    for label, g in segs:
        n = len(g)
        emit(f"{label:<16}{n:>7}{pct(g['present'].sum(), n):>10}"
             f"{pct(g['ok_career'].sum(), n):>10}{pct(g['ok_serve'].sum(), n):>10}"
             f"{pct(g['ok_surface'].sum(), n):>11}{pct(g['modelable'].sum(), n):>11}")

    # by surface
    emit()
    emit("-" * 78)
    emit("MARKET LEVEL BY SURFACE")
    emit("-" * 78)
    for surf, g in mk.groupby("surface", observed=True):
        emit(f"{str(surf):<16}{len(g):>7}{pct(g['modelable'].sum(), len(g)):>10}")

    # currently-active subset
    emit()
    emit("-" * 78)
    emit("CURRENTLY ACTIVE MARKETS ONLY")
    emit("-" * 78)
    act = mk[mk["status"] == "active"]
    emit(f"active matches: {len(act)}")
    if len(act):
        for (tour, tier), g in act.groupby(["tour", "tier"], observed=True):
            emit(f"  {tour} {tier:<8}{len(g):>5}  modelable "
                 f"{pct(g['modelable'].sum(), len(g))}")

    # name-matching diagnostics
    emit()
    emit("-" * 78)
    emit("NAME MATCHING DIAGNOSTICS")
    emit("-" * 78)
    for h, c in how.most_common():
        emit(f"  {h:<22}{c:>6}  ({100.0 * c / len(kalshi_players):.1f}%)")
    emit(f"  unmatched players: {len(unmatched)}")
    for p in unmatched[:40]:
        emit(f"     {p}")

    # sample size distribution -- is the failure mode 'absent' or 'thin'?
    emit()
    emit("-" * 78)
    emit("WHERE COVERAGE FAILS  (per player-market slot)")
    emit("-" * 78)
    for (tour, tier), g in pm.groupby(["tour", "tier"], observed=True):
        n = len(g)
        absent = (~g["present"]).sum()
        thin = (g["present"] & ~g["ok_career"]).sum()
        noserve = (g["ok_career"] & ~g["ok_serve"]).sum()
        nosurf = (g["ok_career"] & g["ok_serve"] & ~g["ok_surface"]).sum()
        emit(f"  {tour} {tier:<7} n={n:<6} absent={pct(absent, n)} "
             f"thin(<20)={pct(thin, n)} no-serve={pct(noserve, n)} "
             f"thin-surface={pct(nosurf, n)}")
        emit(f"      median career matches (present players): "
             f"{g.loc[g['present'], 'career'].median():.0f}, "
             f"median serve-stat matches: "
             f"{g.loc[g['present'], 'serve'].median():.0f}")

    # ---- data recency vs market dates -------------------------------------
    # Upstream went dark, so feature history stops before many markets settle.
    emit()
    emit("-" * 78)
    emit("DATA RECENCY  (feature history vs when matches are played)")
    emit("-" * 78)
    cutoff = pd.Timestamp(matches["date"].max(), tz="UTC")
    ev_dt = ev["date"].fillna(ev["open_dt"])
    after = ev_dt > cutoff
    emit(f"Sackmann history ends       {cutoff.date()}")
    emit(f"markets played after that   {after.sum():,} / {len(ev):,} "
         f"({after.mean() * 100:.1f}%)")
    emit(f"markets fully covered       {(~after).sum():,} "
         f"({(~after).mean() * 100:.1f}%)")
    emit("")
    emit("Settled vs active (Stage 4 backtest supply):")
    st = ev["status"].value_counts()
    for k, v in st.items():
        emit(f"  {k:<12}{v:>6}")
    settled_covered = ((~after) & (ev["status"] != "active")).sum()
    emit(f"  settled AND within history: {settled_covered:,} "
         f"-- the usable backtest pool before any modelability filter")

    (REPORT / "stage0_coverage.txt").write_text("\n".join(out), encoding="utf-8")
    emit()
    emit(f"report written -> {REPORT / 'stage0_coverage.txt'}")


if __name__ == "__main__":
    main()

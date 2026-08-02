"""Task 3e -- both-sides consistency. A validity check, not a hypothesis.

Kalshi lists two mirrored markets per match. The favourite is sometimes the YES
side of the market I kept and sometimes the NO side, and in the NO case every
price is reconstructed arithmetically (fav_bid = 100 - kept_ask). If that
arithmetic is wrong, or if the two sides genuinely disagree, the Phase 2 and
Phase 5 results are void.

Two independent checks:

  ORIENTATION SPLIT -- full sample, 3,427 events. Compare the undershoot on
  matches where the favourite is the YES side against those where it is the NO
  side. These are disjoint halves measured by different code paths. A sign or
  off-by-one error in the NO reconstruction shows up here immediately, and at
  full power.

  MIRROR PAIRS -- literally both markets of the same match, for the 400 sibling
  markets pulled alongside the main data. Small, but it is the same match priced
  twice, so it isolates market disagreement from code error.
"""
import pathlib

import numpy as np
import pandas as pd

import fees
import p2_calib as p2

ROOT = pathlib.Path(__file__).resolve().parents[1]
DATA = ROOT / "data"


def fade_stats(e, rng, label, w, extra=""):
    p = (e["entry_mid"] / 100.0).values
    won = e["fav_won"].values
    mis = 100 * (won - p)
    lo, hi = p2.bootstrap_ci(mis, rng, n=8000)
    _, two = p2.poisson_binom_p(int(won.sum()), p, rng)
    fill = np.minimum(100.0 - e["entry_bid"].values + p2.SLIP, 99.0)
    fee = np.array([float(fees.fee_rate_cents(int(round(f)))) for f in fill])
    net = 100.0 * (1 - won) - fill - fee
    w(f"| {label} | {len(e):,} | {p.mean():.4f} | {won.mean():.4f} | "
      f"{mis.mean():+.2f} | [{lo:+.2f}, {hi:+.2f}] | {two:.4f} | "
      f"{net.mean():+.3f} |{extra}")
    return mis, net


def main():
    st, bid, ask, mid = p2.load("paths")
    rng = np.random.default_rng(505)
    out = []

    def w(s=""):
        print(s, flush=True)
        out.append(s)

    w("# Task 3e — both-sides consistency (validity check)")
    w("")
    w("If the undershoot differs materially between the two sides of the same "
      "match, the")
    w("measurement is broken and Phases 2 and 5 are both void. Run first, "
      "before any")
    w("Phase 5 conclusion depends on it.")
    w("")

    ev = p2.build_events(st, bid, ask, mid, "deep:30", 0, min_minute=38)
    e = ev[ev["is_event"]].copy()
    kif = st.set_index("ticker")["kept_is_fav"].to_dict()
    e["fav_is_yes"] = e["ticker"].map(kif).astype(bool)

    w("## 1. Orientation split — full sample")
    w("")
    w("`fav is YES` reads prices directly. `fav is NO` reconstructs every "
      "price as")
    w("`100 − kept_ask` / `100 − kept_bid`. Different code path, same claimed "
      "quantity.")
    w("")
    w("| side | n | implied | observed | mis pp | 95% CI | p(2s) | fade net ¢ |")
    w("|---|---|---|---|---|---|---|---|")
    m_all, _ = fade_stats(e, rng, "both (Phase 2 headline)", w)
    m_yes, _ = fade_stats(e[e["fav_is_yes"]], rng, "favourite is YES side", w)
    m_no, _ = fade_stats(e[~e["fav_is_yes"]], rng, "favourite is NO side", w)
    w("")

    diff = m_yes.mean() - m_no.mean()
    # bootstrap the difference
    a, b = m_yes, m_no
    d = np.array([a[rng.integers(0, len(a), len(a))].mean()
                  - b[rng.integers(0, len(b), len(b))].mean()
                  for _ in range(8000)])
    dlo, dhi = np.percentile(d, [2.5, 97.5])
    w(f"**Difference (YES minus NO): {diff:+.2f} pp, 95% CI "
      f"[{dlo:+.2f}, {dhi:+.2f}].**")
    w("")
    if dlo <= 0 <= dhi:
        w("The two orientations agree. The NO-side reconstruction is not "
          "introducing a bias,")
        w("and the undershoot is present on both. **Check passed.**")
    else:
        w("**The two orientations DISAGREE.** Something is wrong with the "
          "price")
        w("reconstruction or with the market. Everything downstream is "
          "suspect.")
    w("")

    # spread symmetry, as a second orientation diagnostic
    sy = e[e["fav_is_yes"]]["entry_spread"]
    sn = e[~e["fav_is_yes"]]["entry_spread"]
    w(f"Spread at entry: YES-side median {sy.median():.0f}¢, "
      f"NO-side median {sn.median():.0f}¢ — a reconstruction that flipped bid "
      f"and ask would show a negative or inflated spread on one side.")
    w("")

    # ------------------------------------------------ mirror pairs
    w("## 2. Mirror pairs — the same match priced twice")
    w("")
    mp = DATA / "mirror_state.parquet"
    if not mp.exists():
        w("*(mirror-side state not built; see `p5_mirror_build.py`)*")
    else:
        st2, b2, a2, m2 = p2.load("mirror")
        ev2 = p2.build_events(st2, b2, a2, m2, "deep:30", 0, min_minute=38)
        e2 = ev2[ev2["is_event"]].copy()
        pair = e.merge(e2, on="event_ticker", suffixes=("_k", "_m"))
        w(f"Events firing on **both** sides of the same match: "
          f"**{len(pair):,}**")
        if len(pair) >= 25:
            dm = pair["entry_mid_k"] - (pair["entry_mid_m"])
            w("")
            w(f"- favourite's entry mid, kept side vs sibling side: "
              f"median difference **{dm.median():+.2f}¢**, "
              f"{(dm.abs() <= 2).mean():.1%} within 2¢")
            agree = (pair["fav_won_k"] == pair["fav_won_m"]).mean()
            w(f"- outcome agreement: **{agree:.4f}**")
            w("")
            w("| measured on | n | implied | observed | mis pp | 95% CI | "
              "p(2s) | fade net ¢ |")
            w("|---|---|---|---|---|---|---|---|")
            k = pair[["entry_mid_k", "entry_bid_k", "fav_won_k"]].rename(
                columns=lambda c: c[:-2])
            m = pair[["entry_mid_m", "entry_bid_m", "fav_won_m"]].rename(
                columns=lambda c: c[:-2])
            fade_stats(k, rng, "kept side", w)
            fade_stats(m, rng, "sibling side", w)
        else:
            w("Too few paired firings for a meaningful comparison; the "
              "orientation split above carries the check.")
    w("")

    (ROOT / "reports" / "p5_task3e.md").write_text("\n".join(out),
                                                   encoding="utf-8")
    print(f"\n-> {ROOT / 'reports' / 'p5_task3e.md'}")


if __name__ == "__main__":
    main()

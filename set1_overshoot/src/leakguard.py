"""Permanent guards against selection-on-post-settlement-data.

The volume-dedupe bug was invisible to every check this project had, because
every check looked at *features*. The leak was in *which rows existed*. These
guards look at row membership.

Three-valued on purpose: PASS / FAIL / UNTESTABLE.

UNTESTABLE exists because of a hole found in v1 of this file. `liquidity_dollars`
scored 0.5031 (z = +0.88) and was recorded as a clean alternative dedupe rule.
It is not clean -- it reads 0 on almost every settled tennis market, so the
"rule" almost never actually chooses anything and the tie-break does the work.
Any mostly-null field passes a correlation test for free. **A rule that cannot
be tested is rejected, not passed.**

Two shapes of test, because there are two shapes of selection:

  check_side_choice     -- picking one of two mirrored sides. Null is exactly
                           0.50. Requires the rule to actually discriminate.
  check_selection       -- any filter. A filter may change WHO is in the
                           sample; it may not change how well the market prices
                           them. Requires both arms to be large enough to see a
                           shift that would matter.
"""
import numpy as np

Z_MAX = 4.0            # ~1 in 16,000 two-sided
MDE_MAX_PP = 2.0       # a rule whose test cannot see a 2pp bias is untestable
MIN_DISCRIM = 0.10     # a rule that decides <10% of cases is not the rule
Z_ALPHA, Z_BETA = 1.96, 0.8416      # two-sided 5%, 80% power

PASS, FAIL, UNTESTABLE = "PASS", "FAIL", "UNTESTABLE"


class SelectionLeak(AssertionError):
    pass


class Untestable(AssertionError):
    pass


class Result:
    __slots__ = ("verdict", "z", "stat", "n_eff", "mde_pp", "name", "msg")

    def __init__(self, verdict, z, stat, n_eff, mde_pp, name, msg):
        self.verdict, self.z, self.stat = verdict, z, stat
        self.n_eff, self.mde_pp, self.name, self.msg = n_eff, mde_pp, name, msg

    def raise_if_bad(self):
        if self.verdict == FAIL:
            raise SelectionLeak(self.msg)
        if self.verdict == UNTESTABLE:
            raise Untestable(self.msg)
        return self

    def __repr__(self):
        return f"<{self.verdict} {self.name} z={self.z:+.2f}>"


def _mde_prop_pp(n):
    """Smallest deviation from 0.5, in pp, detectable at 80% power."""
    if n <= 0:
        return float("inf")
    return 100.0 * (Z_ALPHA + Z_BETA) * 0.5 / np.sqrt(n)


def check_side_choice(kept_won, discriminated=None, name="dedupe",
                      z_max=Z_MAX, mde_max_pp=MDE_MAX_PP,
                      min_discrim=MIN_DISCRIM):
    """kept_won: did the KEPT side of each mirrored pair win.

    discriminated: bool array, True where the rule's field actually differed
    between the two sides. Where it did not, the choice fell through to the
    tie-break and tells us nothing about the rule. Omit only if the rule always
    discriminates by construction (e.g. ticker order).
    """
    kept_won = np.asarray(kept_won).astype(float)
    n_all = len(kept_won)
    if discriminated is None:
        disc = np.ones(n_all, bool)
        frac = 1.0
    else:
        disc = np.asarray(discriminated).astype(bool)
        frac = disc.mean() if n_all else 0.0

    n_eff = int(disc.sum())
    sub = kept_won[disc]
    mde = _mde_prop_pp(n_eff)
    p = sub.mean() if n_eff else float("nan")
    se = np.sqrt(0.25 / n_eff) if n_eff else np.nan
    z = (p - 0.5) / se if n_eff and se > 0 else float("nan")

    head = (f"[{name}] decides {frac:.1%} of pairs (n_eff={n_eff:,}/{n_all:,}); "
            f"P(kept wins | decided) = {p:.4f}, z = {z:+.2f}, "
            f"MDE = {mde:.2f} pp")

    if frac < min_discrim:
        return Result(UNTESTABLE, z, p, n_eff, mde, name, head +
                      f"  <-- UNTESTABLE: the field is degenerate, it "
                      f"separates the two sides in under {min_discrim:.0%} of "
                      f"pairs. It passes only because it almost never chooses. "
                      f"Innocence by emptiness is not innocence.")
    if mde > mde_max_pp:
        return Result(UNTESTABLE, z, p, n_eff, mde, name, head +
                      f"  <-- UNTESTABLE: too few decided pairs to detect a "
                      f"{mde_max_pp:.1f} pp bias.")
    if abs(z) > z_max:
        return Result(FAIL, z, p, n_eff, mde, name, head +
                      "  <-- READS THE OUTCOME. The rule must not depend on "
                      "volume, open interest, last price, liquidity, or "
                      "anything else recorded after settlement.")
    return Result(PASS, z, p, n_eff, mde, name, head)


def check_selection(mask, outcome, implied=None, name="filter", z_max=Z_MAX,
                    mde_max_pp=MDE_MAX_PP):
    """A filter may change who is sampled, not how well they are priced.

    mask    : True = row survives
    outcome : 0/1 realised result
    implied : market-implied probability at decision time. With it, the
              statistic is the calibration residual, which is what every
              downstream result actually rests on.
    """
    mask = np.asarray(mask).astype(bool)
    y = np.asarray(outcome, dtype=float)
    stat = y if implied is None else y - np.asarray(implied, dtype=float)
    ok = np.isfinite(stat)
    inn, out = mask & ok, (~mask) & ok
    na, nb = int(inn.sum()), int(out.sum())
    what = "outcome rate" if implied is None else "calibration residual"

    if na < 2 or nb < 2:
        return Result(UNTESTABLE, float("nan"), float("nan"), min(na, nb),
                      float("inf"), name,
                      f"[{name}] UNTESTABLE: one arm is empty "
                      f"({na:,} kept, {nb:,} dropped). The filter cannot be "
                      f"checked against the outcome and must be justified "
                      f"structurally instead.")
    a, b = stat[inn], stat[out]
    diff = a.mean() - b.mean()
    se = np.sqrt(a.var(ddof=1) / na + b.var(ddof=1) / nb)
    z = diff / se if se > 0 else 0.0
    mde = 100.0 * (Z_ALPHA + Z_BETA) * se
    head = (f"[{name}] {what}: kept {a.mean():+.4f} (n={na:,}) vs dropped "
            f"{b.mean():+.4f} (n={nb:,}); diff {diff:+.4f}, z = {z:+.2f}, "
            f"MDE = {mde:.2f} pp")

    if mde > mde_max_pp:
        return Result(UNTESTABLE, z, diff, min(na, nb), mde, name, head +
                      f"  <-- UNTESTABLE: the smaller arm ({min(na, nb):,} "
                      f"rows) cannot resolve a {mde_max_pp:.1f} pp shift.")
    if abs(z) > z_max:
        return Result(FAIL, z, diff, min(na, nb), mde, name, head +
                      "  <-- THE FILTER SHIFTS CALIBRATION. It is selecting on "
                      "something correlated with the outcome.")
    return Result(PASS, z, diff, min(na, nb), mde, name, head)


# ------------------------------------------------------------ assert wrappers
def assert_side_choice_neutral(kept_won, name="dedupe", **kw):
    return check_side_choice(kept_won, name=name, **kw).raise_if_bad()


def assert_selection_neutral(mask, outcome, implied=None, name="filter", **kw):
    return check_selection(mask, outcome, implied, name=name, **kw
                           ).raise_if_bad()


def table(results, title="SELECTION GUARDS"):
    """Render a list of Result objects. UNTESTABLE is never shown as a pass."""
    mark = {PASS: "  pass      ", FAIL: "  **FAIL**  ",
            UNTESTABLE: "  UNTESTABLE"}
    lines = [title, "=" * len(title)]
    for r in results:
        lines.append(mark[r.verdict] + " " + r.msg)
    n_f = sum(r.verdict == FAIL for r in results)
    n_u = sum(r.verdict == UNTESTABLE for r in results)
    lines.append(f"\n{len(results)} rules: {len(results) - n_f - n_u} pass, "
                 f"{n_f} fail, {n_u} untestable")
    return "\n".join(lines)

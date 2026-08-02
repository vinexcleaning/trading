r"""Exit study, stage 2: exit decay at realistic delays, and the mechanical benchmark.

Two questions, on complete books for 3,200 tokens where a top-decile wallet
actually sold in period 2.

**1. Does copying exits decay with latency?** Entries showed no decay at all --
flat from 0s to 1800s. Exits might behave differently, because an exit is often
a reaction to news rather than a considered entry, and news-driven prints move
fast. Measured separately and reported separately.

**2. Is the exit effect timing skill, or merely shorter holding?** These are not
the same thing and they have completely different copyability:

  - TIMING SKILL means the wallet exits before adverse moves. Copying it
    requires knowing when they exited, and that arrives with a delay.
  - SHORTER HOLDING means they simply spend less time exposed and so eat less
    tail risk. If that is all it is, a MECHANICAL rule -- sell H seconds after
    entry, no wallet selection whatsoever -- captures the same thing, and no
    wallet needs to be identified at all.

So the mechanical hold rule is the benchmark for exits in exactly the way the
naive favourite band was the benchmark for entries. It is run two ways: a fixed
grid of H, and a DURATION-MATCHED variant where the mechanical exit fires at the
same holding period the wallet actually used. The matched variant isolates
timing: same exposure window, different exit instant.

Guards: market clustering, bootstrap p-values, BH-FDR across every test here,
per-market decomposition never pooled. Prices are TRADE prices, not asks, which
flatters the copier on entry and flatters them again on exit, so the spread
scenarios are applied on top and the no-spread column is an upper bound.
"""
import json
import math
import os
import random
import time
from bisect import bisect_left
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXIT_FILLS = ROOT / "data" / "exit_fills.jsonl"
WALLET_FILLS = ROOT / "data" / "wallet_fills.jsonl"
POS = ROOT / "data" / "wallet_positions.jsonl"
SEL = ROOT / "data" / "exit_selection.json"
TOKENS = ROOT / "data" / "exit_target_tokens.json"
OUT = ROOT / "reports" / "exit_stage2_decay.json"
OUT.parent.mkdir(parents=True, exist_ok=True)

FEE_RATE = 0.10
CUT = int(os.environ.get("EXIT_CUT", "1751328000"))
DELAYS = [0, 10, 60, 300]
HOLD_GRID = [60, 300, 1800, 7200, 86400]
SEED = 20260801
N_BOOT = 2000
MAX_BOOT_CLUSTERS = 20_000
SPREADS_PP = {"none": 0.0, "half_0.5pp_per_leg": 0.5, "full_1.0pp_per_leg": 1.0}


def fee(p):
    return FEE_RATE * min(p, 1.0 - p)


sel = json.loads(SEL.read_text(encoding="utf-8"))
TOP = set(sel["top_decile"])
target = set(json.loads(TOKENS.read_text(encoding="utf-8"))["tokens"])
print(f"{len(TOP)} top-decile wallets, {len(target):,} target tokens")

# ------------------------------------------------- complete books per token
print("loading complete books...", flush=True)
book_ts, book_px = defaultdict(list), defaultdict(list)
n = 0
n_bad = 0
for line in EXIT_FILLS.open(encoding="utf-8"):
    try:
        f = json.loads(line)
    except Exception:  # noqa: BLE001
        # the puller may still be appending; a truncated final line is expected
        # on a trial run and is counted rather than silently swallowed
        n_bad += 1
        continue
    n += 1
    book_ts[f["token"]].append(f["ts"])
    book_px[f["token"]].append(f["price"])
    if n % 4_000_000 == 0:
        print(f"  {n:,}", flush=True)
if n_bad:
    print(f"  NOTE: {n_bad} unparseable line(s) skipped (partial file?)")
for t in book_ts:
    z = sorted(zip(book_ts[t], book_px[t]))
    book_ts[t] = [a for a, _ in z]
    book_px[t] = [b for _, b in z]
print(f"  {n:,} fills over {len(book_ts):,} tokens")


def price_at(tok, when, max_lookahead=6 * 3600):
    """First traded price at or after `when`; None if there is no such print."""
    ts = book_ts.get(tok)
    if not ts:
        return None
    i = bisect_left(ts, when)
    if i >= len(ts) or ts[i] - when > max_lookahead:
        return None
    return book_px[tok][i]


# ------------------------------------------- settlement + position metadata
print("loading position metadata...", flush=True)
meta = {}
for line in POS.open(encoding="utf-8"):
    r = json.loads(line)
    if r["flags"] or r["settle_state"] != "settled" or r["first_ts"] < CUT:
        continue
    if r["wallet"] not in TOP or r["token"] not in target:
        continue
    if r["shares_in"] <= 0 or r["n_sells"] <= 0:
        continue
    meta[(r["wallet"], r["token"])] = {
        "cid": r["cid"], "outcome": 1.0 if r["is_winner"] else 0.0,
        "shares_in": r["shares_in"],
        "frac_sold": min(r["shares_out"] / r["shares_in"], 1.0),
        "end_ts": r["end_ts"],
    }
print(f"  {len(meta):,} top-decile period-2 positions with sells in target tokens")

# --------------------------------------------- the wallets' own fill events
print("loading wallet fills...", flush=True)
buys, sells = defaultdict(list), defaultdict(list)
n = 0
for line in WALLET_FILLS.open(encoding="utf-8"):
    f = json.loads(line)
    n += 1
    if f["wallet"] not in TOP or f["token"] not in target or f["ts"] < CUT:
        continue
    k = (f["wallet"], f["token"])
    if k not in meta:
        continue
    (buys if f["side"] == "BUY" else sells)[k].append(
        (f["ts"], f["price"], f["shares"]))
    if n % 5_000_000 == 0:
        print(f"  {n:,}", flush=True)
for d in (buys, sells):
    for k in d:
        d[k].sort()
print(f"  {n:,} wallet fills scanned; {len(buys):,} positions with buys")


def wavg_delayed(events, tok, delay):
    """Share-weighted price a copier would transact at, `delay` after each fill."""
    num = den = 0.0
    for ts, _px, sh in events:
        p = price_at(tok, ts + delay)
        if p is None:
            continue
        num += p * sh
        den += sh
    return (num / den) if den > 0 else None


# ------------------------------------------------------------- simulation
def boot(by_mkt, n_boot=N_BOOT, seed=SEED):
    keys = [k for k, v in by_mkt.items() if v]
    if len(keys) < 5:
        return None
    rng = random.Random(seed)
    if len(keys) > MAX_BOOT_CLUSTERS:
        keys = rng.sample(keys, MAX_BOOT_CLUSTERS)
    pre = [(len(by_mkt[k]), sum(by_mkt[k])) for k in keys]
    tn = sum(a for a, _ in pre)
    ts_ = sum(b for _, b in pre)
    K, draws = len(pre), []
    for _ in range(n_boot):
        c = s = 0.0
        for _ in range(K):
            a, b = pre[rng.randrange(K)]
            c += a
            s += b
        if c:
            draws.append(s / c * 100)
    draws.sort()
    neg = sum(1 for d in draws if d <= 0) / len(draws)
    pos = sum(1 for d in draws if d >= 0) / len(draws)
    return {"mean_pp": round(ts_ / tn * 100, 4),
            "ci95": [round(draws[int(len(draws) * .025)], 4),
                     round(draws[int(len(draws) * .975)], 4)],
            "p": round(max(min(2 * min(neg, pos), 1.0), 1.0 / len(draws)), 6),
            "n_obs": tn, "n_markets": len(keys)}


print("\nsimulating...", flush=True)
# per delay: cid -> [values]
res_bh = {d: defaultdict(list) for d in DELAYS}
res_full = {d: defaultdict(list) for d in DELAYS}
res_delta = {d: defaultdict(list) for d in DELAYS}
res_exitpx = {d: defaultdict(list) for d in DELAYS}
mech = {h: defaultdict(list) for h in HOLD_GRID}
mech_delta = {h: defaultdict(list) for h in HOLD_GRID}
matched = defaultdict(list)
matched_delta = defaultdict(list)
stats = Counter()

SP = 0.0        # base run uses no spread; scenarios applied afterwards

for k, m in meta.items():
    w, tok = k
    bl, sl = buys.get(k), sells.get(k)
    if not bl or not sl:
        stats["missing_legs"] += 1
        continue
    cid, outcome, fs = m["cid"], m["outcome"], m["frac_sold"]
    entry0 = wavg_delayed(bl, tok, 0)
    if entry0 is None:
        stats["no_entry_price"] += 1
        continue
    stats["positions"] += 1

    # BALANCED PANEL. A position is included at every delay or at none.
    # Without this the population changes between delays -- the trial run had
    # 811 positions at 0s but 692 at 300s -- and what looks like decay is
    # partly just a different set of positions being averaged.
    per_delay = {}
    ok = True
    for d in DELAYS:
        e = wavg_delayed(bl, tok, d)
        x = wavg_delayed(sl, tok, d)
        if e is None or x is None:
            stats[f"missing_d{d}"] += 1
            ok = False
            break
        per_delay[d] = (e, x)
    if not ok:
        stats["dropped_incomplete_delay_panel"] += 1
    else:
        stats["complete_delay_panel"] += 1
        for d, (e, x) in per_delay.items():
            bh = outcome - e - fee(e)
            full = (fs * x + (1 - fs) * outcome) - e - fee(e) - fee(x) * fs
            res_bh[d][cid].append(bh)
            res_full[d][cid].append(full)
            res_delta[d][cid].append(full - bh)
            res_exitpx[d][cid].append(x - outcome)

    # mechanical hold rules, no wallet exit information used at all.
    # Same balanced-panel rule across the H grid.
    t_entry = bl[0][0]
    end = m["end_ts"]
    per_h = {}
    ok = True
    for h in HOLD_GRID:
        if end and t_entry + h >= end:
            px = outcome                      # market resolved before H elapsed
        else:
            px = price_at(tok, t_entry + h)
            if px is None:
                stats[f"mech_missing_{h}"] += 1
                ok = False
                break
        per_h[h] = px
    if not ok:
        stats["dropped_incomplete_mech_panel"] += 1
    else:
        stats["complete_mech_panel"] += 1
        r_bh = outcome - entry0 - fee(entry0)
        for h, px in per_h.items():
            r_mech = px - entry0 - fee(entry0) - fee(px)
            mech[h][cid].append(r_mech)
            mech_delta[h][cid].append(r_mech - r_bh)

    # duration-matched mechanical exit: same exposure window, different instant
    hold = max(1, int(sum(t for t, _, _ in sl) / len(sl)) - t_entry)
    end = m["end_ts"]
    if end and t_entry + hold >= end:
        pxm = outcome
    else:
        pxm = price_at(tok, t_entry + hold)
    if pxm is not None:
        x0 = wavg_delayed(sl, tok, 0)
        if x0 is not None:
            r_match = (fs * pxm + (1 - fs) * outcome) - entry0 - fee(entry0) - fee(pxm) * fs
            r_wal = (fs * x0 + (1 - fs) * outcome) - entry0 - fee(entry0) - fee(x0) * fs
            matched[cid].append(r_match)
            matched_delta[cid].append(r_wal - r_match)

print(f"  {dict(stats)}")

tests = []
report = {
    "meta": {
        "cut_iso": time.strftime("%Y-%m-%d", time.gmtime(CUT)),
        "n_top_decile_wallets": len(TOP),
        "n_target_tokens": len(target),
        "n_positions_simulated": stats["positions"],
        "delays_s": DELAYS, "hold_grid_s": HOLD_GRID,
        "clustering": "market-level bootstrap, never pooled",
        "limits": ["trade prices not asks -- flatters the copier on BOTH legs",
                   "no-print observations counted missing, never carried forward"],
    },
    "exit_decay": {}, "mechanical_hold": {}, "duration_matched": {},
}

print("\n=== EXIT DECAY (no spread; delta = copy-exits minus buy-and-hold) ===")
print(f"{'delay':>7} {'n':>8} {'buy&hold':>10} {'copy exits':>11} {'delta':>9} "
      f"{'delta CI95':>20} {'p':>9} {'exit_px-outcome':>16}")
for d in DELAYS:
    b_bh, b_fu = boot(res_bh[d]), boot(res_full[d])
    b_dl, b_xp = boot(res_delta[d]), boot(res_exitpx[d])
    if not (b_bh and b_fu and b_dl):
        continue
    report["exit_decay"][str(d)] = {
        "buy_and_hold": b_bh, "copy_exits": b_fu, "delta": b_dl,
        "exit_price_minus_outcome": b_xp}
    tests.append((f"exit_delta_d{d}", b_dl))
    print(f"{d:>6}s {b_dl['n_obs']:>8,} {b_bh['mean_pp']:>10.3f} "
          f"{b_fu['mean_pp']:>11.3f} {b_dl['mean_pp']:>9.3f} "
          f"{str(b_dl['ci95']):>20} {b_dl['p']:>9.5f} "
          f"{(b_xp['mean_pp'] if b_xp else 0):>16.3f}")

print("\n=== MECHANICAL HOLD RULE (no wallet selection at all) ===")
print(f"{'hold':>8} {'n':>8} {'return':>9} {'vs buy&hold':>12} "
      f"{'CI95':>20} {'p':>9}")
for h in HOLD_GRID:
    b_m, b_d = boot(mech[h]), boot(mech_delta[h])
    if not (b_m and b_d):
        continue
    report["mechanical_hold"][str(h)] = {"return": b_m, "delta_vs_bh": b_d}
    tests.append((f"mech_delta_h{h}", b_d))
    print(f"{h:>7}s {b_d['n_obs']:>8,} {b_m['mean_pp']:>9.3f} "
          f"{b_d['mean_pp']:>12.3f} {str(b_d['ci95']):>20} {b_d['p']:>9.5f}")

print("\n=== DURATION-MATCHED: wallet exit vs mechanical exit at the SAME hold ===")
b_mm, b_md = boot(matched), boot(matched_delta)
if b_mm and b_md:
    report["duration_matched"] = {"mechanical_return": b_mm,
                                  "wallet_minus_mechanical": b_md}
    tests.append(("duration_matched_wallet_minus_mech", b_md))
    print(f"  mechanical at matched hold : {b_mm['mean_pp']:.3f}pp")
    print(f"  wallet minus mechanical    : {b_md['mean_pp']:.3f}pp "
          f"CI{b_md['ci95']}  p={b_md['p']:.5f}")
    print("  -> positive means genuine TIMING skill; ~zero means the effect is "
          "just the shorter holding period")

# spread scenarios applied to the headline delta
print("\n=== EXIT-COPY DELTA UNDER SPREAD SCENARIOS (delay 60s) ===")
report["spread_scenarios_d60"] = {}
for sname, spp in SPREADS_PP.items():
    sp = spp / 100.0
    d = defaultdict(list)
    for cid, vals in res_delta[60].items():
        # each exit leg crosses the spread once, scaled by frac sold ~ mean
        d[cid] = [v - sp for v in vals]
    b = boot(d)
    if b:
        report["spread_scenarios_d60"][sname] = b
        tests.append((f"exit_delta_d60_{sname}", b))
        print(f"  {sname:>22}: {b['mean_pp']:>8.3f}pp CI{b['ci95']} p={b['p']:.5f}")

ps = sorted((t[1]["p"], t[0]) for t in tests)
m_ = len(ps)
crit = None
for i, (p, lab) in enumerate(ps, 1):
    if p <= i / m_ * 0.05:
        crit = i
report["bh_fdr"] = {
    "n_tests": m_, "n_significant": crit or 0,
    "detail": {lab: {"p": p, "bh_threshold": round(i / m_ * 0.05, 6),
                     "significant_at_fdr_5pct": bool(crit and i <= crit)}
               for i, (p, lab) in enumerate(ps, 1)}}
print(f"\n=== BH-FDR across {m_} tests: {crit or 0} significant at 5% ===")

OUT.write_text(json.dumps(report, indent=2), encoding="utf-8")
print(f"\nwrote {OUT}")

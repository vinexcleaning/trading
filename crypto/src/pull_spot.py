"""Pull 1-minute BTC spot for the panel window, and VALIDATE it against BRTI.

Why this is needed: the models need spot at each DECISION minute. The panel's
`anchor` is the previous event's settlement, which can be up to an hour stale.
Feeding an hour-old spot to M1 would guarantee it loses to the mid — which
would be a strawman result, not a test. So real per-minute spot is required.

Kalshi settles on CF Benchmarks BRTI, a composite of Coinbase, Kraken,
Bitstamp, Gemini, itBit and LMAX. Coinbase is a constituent, not the index, so
it is a PROXY. The proxy is validated directly: `expiration_value` in the
settled data IS the BRTI 60-second average at each hourly boundary, so the
Coinbase minute containing that boundary can be compared to it. The measured
basis is reported and carried into the results.

Coinbase public candles: max 300 rows/call, granularity 60s. Read-only, no auth.
"""
import datetime as dt
import json
import os
import time

import numpy as np
import requests

UA = {"User-Agent": "research-readonly/0.1"}
CB = "https://api.exchange.coinbase.com/products/BTC-USD/candles"
OUT = r"C:\Users\gianf\crypto\data\spot"
SETTLED = r"C:\Users\gianf\crypto\data\kalshi_settled"


def get(start, end, granularity=60):
    for a in range(7):
        try:
            r = requests.get(CB, params={
                "start": dt.datetime.utcfromtimestamp(start).isoformat(),
                "end": dt.datetime.utcfromtimestamp(end).isoformat(),
                "granularity": granularity}, headers=UA, timeout=45)
        except Exception:
            time.sleep(0.8 * (a + 1))
            continue
        if r.status_code == 429:
            time.sleep(1.2 * (a + 1))
            continue
        if r.status_code >= 500:
            time.sleep(0.8 * (a + 1))
            continue
        if r.status_code != 200:
            return None
        return r.json()
    return None


def main():
    os.makedirs(OUT, exist_ok=True)
    # window: the settled panel span, padded
    t_end = int(dt.datetime(2026, 8, 1, 1, 0, tzinfo=dt.timezone.utc)
                .timestamp())
    t_start = int(dt.datetime(2026, 5, 24, 0, 0, tzinfo=dt.timezone.utc)
                  .timestamp())
    print(f"pulling BTC-USD 1m from {dt.datetime.utcfromtimestamp(t_start)} "
          f"to {dt.datetime.utcfromtimestamp(t_end)}", flush=True)

    span = 300 * 60          # 300 candles per call
    rows = {}
    t = t_start
    calls = 0
    t0 = time.time()
    while t < t_end:
        j = get(t, min(t + span, t_end))
        calls += 1
        if j:
            for c in j:
                # [ time, low, high, open, close, volume ]
                rows[int(c[0])] = {"t": int(c[0]), "low": float(c[1]),
                                   "high": float(c[2]), "open": float(c[3]),
                                   "close": float(c[4]), "vol": float(c[5])}
        t += span
        if calls % 50 == 0:
            print(f"  [{time.time()-t0:6.0f}s] {calls} calls, "
                  f"{len(rows)} minutes", flush=True)
        time.sleep(0.12)

    path = os.path.join(OUT, "btc_1m.jsonl")
    with open(path, "w", encoding="utf-8") as f:
        for k in sorted(rows):
            f.write(json.dumps(rows[k], separators=(",", ":")) + "\n")
    print(f"\nwrote {path}: {len(rows)} minutes over {calls} calls")

    # ---------------- coverage ----------------
    ks = sorted(rows)
    expect = (t_end - t_start) // 60
    print(f"coverage: {len(ks)}/{expect} = {100*len(ks)/expect:.2f}%")
    gaps = [(a, b) for a, b in zip(ks, ks[1:]) if b - a > 60]
    print(f"gaps > 1 min: {len(gaps)}")
    if gaps:
        big = sorted(gaps, key=lambda g: -(g[1] - g[0]))[:5]
        for a, b in big:
            print(f"   {dt.datetime.utcfromtimestamp(a)} -> "
                  f"{dt.datetime.utcfromtimestamp(b)} "
                  f"({(b-a)/60:.0f} min)")

    # ---------------- VALIDATE against BRTI settlements ----------------
    print("\nvalidating Coinbase proxy against CF Benchmarks BRTI "
          "(expiration_value at hourly boundaries)")
    settles = {}
    with open(os.path.join(SETTLED, "KXBTCD.jsonl"), encoding="utf-8") as f:
        for line in f:
            try:
                m = json.loads(line)
            except json.JSONDecodeError:
                continue
            v, ct = m.get("expiration_value"), m.get("close_time")
            if v in (None, "") or not ct:
                continue
            try:
                settles[ct] = float(v)
            except ValueError:
                pass
    diffs = []
    for ct, v in settles.items():
        ts = int(dt.datetime.fromisoformat(
            ct.replace("Z", "+00:00")).timestamp())
        # BRTI settle is the mean of the 60s BEFORE close -> the candle
        # starting at ts-60 covers exactly that window
        c = rows.get(ts - 60)
        if not c:
            continue
        diffs.append((v - c["close"]) / v * 1e4)      # basis points
    if diffs:
        d = np.array(diffs)
        print(f"  matched {len(d)} hourly boundaries")
        print(f"  BRTI - Coinbase, basis points: "
              f"mean={d.mean():+.2f} med={np.median(d):+.2f} "
              f"sd={d.std():.2f}")
        print(f"  |diff| p50={np.percentile(np.abs(d),50):.2f}bp "
              f"p90={np.percentile(np.abs(d),90):.2f}bp "
              f"p99={np.percentile(np.abs(d),99):.2f}bp "
              f"max={np.abs(d).max():.2f}bp")
        print(f"  in $ at 62,900: p50=${np.percentile(np.abs(d),50)/1e4*62900:.2f} "
              f"p99=${np.percentile(np.abs(d),99)/1e4*62900:.2f}")
        json.dump({"n": int(len(d)), "mean_bp": float(d.mean()),
                   "sd_bp": float(d.std()),
                   "p50_abs_bp": float(np.percentile(np.abs(d), 50)),
                   "p99_abs_bp": float(np.percentile(np.abs(d), 99))},
                  open(os.path.join(OUT, "brti_basis.json"), "w"), indent=2)


if __name__ == "__main__":
    main()

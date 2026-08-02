"""Can we resolve Kalshi player names to tennisabstract.com pages, at scale?

Tests the slug convention (FirstnameLastname, no spaces/accents) against a
stratified sample of real Kalshi players across all four tiers.
"""
import concurrent.futures as cf
import json
import pathlib
import re
import sys

import pandas as pd
import requests

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import tennis_data as td  # noqa: E402

H = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}


def slug(name):
    s = td.strip_accents(name)
    return re.sub(r"[^A-Za-z]", "", s)


def probe(name):
    url = f"https://www.tennisabstract.com/jsmatches/{slug(name)}.js"
    try:
        r = requests.get(url, headers=H, timeout=45)
    except Exception as e:  # noqa: BLE001
        return name, "error", str(e)[:40], None
    if r.status_code != 200:
        return name, f"http{r.status_code}", None, None
    txt = r.text
    m = re.search(r"var\s+matchmx\s*=\s*\[\[", txt)
    if not m:
        return name, "no-matchmx", None, None
    start = txt.index("[[", m.end() - 2)
    depth, i = 0, start
    while i < len(txt):
        if txt[i] == "[":
            depth += 1
        elif txt[i] == "]":
            depth -= 1
            if depth == 0:
                break
        i += 1
    try:
        rows = json.loads(txt[start:i + 1])
    except json.JSONDecodeError:
        return name, "unparsed", None, None
    dates = [r0[0] for r0 in rows if r0 and r0[0]]
    ncols = len(rows[0]) if rows else 0
    return name, "ok", f"n={len(rows)} cols={ncols} {min(dates)}..{max(dates)}", max(dates)


def main():
    ev = td.load_kalshi_events()
    sample = []
    for (tour, tier), g in ev.groupby(["tour", "tier"], observed=True):
        names = pd.unique(pd.concat([g["player_a"], g["player_b"]]).dropna())
        for n in names[:15]:
            sample.append((f"{tour} {tier}", n))

    print(f"probing {len(sample)} players ...\n")
    results = []
    with cf.ThreadPoolExecutor(max_workers=8) as ex:
        futs = {ex.submit(probe, n): (seg, n) for seg, n in sample}
        for f in cf.as_completed(futs):
            seg, n = futs[f]
            results.append((seg, *f.result()))

    df = pd.DataFrame(results, columns=["seg", "name", "status", "detail", "last"])
    df = df.sort_values(["seg", "name"])
    for seg, g in df.groupby("seg"):
        ok = (g["status"] == "ok").mean()
        print(f"=== {seg}: {(g['status'] == 'ok').sum()}/{len(g)} resolved ({ok * 100:.0f}%)")
        for _, r in g.iterrows():
            print(f"    {r['name']:<32} {r['status']:<12} {r['detail'] or ''}")
        print()

    good = df[df["status"] == "ok"]
    if len(good):
        print(f"OVERALL resolved: {len(good)}/{len(df)} ({len(good) / len(df) * 100:.0f}%)")
        print(f"most recent match date across sample: {good['last'].max()}")
        print("\nrecency distribution of last match per player:")
        print(good["last"].str[:6].value_counts().sort_index().to_string())


if __name__ == "__main__":
    main()

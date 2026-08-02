"""Validate the community Brasileirao dataset by pulling and parsing it."""
import csv
import hashlib
import io
import json
import os

import requests

UA = {"User-Agent": "Mozilla/5.0 (soccer-research/1.0)"}
REP = os.path.join(os.path.dirname(__file__), "..", "reports")
RAW = "https://raw.githubusercontent.com/leeofernandes1980/brasileirao-dataset/HEAD/"
FILES = ["campeonato-brasileiro-full.csv",
         "campeonato-brasileiro-estatisticas-full.csv",
         "campeonato-brasileiro-gols.csv",
         "campeonato-brasileiro-cartoes.csv"]

out = {}
for f in FILES:
    try:
        r = requests.get(RAW + f, headers=UA, timeout=90)
    except requests.RequestException as e:
        print(f"{f}: ERR {e}")
        continue
    if r.status_code != 200:
        print(f"{f}: http {r.status_code}")
        out[f] = {"http": r.status_code}
        continue
    rows = list(csv.reader(io.StringIO(r.text)))
    hdr, body = rows[0], rows[1:]
    print(f"\n=== {f} ===")
    print(f"  http=200 bytes={len(r.content):,} sha256={hashlib.sha256(r.content).hexdigest()[:16]}")
    print(f"  rows={len(body):,} cols={len(hdr)}")
    print(f"  columns: {hdr[:18]}")
    di = next((i for i, c in enumerate(hdr)
               if c.strip().lower() in ("data", "date")), None)
    if di is not None:
        ds = sorted(x[di] for x in body if len(x) > di and x[di])
        print(f"  date range: {ds[0]} .. {ds[-1]}")
        out[f] = {"rows": len(body), "cols": len(hdr),
                  "date_first": ds[0], "date_last": ds[-1], "columns": hdr}
    else:
        out[f] = {"rows": len(body), "cols": len(hdr), "columns": hdr}
    if body:
        print(f"  sample row: {body[0][:12]}")

with open(os.path.join(REP, "brasileirao.json"), "w", encoding="utf-8") as fh:
    json.dump(out, fh, indent=1, default=str)
print("\nwrote reports/brasileirao.json")

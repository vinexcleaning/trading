"""Is there a surviving mirror of Sackmann's deleted tennis_atp / tennis_wta?

This matters more than its size suggests. The whole Stage 0-5 player model
(LEDGER section 4, ~1 GB of derived artifacts, a full session to compute) runs
on a frozen local mirror that ends 2026-06-02. If a live fork exists and is
still updating, the tennis thread's binding constraint (T002: features end
2026-06-02, 85% of markets are after that) is relieved. If not, it is confirmed
permanent.

Verified by fetching the actual CSV and reading its last date, not by the fork
count on a listing page.
"""
import csv
import io
import json
import os
import time

import requests

UA = {"User-Agent": "Mozilla/5.0 (market-selection-research/1.0)"}
REP = os.path.join(os.path.dirname(__file__), "..", "reports")


def gh(url, params=None):
    r = requests.get(url, params=params, headers=UA, timeout=45)
    time.sleep(0.7)
    return r


def main():
    out = {}
    print("=== does JeffSackmann still have the repos? ===")
    r = gh("https://api.github.com/users/JeffSackmann/repos",
           {"per_page": 100, "type": "all"})
    repos = r.json() if r.status_code == 200 else []
    print(f"  public repos on the account: {len(repos)}")
    for x in repos:
        print(f"    {x['full_name']:52s} pushed={x['pushed_at']} "
              f"size={x['size']}KB")
    out["sackmann_repos"] = [x["full_name"] for x in repos]

    print("\n=== searching for surviving copies of atp_matches ===")
    cands = []
    for q in ["atp_matches filename:atp_matches_2025.csv",
              "tennis_atp", "tennis_wta sackmann", "atp_matches"]:
        r = gh("https://api.github.com/search/repositories",
               {"q": q, "sort": "updated", "per_page": 12})
        if r.status_code != 200:
            print(f"  search {q!r}: http {r.status_code}")
            continue
        d = r.json()
        print(f"  {q!r}: {d.get('total_count')} repos")
        for x in d.get("items", [])[:12]:
            print(f"    {x['full_name']:48s} pushed={x['pushed_at']} "
                  f"stars={x['stargazers_count']} size={x['size']}KB")
            cands.append(x["full_name"])

    cands = list(dict.fromkeys(cands))
    print(f"\n=== fetching atp_matches_2026.csv / 2025 from {len(cands)} candidates ===")
    results = []
    for full in cands:
        for branch in ("master", "main"):
            for fn in ("atp_matches_2026.csv", "atp_matches_2025.csv"):
                url = f"https://raw.githubusercontent.com/{full}/{branch}/{fn}"
                try:
                    r = requests.get(url, headers=UA, timeout=45)
                except Exception:  # noqa: BLE001
                    continue
                time.sleep(0.3)
                if r.status_code != 200 or len(r.content) < 500:
                    continue
                rows = list(csv.reader(io.StringIO(r.text)))
                if len(rows) < 2:
                    continue
                hdr = rows[0]
                di = hdr.index("tourney_date") if "tourney_date" in hdr else None
                dates = sorted(x[di] for x in rows[1:] if di is not None
                               and len(x) > di and x[di])
                rec = {"repo": full, "branch": branch, "file": fn,
                       "rows": len(rows) - 1, "cols": len(hdr),
                       "first_date": dates[0] if dates else None,
                       "last_date": dates[-1] if dates else None}
                results.append(rec)
                print(f"  HIT {full}/{branch}/{fn}: {rec['rows']} rows, "
                      f"{rec['cols']} cols, {rec['first_date']}..{rec['last_date']}")
    out["mirrors"] = results
    if not results:
        print("  no surviving mirror carried a readable atp_matches CSV")
    with open(os.path.join(REP, "sackmann_forks.json"), "w",
              encoding="utf-8") as fh:
        json.dump(out, fh, indent=1, default=str)
    print("\nwrote reports/sackmann_forks.json")


if __name__ == "__main__":
    main()

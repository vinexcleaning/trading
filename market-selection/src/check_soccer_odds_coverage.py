"""Does a free Pinnacle CLOSING line exist for the soccer leagues Kalshi trades?

The interim scorecard showed Kalshi's soccer book is not European. It is
Liga MX, USL, NWSL, DIMAYOR (Colombia), Argentine Primera, Copa do Brasil,
Peru Liga 1, Ecuador LigaPro, Uruguay Primera and Chile. Those are exactly the
leagues where you would NOT assume a free sharp reference exists.

If one does, these families are testable by the T012/T013 method -- compare
Kalshi to the closing line, which is the only pattern in this project's history
that produced a trustworthy answer rather than a retraction.
"""
import csv
import io
import json
import os
import time

import requests

UA = {"User-Agent": "Mozilla/5.0 (market-selection-research/1.0)"}
REP = os.path.join(os.path.dirname(__file__), "..", "reports")
BASE = "https://www.football-data.co.uk/new/{}.csv"

# code -> the Kalshi series it would serve
LEAGUES = {
    "MEX": "KXLIGAMXGAME / KXLIGAMXTOTAL / KXLIGAMXSPREAD / KXLIGAMX1H",
    "USA": "KXMLSGAME / KXMLSTOTAL / KXUSLGAME / KXNWSLGAME",
    "ARG": "KXARGPREMDIVGAME / KXARGPREMDIVTOTAL / KXARGNACBGAME",
    "BRA": "KXCOPADOBRASILGAME / KXCOPADOBRASILTOTAL",
    "COL": "KXDIMAYORGAME / KXDIMAYORTOTAL",
    "PER": "KXPERLIGA1GAME / KXPERLIGA1TOTAL",
    "ECU": "KXECULPGAME",
    "URY": "KXURYPDGAME",
    "CHN": "(Chinese Super League)",
    "JPN": "(J-League)",
    "KOR": "(K-League)",
    "DNK": "", "SWE": "", "NOR": "", "FIN": "", "IRL": "", "POL": "",
    "ROU": "", "RUS": "", "SWZ": "", "AUT": "",
}
# Chile is not an obvious 3-letter code; try the plausible ones
EXTRA = ["CHL", "CHI", "VEN", "BOL", "PRY", "GUA", "CRC"]


_SEEN = {}


def probe(code):
    """CAUTION: football-data.co.uk returns HTTP 200 with a WRONG-COUNTRY file
    for codes it does not carry. Confirmed byte-identical by sha256:

        COL == POL == BOL   (all are Poland's Ekstraklasa)
        KOR == NOR          (both are Norway's Eliteserien)
        CHL == CHI == CHN   (all are China's Super League)

    So a naive probe "confirms" free Pinnacle closing odds for Colombia, Peru,
    Korea and Chile that do not exist, and would have put Polish league results
    behind a Colombian market. The `League` column and a content hash are the
    only things that catch it -- status code, byte count and column names all
    look perfectly healthy.
    """
    try:
        r = requests.get(BASE.format(code), headers=UA, timeout=45)
    except requests.RequestException as e:
        return {"code": code, "status": "ERROR", "err": str(e)[:80]}
    if r.status_code != 200 or len(r.content) < 2000:
        return {"code": code, "status": "DEAD", "http": r.status_code,
                "bytes": len(r.content)}
    import hashlib
    digest = hashlib.sha256(r.content).hexdigest()[:16]
    dup_of = _SEEN.get(digest)
    _SEEN.setdefault(digest, code)
    rows = list(csv.reader(io.StringIO(r.text)))
    hdr = rows[0]
    body = rows[1:]
    di = hdr.index("Date") if "Date" in hdr else None
    li = hdr.index("League") if "League" in hdr else None
    dates = [x[di] for x in body if di is not None and len(x) > di and x[di]]
    leagues = sorted({x[li] for x in body if li is not None and len(x) > li})
    has_pinn = any(c.startswith("PSC") for c in hdr)
    # how many rows actually carry a Pinnacle closing price
    pi = hdr.index("PSCH") if "PSCH" in hdr else None
    with_pinn = sum(1 for x in body
                    if pi is not None and len(x) > pi and x[pi].strip())
    return {"code": code,
            "status": "DUPLICATE_OF_" + dup_of if dup_of else "OK",
            "sha256_16": digest, "duplicate_of": dup_of,
            "rows": len(body),
            "columns": len(hdr), "leagues": leagues[:6],
            "n_leagues": len(leagues),
            "date_first": dates[0] if dates else None,
            "date_last": dates[-1] if dates else None,
            "has_pinnacle_close": has_pinn,
            "rows_with_pinnacle": with_pinn,
            "pct_with_pinnacle": round(100 * with_pinn / max(len(body), 1), 1)}


def main():
    out = []
    print(f"{'code':5s} {'status':7s} {'rows':>6s} {'pinn%':>6s} "
          f"{'first':>10s} {'last':>10s}  leagues")
    for code in list(LEAGUES) + EXTRA:
        rec = probe(code)
        rec["kalshi_series"] = LEAGUES.get(code, "")
        out.append(rec)
        if rec["status"] == "OK":
            print(f"{code:5s} {rec['status']:7s} {rec['rows']:6d} "
                  f"{rec['pct_with_pinnacle']:6.1f} {str(rec['date_first']):>10s} "
                  f"{str(rec['date_last']):>10s}  {rec['n_leagues']} "
                  f"{rec['leagues']}")
        else:
            print(f"{code:5s} {rec['status']:7s} {'':6s} {'':6s} "
                  f"http={rec.get('http')}")
        time.sleep(0.3)
    with open(os.path.join(REP, "soccer_odds_coverage.json"), "w",
              encoding="utf-8") as fh:
        json.dump(out, fh, indent=1)
    dups = [r for r in out if str(r["status"]).startswith("DUPLICATE")]
    if dups:
        print(f"\n*** {len(dups)} codes returned a file ALREADY SERVED FOR "
              f"ANOTHER COUNTRY (HTTP 200, wrong data): ***")
        for r in dups:
            print(f"    {r['code']} is byte-identical to {r['duplicate_of']} "
                  f"-> actually {r['leagues']}")

    ok = [r for r in out if r["status"] == "OK" and r["rows_with_pinnacle"] > 100]
    print(f"\n{len(ok)} country files carry a Pinnacle closing line on >100 matches")
    print(f"total matches with a free Pinnacle close: "
          f"{sum(r['rows_with_pinnacle'] for r in ok):,}")
    print("\nmapped to Kalshi series:")
    for r in ok:
        if r["kalshi_series"]:
            print(f"  {r['code']:4s} {r['rows_with_pinnacle']:6,d} matches  "
                  f"-> {r['kalshi_series']}")


if __name__ == "__main__":
    main()

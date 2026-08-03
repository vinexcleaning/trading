"""Why the >=50%-of-retrieved bar does not prune Bloomberg.

The bar measures the on-topic share of the videos we happened to RETRIEVE from a
channel. Bloomberg Television was retrieved twice, and both hits genuinely were
about prediction markets -- Bloomberg does cover Kalshi and Polymarket. So its
specialisation score is 100% and it sails through, while its 200-upload catalogue
is general financial news. The metric is computed on the wrong denominator.

The thing the rule was meant to capture is CATALOGUE specialisation: what share of
everything the channel publishes is on topic. That is computable for free -- the
expansion already stored up to 200 upload titles per channel. G3 on a title alone
is weaker than G3 on a transcript, but for a channel-level ratio it is enough, and
it costs no network.

This script compares the two bars. It changes nothing.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import db  # noqa: E402
import gates  # noqa: E402

WATCH = ["Bloomberg Television", "OddsJam Sports Betting Picks",
         "DGFantasy - Prizepicks & Sports Betting", "Nates Tokens",
         "Trading with DaviddTech", "Moon Dev", "freeCodeCamp.org",
         "Emergent Mind", "LINEMAKER SPORTS", "Captain Altcoin"]

con = db.connect()

rows = con.execute(
    """SELECT channel_id, channel_name,
              SUM(CASE WHEN source='search' THEN 1 ELSE 0 END) AS retrieved,
              SUM(CASE WHEN source='search' AND gate_status NOT IN
                    ('DROP_G3_OFF_TOPIC','DROP_G3_DISCRETIONARY')
                    AND gate_status IS NOT NULL AND gate_status!='DROP_META'
                  THEN 1 ELSE 0 END) AS g3_ok,
              SUM(CASE WHEN source='channel_expansion' THEN 1 ELSE 0 END) AS catalogue
       FROM videos WHERE channel_id IS NOT NULL GROUP BY channel_id"""
).fetchall()

print(f"{'channel':<40}{'retr':>6}{'ret%':>7}{'cat':>6}{'cat%':>7}   verdict")
print("-" * 82)
results = []
for r in rows:
    if not r["catalogue"]:
        continue
    titles = [t["title"] for t in con.execute(
        "SELECT title FROM videos WHERE channel_id=? AND source='channel_expansion'",
        (r["channel_id"],)) if t["title"]]
    if not titles:
        continue
    on = sum(1 for t in titles if gates.g3_on_topic(t, "")[0])
    cat_share = on / len(titles)
    ret_share = (r["g3_ok"] / r["retrieved"]) if r["retrieved"] else 0.0
    results.append({
        "name": r["channel_name"] or "?", "retrieved": r["retrieved"],
        "ret_share": ret_share, "catalogue": len(titles), "cat_share": cat_share,
    })

results.sort(key=lambda x: -x["cat_share"])
for x in results:
    if x["name"] not in WATCH:
        continue
    passes_ret = x["ret_share"] >= 0.5 and x["retrieved"] >= 2
    passes_cat = x["cat_share"] >= 0.30
    verdict = (f"retrieved-bar {'PASS' if passes_ret else 'FAIL'} | "
               f"catalogue-bar {'PASS' if passes_cat else 'FAIL'}")
    print(f"{x['name'][:39]:<40}{x['retrieved']:>6}{100*x['ret_share']:>6.0f}%"
          f"{x['catalogue']:>6}{100*x['cat_share']:>6.0f}%   {verdict}")

print("\nfull distribution of catalogue specialisation across expanded channels:")
for lo, hi in [(0, .05), (.05, .10), (.10, .20), (.20, .30), (.30, .50), (.50, 1.01)]:
    n = sum(1 for x in results if lo <= x["cat_share"] < hi)
    print(f"  {int(100*lo):>3}-{int(100*hi):>3}%  {n:>3} channels")

for thr in (0.20, 0.30, 0.40, 0.50):
    keep = [x for x in results if x["cat_share"] >= thr]
    rows_kept = sum(x["catalogue"] for x in keep)
    total_rows = sum(x["catalogue"] for x in results)
    print(f"\n  catalogue bar >={int(100*thr)}%: keeps {len(keep)}/{len(results)} channels, "
          f"{rows_kept}/{total_rows} rows ({100*rows_kept/total_rows:.0f}%)")
con.close()

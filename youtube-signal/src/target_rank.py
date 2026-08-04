"""Reading order for the TARGETED Kalshi/Polymarket campaign.

Different job from rank_substance.py, which orders by substance proxy alone.
That is right for building a knowledge base and wrong for hunting a live edge,
because it is indifferent to whether an edge has already been competed away.

THE SATURATION RULE, stated by the user and encoded here:

    "If it's been on YouTube, has a lot of views, and it's old, most likely
     it's already saturated."

That is a claim about the MARKET, not about the video, and it is a sound one for
this domain. A strategy explained to 500,000 people three years ago is being run
by some fraction of them; whatever inefficiency it named has had three years of
capital pointed at it. The same video at 800 views is a different proposition,
and so is the same view count three weeks old.

So the penalty is on the INTERACTION of reach and age, not on either alone:

    saturation = log10(views / 5000) * age_years * 2,  capped at 6, floor 0

  * under 5,000 views      -> no penalty at any age. Nobody competed it away.
  * 500k views, 3 years    -> 2 * 3 * 2 = 12 -> capped 6. Heavily deprioritised.
  * 500k views, 2 months   -> 2 * 0.17 * 2 = 0.67. Barely touched.
  * 50k views, 18 months   -> 1 * 1.5 * 2 = 3. Middling.

Deliberately NOT a filter. A saturated video can still carry a durable mechanism
or a data source, and the user's own framing allows that an old strategy may
still work. It is reordered, never dropped, and the penalty is printed beside the
score so the judgment stays visible instead of buried.

WHERE THE PENALTY DOES NOT APPLY: families V3 (data sources) and V4 (validation
and backtesting). A GraphQL endpoint or a backtest method does not stop working
because many people know about it -- there is no crowding mechanism. Saturation
is a claim about ALPHA, and only V1/V2 make alpha claims. Applying it to a data
source would be superstition rather than reasoning.

Usage:  $env:SIGNAL_DB = "kalshi_edge"
        python src/target_rank.py [n]
"""

import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import db_phase2  # noqa: E402
import rank_substance as RS  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
LOW_VIEW = 5_000
ALPHA_FAMILIES = {"V1", "V2"}     # only these make a crowdable claim


def saturation(views, age_months, families):
    """Reach x age, but only for families that claim an edge."""
    if not (families & ALPHA_FAMILIES):
        return 0.0
    v = views or 0
    if v <= LOW_VIEW or not age_months:
        return 0.0
    return min(6.0, math.log10(v / LOW_VIEW) * (age_months / 12.0) * 2.0)


def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 25
    con = db_phase2.connect()

    fam = {}
    for r in con.execute("SELECT DISTINCT video_id, family FROM retrieval_hits"):
        fam.setdefault(r["video_id"], set()).add(r["family"])

    rows = con.execute(
        """SELECT v.video_id, v.title, v.channel_name, v.view_count, v.duration_s,
                  v.age_months, v.gate_status, t.snippets_json
           FROM videos v JOIN transcripts t ON t.video_id = v.video_id
           WHERE v.gate_status IN ('PASS','STALE_G2')"""
    ).fetchall()
    print(f"corpus: {len(rows)} gated videos with transcripts\n")

    out = []
    for r in rows:
        f = fam.get(r["video_id"], set())
        text = " ".join(s["text"] for s in json.loads(r["snippets_json"]))
        proxy, _parts, detail = RS.score(text)
        sat = saturation(r["view_count"], r["age_months"], f)
        out.append({
            "video_id": r["video_id"], "title": r["title"],
            "channel": r["channel_name"], "views": r["view_count"],
            "age_months": r["age_months"], "duration_s": r["duration_s"],
            "families": sorted(f), "proxy": round(proxy, 1),
            "saturation": round(sat, 1), "priority": round(proxy - sat, 1),
            "n_urls": detail["n_urls"], "stale": r["gate_status"] == "STALE_G2",
        })
    out.sort(key=lambda x: -x["priority"])

    print(f"{'#':>3} {'prio':>6} {'prox':>6} {'sat':>5} {'views':>9} {'age':>5} "
          f"{'min':>4}  {'fam':<12} title")
    for i, x in enumerate(out[:n], 1):
        v = f"{x['views']:,}" if x["views"] is not None else "?"
        print(f"{i:>3} {x['priority']:>6.1f} {x['proxy']:>6.1f} {x['saturation']:>5.1f} "
              f"{v:>9} {(x['age_months'] or 0):>5.0f} {(x['duration_s'] or 0)/60:>4.0f}  "
              f"{','.join(x['families']):<12} {(x['title'] or '')[:40]}")

    demoted = sorted([x for x in out if x["saturation"] >= 3],
                     key=lambda x: -x["proxy"])[:6]
    if demoted:
        print(f"\n  DEMOTED BY SATURATION (high proxy, high reach x age) — "
              f"{len(demoted)} shown, not dropped:")
        for x in demoted:
            print(f"    proxy {x['proxy']:>5.1f} -> prio {x['priority']:>5.1f}  "
                  f"{x['views']:>9,} views {(x['age_months'] or 0):>3.0f}mo  "
                  f"{(x['title'] or '')[:44]}")

    p = ROOT / "reports" / "target_ranking.json"
    p.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"\nwrote {p} ({len(out)} ranked)")
    con.close()


if __name__ == "__main__":
    main()

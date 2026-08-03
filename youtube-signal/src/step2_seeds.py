"""STEP 2 / premise 5 -- verify the pinned seed channels still resolve and that
their stats have not drifted. Writes them into the channels table as is_seed=1.

Identity comes from channels.json only. There is no name resolver to fall back on.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import channels  # noqa: E402
import db  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent

con = db.connect()
out = []
print("STEP 2 -- seed channel verification (pinned IDs, no name resolution)\n")
for seed in channels.load_seeds():
    print(f"  --- {seed['name']!r}  ({seed['channel_id']})")
    if seed["name"].strip().lower() != seed["prompt_name_was"].strip().lower():
        print(f"      original prompt name was {seed['prompt_name_was']!r} -- wrong")
    try:
        st = channels.channel_stats(seed["channel_id"])
    except Exception as exc:  # noqa: BLE001
        print(f"      FAILED TO RESOLVE: {type(exc).__name__}: {str(exc)[:110]}")
        out.append({**seed, "resolved": False, "error": str(exc)[:200]})
        continue
    drift = channels.drift_check(seed, st)
    name_ok = (st["channel"] or "").strip().lower() == seed["name"].strip().lower()
    print(f"      name now   : {st['channel']!r} {'(matches)' if name_ok else '(DIFFERS)'}")
    print(f"      subscribers: {st['subscribers']:,}  pinned {seed['subscribers']:,}")
    print(f"      med. views : {st['median_views']:,}  pinned {seed['median_views']:,}")
    print(f"      uploads    : {st['upload_count']}{'+' if st['upload_count_is_floor'] else ''}")
    print(f"      drift      : {drift if drift else 'within 5x -- consistent'}")
    con.execute(
        """INSERT INTO channels (channel_id, name, subscribers, median_views,
               upload_count, is_seed, stats_flag, first_seen_utc, last_refresh_utc)
           VALUES (?,?,?,?,?,1,?,?,?)
           ON CONFLICT(channel_id) DO UPDATE SET
               name=excluded.name, is_seed=1, stats_flag=excluded.stats_flag,
               last_refresh_utc=excluded.last_refresh_utc""",
        (seed["channel_id"], st["channel"], st["subscribers"], st["median_views"],
         st["upload_count"], drift, db.now(), db.now()),
    )
    out.append({
        **seed, "resolved": True, "name_matches": name_ok,
        "fresh_subscribers": st["subscribers"], "fresh_median_views": st["median_views"],
        "fresh_upload_count": st["upload_count"], "drift_flag": drift,
    })
con.commit()
con.close()

n_ok = sum(1 for o in out if o.get("resolved"))
n_drift = sum(1 for o in out if o.get("drift_flag"))
print(f"\nVERDICT: {n_ok}/4 resolved, {n_drift} drift flags")
(ROOT / "reports" / "step2_seeds.json").write_text(
    json.dumps(out, indent=2), encoding="utf-8"
)

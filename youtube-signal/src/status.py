"""One-screen state of the corpus. No network, no cost.

Written because checking progress through a shell one-liner kept losing to
quoting rules on Windows, and a mistyped check that silently reports the wrong
number is worse than no check.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import db_phase2  # noqa: E402


def main():
    con = db_phase2.connect()
    q = lambda s, *a: con.execute(s, a).fetchone()[0]  # noqa: E731

    n_search = q("SELECT COUNT(*) FROM videos WHERE source='search'")
    n_gated = q("SELECT COUNT(*) FROM videos WHERE gate_status IS NOT NULL")
    print(f"RETRIEVAL   {q('SELECT COUNT(*) FROM videos')} video rows "
          f"({n_search} from search), "
          f"{q('SELECT COUNT(*) FROM retrieval_log')} searches logged")
    print(f"GATES       {n_gated}/{n_search} gated"
          f"   ({100*n_gated/n_search:.0f}%)" if n_search else "GATES  none")
    for r in con.execute("SELECT gate_status, COUNT(*) c FROM videos"
                         " WHERE gate_status IS NOT NULL"
                         " GROUP BY gate_status ORDER BY c DESC"):
        print(f"              {r['gate_status']:<26} {r['c']:>4}")
    print(f"TRANSCRIPTS {q('SELECT COUNT(*) FROM transcripts')} cached")

    try:
        n_rs = q("SELECT COUNT(*) FROM read_set")
        n_sc = q("SELECT COUNT(*) FROM scores")
        # These two are NOT the same number and conflating them overstates
        # progress. Videos can be scored without being in the read set -- the 19
        # merged from the laptop mostly are, because that machine read top-down
        # by proxy score rather than from its own sample. Only the read_set
        # intersection counts as progress through the read set, and only it
        # feeds the retrieval test.
        n_rs_sc = q("SELECT COUNT(*) FROM scores s"
                    " WHERE s.video_id IN (SELECT video_id FROM read_set)")
        print(f"SCORES      {n_sc} videos scored in total")
        print(f"READ SET    {n_rs} selected, {n_rs_sc} of them scored, "
              f"{n_rs - n_rs_sc} remaining")
        if n_sc != n_rs_sc:
            print(f"            ({n_sc - n_rs_sc} scored videos are OUTSIDE the "
                  f"read set and do not enter the retrieval test)")
        if n_rs:
            print("            by family bucket (read / total):")
            for r in con.execute(
                    """SELECT r.family_bucket b, COUNT(*) t,
                              SUM(CASE WHEN s.video_id IS NOT NULL THEN 1 ELSE 0 END) d
                       FROM read_set r LEFT JOIN scores s ON s.video_id=r.video_id
                       GROUP BY r.family_bucket ORDER BY t DESC"""):
                print(f"              {r['b']:<12} {r['d']:>2}/{r['t']:<3}")
        if n_sc:
            print("EXTRACTION  "
                  f"{q('SELECT COUNT(*) FROM claims')} claims, "
                  f"{q('SELECT COUNT(*) FROM tools')} tools, "
                  f"{q('SELECT COUNT(*) FROM methods')} methods, "
                  f"{q('SELECT COUNT(*) FROM watch_segments')} watch segments")
            print("            verdicts:")
            for r in con.execute("SELECT verdict, COUNT(*) c FROM scores"
                                 " GROUP BY verdict ORDER BY c DESC"):
                print(f"              {r['verdict']:<28} {r['c']:>3}")
    except Exception as exc:  # noqa: BLE001
        print(f"(phase 2 tables not populated yet: {exc})")
    con.close()


if __name__ == "__main__":
    main()

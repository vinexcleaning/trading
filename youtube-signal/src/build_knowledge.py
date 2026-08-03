"""Build KNOWLEDGE.md -- the file a future Claude session reads.

This is the point of the whole project. Everything upstream exists to fill this
file: what tools exist, what claims were made, which survived arithmetic, and
which videos are worth a human's own time.

Written for a machine reader first and a human second. Claims keep their source
video, timestamp and expiry so a later session can tell a verified repo from a
marketer's assertion three months from now -- which is exactly what a summary
would destroy.
"""

import datetime as dt
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import db_phase2  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
TODAY = dt.date(2026, 8, 3)


def main():
    con = db_phase2.connect()
    scored = con.execute(
        """SELECT s.*, v.title, v.channel_name, v.view_count, v.duration_s,
                  v.upload_date
           FROM scores s JOIN videos v ON v.video_id = s.video_id
           ORDER BY s.s_total DESC"""
    ).fetchall()

    L = []
    L += [
        "# YouTube knowledge base — prediction markets, trading bots, algo trading",
        "",
        f"Generated {TODAY} by `youtube-signal`. **Read this before searching YouTube",
        "yourself.** It is the distilled output of transcripts already read in full.",
        "",
        "## How to use this file",
        "",
        "- **Claims carry an expiry.** A mechanism never expires. A price, fee or API",
        "  spec expires in 3 months. Check `expires` before repeating a number.",
        "- **`n-check` is arithmetic, not opinion.** `REFUTED` means the stated win rate",
        "  cannot beat its own break-even given the sample size. Trust it over the",
        "  creator's framing.",
        "- **S is substance (0–10), H is honesty (−10 to +11). They are never averaged.**",
        "  A high-S low-H video still has good tools; discount its *results* only.",
        "- Nothing here is a summary. Every line traces to a video and a timestamp.",
        "",
        f"**Coverage so far: {len(scored)} videos read in full.** Corpus available: "
        f"{con.execute('SELECT COUNT(*) c FROM videos').fetchone()['c']:,} known, "
        f"{con.execute(chr(83) + 'ELECT COUNT(*) c FROM transcripts').fetchone()['c']:,} "
        "transcripts cached locally.",
        "",
        "---",
        "",
    ]

    # ---------- tools ----------
    tools = con.execute(
        "SELECT * FROM tools ORDER BY mention_count DESC, name"
    ).fetchall()
    if tools:
        L += ["## Tools and sites mentioned", "",
              "`own` = the creator's own product (a reason to discount their praise, "
              "not the tool).", "",
              "| tool | what it does | own? | verified |", "|---|---|---|---|"]
        for t in tools:
            url = f"[{t['name']}]({t['url']})" if t["url"] and t["url"].startswith("http") else t["name"]
            own = {"disclosed": "yes, disclosed", "undisclosed": "**yes, UNDISCLOSED**",
                   "no": "no"}.get(t["is_creators_own"], t["is_creators_own"] or "?")
            L.append(f"| {url} | {t['claimed_purpose'] or ''} | {own} | "
                     f"{t['resolution']} |")
        L += [""]

    # ---------- claims that survived arithmetic ----------
    checked = con.execute(
        "SELECT c.*, v.title, v.channel_name FROM claims c "
        "JOIN videos v ON v.video_id=c.video_id "
        "WHERE c.n_check_verdict IS NOT NULL"
    ).fetchall()
    if checked:
        L += ["## Numeric claims put through the n-check", "",
              "Wilson score interval vs the claim's own break-even.", ""]
        for c in checked:
            d = json.loads(c["n_check_detail"]) if c["n_check_detail"] else {}
            mark = {"SUPPORTED": "**SUPPORTED**", "REFUTED": "**REFUTED**"}.get(
                c["n_check_verdict"], c["n_check_verdict"])
            L += [f"- {mark} — {c['claim_text']}",
                  f"  - rate {100*(c['stated_win_rate'] or 0):.2f}% vs break-even "
                  f"{100*d.get('breakeven', 0.5):.0f}%, n={d.get('n', 0):,}, "
                  f"Wilson [{100*d.get('wilson_lo',0):.2f}%, {100*d.get('wilson_hi',0):.2f}%]",
                  f"  - source: {c['channel_name']} — *{c['title']}* @{int(c['timestamp_s'] or 0)}s"]
        L += [""]

    # ---------- mechanisms and concepts (never expire) ----------
    mech = con.execute(
        "SELECT c.*, v.title, v.channel_name FROM claims c "
        "JOIN videos v ON v.video_id=c.video_id "
        "WHERE c.claim_type IN ('mechanism','concept','math') ORDER BY c.video_id"
    ).fetchall()
    if mech:
        L += ["## Mechanisms and concepts (no expiry)", ""]
        for c in mech:
            L += [f"- {c['claim_text']}",
                  f"  - {c['channel_name']} — *{c['title']}* @{int(c['timestamp_s'] or 0)}s"]
        L += [""]

    # ---------- specs (expire fast) ----------
    specs = con.execute(
        "SELECT c.*, v.title, v.channel_name FROM claims c "
        "JOIN videos v ON v.video_id=c.video_id "
        "WHERE c.claim_type IN ('spec','tool_rec') ORDER BY c.video_id"
    ).fetchall()
    if specs:
        L += ["## Specs and tool recommendations — SHORT SHELF LIFE", "",
              "Verify before relying on any of these.", ""]
        for c in specs:
            L += [f"- {c['claim_text']}  *(expires {c['expires_after_months']}mo "
                  f"from upload)*",
                  f"  - {c['channel_name']} — *{c['title']}* @{int(c['timestamp_s'] or 0)}s"]
        L += [""]

    # ---------- methods ----------
    methods = con.execute(
        "SELECT m.*, v.title, v.channel_name FROM methods m "
        "JOIN videos v ON v.video_id=m.video_id"
    ).fetchall()
    if methods:
        L += ["## Step-by-step methods", ""]
        for m in methods:
            L += [f"### {m['title']}",
                  f"*{m['channel_name']} — {m['title']}*  ",
                  f"<https://www.youtube.com/watch?v={m['video_id']}&t="
                  f"{int(m['ts_start'] or 0)}s>", ""]
            for st in json.loads(m["steps_json"]):
                L.append(f"{st['n']}. {st['step']}  `@{int(st['t'])}s`")
            L += [""]

    # ---------- recommended to watch ----------
    rec = [r for r in scored if r["verdict"] in ("RECOMMEND", "ABSORB_AND_RECOMMEND")]
    L += ["## Worth watching yourself", ""]
    if rec:
        for r in rec:
            L += [f"- **{r['title']}** — {r['channel_name']}, "
                  f"{(r['duration_s'] or 0)/60:.0f} min, "
                  f"{r['view_count']:,} views (S={r['s_total']}, H={r['h_total']})  ",
                  f"  <https://www.youtube.com/watch?v={r['video_id']}>"]
    else:
        L += ["*None yet.* Educational picks require a short, well-taught, "
              "low-marketing video; none of the videos read so far qualified.", ""]
    L += [""]

    # ---------- watch segments ----------
    seg = con.execute(
        "SELECT w.*, v.title, v.duration_s FROM watch_segments w "
        "JOIN videos v ON v.video_id=w.video_id"
    ).fetchall()
    if seg:
        L += ["## The only bits worth putting eyes on", "",
              "Everything else in these videos is already extracted above.", ""]
        for s in seg:
            L += [f"- *{s['title']}* — **{int(s['ts_start'])//60}:"
                  f"{int(s['ts_start'])%60:02d} to {int(s['ts_end'])//60}:"
                  f"{int(s['ts_end'])%60:02d}** — {s['why']}  ",
                  f"  <https://www.youtube.com/watch?v={s['video_id']}&t="
                  f"{int(s['ts_start'])}s>"]
        L += [""]

    # ---------- per-video index ----------
    L += ["---", "", "## Videos read in full", "",
          "| S | H | verdict | views | video |", "|---|---|---|---|---|"]
    for r in scored:
        L.append(f"| {r['s_total']} | {r['h_total']} | {r['verdict']} | "
                 f"{r['view_count']:,} | [{r['title']}]"
                 f"(https://www.youtube.com/watch?v={r['video_id']}) |")
    L += [""]

    out = ROOT / "KNOWLEDGE.md"
    out.write_text("\n".join(L), encoding="utf-8")
    print(f"wrote {out}  ({len('\n'.join(L)):,} chars)")
    print(f"  videos read : {len(scored)}")
    print(f"  tools       : {len(tools)}")
    print(f"  claims      : {con.execute('SELECT COUNT(*) c FROM claims').fetchone()['c']}")
    print(f"  methods     : {len(methods)}")
    con.close()


if __name__ == "__main__":
    main()

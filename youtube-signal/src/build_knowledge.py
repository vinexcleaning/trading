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


def fmt_date(upload_date):
    """YYYYMMDD -> 'Jan 2026'. Undated content is stated as undated, never blank."""
    if not upload_date:
        return "date unknown"
    try:
        d = dt.datetime.strptime(str(upload_date)[:10].replace("-", ""), "%Y%m%d").date()
        return d.strftime("%d %b %Y")
    except Exception:  # noqa: BLE001
        return str(upload_date)


def src_line(c):
    """Provenance with the DATE on it.

    A fee formula from two years ago and one from last month look identical once
    the sentence is extracted. The upload date is what stops a future session
    quoting a stale number as current, so it goes on every single claim.
    """
    age = c["age_months"]
    age_s = f", {age:.0f} mo old" if age is not None else ""
    return (f"{c['channel_name']} — *{c['title']}* · "
            f"**{fmt_date(c['upload_date'])}**{age_s} · @{int(c['timestamp_s'] or 0)}s")


def expiry_flag(c):
    """Has this claim outlived its shelf life, given the video's own age?"""
    months, age = c["expires_after_months"], c["age_months"]
    if not months:
        return ""
    if age is None:
        return f"*(expires {months}mo after upload; upload date unknown)*"
    if age > months:
        return (f"**⚠ EXPIRED — {age:.0f} months old, shelf life {months} months. "
                f"Re-verify before use.**")
    return f"*(valid — {age:.0f} of {months} months elapsed)*"


def main():
    con = db_phase2.connect()
    scored = con.execute(
        """SELECT s.*, COALESCE(s.b_total,0) AS b_total, v.title, v.channel_name,
                  v.view_count, v.duration_s, v.upload_date, v.age_months
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
        "SELECT c.*, v.title, v.channel_name, v.upload_date, v.age_months FROM claims c "
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
                  f"  - source: {src_line(c)}"]
        L += [""]

    # ---------- mechanisms and concepts (never expire) ----------
    mech = con.execute(
        "SELECT c.*, v.title, v.channel_name, v.upload_date, v.age_months FROM claims c "
        "JOIN videos v ON v.video_id=c.video_id "
        "WHERE c.claim_type IN ('mechanism','concept','math') ORDER BY c.video_id"
    ).fetchall()
    if mech:
        L += ["## Mechanisms and concepts — no expiry", "",
              "Still dated, because a mechanism can be superseded even if it does not "
              "rot.", ""]
        for c in mech:
            L += [f"- {c['claim_text']}",
                  f"  - {src_line(c)}"]
        L += [""]

    # ---------- specs (expire fast) ----------
    specs = con.execute(
        "SELECT c.*, v.title, v.channel_name, v.upload_date, v.age_months FROM claims c "
        "JOIN videos v ON v.video_id=c.video_id "
        "WHERE c.claim_type IN ('spec','tool_rec','procedure') ORDER BY c.video_id"
    ).fetchall()
    if specs:
        L += ["## Specs, fees and procedures — SHORT SHELF LIFE", "",
              "**Check the age before repeating any number here.** A fee formula or "
              "API detail from a two-year-old video is a lead, not a fact.", ""]
        for c in specs:
            L += [f"- {c['claim_text']}",
                  f"  - {src_line(c)}  {expiry_flag(c)}"]
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
    # BUILD section: the videos that produce working code, which the S axis alone
    # would have buried. Listed before the index because "how do I actually build
    # this" is the question the user asks most.
    builds = [r for r in scored if (r["b_total"] or 0) >= 6]
    if builds:
        L += ["## Follow these to BUILD something", "",
              "Scored on the Build axis: working code on screen, named endpoints, a",
              "complete path from auth to order, the gotchas, and a resolvable repo.", ""]
        for r in builds:
            L += [f"- **{r['title']}** — {r['channel_name']} · "
                  f"B={r['b_total']}/10, S={r['s_total']}, H={r['h_total']} · "
                  f"{fmt_date(r['upload_date'])}  ",
                  f"  <https://www.youtube.com/watch?v={r['video_id']}>"]
        L += [""]

    L += ["---", "", "## Videos read in full", "",
          "| S | B | H | verdict | uploaded | age | views | video |",
          "|---|---|---|---|---|---|---|---|"]
    for r in scored:
        age = f"{r['age_months']:.0f} mo" if r["age_months"] is not None else "?"
        L.append(f"| {r['s_total']} | {r['b_total'] or 0} | {r['h_total']} | {r['verdict']} | "
                 f"{fmt_date(r['upload_date'])} | {age} | {r['view_count']:,} | "
                 f"[{r['title']}](https://www.youtube.com/watch?v={r['video_id']}) |")
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

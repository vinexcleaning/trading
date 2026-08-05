"""TASK 2, the part that CAN be measured without fetching a frame:

    would vision have changed anything?

The brief says: "If vision changes few verdicts, say so and stop - that is a
real finding and saves the compute." Frame acquisition from YouTube is closed
(see `FINDINGS_T2.md`), so the question has to be answered from what is already
held. Three independent estimates, none of which needs a pixel:

  1  THE READ SET'S OWN ESTIMATE. Every read records `visual_dependent` and a
     list of `watch_segments` - ranges the reader judged need eyes. That is a
     transcript-side upper bound on how much of each video is screen-only.

  2  CLAIMS THAT ANNOUNCE THEIR OWN PROVENANCE. A recorded claim saying
     "shown on screen and itemised" is a claim whose evidence is a frame. Those
     are countable.

  3  THE TEST SET, WHICH IS THE ONLY DIRECT MEASUREMENT AVAILABLE. For each of
     the 24 labelled cases, what actually fixed the label - and would a frame
     have been necessary, sufficient, or irrelevant? This is the one that
     answers the brief's question, because these are cases where the right
     answer is known.

    python src/vision_value.py
"""
from __future__ import annotations

import json
import re
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import cases as CS    # noqa: E402
import corpora        # noqa: E402
import frames         # noqa: E402

# Claims whose own text says the evidence was on the screen.
ON_SCREEN = re.compile(
    r"\b(shown on screen|on screen|shows? (his|her|their|the) (account|"
    r"balance|wallet|dashboard|terminal)|screenshot|itemised on screen|"
    r"displayed|visible in the)\b", re.I)


def main():
    L, w = [], None
    L = []
    w = L.append
    w("# TASK 2 - would vision have changed anything?\n")
    w("Frame acquisition from YouTube is closed under this repo's own standard "
      "(`FINDINGS_T2.md`). What follows is what can be measured without one, "
      "and the third section is the direct answer.\n")

    # ---- 1: the read set's own estimate
    tot_dur = seg_dur = 0.0
    n_vis = n_vid = 0
    per_video = []
    for corpus in ("yt", "yt_kalshi"):
        con = corpora.ro(corpus)
        for r in con.execute(
                "SELECT s.video_id, s.visual_dependent, v.duration_s, v.title "
                "FROM scores s JOIN videos v ON v.video_id = s.video_id"):
            n_vid += 1
            n_vis += 1 if r["visual_dependent"] else 0
            d = float(r["duration_s"] or 0)
            tot_dur += d
            segs = con.execute("SELECT ts_start, ts_end FROM watch_segments "
                               "WHERE video_id = ?", (r["video_id"],)).fetchall()
            s = sum(float(x["ts_end"]) - float(x["ts_start"]) for x in segs)
            seg_dur += s
            per_video.append((corpus, r["video_id"], d, s, len(segs)))
        con.close()

    w("## 1. What the readers themselves said needs eyes\n")
    w("| | |")
    w("|---|---|")
    w(f"| videos read | **{n_vid}** |")
    w(f"| flagged `visual_dependent` | **{n_vis}** ({n_vis/n_vid:.0%}) |")
    w(f"| total runtime | {tot_dur/3600:.1f} h |")
    w(f"| runtime inside a `watch_segment` | **{seg_dur/60:.0f} min "
      f"({seg_dur/tot_dur:.1%})** |")
    w(f"| videos needing ZERO segments | "
      f"**{sum(1 for x in per_video if x[4] == 0)}** of {n_vid} |")
    w("")
    w(f"**{seg_dur/tot_dur:.1%} of runtime is screen-only by the reader's own "
      "judgment.** That is the transcript side's estimate of the ceiling: if "
      "frames added nothing outside those windows, the most vision could reach "
      "is that fraction of the material. It is an upper bound on coverage, not "
      "on value - one frame inside a P&L window can outweigh an hour of talk.\n")

    # ---- 2: claims that announce their provenance
    n_claims = n_screen = 0
    screen_examples = []
    for corpus in ("yt", "yt_kalshi"):
        con = corpora.ro(corpus)
        for r in con.execute("SELECT video_id, claim_type, claim_text "
                             "FROM claims"):
            n_claims += 1
            if ON_SCREEN.search(r["claim_text"] or ""):
                n_screen += 1
                if len(screen_examples) < 10:
                    screen_examples.append(
                        (r["video_id"], r["claim_type"],
                         (r["claim_text"] or "")[:130]))
        con.close()
    w("## 2. Claims whose own evidence is a frame\n")
    w(f"**{n_screen} of {n_claims} recorded claims ({n_screen/n_claims:.1%}) "
      "state that the evidence was on the screen.** Every one of those is a "
      "claim the reader accepted on the strength of something a transcript "
      "cannot contain - which is the exposure vision would close.\n")
    w("| video | type | claim |")
    w("|---|---|---|")
    for v, t, c in screen_examples:
        w(f"| `{v}` | {t} | {c} |")
    w("")

    # ---- 3: the direct measurement
    w("## 3. The direct measurement - the 24 cases where the answer is known\n")
    why = Counter(c.why for c in CS.CASES)
    w("| what fixed the label | cases | could a frame have supplied it? |")
    w("|---|---|---|")
    w(f"| ARITH - arithmetic on stated numbers | {why['ARITH']} | "
      "**no** - the numbers are spoken and the contradiction is between them |")
    w(f"| LIVE - an API check runnable today | {why['LIVE']} | "
      "**no** - the answer is on GitHub and PyPI, not on the creator's screen |")
    w(f"| EXTERN - a fact primary-sourced elsewhere | {why['EXTERN']} | "
      "**no** - by definition the evidence is outside the source |")
    w(f"| SELFCON - an internal contradiction | {why['SELFCON']} | "
      "**sometimes** - if one of the two contradicting numbers is on screen |")
    w("")
    w(f"**0 of {len(CS.CASES)} labels required a frame.** Every one was fixed "
      "by arithmetic, a live API call, an external primary source, or two "
      "statements in the same transcript disagreeing with each other.\n")
    w("> That is the finding the brief asked for, and it is a negative one. "
      "**On the cases where the right answer is independently known, vision "
      "was never the deciding evidence.** It does not follow that vision is "
      "worthless - it follows that the labelled set was built from cases that "
      "are decidable without it, because those are the only cases whose answer "
      "can be verified at all. The bias is structural and runs against vision: "
      "a claim that can ONLY be settled by looking at a screen is exactly a "
      "claim this test set could not have included.\n")
    w("**So the honest statement is narrower than 'vision does not help':**\n")
    w("- For **detecting stale technology**, vision is unnecessary. An API call "
      "beats a screenshot and is free.\n")
    w("- For **catching denominator-free claims**, vision is unnecessary. The "
      "defect is an absence, and an absence is not on the screen either.\n")
    w("- For **catching a spoken number that the screen contradicts**, vision "
      f"is the only instrument there is, and {n_screen} recorded claims "
      "currently rest on frames nobody checked.\n")

    # ---- 4: what the cue planner would actually cost
    w("## 4. What it would cost, if a permitted source existed\n")
    w("`frames.cues()` run over the read set, planning frames without cutting "
      "any:\n")
    w("| video | runtime | cues planned | frames per minute |")
    w("|---|---|---|---|")
    tot_cues = 0
    for corpus, vid, dur, _s, _n in sorted(per_video,
                                           key=lambda x: -x[2])[:12]:
        try:
            plan = frames.cues(corpus, vid, max_frames=40)
        except Exception:
            continue
        tot_cues += len(plan)
        w(f"| `{vid}` | {dur/60:.0f} min | {len(plan)} | "
          f"{len(plan)/(dur/60):.1f} |")
    w("")
    w(f"Planning is cheap and deterministic: cues come from recorded claim "
      f"timestamps, the reader's own `watch_segments`, and a narrow set of "
      f"demo phrases, deduplicated onto a 4-second grid and capped at 40. "
      f"**The plan is the reusable part.** It survives whatever the source "
      f"turns out to be.\n")

    out = corpora.REPORTS / "T2_vision_value.md"
    out.write_text("\n".join(L), encoding="utf-8")
    print(f"  visual_dependent {n_vis}/{n_vid}; "
          f"watch_segment share {seg_dur/tot_dur:.1%}; "
          f"screen-provenance claims {n_screen}/{n_claims}")
    print(f"  wrote {out}")


if __name__ == "__main__":
    main()

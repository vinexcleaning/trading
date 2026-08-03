"""STEP 2 -- the LLM read. ONE call per video, full transcript in, JSON out.

*** THIS MODULE HAS NEVER BEEN EXECUTED. ***
Phase 2 Step 0 found no ANTHROPIC_API_KEY on this machine, so nothing here has
run against a real model. It is written, type-checked and dry-runnable
(`--dry-run` prints the assembled prompt and exits), but every line below the
API call is unvalidated. Treat it as a draft, not a working component.

Design points that are deliberate:

  * ONE call produces scores, evidence, tools, claims, methods and watch
    segments together. A second scoring pass would let the score drift away from
    the extraction it is supposed to summarise.
  * Every score component must carry a timestamp and a verbatim quote under 15
    words. The schema enforces it (score_evidence has NOT NULL on both), and
    `validate_response` drops any component that arrives without them rather
    than trusting the model to have followed instructions.
  * S and H are never averaged. They are stored as separate totals and the
    verdict function reads them separately.
"""

import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import db_phase2  # noqa: E402
import ncheck  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
MODEL = "claude-sonnet-5"
MAX_QUOTE_WORDS = 15

S_WEIGHTS = {"S1": 3, "S2": 2, "S3": 2, "S4": 2, "S5": 1}
H_WEIGHTS = {"H1": 3, "H1b": 1, "H2": 3, "H3": 2, "H4": 1, "H5": 2,
             "H6": -4, "H7": -2, "H8": -1, "H9": -2, "H10": -4}

RUBRIC = """You are extracting substance from a YouTube transcript about prediction
markets, trading bots, and algorithmic trading. You are not summarising. The reader
wants the tools, sites, procedures and specific claims so they never have to watch it.

Captions are auto-generated: punctuation is unreliable, homophones are common
("Kashi" is Kalshi, "Poly Market" is Polymarket). Read through transcription noise.

SCOPE: prediction markets, trading bots, algorithmic and systematic method, and the
tooling and data around them. Discretionary/manual trading education (chart reading,
technical analysis, trading psychology) is OUT OF SCOPE -- if the video is entirely
that, say so via on_topic=false and score nothing.

=== HARD RULE ===
Every score component you award MUST carry a timestamp (seconds, a number) and a
verbatim quote of FEWER THAN 15 WORDS copied exactly from the transcript. If you
cannot cite it, do not award it. A component you cannot quote did not happen.
Do not paraphrase quotes. Do not invent timestamps.

=== S -- SUBSTANCE (award only what fires) ===
S1 (+3) Names the cost side: fees, spread, slippage, gas, or the domain equivalent.
S2 (+2) Distinguishes backtest/theory from live/actual results.
S3 (+2) States a sample size for a performance claim (n of trades/bets/days).
S4 (+2) Gives a mechanism: why this works, who is on the other side of the trade.
S5 (+1) Names specific tools, sites or steps rather than gesturing at them.

=== H -- HONESTY (discounts results claims only; never blocks extraction) ===
H1  (+3) Shows a failure AND does not pivot to selling a fix.
H1b (+1) Shows a failure that sets up a sale.
H2  (+3) Points to a verifiable artifact (repo URL, wallet address, public account).
H3  (+2) A performance claim carrying n AND period AND starting capital (+1 partial).
H4  (+1) Names a weakness in their own method, unprompted.
H5  (+2) Discloses which promoted tools are their own.
H6  (-4) Performance claim with no denominator ("I made $5k" with no n, no period).
H7  (-2) Sells the method without disclosing the mechanism.
H8  (-1) Urgency or scarcity language.
H9  (-2) Promotes a strategy they have abandoned without saying so.
Award H1 or H1b, never both.

=== EXTRACTION ===
tools: every tool/site/app named. Include the URL if spoken or shown.
claims: every assertion. claim_type is one of
        mechanism | concept | math | procedure | tool_rec | spec | result
        For a result, fill stated_n, stated_period, stated_capital, stated_win_rate
        where given, else null. Never guess a number that was not stated.
methods: step-by-step procedures, as numbered steps with timestamps.
watch_segments: ONLY ranges that genuinely need eyes -- code on screen, a live
        dashboard, a chart being read. If nothing needs eyes, return an empty list.
        Never return the whole video. Be stingy: this is the number that decides
        whether extraction beat watching.

Return ONE JSON object, no prose, no markdown fence:
{
 "on_topic": true,
 "visual_dependent": false,
 "s_components": [{"component":"S1","timestamp_s":123.4,"quote":"..."}],
 "h_components": [{"component":"H6","timestamp_s":45.0,"quote":"..."}],
 "tools": [{"name":"...","url":null,"claimed_purpose":"...",
            "is_creators_own":"no|disclosed|undisclosed","is_referral_link":false}],
 "claims": [{"timestamp_s":12.0,"claim_text":"...","claim_type":"result",
             "stated_n":33,"stated_period":"2 weeks","stated_capital":"$500",
             "stated_win_rate":0.55,"confidence":"high"}],
 "methods": [{"title":"...","ts_start":10.0,"ts_end":300.0,
              "steps":[{"n":1,"step":"...","t":12.0}]}],
 "watch_segments": [{"ts_start":300.0,"ts_end":360.0,"why":"code on screen"}]
}"""


def build_prompt(title, channel, transcript_snippets):
    lines = []
    for s in transcript_snippets:
        lines.append(f"[{int(s['start'])}] {s['text']}")
    return (f"{RUBRIC}\n\n=== VIDEO ===\nTitle: {title}\nChannel: {channel}\n\n"
            f"=== TRANSCRIPT (each line prefixed with its start second) ===\n"
            + "\n".join(lines))


def validate_response(doc):
    """Drop any component lacking a timestamp or a short verbatim quote.

    Returns (clean_doc, rejections). The model is not trusted to have obeyed the
    hard rule; this is where the rule is actually enforced.
    """
    rejects = []
    for axis, key, weights in (("S", "s_components", S_WEIGHTS),
                               ("H", "h_components", H_WEIGHTS)):
        kept = []
        for c in doc.get(key) or []:
            comp = c.get("component")
            q = (c.get("quote") or "").strip()
            t = c.get("timestamp_s")
            if comp not in weights:
                rejects.append((axis, comp, "unknown component"))
            elif not q:
                rejects.append((axis, comp, "no quote"))
            elif len(q.split()) >= MAX_QUOTE_WORDS:
                rejects.append((axis, comp, f"quote too long ({len(q.split())} words)"))
            elif not isinstance(t, (int, float)):
                rejects.append((axis, comp, "no numeric timestamp"))
            else:
                kept.append(c)
        # H1 and H1b are mutually exclusive; keep the stronger claim only.
        if axis == "H":
            names = {c["component"] for c in kept}
            if "H1" in names and "H1b" in names:
                kept = [c for c in kept if c["component"] != "H1b"]
                rejects.append(("H", "H1b", "H1 also awarded; mutually exclusive"))
        doc[key] = kept
    return doc, rejects


def totals(doc):
    s = sum(S_WEIGHTS[c["component"]] for c in doc.get("s_components", []))
    h = sum(H_WEIGHTS[c["component"]] for c in doc.get("h_components", []))
    # H6 is capped at -4 in aggregate, not per occurrence.
    return min(s, 10), max(-10, min(11, h))


# Two different jobs, which the old single verdict conflated.
#
#   INFORMATIVE  -- the 400-view ones. Claude absorbs them, the user never
#                   watches. Judged purely on substance.
#   EDUCATIONAL  -- worth the USER's own time: short, clearly taught, not a
#                   sales pitch. This is what gets handed back as "watch this".
#
# A video can be both, either, or neither. "Visual-dependent" is a separate
# property (it drives watch_segments) and is not a verdict -- a video can be
# worth absorbing AND have two minutes that need eyes.
EDUCATIONAL_MAX_MINUTES = 20


def is_informative(s):
    return s >= 4


def is_educational(s, h, duration_s, teaching_quality):
    """Worth the user's own minutes.

    Requires real substance, non-negative honesty (a sales pitch is never
    recommended however slick), a runtime a person will actually sit through,
    and an explicit teaching judgment from the read.
    """
    if s < 5 or h < 0:
        return False
    if duration_s and duration_s > EDUCATIONAL_MAX_MINUTES * 60:
        return False
    return teaching_quality in ("good", "excellent")


def verdict(s, h, visual, duration_s=None, teaching_quality=None):
    info = is_informative(s)
    edu = is_educational(s, h, duration_s, teaching_quality)
    if info and edu:
        return "ABSORB_AND_RECOMMEND"
    if edu:
        return "RECOMMEND"
    if info and h < 0:
        return "ABSORB_RESULTS_DISCOUNTED"
    if info:
        return "ABSORB"
    return "SKIP"


def run_ncheck_on_claims(doc, breakeven=0.50):
    """Break-even is PER CLAIM, not a constant.

    A 50% default is right for a coin-flip bet and wrong for almost every
    prediction-market claim, where break-even is the price paid: a contract
    bought at 5 cents needs a 5% hit rate, not 50%. Comparing 4.18% against 0.50
    produces a technically-true REFUTED for entirely the wrong reason. Claims
    carry their own `breakeven` where the price is known.
    """
    for c in doc.get("claims", []):
        if c.get("claim_type") == "result" and c.get("stated_win_rate") and c.get("stated_n"):
            be = c.get("breakeven", breakeven)
            r = ncheck.n_check(c["stated_win_rate"], c["stated_n"], be)
            c["n_check_verdict"] = r["verdict"]
            c["n_check_detail"] = json.dumps(r)
        c["expires_after_months"] = db_phase2.EXPIRY_MONTHS.get(c.get("claim_type"), 12)
    return doc


def call_model(prompt, model=MODEL):
    """The only networked function here. Never executed -- no key exists."""
    import anthropic

    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    resp = client.messages.create(
        model=model, max_tokens=8000,
        messages=[{"role": "user", "content": prompt}],
    )
    text = resp.content[0].text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1].rsplit("```", 1)[0]
    return json.loads(text), resp.usage.input_tokens, resp.usage.output_tokens


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true",
                    help="assemble and print one prompt, make no API call")
    ap.add_argument("--limit", type=int, default=None)
    args = ap.parse_args()

    if not os.environ.get("ANTHROPIC_API_KEY") and not args.dry_run:
        print("ANTHROPIC_API_KEY is not set. Step 2 cannot run.")
        print("Re-run with --dry-run to inspect the assembled prompt.")
        raise SystemExit(2)

    con = db_phase2.connect()
    rows = con.execute(
        """SELECT r.video_id, v.title, v.channel_name, t.snippets_json
           FROM read_set r JOIN videos v ON v.video_id=r.video_id
           JOIN transcripts t ON t.video_id=r.video_id
           WHERE r.video_id NOT IN (SELECT video_id FROM scores)"""
    ).fetchall()
    if args.limit:
        rows = rows[:args.limit]
    print(f"{len(rows)} videos to read")

    if args.dry_run:
        r = rows[0]
        p = build_prompt(r["title"], r["channel_name"],
                         json.loads(r["snippets_json"]))
        print(f"\n--- prompt for {r['video_id']} "
              f"({len(p):,} chars, ~{len(p)//4:,} tokens) ---\n")
        print(p[:2500])
        print(f"\n... [{len(p)-2500:,} more chars]")
        con.close()
        return

    raise SystemExit("unreachable without a key")


if __name__ == "__main__":
    main()

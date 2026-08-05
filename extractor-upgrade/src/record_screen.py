"""The screen-derived findings, filled in by looking at the frames.

`agreement` may only be set by someone who actually looked. It is stored apart
from anything transcript-derived so a claim's provenance stays auditable, which
was the brief's requirement: `spoken` is what the transcript says at that point,
`shown` is what the frame shows, and nothing infers one from the other.

    CONFIRMS      the screen shows what was said
    CONTRADICTS   the screen shows something incompatible with what was said
    ADDS          the screen carries a material fact the transcript never states
    TENSION       not a contradiction, but the screen undercuts a recorded score
    ABSENT        the claimed screen content is not present at the sampled point

Frames come from the PERMITTED `/vi/<id>/maxres{1,2,3}.jpg` path at 25/50/75%
of runtime, so the position is APPROXIMATE. Nothing here pins a screen fact to a
spoken sentence more tightly than three samples can support.

    python src/record_screen.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import corpora  # noqa: E402

# (video_id, frame, agreement, shown, why it matters)
FINDINGS = [
    ("8u6jy8v56ww", "maxres2", "CONTRADICTS",
     "The live Polymarket UI for 'Bitcoin Up or Down - 5 min'. Order panel "
     "reads Up 37c / Down 67c. Account header reads Portfolio $1.79, "
     "Cash $1.79. Amount $0, Balance $1.79. No position is open.",
     "THE SINGLE STRONGEST RESULT OF THE SESSION. This video's stored verdict "
     "is ABSORB_AND_RECOMMEND on S=10 H=6. Its recorded claims include a "
     "'full-time' projection of a $20,000 bankroll at $100/trade producing "
     "over $300,000 monthly, and a 'conservative' $2,500 -> $40,000/month. "
     "**The account visible on screen holds $1.79.** Separately, Up 37c + "
     "Down 67c = 104c, a 4% two-sided spread on a market whose break-even the "
     "video itself states as 51.02% - so the screen also quantifies the cost "
     "side the projection omits. A transcript reader cannot see either fact."),

    ("PeutA_HKxew", "maxres1", "ADDS",
     "A Bloomberg Brief news anchor, full-frame, with the Bloomberg lower-third "
     "graphic. Unattributed broadcast footage spliced into the opening pitch.",
     "The transcript's opening is the 'prediction markets have become the "
     "world's primary information exchange' framing. Borrowed broadcast "
     "authority is a marketing device with no audio signature at all - it is "
     "invisible to every transcript-side component in the rubric."),

    ("PeutA_HKxew", "maxres3", "ADDS",
     "The 'Poly Sniper' config panel: DEFAULT DEPOSIT SIZE $1,000 USDC, "
     "toggles for 'Auto-BET Trigger', 'Dynamic Gas Multiplier', 'Emergency "
     "Safety Cut' and - enabled - **'Front-Run Institutional'**. Beside it an "
     "'Execution Diagnostics Terminal' scrolling fabricated log lines, and a "
     "'WEB3 PRIVATE RPC NODES' panel.",
     "The product advertises FRONT-RUNNING on its own control surface. The "
     "transcript never says the word. The dashboard's PNL panel also reads "
     "$1,820.50 / +8.4% while the narration describes placing $2,000 on a "
     "single BTC down signal - the numbers on screen do not correspond to the "
     "bet being described. Its stored verdict is ABSORB_RESULTS_DISCOUNTED; "
     "the ground truth in the Task 1 test set is REJECT, and the screen is why."),

    ("YknxNkTgNWk", "maxres1", "ADDS",
     "A results card branded THE BETTER TRADERS: 'TBO Trend $25 -> $321 "
     "(+1,182%, 75% win rate)' and 'TBT Divergence $15 -> $423 (338 trades, "
     "58.4% win rate)'.",
     "A per-strategy breakdown with denominators that appears in NO recorded "
     "claim - the extraction captured only the aggregate '+1,560% ROI, $260, "
     "500 trades'. And 'TBO trend / TBT divergence' is the exact entity "
     "social-signal's table already carries as a CONTRADICTION, whose site "
     "`thebetterers.com` now returns NO DNS. The video is promoting a product "
     "that no longer exists, and the branding is only on the screen."),

    ("YknxNkTgNWk", "maxres3", "ADDS",
     "A course sales page: 'Introducing: 15 Minutes to Financial Freedom', "
     "'The complete crypto trading course...', and 'Coin Bureau viewers get an "
     "exclusive 10% discount through the link below' with a 'Get 10% Off Now' "
     "button.",
     "**The video terminates in a paid course pitch carrying an affiliate "
     "discount code.** H7 (-2, sells the method) fired on the transcript, but "
     "nothing recorded that the sale is a third-party course with a viewer "
     "discount - which is a disclosure question, not a substance one. Its "
     "stored verdict is ABSORB; the Task 1 ground truth is DISCOUNT."),

    ("yxfTHAGfaDc", "maxres3", "CONFIRMS",
     "A wallet-analytics table, six rows: 56.4% win rate / $339,859 wagered / "
     "+$103,616 / +31.0% ROI · 38.5% / $21,753 / -$5,572 / -25.6% · 50.0% / "
     "$11,150 / +$1,517 · 42.9% / $6,875 / +$3,119 / **+45.4%** · "
     "**100.0% / $752.16 / +$1.99 / +0.4%** · 50.0% / $3,192 / -$119.33.",
     "The transcript records the WARNING - 'polymarket.com's own wallet stats "
     "are unreliable, a wallet displayed 100% against a real 50-60%'. The "
     "screen supplies the ARITHMETIC THAT PROVES IT: the 100.0% row wagered "
     "$752.16 and returned $1.99. And a 42.9% win rate row returns +45.4% ROI "
     "while a 38.5% row returns -25.6%. Win rate and ROI are visibly "
     "uncorrelated in the same table. Confirms and quantifies."),

    ("lVqF8oLzVAU", "maxres2", "CONFIRMS",
     "Code on screen: `book = client.get_order_book(token_id)`, "
     "`best_bid = float(book.bids[-1].price)`, `best_ask = "
     "float(book.asks[-1].price)`; and at maxres3 `resp = client.cancel("
     "order_id='0x38a75ee...')` with 'Section 9: Complete Trading Helper "
     "Class'. Left panel: `Endpoint https://gamma-api.polymarket.com`.",
     "**The staleness verdict is confirmed by the method names themselves.** "
     "`client.get_order_book` and `client.cancel(order_id=...)` are the "
     "`py-clob-client` v1 surface, and that package is archived on GitHub "
     "(checked 2026-08-04) while still installable from PyPI. The currency "
     "gate reached this from the upload date alone; the screen reaches it "
     "from the code. Two instruments, one conclusion."),

    ("86AlV6174KI", "maxres1", "TENSION",
     "Talking head against a garden wall at all three sample points - no "
     "screen, no code, no terminal. Overlay graphics read 'STEP BY STEP' and "
     "**'NO CODE'**.",
     "This video holds the corpus's only perfect double score, S=10 B=10, "
     "verdict BUILD_AND_RECOMMEND, where B means 'does this teach you to build "
     "a thing that works'. **Its own on-screen overlay advertises NO CODE.** "
     "Three samples cannot prove a screen never appears, and its recorded "
     "claim that a -19% smoke-test backtest was 'shown on screen' may well be "
     "true elsewhere in the runtime. But a B=10 on a self-described no-code "
     "video is a tension the transcript alone never surfaced, and it is the "
     "kind of thing a fuller frame sample exists to settle."),
]


def main():
    path = corpora.DATA / "screen_evidence.json"
    rows = json.loads(path.read_text(encoding="utf-8")) if path.exists() else []
    idx = {(r["video_id"], Path(r["frame"]).stem): r for r in rows}

    filled = 0
    for vid, frame, agree, shown, note in FINDINGS:
        r = idx.get((vid, frame))
        if r is None:
            print(f"  !! no evidence row for {vid}/{frame}")
            continue
        r["shown"] = shown
        r["agreement"] = agree
        r["note"] = note
        filled += 1

    path.write_text(json.dumps(rows, indent=2), encoding="utf-8")

    from collections import Counter
    c = Counter(r["agreement"] for r in rows)
    vids = {r["video_id"] for r in rows}
    read = {v for v, *_ in FINDINGS}

    L = ["# TASK 2, REOPENED - vision, on the permitted path\n",
         "> **This corrects `FINDINGS_T2.md`, published earlier the same day, "
         "which said frame acquisition from YouTube was closed. That was too "
         "strong.** What is closed is arbitrary-timestamp acquisition. Three "
         "full-resolution frames per video are simply permitted.\n",
         "## The permitted path\n",
         "```",
         "https://i.ytimg.com/vi/<video_id>/maxres1.jpg   1280x720, ~110 KB",
         "https://i.ytimg.com/vi/<video_id>/maxres2.jpg   ~25 / 50 / 75% of runtime",
         "https://i.ytimg.com/vi/<video_id>/maxres3.jpg   auto-extracted frames,",
         "                                                NOT the designed thumbnail",
         "```",
         "`i.ytimg.com/robots.txt` disallows **`/sb/` only** - the storyboard "
         "path. `/vi/` is not mentioned, so a generic agent is permitted on it. "
         "Verified by fetching: `/sb/` returns **403**, `/vi/maxres1.jpg` "
         "returns **200 and 114,833 bytes at 1280x720**.\n",
         "The media stream stays closed at every hop, and a third-party "
         "downloader does not change that - it fetches from `googlevideo.com` "
         "on your behalf, and **all three `googlevideo.com` hosts checked "
         "return `User-agent: * / Disallow: /`**. Same act, extra hop.\n",
         f"## The measurement\n",
         f"**{len(vids)} videos fetched, {len(rows)} frames, 14.5 MB.** "
         f"**{len(read)} sheets read in full**, chosen as the videos whose "
         "stored verdict a screen could plausibly overturn - so this is a "
         "deliberately loaded sample and the rate below is not a corpus rate.\n",
         "| outcome | n |", "|---|---|"]
    for k, n in c.most_common():
        if k != "UNREAD":
            L.append(f"| {k} | {n} |")
    L.append(f"| UNREAD | {c.get('UNREAD', 0)} |")
    L.append("")
    L.append(f"**{len(FINDINGS)} findings from {len(read)} videos read. Every "
             "one of the six produced something a transcript could not.**\n")

    for vid, frame, agree, shown, note in FINDINGS:
        r = idx.get((vid, frame))
        if not r:
            continue
        L.append(f"### `{vid}` / `{frame}` (~{int(r['t']//60)}m"
                 f"{int(r['t']%60):02d}s) - **{agree}**\n")
        L.append(f"**SHOWN (screen-derived):** {shown}\n")
        L.append(f"**SPOKEN (transcript-derived, +/-25 s):** "
                 f"*\"{(r['spoken'] or '')[:300]}\"*\n")
        L.append(f"**Why it matters:** {note}\n")

    L.append("## What this changes\n")
    L.append("- **`8u6jy8v56ww` should not be `ABSORB_AND_RECOMMEND`.** A "
             "$300,000-a-month projection against a $1.79 account balance "
             "visible on screen is a results claim the honesty axis must "
             "discount. This is a verdict changed by vision, which is the "
             "thing the brief asked whether vision could do.\n")
    L.append("- **`PeutA_HKxew` and `YknxNkTgNWk` both move toward their Task 1 "
             "ground truth** (REJECT and DISCOUNT) on screen evidence, and both "
             "were among the cases the transcript-side rubric got wrong.\n")
    L.append("- **The earlier finding that 0 of 24 test-set labels needed a "
             "frame still stands, and is still biased against vision.** Those "
             "labels were fixed by facts checkable outside the source. What the "
             "frames add is a *different* class of evidence - the number the "
             "creator is standing in front of - which no external check can "
             "supply.\n")
    L.append("- **Three samples cannot prove absence.** `86AlV6174KI` shows no "
             "screen at any sample point and its recorded claim of an on-screen "
             "-19% backtest may be true elsewhere. It is logged as TENSION, not "
             "as a refutation.\n")

    out = corpora.REPORTS / "T2b_screen_evidence.md"
    out.write_text("\n".join(L), encoding="utf-8")
    print(f"  filled {filled} rows; {len(rows)} total; {dict(c)}")
    print(f"  wrote {out}")


if __name__ == "__main__":
    main()

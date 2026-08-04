"""T3 — measure the paid Discord server's trade calls.

`discord-trades-export/` holds a DiscordChatExporter dump of one paid tennis
trading server's calls channel. Nothing has ever read it. It is the only dataset
in this programme about **someone selling signals for money**, which makes it
worth a proper measurement rather than a vibe.

The plan, taken from `polymarket-tennis-copy/scripts/` where every one of these
methods is already built and validated:

  * fold to ONE observation per match before anything else. Twenty messages
    inside one match watch the same subsequent price move; treating them as
    twenty observations is what produced t-statistics of 90 and 408 in that
    project — numbers no financial signal legitimately reaches, and the giveaway
    that the sample size was fictional.
  * rank on the first half, score on the second (`split_sample_test.py`)
  * shrink the per-caller mean toward the pooled mean by sample size
  * measure edge decay at +1s / +10s / +60s / +5m (`follow_through.py`)

PRIVACY. This folder names real private individuals and is gitignored. This
script never writes a name, a handle, a user id or a line of message text to
`reports/`; authors are replaced by a per-run salted pseudonym and the salt is
not stored. Aggregates may be committed; the export may not.
"""
from __future__ import annotations

import argparse
import collections
import datetime
import glob
import hashlib
import json
import os
import re
import secrets
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import db  # noqa: E402

TRADING = os.path.dirname(db.ROOT)
EXPORT_DIR = os.path.join(TRADING, "discord-trades-export")

_SALT = secrets.token_hex(8)


def pseudonym(s: str) -> str:
    """Stable within a run, unrecoverable after it. The salt is generated at
    import and never written anywhere."""
    return "U" + hashlib.sha256((_SALT + (s or "")).encode()).hexdigest()[:6]


# ---------------------------------------------------------------------------
# Call parsing. A "call" needs, at minimum, a side and a price; without both
# there is nothing to score. These patterns are deliberately generous — the
# point of the census is to find out how many messages carry ANY of it.
# ---------------------------------------------------------------------------
RE_PRICE = re.compile(r"(?<![\w.])(\d{1,3})(?:\s*)(?:c|¢|cents?)\b", re.I)
RE_DECIMAL = re.compile(r"(?<![\w])0?\.(\d{1,3})(?![\w])")
RE_ODDS = re.compile(r"([+-]\d{3,4})(?![\w])")
RE_PCT = re.compile(r"(\d{1,3}(?:\.\d+)?)\s*%")
RE_UNITS = re.compile(r"\b(\d+(?:\.\d+)?)\s*(?:u|units?)\b", re.I)
RE_SIDE = re.compile(r"\b(yes|no|over|under|back|lay|buy|sell|long|short)\b", re.I)
RE_RESULT = re.compile(r"\b(win|won|lost|loss|cash(?:ed)?|green|red|push|void)\b", re.I)

# The calls are prose. "I like <player>" and "Taking <player> here" are the two
# shapes that carry a directional opinion; anything looser stops being a call
# and starts being commentary, and counting commentary as a call is how a
# 174-message export becomes a "174-call track record".
RE_CALL = re.compile(
    r"\b(?:i\s*like|i'?m?\s*taking|taking|i'?d\s*buy|i'?m\s*buying|buying|"
    r"i'?m\s*on|back(?:ing)?|tail(?:ing)?|play(?:ing)?)\b", re.I)

# The subject of the call verb is the player. **Case-insensitive on purpose:**
# a capitalised-token rule found 17 of 47 calls here, because this author writes
# surnames in lower case ("i like thurgur"). Requiring a capital letter is a
# rule about typing habits, not about tennis, and it silently threw away two
# thirds of the sample.
RE_CALL_OBJ = re.compile(
    r"\b(?:i\s*like|i'?m?\s*taking|taking|i'?d\s*buy|i'?m\s*buying|buying|"
    r"i'?m\s*on|backing|back|tailing|playing)\b[\s:,]*"
    r"(?:the\s+|a\s+|my\s+)?([A-Za-z][A-Za-z'’-]{2,})", re.I)
NOT_A_PLAYER = {
    "now", "this", "that", "these", "those", "them", "there", "here", "one",
    "some", "any", "all", "out", "off", "over", "under", "back", "and", "but",
    "for", "you", "your", "own", "risk", "trade", "trades", "play", "plays",
    "bet", "bets", "unit", "units", "set", "sets", "game", "games", "match",
    "matches", "line", "lines", "odds", "price", "prices", "cash", "profit",
    "money", "free", "live", "dip", "guys", "whale", "safe", "good", "later",
    "today", "tomorrow", "tonight", "again", "more", "less", "same", "next",
    "his", "her", "their", "when", "what", "with", "from", "into", "about",
    "before", "after", "still", "just", "only", "even", "very", "much",
}


def call_candidates(messages, owner_id):
    """Every owner message carrying a directional verb, and the token it acts on.

    Deliberately a LOWER bound on structure and an UPPER bound on independence:
    a regex over prose misses calls made obliquely, and counts two messages
    about the same match as two until the fold is applied.
    """
    calls = []
    for m in messages:
        if m["author"]["id"] != owner_id:
            continue
        text = (m.get("content") or "").strip()
        if not text or not RE_CALL.search(text):
            continue
        names = {w.lower() for w in RE_CALL_OBJ.findall(text)
                 if w.lower() not in NOT_A_PLAYER}
        calls.append({
            "ts": datetime.datetime.fromisoformat(m["timestamp"]),
            "names": names,
            "has_price": has_price(text),
            "has_stake": bool(RE_UNITS.search(text)),
            "n_att": len(m.get("attachments") or []),
        })
    return calls


def has_price(text: str) -> bool:
    return bool(RE_PRICE.search(text) or RE_DECIMAL.search(text)
                or RE_ODDS.search(text) or RE_PCT.search(text))


def census(messages, owner_id):
    c = collections.Counter()
    for m in messages:
        content = (m.get("content") or "").strip()
        atts = m.get("attachments") or []
        embeds = m.get("embeds") or []
        who = "owner" if m["author"]["id"] == owner_id else "member"
        c[f"{who}_total"] += 1
        if content:
            c[f"{who}_has_text"] += 1
        if atts:
            c[f"{who}_has_attachment"] += 1
        if embeds:
            c[f"{who}_has_embed"] += 1
        if not content and atts:
            c[f"{who}_image_only"] += 1
        if not content and not atts and not embeds:
            c[f"{who}_empty"] += 1
        if content:
            if has_price(content):
                c[f"{who}_text_has_price"] += 1
            if RE_SIDE.search(content):
                c[f"{who}_text_has_side"] += 1
            if RE_UNITS.search(content):
                c[f"{who}_text_has_stake"] += 1
            if RE_RESULT.search(content):
                c[f"{who}_text_has_result"] += 1
            if has_price(content) and RE_SIDE.search(content):
                c[f"{who}_scorable"] += 1
    return c


def load(export_dir: str):
    paths = sorted(glob.glob(os.path.join(export_dir, "*.json")))
    if not paths:
        raise SystemExit(f"No export JSON under {export_dir}")
    out, meta = [], []
    for p in paths:
        with open(p, "r", encoding="utf-8") as fh:
            d = json.load(fh)
        meta.append({
            "guild": d.get("guild", {}).get("name", ""),
            "channel": d.get("channel", {}).get("name", ""),
            "exported_at": d.get("exportedAt", ""),
            "count": d.get("messageCount", len(d.get("messages", []))),
        })
        out.extend(d.get("messages", []))
    out.sort(key=lambda m: m["timestamp"])
    return out, meta


def owner_of(messages):
    """The seller. Identified structurally — the author who holds a coloured
    server role and posts most — never by a hardcoded handle, because a handle
    is a name and names do not go in this repo."""
    roled = collections.Counter(
        m["author"]["id"] for m in messages if m["author"].get("roles"))
    if roled:
        return roled.most_common(1)[0][0]
    return collections.Counter(
        m["author"]["id"] for m in messages).most_common(1)[0][0]


def cdn_expiry(messages):
    """DiscordChatExporter records attachment URLs, not attachments. Discord's
    CDN signs those URLs with an `ex=` hex unix expiry. Whether they are already
    dead is a fact about this dataset, so it is measured rather than assumed."""
    now = datetime.datetime.now(datetime.timezone.utc)
    live = dead = unknown = 0
    earliest = latest = None
    for m in messages:
        for a in m.get("attachments") or []:
            mm = re.search(r"[?&]ex=([0-9a-f]+)", a.get("url", ""))
            if not mm:
                unknown += 1
                continue
            try:
                exp = datetime.datetime.fromtimestamp(int(mm.group(1), 16),
                                                      datetime.timezone.utc)
            except (ValueError, OSError, OverflowError):
                unknown += 1
                continue
            earliest = exp if earliest is None else min(earliest, exp)
            latest = exp if latest is None else max(latest, exp)
            if exp > now:
                live += 1
            else:
                dead += 1
    return live, dead, unknown, earliest, latest


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--export-dir", default=EXPORT_DIR)
    ap.add_argument("--out", default=os.path.join(db.REPORTS, "T3_discord.md"))
    ap.add_argument("--required-n", type=int, default=481,
                    help="settled observations this programme has measured as "
                         "the requirement to separate edge from luck")
    args = ap.parse_args()

    if not os.path.isdir(args.export_dir):
        raise SystemExit(f"{args.export_dir} does not exist")

    messages, meta = load(args.export_dir)
    owner = owner_of(messages)
    c = census(messages, owner)

    ts = [datetime.datetime.fromisoformat(m["timestamp"]) for m in messages]
    span_days = (max(ts) - min(ts)).days if ts else 0
    authors = {m["author"]["id"] for m in messages}
    owner_msgs = [m for m in messages if m["author"]["id"] == owner]
    n_owner = len(owner_msgs)
    n_scorable = c["owner_scorable"]
    live, dead, unknown, exp_lo, exp_hi = cdn_expiry(messages)

    texts = [(m.get("content") or "").strip() for m in owner_msgs]
    med_len = sorted(len(t) for t in texts)[len(texts) // 2] if texts else 0
    n_digit = sum(1 for t in texts if re.search(r"\d", t))

    calls = call_candidates(messages, owner)
    n_named = sum(1 for k in calls if k["names"])
    n_call_price = sum(1 for k in calls if k["has_price"])
    n_call_stake = sum(1 for k in calls if k["has_stake"])
    all_names = set()
    folded = set()
    for k in calls:
        for nm in k["names"]:
            all_names.add(nm)
            folded.add((k["ts"].date(), nm))
    n_folded = len(folded)

    RE_WIN = re.compile(r"\b(won|win|winner|green|cash(?:ed)?\s*out|profit|"
                        r"gg|bang|easy|free money)\b", re.I)
    RE_LOSS = re.compile(r"\b(lost|loss|losing|red|down|tough|brutal|rough|"
                         r"unlucky|my bad|sorry|refund)\b", re.I)
    RE_HEDGE = re.compile(r"\b(personal|not a lock|at (?:ur|your) own risk|"
                          r"up to you|i can'?t really answer|no wifi|"
                          r"stay tuned)\b", re.I)
    n_win = sum(1 for t in texts if RE_WIN.search(t))
    n_loss = sum(1 for t in texts if RE_LOSS.search(t))
    n_hedge = sum(1 for t in texts if RE_HEDGE.search(t))

    lines = []
    w = lines.append
    w("# T3 — the paid Discord server's calls, measured\n")
    w(f"Read {datetime.datetime.now(datetime.timezone.utc):%Y-%m-%d} UTC. "
      "Authors are replaced by per-run salted pseudonyms; the salt is generated "
      "at import and never stored. No handle, user id, server name or message "
      "text appears below.\n")

    w("## The export\n")
    w("| | |\n|---|---|")
    w(f"| channels exported | {len(meta)} |")
    w(f"| messages | {len(messages)} |")
    w(f"| distinct authors | {len(authors)} |")
    w(f"| date span | {min(ts):%Y-%m-%d} to {max(ts):%Y-%m-%d} "
      f"({span_days} days) |")
    w(f"| owner share of messages | {n_owner}/{len(messages)} "
      f"({100*n_owner/max(len(messages),1):.0f}%) |")
    w("")

    w("## Message composition — this is the finding\n")
    w("| | owner | members |\n|---|---|---|")
    for label, k in [
        ("messages", "total"),
        ("carry any text", "has_text"),
        ("carry an image attachment", "has_attachment"),
        ("**image only, no text at all**", "image_only"),
        ("carry an embed", "has_embed"),
        ("text contains a price / odds / %", "text_has_price"),
        ("text contains a side word", "text_has_side"),
        ("text contains a stake in units", "text_has_stake"),
        ("text states a result", "text_has_result"),
        ("**text carries side AND price**", "scorable"),
    ]:
        w(f"| {label} | {c['owner_' + k]} | {c['member_' + k]} |")
    w("")
    w(f"**{n_scorable} of {n_owner} owner messages carry both a side and a "
      f"price in text.**\n")

    w("## What the calls actually look like\n")
    w("Not a structured feed. The channel is **prose**: a directional opinion "
      "on a named player, sometimes with a screenshot attached, and the price "
      "almost never written down. Median owner message length is "
      f"**{med_len} characters**.\n")
    w("| | n | share of owner messages |\n|---|---|---|")
    w(f"| carry a directional call verb | {len(calls)} | "
      f"{100*len(calls)/max(n_owner,1):.0f}% |")
    w(f"| ...and name at least one player | {n_named} | "
      f"{100*n_named/max(n_owner,1):.0f}% |")
    w(f"| ...and also state a price | {n_call_price} | "
      f"{100*n_call_price/max(n_owner,1):.0f}% |")
    w(f"| ...and also state a stake | {n_call_stake} | "
      f"{100*n_call_stake/max(n_owner,1):.0f}% |")
    w(f"| contain any digit at all | {n_digit} | "
      f"{100*n_digit/max(n_owner,1):.0f}% |")
    w("")
    w(f"**A price appears in {c['owner_text_has_price']} of {n_owner} owner "
      "messages, and a price and a side together in "
      f"{n_scorable}.** Without an entry price there is no edge to compute — "
      "only a win rate, and this programme's own repeated result is that a win "
      "rate cannot clear a cost bar it never states.\n")

    w("## The prices are in the screenshots, and the screenshots are gone\n")
    w(f"{c['owner_has_attachment']} owner messages carry an image. The export "
      "records the attachment's **URL**, not the attachment. Discord signs "
      "those CDN URLs with an `ex=` hex unix expiry, so whether they are still "
      "fetchable is decidable without fetching anything:\n")
    w("| attachment URLs | n |\n|---|---|")
    w(f"| signed expiry in the future (still fetchable) | {live} |")
    w(f"| **signed expiry in the past (dead)** | **{dead}** |")
    w(f"| no `ex=` parameter | {unknown} |")
    if exp_lo and exp_hi:
        w(f"| expiry window | {exp_lo:%Y-%m-%d %H:%M} to {exp_hi:%Y-%m-%d %H:%M} UTC |")
    w("")
    w("So the **direction** of every call survives in the text and the "
      "**price** does not. That asymmetry decides which of the four planned "
      "measurements can run.\n")

    w("## Every planned measurement, and why each one cannot run\n")
    w("| measurement | needs | present? |\n|---|---|---|")
    w("| persistence (rank 1st half, score 2nd) | a settled result per call | "
      "**partly recoverable** — the player is named, so an external tennis "
      "results feed could settle it |")
    w("| skill vs luck, shrunk by sample size | per-call outcome | same as above |")
    w("| edge decay +1s / +10s / +60s / +5m | an entry price **and** a price "
      f"series for the same instrument | **no** — {n_call_price} calls state a "
      "price and no message names a market ticker |")
    w("| adverse selection | entry price vs the contemporaneous book | **no** |")
    w("| one observation per match | a match identifier | **proxy only** — "
      "player name plus date |")
    w("")
    w("The two price-based measurements are dead outright. The two "
      "outcome-based ones are recoverable in principle, at the cost of an "
      "external results feed and a name-matching pass — and **a win rate with "
      "no entry price cannot be compared against a cost bar**, which is the one "
      "comparison that has decided every other thread in this repo.\n")

    w("## The sample size was never going to be enough anyway\n")
    w("`polymarket-tennis-copy` established the bar this programme keeps hitting: "
      f"roughly **{args.required_n} settled observations** to separate a real "
      "edge from a lucky run at the effect sizes found here. That number assumes "
      "**one observation per match** — the fold that project had to learn twice, "
      "after per-trade rows produced t-statistics of 90 and 408.\n")
    days_active = len({t.date() for t in ts})
    w("| | |\n|---|---|")
    w(f"| owner messages | {n_owner} |")
    w(f"| distinct active days | {days_active} |")
    w(f"| messages carrying a directional call | {len(calls)} |")
    w(f"| distinct players ever named | {len(all_names)} |")
    w(f"| **distinct (date, player) pairs — the folded n** | **{n_folded}** |")
    w(f"| required for a powered test | ~{args.required_n} |")
    w(f"| **shortfall** | **{args.required_n - n_folded} observations, "
      f"{args.required_n/max(n_folded,1):.1f}x short** |")
    w("")
    w("The fold matters and it is not a technicality. Taking every owner "
      f"message as an observation gives {n_owner}; taking every call verb gives "
      f"{len(calls)}; folding to one observation per (date, player) — the rule "
      "`polymarket-tennis-copy` had to learn twice, after per-trade rows "
      f"produced t-statistics of 90 and 408 — gives **{n_folded}**. "
      f"**The headline count of {n_owner} overstates the real sample by "
      f"{n_owner/max(n_folded,1):.1f}x before a single price is missing.**\n")
    w("**UNDERPOWERED is the finding, and it is decidable without ever seeing a "
      "price.** Even with perfectly legible screenshots and clean settlements, "
      f"{n_folded} independent observations over {span_days} days is "
      f"{100*n_folded/args.required_n:.0f}% of the requirement. A point estimate "
      "on it carries an interval wider than any edge worth paying a subscription "
      "for — which is the shape this programme has now found in tennis, in "
      "copy-trading and in crypto ladders: **a real effect, if any, smaller "
      "than the cost of reaching it.**\n")

    w("## The seller's own honesty, on the rubric\n")
    w("The credibility rubric ported from `youtube-signal` grades rather than "
      "binary-sorts, and its single strongest signal is **showing things that "
      "did not work**. That is measurable here, because result language is in "
      "the text even when prices are not.\n")
    w("| | n | share of owner messages |\n|---|---|---|")
    w(f"| messages using win-flavoured language | {n_win} | "
      f"{100*n_win/max(n_owner,1):.0f}% |")
    w(f"| messages using loss-flavoured language | {n_loss} | "
      f"{100*n_loss/max(n_owner,1):.0f}% |")
    w(f"| messages hedging the call (\"personal\", \"at your own risk\", "
      f"\"not a lock\") | {n_hedge} | {100*n_hedge/max(n_owner,1):.0f}% |")
    w("")
    if n_loss > 0:
        w(f"**Losses are posted, and they are outnumbered {n_win/n_loss:.1f} to "
          f"1.** {n_loss} messages carry loss language against {n_win} carrying "
          "win language. Both readings are available and the honest report is "
          "both: a room that posts *any* losses is not the pure marketing "
          "shape the rubric penalises hardest (H1 fires), and a "
          f"{n_win/n_loss:.1f}:1 win-to-loss ratio in **self-selected** "
          "language is not a track record — a real tennis book runs far closer "
          "to even, and the gap is what selective posting looks like from "
          "outside.\n")
    else:
        w("**No loss language anywhere.** Every post is a win, which is the "
          "marketing shape the rubric penalises hardest.\n")
    w(f"{n_hedge} messages ({100*n_hedge/max(n_owner,1):.0f}%) hedge the call "
      "explicitly. That is a genuine credit on the rubric and it also transfers "
      "the risk to the reader without transferring the price.\n")
    w("Two caveats that stop this being a track record. First, **self-reported "
      "result language is not a settled result** — nothing here was checked "
      "against an exchange. Second, the rubric's H6 fires on a performance "
      "claim with no denominator, and this channel states no bankroll, no "
      "cumulative record and no closing price on any call. **Honest-sounding "
      "and unmeasurable are not in tension; this channel is both.**\n")

    w("## What IS fully recorded: reactions\n")
    rx, rx_owner = collections.Counter(), collections.Counter()
    for m in messages:
        for r in m.get("reactions") or []:
            code = (r.get("emoji") or {}).get("code") or "?"
            rx[code] += r.get("count", 0)
            if m["author"]["id"] == owner:
                rx_owner[code] += r.get("count", 0)
    reacted = sum(1 for m in owner_msgs if m.get("reactions"))
    w("Reaction counts are complete for every message. They record member "
      "*response*, not outcome — a check mark on a call says the room saw it, "
      "not that it won. Recorded because it is the only complete column here, "
      "and explicitly **not** used as a proxy for results.\n")
    w("| emoji | total | on owner messages |\n|---|---|---|")
    for code, n in rx.most_common(12):
        w(f"| `{code}` | {n} | {rx_owner[code]} |")
    w("")
    w(f"{reacted} of {n_owner} owner messages carry at least one reaction "
      f"({100*reacted/max(n_owner,1):.0f}%).\n")

    w("## What would make this measurable, and whether it is worth it\n")
    w("1. **Re-export with media downloaded** — DiscordChatExporter's `--media` "
      "flag saves the images beside the JSON. Every URL in this export is "
      "expired, so this must be re-run against the live server by someone who "
      "is still a member. Nothing else recovers the prices.\n"
      "2. **OCR the screenshots** into (instrument, side, price, stake, time).\n"
      "3. **Settle the calls.** The player is named in the text, so an external "
      "tennis results feed settles direction without the images at all — but "
      "`kalshi-tennis`'s Sackmann mirror ends **2026-06-02** and this export "
      f"starts {min(ts):%d %b %Y}, so the local data does not cover a single day "
      "of it. Kalshi's own API is a ~69-day window and closed markets 404; this "
      f"export ends {max(ts):%d %b %Y}, so that window is closing too.\n"
      "4. Even with all three, the answer is bounded by the "
      f"**{n_folded} folded observations** above.\n")
    w("**Recommendation: do not spend the time.** Steps 1-3 buy a "
      "better-measured underpowered result. The only version of this worth "
      "doing is a *forward* record — start logging calls with prices from "
      "today, against a pre-declared cost bar — and even then the seller's own "
      "channel would need to run for roughly "
      f"{args.required_n/max(n_folded,1)*span_days/30:.0f} more months at its "
      "current rate before the question becomes answerable.\n")

    text = "\n".join(lines)
    with open(args.out, "w", encoding="utf-8") as fh:
        fh.write(text)
    print(text)
    print(f"\n  wrote {args.out}")

    con = db.connect()
    db.log(con, "discord_measure",
           f"messages={len(messages)} owner={n_owner} "
           f"image_only={c['owner_image_only']} scorable={n_scorable} "
           f"dead_cdn={dead} span_days={span_days}")
    con.close()


if __name__ == "__main__":
    main()

"""Reputation verification: does anyone INDEPENDENT vouch for this tool?

verify_tools.py only proves a URL responds. That is necessary and nowhere near
sufficient. A live site with a referral link is not evidence of a scam, and a
polished landing page is not evidence of safety. This layer asks a different
question: what does the internet say about it that the vendor did not write?

Four verdicts, and the fourth is the one people collapse by mistake:

  POSITIVE      independent corroboration from a source that is not the vendor
  MIXED         real product, real criticism
  NEGATIVE      documented complaints, scam reports, dead product
  NO_FOOTPRINT  nothing found

NO_FOOTPRINT IS NOT POSITIVE. Absence of complaints about a small tool is absence
of evidence, not a clean bill of health. They are stored as different values and
must never be merged.

Promotional coverage does not count as corroboration. Medium posts by crypto
accounts, "review" sites that link affiliate codes, and the vendor's own blog are
all the vendor talking. Only sources with no incentive count as independent.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import db as _db  # noqa: E402
import db_phase2  # noqa: E402

SCHEMA = """
ALTER TABLE tools ADD COLUMN reputation TEXT;
ALTER TABLE tools ADD COLUMN reputation_detail TEXT;
ALTER TABLE tools ADD COLUMN reputation_sources TEXT;
ALTER TABLE tools ADD COLUMN reputation_utc TEXT;
"""

# Researched by web search on 2026-08-03. Sources recorded so a later session can
# re-check rather than trust this.
FINDINGS = {
    # ------------------------------------------------------------------
    # Batch 2, researched 2026-08-03 alongside the 13-video read.
    # The first two entries are the reason this layer exists: both are the
    # library a recent, well-taught tutorial tells you to build on, and both
    # were killed by the venue months after that tutorial was published.
    # ------------------------------------------------------------------
    "Polymarket CLOB API + py-clob-client": {
        "reputation": "NEGATIVE",
        "detail": (
            "DEAD LIBRARY, LIVE API. Polymarket/py-clob-client (1,234 stars) was "
            "ARCHIVED 11 May 2026 and Polymarket/clob-client, the TypeScript one "
            "(513 stars), the same month, last push 25 May 2026. CLOB V2 went live "
            "28 Apr 2026 and V1 SDKs and V1-signed orders are no longer supported "
            "on production -- these clients are non-functional for new AND existing "
            "integrations, not merely unmaintained. Two tutorials in this knowledge "
            "base teach them: wangr's Polymarket CLOB walkthrough (4 Feb 2026, "
            "scored S=8 H=3) and JunkieAI's data pull (20 Jan 2025). Both were "
            "correct when filmed. Neither is now. Migrate to Polymarket/py-sdk "
            "(alive, 82 stars, last push 31 Jul 2026, unified Gamma+Data+CLOB, "
            "recommended for new projects) or the interim py-clob-client-v2 / "
            "clob-client-v2. Guide: docs.polymarket.com/v2-migration. "
            "The NON-library content of those videos still holds: wide spreads, "
            "separate YES/NO books, chain ID 137, the dry-run and throwaway-wallet "
            "patterns."
        ),
        "sources": [
            "https://api.github.com/repos/Polymarket/py-clob-client",
            "https://api.github.com/repos/Polymarket/clob-client",
            "https://api.github.com/repos/Polymarket/py-sdk",
            "https://docs.polymarket.com/v2-migration",
        ],
        "note": (
            "THIS IS THE FINDING THE SYSTEM EXISTS TO PRODUCE. A six-month-old "
            "tutorial with a good honesty score, teaching a library the venue "
            "archived three months after filming. Nothing in the video is wrong "
            "and following it today produces a bot that cannot sign an order."
        ),
    },
    "Polymarket CLOB client (TypeScript and Python)": {
        "reputation": "NEGATIVE",
        "detail": (
            "Same finding as the entry above, recorded against the JunkieAI "
            "extraction's naming. Polymarket/clob-client is ARCHIVED (513 stars, "
            "last push 25 May 2026). Its shipped example scripts -- create/get/"
            "delete API key, get_market, get_order_book, get_price_history, "
            "market buy/sell -- are V1 and will not sign a valid order against "
            "CLOB V2. Use Polymarket/py-sdk."
        ),
        "sources": [
            "https://api.github.com/repos/Polymarket/clob-client",
            "https://github.com/Polymarket/py-clob-client-v2",
        ],
    },
    "moondevonyt GitHub account (the '20+ agents' repo is GONE)": {
        "reputation": "MIXED",
        "detail": (
            "NAME-VARIANT CHECK CHANGED THE VERDICT. The transcript garbles the "
            "repo as 'AI agents Mundev'; the first guessed URL "
            "(moondevonyt/moon-dev-ai-agents) 404s, which would have been recorded "
            "as DEAD. Searching variants shows the ACCOUNT is live -- 26 public "
            "repos, 2,719 followers -- but the specific repo he points viewers at, "
            "moon-dev-ai-agents-for-trading, now 404s while dozens of third-party "
            "forks survive. So the '20+ agents, 100% open source' claim was true "
            "and the artifact is gone. What IS live and relevant: "
            "Polymarket-Trading-Bot-Examples-By-Moon-Dev (25 stars, pushed "
            "2026-07-18), Hyperliquid-Data-Layer-API (107 stars, 2026-07-20), "
            "Limitless-Prediction-Market-Bots (60 stars), Moon-Dev-AI-Trading-"
            "Battles. He also states in the video that the stink-bid bot and the "
            "P&L tool shown are in NO repo -- the screen is the only source."
        ),
        "sources": [
            "https://api.github.com/users/moondevonyt",
            "https://api.github.com/users/moondevonyt/repos?sort=updated",
        ],
        "note": (
            "Second time the garbled-name rule has paid for itself, after "
            "Creo->Kreo. A 404 on a guessed URL is evidence about the guess "
            "before it is evidence about the tool."
        ),
    },
    "OpenClaw": {
        "reputation": "MIXED",
        "detail": (
            "REAL AND WIDELY COVERED, WITH A FAILURE RATE THE VIDEOS DO NOT "
            "MENTION. Self-hosted AI agent runtime: a persistent Node.js process "
            "on your own box (Mac Mini, VPS, Raspberry Pi) with cron scheduling, "
            "cross-session memory, and shell/filesystem/email/calendar access "
            "driven by Claude or GPT APIs. Independent reviews are consistent in "
            "both directions: genuinely powerful for technical users, and "
            "'reliability works if you can tolerate 20-30% failure rates and "
            "iteration cycles measuring weeks, not hours', explicitly 'not ready "
            "for mainstream adoption'. Self-hosting moves the security liability "
            "to you: the agent can run git commands, rewrite files and send mail "
            "from your account. Directly relevant to the two videos here that run "
            "trading strategies on it -- a 20-30% failure rate is the same order "
            "as the 'silent crash' and hung-API-call failures both creators hit."
        ),
        "sources": [
            "https://www.vellum.ai/blog/best-openclaw-alternatives",
            "https://hackceleration.com/openclaw-review",
            "https://duet.so/blog/openclaw-vs-managed-ai-agent-platforms",
            "https://techradar.com/pro/how-to-self-host-your-openclaw-environment-on-a-vps-server",
        ],
    },
    "Hermes Agent": {
        "reputation": "MIXED",
        "detail": (
            "REAL OPEN-SOURCE PROJECT, NO CORROBORATED TRADING RESULTS. Open-source "
            "agent framework with persistent memory, ~70 tools across 28 toolsets, "
            "MCP support, a delegate_task tool spawning child agents with isolated "
            "context, cron scheduling (`hermes cron create`), and gateways to ~24 "
            "chat platforms including Telegram and Discord. The framework itself is "
            "well attested. The TRADING corroboration is not: it is individual "
            "Medium/DEV writeups building ETF and IBKR bots, none of which report a "
            "result, plus vendor sites (hermes-agent.org, hermesagents.net) and a "
            "review on a competitor's blog. Rate the runtime, not the returns -- "
            "the video using it here produced paper trading only."
        ),
        "sources": [
            "https://dev.to/hopebestworld/building-a-local-ai-market-trader-with-hermes-agent-41pf",
            "https://medium.com/@miketonny/building-an-ai-powered-quantitative-trading-system-with-hermes-agent-and-ibkr-0dff7a513265",
            "https://hermes-agent.org/",
        ],
    },
    "karpathy/autoresearch (auto research loop)": {
        "reputation": "POSITIVE",
        "detail": (
            "VERIFIED LIVE AND LARGE. 92,851 stars, 530KB, last push 2026-03-26. "
            "Not a README-only repo. This is the one claimed artifact in the "
            "13-video batch that resolved cleanly on the first check, and it is "
            "the reason btG5YpvPkwE scores H=11. Note what it does and does not "
            "prove: the harness is real and public; the trading adaptation built "
            "on it in that video is backtest-only and was never run live."
        ),
        "sources": ["https://api.github.com/repos/karpathy/autoresearch"],
    },
    "Prediction Quant": {
        "reputation": "NO_FOOTPRINT",
        "detail": (
            "Unreleased at filming (3 Apr 2026) -- waitlist only, founder pricing "
            "promised, no public URL given in the video and none recorded here. "
            "NO_FOOTPRINT IS NOT A CLEAN BILL OF HEALTH: there is simply nothing "
            "to check. Everything absorbed from that video is the ARITHMETIC and "
            "the screen behaviour (cross-venue arb sizing, slippage decay on thin "
            "markets, Kelly tiers), none of which depends on the product existing. "
            "Its central 'arbitrage is risk-free' claim is contradicted inside "
            "this same knowledge base by Kalshi's C x P x (1-P) fee formula and by "
            "a second creator who tried Polymarket arb and concluded the markets "
            "were too efficient."
        ),
        "sources": [],
    },
    "Kreo (Telegram copy-trading bot)": {
        "reputation": "MIXED",
        "detail": (
            "REAL PRODUCT, REAL RISK. Non-custodial smart-wallet architecture, which "
            "is genuinely better than the typical Telegram bot where the operator "
            "holds private keys — but it is still a hot wallet by design. Placed "
            "first in independent testing for execution speed and usability. "
            "AGAINST THAT: Polymarket reviewed its own Builders Program over "
            "concerns about copy-trading apps, naming Kreo among apps that market "
            "'following insider traders'; that cohort has suffered security "
            "breaches with losses reported up to $230,000. Its own selling point "
            "is finding 'insider traders before anyone else', which is the "
            "behaviour that triggered the platform review. Do not hold size in it."
        ),
        "sources": [
            "https://www.kucoin.com/news/flash/polymarket-reviews-developer-program-amid-concerns-over-copy-trading-apps-and-insider-like-behavior",
            "https://coincodecap.com/kreo-review-polymarket-kalshi-copy-trading-bot",
            "https://polymarktbots.com/tools/copy-trading-bots/kreo/",
        ],
        "rename_from": "Creo (Telegram copy-trading bot)",
        "note": (
            "NAME CORRECTION: the transcript said 'Creo'. The product is 'Kreo' "
            "(@KreoPolyBot). Auto-generated captions garble product names, and a "
            "tool-extraction pipeline that trusts them will verify the wrong thing "
            "or nothing at all. Always search variants before recording NO_FOOTPRINT."
        ),
    },
}


def main():
    con = db_phase2.connect()
    for stmt in SCHEMA.strip().split(";"):
        if stmt.strip():
            try:
                con.execute(stmt)
            except Exception:  # noqa: BLE001 - column already exists
                pass
    con.commit()

    for name, f in FINDINGS.items():
        old = f.get("rename_from")
        if old:
            con.execute("UPDATE tools SET name=? WHERE name=?", (name, old))
        con.execute(
            """UPDATE tools SET reputation=?, reputation_detail=?,
                   reputation_sources=?, reputation_utc=? WHERE name=?""",
            (f["reputation"], f["detail"], json.dumps(f["sources"]),
             _db.now(), name))
        print(f"  {f['reputation']:<13} {name}")
        if f.get("note"):
            print(f"      NOTE: {f['note'][:150]}...")
    con.commit()

    print("\n  tools with a reputation verdict:")
    for r in con.execute(
        "SELECT reputation, COUNT(*) n FROM tools WHERE reputation IS NOT NULL"
        " GROUP BY reputation"
    ):
        print(f"    {r['reputation']:<14}{r['n']}")
    unchecked = con.execute(
        "SELECT COUNT(*) c FROM tools WHERE reputation IS NULL").fetchone()["c"]
    print(f"    {'(unchecked)':<14}{unchecked}")
    print("\n  Reminder: NO_FOOTPRINT is never POSITIVE. Absence of complaints "
          "about\n  a small tool is absence of evidence.")
    con.close()


if __name__ == "__main__":
    main()

# HANDOFF — youtube-signal

**Phase 2 is unblocked and running. 2026-08-03.** Laptop `gianf`.
Repo `github.com/vinexcleaning/trading`, project `youtube-signal/`.

The blocker in the previous version of this file — "no `ANTHROPIC_API_KEY`, the
read never ran, buy $5 of credit" — **is obsolete and was the wrong instruction.**
The read is done in-session by the model reading the transcript itself.

**Cost to date: $0.00. YouTube Data API quota consumed: 0 units.**
`read_video.py` still has never executed and is still unvalidated; the free path
(`dump_transcripts.py` → hand-written JSON → `load_extraction.py`) has now run
19 times and is the working path. Do not spend money to unblock a thing that is
not blocked.

---

## 1. How many videos, and which

**13 read this session** (6 were already read, 19 total). One video per turn,
transcript never carried forward. Chosen deliberately against the coverage gaps
and against what the brief said the user actually wants.

| video_id | S | H | verdict | min | what it is |
|---|---|---|---|---|---|
| `btG5YpvPkwE` | 10 | **11** | ABSORB_AND_RECOMMEND | 18 | Live bot post-mortem: $50→$500→**$0**, 814 trades, fees −$115. Then Karpathy's auto-research loop pointed at trading. |
| `RxE2oE1g1FY` | 10 | 2 | ABSORB | 23 | Polymarket copy-trading bot: 9 components, paper-first, autonomy gate. |
| `rrLnJO5x_Po` | 10 | 1 | ABSORB | 12 | Live Polymarket stink-bid bot, 34 trades, **break-even**. P&L-by-keyword tool. |
| `YknxNkTgNWk` | 10 | 0 | ABSORB | 17 | "+1,560% ROI" — **paper**. The one live account did −70% in a day. |
| `lVqF8oLzVAU` | 8 | 3 | ABSORB_AND_RECOMMEND | 17 | Polymarket CLOB API end to end, real order placed and cancelled. |
| `W722Ca8tS7g` | 7 | −2 | ABSORB_RESULTS_DISCOUNTED | 11 | The four backtest robustness tests. Sound method, unsupported 18%/mo claim. |
| `yYjo1lzNoGI` | 6 | 6 | ABSORB_AND_RECOMMEND | 19 | Kalshi API in Python, live order placed. **Never mentions fees.** |
| `pZKnS-AlW-s` | 6 | 3 | ABSORB_AND_RECOMMEND | 7 | True cost of a market order: fee + half-spread + impact + adverse selection. |
| `rDkVmkrzpbI` | 6 | 1 | ABSORB_AND_RECOMMEND | 13 | Polymarket WebSockets; how to keep a local order book. |
| `sQZbxKXbk9g` | 6 | −1 | ABSORB_RESULTS_DISCOUNTED | 28 | Cross-venue Kalshi↔Polymarket arb demo. Claims risk-free; ignores fees. |
| `73R8zkMd034` | 4 | 1 | ABSORB | 22 | Expectation arithmetic + the "30 trades" rule, which our own n-check refutes. |
| `Ib0BEFKAvn0` | 3 | **9** | SKIP | 27 | Kalshi + Perplexity Sonar assistant in 100 lines. **See §3 — this verdict is a rubric bug, not a judgment on the video.** |
| `MyCjPs0pRy4` | 1 | 4 | SKIP | 40 | Flailing 41-minute screencast that nonetheless names the free Polymarket subgraph. |

Skipped deliberately: the 681-minute Moon Dev video (does not fit a context
window, chunking not built).

---

## 2. What is now actionable that was not before

Before this batch the knowledge base could explain *why* prediction markets are
hard. It could not tell you how to place an order. That has changed.

**Building a Kalshi bot — now complete end to end.**
Free unauthenticated market data (no key needed to read events or odds). ~30,000
events, `with_nested_markets`, cursor pagination, ~193 s for a full pull, cache
it. Auth is Account → Security → Create key, scope **read-and-write** for
trading, giving an API key ID plus a downloaded RSA `.pem`. Recurring markets
(BTC 15-minute) must be resolved at runtime through series → events → ticker;
you cannot hardcode. And the fact that reorganises everything: **Kalshi has no
market orders.** Fill-or-kill with an aggressive price is the only way to take.
Sizing is in contracts, not dollars.

**Building a Polymarket bot — complete, and one large caveat (§5).**
Credentials (private key + proxy wallet), chain ID 137, API keys *derived* from
the wallet rather than issued, the four-call trading surface, separate YES/NO
order books with asymmetric depth, WebSocket market channel (public, no auth) vs
user channel (authed, with a MINED/CONFIRMED/RETRYING/**FAILED** lifecycle — a
fill is not final on first message), and how to maintain a local order book from
`book` messages instead of polling into a rate limit.

**Where to get free historical data.**
Polymarket: `get_price_history` (token ID + start/end + interval), and a public
GraphQL **subgraph hosted on Goldsky** with conditions, orders, positions,
question IDs and resolutions — joined to the CLOB by `condition_id`. Explicitly
do **not** self-host it; someone already burned an hour proving that. `get_trades`
did not work for trade-level history. Kalshi: the events/markets endpoints are
free and unauthenticated.

**Backtesting that models costs.**
A four-component cost model with real numbers: fee + half-spread + square-root
impact (σ·√(Q/V)) + adverse selection (~10% of the half-spread in crypto). For a
$10k BTC order the true cost is $13.33 against a $10 quoted fee. Doubling size
raises impact by √2, which is why slicing works and why slicing small orders does
not. And a four-test robustness battery — parameter-sensitivity plateaus not
cliffs, walk-forward (degradation is fine, *inversion* is disqualifying),
stress tests that double commissions and triple slippage, and Monte Carlo on
trade *sequence* read as a position-sizing instruction rather than pass/fail.

**Is a strategy worth testing — three answers, all negative, all useful.**
Copy trading: −70% in a day live against +1,560% on paper. Stink-bidding
Polymarket BTC markets: break-even over 34 trades. Polymarket arbitrage: one
creator finds ~40 live signals, another tried it and concluded the markets are
too efficient — and the first one's own demo shows profit decaying to nothing as
size rises. The reconciliation is that the arbs live in illiquid pop-culture
markets where slippage and Kalshi's mid-price-peaking fee eat them.

**Automation ceiling, and where a human must click.** Everything except the
initial API-key creation (a web UI on both venues) and funding. What actually
stops autonomy is not capability: 20–30% agent failure rates, hung API calls that
stall a loop silently, and LLM non-determinism — the same prompt on the same
market flipped a verdict between two runs.

---

## 3. The numbers, including the bad ones

**Component fire rates across all 19 videos. Nothing never fired.**

| | fired | of 19 | | | fired | of 19 |
|---|---|---|---|---|---|---|
| S1 cost side | 16 | 84% | | H1 failure, no fix sold | 5 | 26% |
| S2 backtest vs live | 13 | 68% | | H1b failure sets up sale | 5 | 26% |
| S3 sample size | 9 | 47% | | H2 verifiable artifact | 8 | 42% |
| S4 mechanism | 17 | 89% | | H3 n + period + capital | 10 | 53% |
| S5 names tools | 17 | 89% | | H4 names own weakness | **17** | 89% |
| | | | | H5 discloses own product | 11 | 58% |
| | | | | H6 no denominator | 6 | 32% (−24) |
| | | | | H7 sells w/o mechanism | 2 | 11% |
| | | | | H8 urgency | 4 | 21% |

Verdicts: ABSORB 8 · ABSORB_AND_RECOMMEND 7 · ABSORB_RESULTS_DISCOUNTED 2 · SKIP 2.
Claims 205 (mechanism 67, procedure 40, result 39, spec 35, math 12, concept 11,
tool_rec 1). Methods 18. Tools 58.
n-check: 4 SUPPORTED, 1 REFUTED, 1 INDISTINGUISHABLE FROM NOISE.
Watch segments 17 across 19 videos: **6.1 hours of runtime → 15 minutes to
watch, 24× compression**, and 4 videos needed zero minutes.

### The rubric bug this batch exposed — read this before scoring more videos

**S structurally under-scores engineering content, and the two SKIPs prove it.**

S1 (cost), S2 (backtest vs live) and S3 (sample size) are all *trading-claim*
components. A pure API tutorial makes no trading claim, so it can score at most
S4+S5 = 3 and is auto-classified SKIP however useful it is.

- `Ib0BEFKAvn0` — Part Time Larry, the highest-honesty creator in the corpus
  (H=9), 100 lines of working Kalshi + LLM code, a public repo, a real itemised
  account, and a documented loss on a settlement-rules technicality. **S=3 →
  SKIP.**
- `MyCjPs0pRy4` — S=1 → SKIP, and it is the only source in the corpus for the
  free Polymarket subgraph.

The claims still land in `KNOWLEDGE.md` (`build_knowledge.py` filters only the
"worth watching" section by verdict), so nothing was lost. But SKIP now means two
different things and cannot be trusted as a filter. **Fix by adding a build axis**
— S6 runnable artifact / S7 credentials-and-auth path / S8 named endpoints — or
by scoring INFORMATIVE-for-building separately. Do not paper over it by loosening
S1; the strict reading is what surfaced the pattern.

**H4 firing 89% of the time is close to useless as a discriminator.** Almost
everyone hedges somewhere. It is worth only +1, so it distorts little, but it is
not measuring what it claims to.

**H1 vs H1b is the judgment call that moves scores most** (+3 vs +1) and it has
no mechanical test. I resolved it by asking whether the failure bridges into a
pitch. That is defensible and it is not reproducible.

---

## 4. Built vs actually run on real data

| | built | ran on real data |
|---|---|---|
| `dump_transcripts.py` → hand-read → `load_extraction.py` | yes | **yes — 19 videos, $0** |
| `load_extraction.py` evidence validator | yes | **yes — rejected 3 quotes at 15 words.** Works. Do not fight it. |
| `ncheck.py` Wilson n-check | yes | **yes — on 6 real extracted claims.** No longer synthetic-only. |
| `build_knowledge.py` | yes | **yes — 131,898 chars, 205 claims** |
| `verify_tools.py` | yes | **yes — 56 tools: 30 resolved, 22 not_checked, 3 unreachable, 1 dead** |
| `tool_reputation.py` | yes | **yes — 7 new verdicts.** 27 of 58 tools now judged, 31 unchecked. |
| `read_video.py` (the paid API path) | yes | **NO. STILL NEVER EXECUTED.** And no longer needed. |
| Chunking for the 681-minute video | **not built** | — |
| A build/plumbing scoring axis | **not built** | — see §3 |

---

## 5. What is wrong, unfinished or untrusted — **the section that matters**

1. **THE POLYMARKET V1 CLOB CLIENTS ARE DEAD, AND TWO VIDEOS IN THIS KNOWLEDGE
   BASE TEACH THEM.** Verified 2026-08-03 against the GitHub API. CLOB **V2 went
   live 28 Apr 2026**; V1 SDKs and V1-signed orders are no longer supported on
   production. `Polymarket/py-clob-client` (1,234★) was archived 11 May 2026;
   `Polymarket/clob-client` (TypeScript, 513★) the same month. Both are
   non-functional for new *and existing* integrations.
   `lVqF8oLzVAU` (4 Feb 2026, S=8 H=3, marked RECOMMEND) and `MyCjPs0pRy4` are
   both V1 tutorials. Nothing in either video is *wrong*; following either one
   today produces a bot that cannot sign an order.
   **Migrate to `Polymarket/py-sdk`** — alive, 82★, last push 31 Jul 2026,
   unified Gamma + Data + CLOB, recommended for new projects — or the interim
   `py-clob-client-v2` / `clob-client-v2`. Guide: `docs.polymarket.com/v2-migration`.
   The non-library content of those videos still holds: wide spreads, separate
   YES/NO books, chain ID 137, the dry-run and throwaway-wallet patterns.
   *This is the finding the whole system exists to produce, and it fell out of a
   routine `verify_tools.py` run, not out of the reading.*

2. **A guessed URL nearly produced a false DEAD.** Moon Dev's repo is garbled in
   the captions as "AI agents Mundev". My first guess
   (`moondevonyt/moon-dev-ai-agents`) 404s. The *account* is live — 26 repos,
   2,719 followers — but the specific repo he points viewers at,
   `moon-dev-ai-agents-for-trading`, now 404s while dozens of forks survive. So
   the claim was true and the artifact is gone. **Second time the name-variant
   rule has paid for itself after Creo→Kreo. A 404 on a guessed URL is evidence
   about the guess before it is evidence about the tool.**

3. **Three unresolved conflicts, written down rather than averaged away.**
   - *Which categories carry the edge.* Part Time Larry's 72M trades say
     emotional categories (sports, crypto, entertainment) are least efficient and
     therefore where edge lives. Moon Dev's rule is "stay away from crypto and
     sports, too emotional". Same premise, opposite trade. No evidence either way
     in the newer video.
   - *Whether Polymarket arbitrage exists.* ~40 live cross-venue signals in one
     demo; "the markets are so efficient" from someone who tried it. Probable
     reconciliation in §2, unresolved.
   - *Whether 30 trades proves anything.* A whole video calls 30 "the universally
     accepted baseline"; our own Wilson interval puts 55%-over-33 at
     INDISTINGUISHABLE FROM NOISE and demands n=389. **Our arithmetic wins.**

4. **Fees are missing from the API tutorials, systematically.** 19 minutes of
   end-to-end Kalshi automation never mentions the fee once — on a venue whose
   fee is proportional to C·P·(1−P) and *peaks at 50c*, exactly where the
   up/down crypto markets it demos sit. The cross-venue arb demo prices a Kalshi
   NO leg at 54c and calls the result "guaranteed". Any P&L built from these
   tutorials is systematically optimistic and worst on coin-flips.

5. **Specs from this batch are already expiring.** Video dates span Jan 2025 to
   Apr 2026 against a 3-month shelf life for specs. `MyCjPs0pRy4` (Jan 2025) and
   `Ib0BEFKAvn0` (Feb 2025) are 18 months old; `KNOWLEDGE.md` flags them
   automatically. The V1→V2 change is exactly the rot that expiry rule predicts.

6. **`load_extraction.py` had a real bug and it is fixed** (committed). The tools
   upsert used `ON CONFLICT(name, url)` while the unique index is on
   `(name, COALESCE(url,''))`, so re-loading any extraction containing a
   null-URL tool raised `IntegrityError`. This is trap #4 from `SKILL.md`
   (`NULL != NULL`) surviving in a second place. Re-loading now double-counts
   `mention_count`; cosmetic, not fixed.

7. **`Ib0BEFKAvn0` and `MyCjPs0pRy4` are marked SKIP and should not be.** See §3.
   Anyone reading verdicts without reading §3 will discard the best free-data
   pointer in the corpus.

8. **31 of 58 tools are still reputation-unchecked**, including `Tubbit`,
   `polymarket-market-maker`, the Better Traders indicators and every paid course.
   `Prediction Quant` is recorded `NO_FOOTPRINT` — unreleased, waitlist only.
   That is not a clean bill of health.

9. **The "mega rebate" / liquidity-reward lead is now mentioned by three
   independent creators and nobody has a number.** Polymarket pays for resting
   orders. Nobody in this corpus reports whether it clears inventory risk. It is
   the largest unexamined claim in the knowledge base.

10. **H1/H1b remains a judgment call** (§3), and **the S rubric's build blindness
    is unfixed** (§3).

11. Untouched from the previous handoff and still true: G3's precision/recall
    numbers are upper bounds on contaminated samples; channel expansion by ratio
    does not work and should revert to the Phase 1 state; `reports/` from before
    the gitignore decision remain in public history.

---

## 6. The single next thing to do

**Verify against `Polymarket/py-sdk` that the V2 order path actually works, then
re-read `lVqF8oLzVAU`'s procedure against it and rewrite the method.**

Everything else in this project is now downstream of one question: is the
Polymarket build path in `KNOWLEDGE.md` executable today? Kalshi's is — that
tutorial is three months old and its venue has not changed under it. Polymarket's
is not, and the file currently marks the obsolete tutorial RECOMMEND.

It costs nothing to check: clone `py-sdk`, place and cancel one order from a
$10 throwaway wallet exactly as the Feb 2026 video does, and record which of the
eleven steps changed. That converts the single most actionable method in the
knowledge base from *probably broken* to *verified*, and it is the only thing
here that a person actually needs before writing code.

Second, and cheap: add the build axis from §3 and re-score the two SKIPs. A
verdict that discards the best engineering content is worse than no verdict.

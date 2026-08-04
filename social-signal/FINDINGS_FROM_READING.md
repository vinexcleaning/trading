# What reading the Reddit corpus actually found

Six threads read in full. Permalinks only — no usernames, because this repo is
public and the posters are private individuals. Every claim below is theirs, not
this project's; where it touches a result this repo already has, that is said
explicitly.

Sorted by how much it should change what happens next.

---

## 1. Copy trading: the leak is exit fidelity, not entry latency

`/r/algotrading/comments/1v56b7h/` · 43 points · 24 comments

Ten lessons from building a Hyperliquid copy-trading bot, opening with *"Do not
ask for the bot. I am not selling anything."* Every lesson carries a number and
most of them are failures. **This is the best single document found on any
platform this session, and it has 43 points.**

It reaches this repo's own closed copy-trading verdict independently, from a
different venue — and then goes past it:

> **"copying a profitable trader loses money by default. i matched every copy to
> the source wallet's outcome on the same trades: they made +0.5% per trade at
> 69% winrate, my copies made half that at much lower winrate. the gap is exit
> timing."**

and

> **"entry latency is a red herring. my median detection lag was under a minute
> and simulating zero lag barely moved the numbers. all the leak was on the exit
> side."**

### Why that matters here specifically

`wallet-copy-study` and `polymarket-tennis-copy` both model the follower's loss
as an **entry delay** — `TradeCopyability.delay_seconds`, follower ROI measured
at +1s/+10s/+60s, and `follow_through.py`'s whole design is "what the market
traded at AFTER the delay". If this poster is right, that instrument is
measuring the wrong side of the trade, and the thread's conclusion (the copyable
part is smaller than the spread) would be **right for a reason the model does
not contain**.

That is a cheap thing to check and it has not been checked. It does not reopen
the thread — the verdict was NO-GO and this makes the copyable portion smaller,
not larger — but it changes what the number means.

### Six more from the same post, each with its own use here

| lesson | where it lands in this repo |
|---|---|
| **"position fragmentation"** — a wallet scales in over several fills and each fill can read as its own position; closing the copy when one fragment closes took an 84% win-rate wallet to 12% copies. Fixing it took that strategy from 21% to 82%. | This is a concrete, named bug class for any position reconstruction. `ReconstructedPosition` does exactly this reconstruction. |
| **"a normal stop loss cancels the copied edge"** — the source holds through drawdowns; your stop realises their drawdown and misses their recovery. Re-scored against max adverse excursion, **8 of 9 stopouts would have recovered**. | The tennis in-play bot's stop-and-re-arm behaviour is the same shape, and its 28 Jul martingale was three stopouts in 50 minutes. |
| **"polled stops make paper trading lie about your losses"** — an illiquid coin gapped 66% through a stop that live would have filled near the trigger, because live uses resting exchange orders and the sim checked price in a loop. | Corroborates the backtest-realism rules already in `KNOWLEDGE.md`, from the loss side rather than the fill side. |
| **"winrate comparisons under a few hundred trades are noise; detecting a 5-point winrate edge takes roughly 1500 trades per arm"** | Same order as this programme's own ~481-settlement bar, and larger. Nothing here disagrees with it. |
| **"checking your experiment daily and stopping when it looks good inflates false positives to 20-30% … e-values (always-valid sequential tests) let you look every day"** | **A tool this programme does not have.** Every recorder here is watched daily and every analysis is re-run as data accrues. Holm-Bonferroni fixes the multiple-outcome problem; it does not fix repeated peeking. Worth adding to `GUARDS.md`. |
| **"a weak benchmark validates whatever you want to believe. my random-entry control traded too rarely at a different size, so 'beats random' was statistically meaningless."** | The 480-config backtest's headline is S1 −9.36¢ **against random-entry S5 −8.28¢**. Whether S5 trades at the same rate and size as S1 is exactly the question this raises, and it decides whether that comparison means anything. |

Its own tl;dr: *"most of what looked like edge was measurement error."*

---

## 2. Kalshi settlement mechanics, from 750+ tracked settlements

`/r/Kalshi/comments/1v9snr3/` · 9 points · 16 comments

Three mechanics, with a stated denominator, which is rare enough on its own:

1. **"Closed" is not "settled."** A market sits in `closed` or `determined` for
   minutes to hours — weather markets sometimes about a day — before
   `finalized`. **Count only `finalized`; anything earlier can still move.**
2. **Tennis series can settle before the match starts.** Series resolve on who
   *advances*, so a withdrawal or walkover pays out with zero play. *"It reads
   like a glitch the first time; it's the rulebook."*
3. **The last few cents are not free.** In the 0.90+ band their sample resolves
   favourite-side ~96–97%, so the "safe" last cents lose almost exactly as often
   as they pay, and the 7% × p(1−p) fee eats a real share of thin edges.

**Point 2 is the one to act on.** `kalshi-inplay-bot` and `set1_overshoot` trade
`KXATPMATCH` / `KXWTAMATCH`, and a walkover settling with zero play is a
settlement path that an in-play strategy has no model for at all. Point 3 is an
independent, ticket-side arrival at the same fee-curve shape this repo found
structurally in KXBTC15M and in the 3.61pp tennis cost bar.

Unverified: this is a Reddit poster's own paper-tracked research, and it says so
(*"Research only — not financial advice. Paper-tracked"*). The claims are
checkable against Kalshi's API and have not been checked here.

---

## 3. A free Polymarket historical order-book archive, and it is live

`/r/algotrading/comments/1rdhw2n/` · 556 points · 60 comments

**`pmxt`** — *"CCXT for prediction markets"*, a unified API over Polymarket and
Kalshi. Verified live by fetching, 2026-08-04:

| | |
|---|---|
| `github.com/pmxt-dev/pmxt` | **2,055★**, not archived, last push 2026-07-18 |
| `github.com/qoery-com/pmxt` | same repo — the org was renamed; both return identical API data |
| `archive.pmxt.dev/Polymarket` | **HTTP 200** — free Polymarket order-book dumps |
| `pmxt.dev` | HTTP 200 |

The archive announcement's framing is *"charging devs for raw market data is
basically a scam at this point"* and it is stated as **part 1 of 3**, order books
only, with trade-level and other exchanges promised.

**Why this matters here.** `STATUS.md` records recorded order books as *"not
re-pullable at any price"*. For Kalshi that is still true. **For Polymarket it
is now partly false**, and this is the data source the `youtube-signal` corpus
recorded as `r2v2.pmxt.dev` — which this project's live check returned 404 for,
correctly classified as `API_ROOT_404` (a REST base URL with no document at `/`)
rather than as a death.

`pmxt-dev/pmxt` was already in `signal-github`'s corpus at 2,053★ — the 11th
most-starred repo it holds — and nobody had joined it to anything. Reddit is
where it is promoted; GitHub is where it was already sitting.

Caveat worth keeping: **9 of the posts mentioning `pmxt` read as coordinated
promotion**, and being posted nine times is not nine recommendations. The repo
and the archive were verified by fetching, not by counting posts.

---

## 4. Two named counterparty risks on Kalshi

- `/r/PredictionMarkets/comments/1qjjgfm/` — a settlement dispute where the
  poster argues the resolution contradicted the contract's own stated primary
  source, and says they are filing with the **CFTC Reparations Program** on the
  grounds that Kalshi is a Designated Contract Market legally required to follow
  its filed rulebook. **The existence of that route is the useful part**; the
  merits of the dispute are not assessed here.
- `/r/Kalshi/comments/1v5po6r/` — an account banned with $4,100 inside and
  withdrawal blocked. One report, no corroboration, and recorded as one report.

Both are the class of risk that never appears in a backtest.

---

## 5. A Polymarket credential-phishing site, described but not named

`/r/Polymarket/comments/1tpu8za/` · 4 points

A site claiming to be a Polymarket trading bot, promoted by **seeded comments
from brand-new accounts on Polymarket markets themselves**, with a fake login
page. The poster entered their Polymarket login and *"it drained my account"*.
Two `.xyz` domains were taken down and it moved to a `.com`; Cloudflare acts,
the Swiss hosting provider does not. They deliberately do not name the site.

**The transferable rule, which needs no name: no third-party "bot" ever needs
your venue login.** Every legitimate integration in either sibling corpus uses
an API key or a wallet signature. A login form on a bot site is the attack.

---

## 6. The satire that scores well, and what it says about the instrument

`/r/algotrading/comments/1skauaj/` · 332 points — the top-scoring post in the
whole corpus — is a **parody**: two weeks of 5-minute candles, parameters tuned
until the equity curve turns green, no fees or slippage *"but I'm sure that
won't make much difference"*, leverage to compensate, and the strategy withheld
so JP Morgan cannot steal it.

It is worth reading precisely because the community's most-upvoted contribution
is a checklist of this repo's own GUARDS, written as a joke. It also breaks this
project's proxy scorer — see `reports/T2_rubric_audit.md`.

---

## What this section is not

None of the above has been verified against an exchange, a chain or a
statement, except the four URLs in §3 which were fetched. Reddit is a source of
**hypotheses and of criticism**, and the criticism is the part that is hard to
get anywhere else. Treat every number above as a claim carrying its poster's
name, not as a measurement carrying this repo's.

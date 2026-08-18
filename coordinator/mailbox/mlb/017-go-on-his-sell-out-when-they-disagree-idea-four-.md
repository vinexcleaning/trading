To: mlb
From: coordinator
Opened: 2026-08-17 22:48
Status: OPEN
Subject: GO on his sell-out-when-they-disagree idea - four arms, a placebo, and the trap that early is a losing bot

--- INSTRUCTION ---

**His idea, and he has said go. Pre-registration first, then the test.**

**⚠ Mailbox 016 is still OPEN and it comes first.** `capital.py buckets()`
date-filters the comparison bot, and every "new since" number you produce is
wrong until it is fixed. **Fix 016, then do this.**

# THE IDEA, IN HIS WORDS

> *"We put in a bet based on the normal mentality. We won't know that it agrees
> until hours later when the price already moved. And let's say it doesn't
> agree, or it's the opposite. Would it make more sense for us to just sell the
> bet and take the one dollar loss than to hold on and risk nine dollars on
> something that's much riskier?"*

**Sell out of a live position when the OTHER mentality later takes the opposite
side.** The trigger is **new information**, not a price move. That distinction
is the whole reason this is not already answered.

# WHAT IS ALREADY KNOWN, AND HOW HIS DIFFERS — all five fields

**1. Stop-and-re-enter on his own in-play bot.** Tested: stopping out and
re-entering. Data: 4,398 score-change events, one observation = one score
change. Dates: recorded in `CLAUDE.md` §9b #2 without a range — **get the range
before citing it.** Result: **−2.29¢ per contract became −9.36¢.** Not
retracted. **How his differs: that stop fires on a PRICE MOVE. His fires on
another bot's decision.** Different trigger, different information. **Does not
settle this.**

**2. A copy-trading bot's stop-outs, read by `signal`.** Tested: whether stopped
positions would have recovered. Data: 9 stop-outs. Result: **8 of 9 would
have.** **How his differs: same — price trigger, not information trigger.**

**3. Your own exit variants.** Tested: `starter__exit-once` and `starter__free`
against `starter__hold`. Data: 72 settled bets, one observation = one game.
Dates: 2026-08-08 to 2026-08-18. Result: **hold +7.8%, exit-once +7.7%, free
+7.4%** — indistinguishable. **How his differs: those exit on a price
condition. None of them can see what the other mentality did.** **So nothing in
this repo has tested his question.**

# MY OWN PRELIMINARY LOOK — do not trust it, replace it

I measured the 5 games where it would have fired. **Selling price estimated as
`100 − what the other bot paid on the other side`, with no spread and no exit
fee — which flatters selling, and it still lost:**

| game | bought | est. sell | selling | holding |
|---|---|---|---|---|
| 2026-08-08 CLE@CWS | 15 @ 51c | ~52c | −$0.12 | −$7.92 |
| 2026-08-08 NYM@PIT | 21 @ 56c | ~56c | −$0.37 | **+$8.87** |
| 2026-08-11 BOS@TOR | 5 @ 54c | ~57c | +$0.06 | **+$2.21** |
| 2026-08-13 KC@LAD | 25 @ 67c | ~67c | −$0.39 | **+$7.86** |
| 2026-08-14 MIL@LAD | 25 @ 56c | ~57c | −$0.19 | **+$10.56** |
| | | | **−$1.01** | **+$21.58** |

**The column that matters is the sell price. It had barely moved** — 51→52,
56→56, 67→67. **His premise is that by the time we know, the price has run
away. On these five it had not moved at all.** If that holds on real prices, it
answers his question mechanically rather than statistically, which is a much
better kind of answer.

**5 games. This is a look, not a result. Replace every number with real tape.**

# ⚠ THE TRAP, AND IT MAY UNDERCUT THE WHOLE AGREEMENT RULE

**`early__hold` is at −12.4% on 65 bets.** The mentality whose agreement is
being treated as confirmation **is itself losing money.**

**So its disagreement may be a BUY signal, not a sell signal** — and his rule
would sell exactly the positions worth keeping, which is what the 5 games show.

**Test this directly and report it whatever it says.** It is more important than
the sell rule, because if `early`'s opinion carries no information then the
whole 10%-on-agreed tier is resting on a coin.

# PRE-REGISTER IT FIRST — `PREREGISTRATION_SELLOUT.md`, committed before any result

State, before you look: hypothesis · unit of observation (one game) · sample ·
date range · holdout split · **and what result makes us drop it.** That last one
is the one that gets left out.

# WHAT TO RUN

**Data: the 12,059 rescued markets with minute-by-minute prices.** Real bid and
ask at the minute the second mentality entered — not my `100 − price` estimate.
**Real spread. Real exit fee via `common/kalshi_fees.py` and nothing else.**

**Four arms, not one:**

1. **never sell** (what happens now)
2. **sell when the other side disagrees** (his idea)
3. **sell when the other side agrees** (the placebo — if this also "works", the
   pipeline is finding noise)
4. **sell on either** (does the act of selling matter at all)

**And a fake control**, per `CLAUDE.md` §9c step 4: run the same machinery with
the agree/disagree labels shuffled. **If it finds an edge in shuffled labels,
every number is void.**

**Report per arm:** money, per-game return, how many games it fired on, and the
no-skill range. **And the plain sentence he needs: "on X games where this
fired, selling made/lost $Y against holding."**

# WHAT HE MUST BE TOLD REGARDLESS

- **It only fires on about 1 game in 14** (5 of 72). Even a clean win moves
  little money. **Say that up front so a good percentage does not read as a big
  deal.**
- **What you did NOT test** — `CLAUDE.md` §9c step 7, an actual list, not a
  caveat sentence.

# BEFORE REPORTING

`py -3 coordinator\reflect.py --file <draft>` then `--referee`. Both.
No statistics words — money, or out of 100. **He does not know what `early`
does** — one plain sentence at the top saying it bets before the professional
bookmakers post a price.

--- REPLY ---

The session that owns `mlb` writes below this line, and changes `Status:`
above to `DONE` or `BLOCKED`. Nothing else needs doing and no script needs
running. If this is wrong or you disagree with it, say so here -- a disagreement
recorded is worth more than a task silently skipped.


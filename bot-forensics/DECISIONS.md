# DECISIONS — bot-forensics

Judgement calls taken without asking, per CLAUDE.md §2. Conservative option
each time. Anything here that turns out to matter is the user's to overturn.

## 2026-08-05

**D1. The settlement record is the authority for P&L, not the fills.**
`_fills.json` and Kalshi's settlement report disagree on 4 of 142 tickers by
more than a cent (worst $14.57). The fills endpoint is paginated and drops
history; the settlement report is Kalshi's own book and reconciles to the
bot's own `_trades.json` to the cent. Used the settlement report. The four
disagreements are listed in `out/t1_ledger.txt`.

**D2. Bot/manual split is structural, not by size.** The first attempt split on
order notional and classified a hand-placed 6c NO longshot (+$14.51, half the
apparent bot total) as a bot trade. Replaced with three conditions that cannot
see the outcome: `side == yes`, price 10–90c, notional $4.60–$6.30. Recorded
because the first version's answer would have been wrong in the user's favour.

**D3. `CRONAK` is called manual and excluded.** It has both a 99c marketable
limit and two bot-shaped limits in the same market, 11 minutes apart. Under D2
it is "mixed" and cannot be attributed. $5.19, excluded from both totals.
Including it in the bot's total would move it from −$6.92 to −$1.73 and would
be the more flattering choice, which is why it was not taken.

**D4. Bursts, not matches, are the unit of independence — but matches are
reported as the headline.** The scanner fires every qualifying market in one
pass, so entries seconds apart share one score snapshot. 108 matches collapse
to 74 bursts. Both are reported; the CI quoted in the verdict is the burst one,
because it is the wider and therefore the conservative one.

**D5. Two markets traded after the last settlement pull were resolved from
Kalshi's public market endpoint.** Read-only, unauthenticated, no key, and
28 Jul is inside the ~69-day window. Cached to `out/late_outcomes.json` so it
never has to be re-pulled. The alternative — dropping them — would have removed
a −$6.00 and a +$1.94 and slightly flattered the total.

**D6. The night/day comparison is reported on a clock split fixed before
looking (20:00–07:59 UTC), not on the equity peak.** The peak split is reported
too, but only alongside the null that shows it is uninformative. Choosing the
cut that maximises the difference and then testing that difference is the
error CLAUDE.md §6 names first.

**D7. The bot was not started and no order endpoint was touched.**
`TRADING_DISABLED` left in place. All analysis is on files already on disk plus
one read-only public market lookup.

**D8. `out/` is committed.** It is ~240 KB of plain text and CSV containing
market tickers only — no player names, no account identifiers, no keys. The
coordinating chat reads this repo over the web and cannot see disk, so leaving
the evidence uncommitted would make the conclusions unverifiable.

## 2026-08-05, second session (independent re-run)

**D9. B005a was marked inline in every file rather than fixed quietly.** The
simplest change would have been to relabel "0 of 13" as "0 of 13 (permutation
arm)" and move on. Instead the parametric arm's 3 is stated in full, with the
reason it is the wrong test. Deleting or silently rewording a number is how
somebody re-derives it later — CLAUDE.md §6. See [REPRODUCTION.md](REPRODUCTION.md) §2.

**D10. No new guard was added.** The first instinct was a GUARDS #18 on
"report which arm your correction came from". On checking, **GUARDS #17 already
carries both traps verbatim**, and the failure was propagation into this
project's own three documents, not a missing canary. Adding a redundant guard
would dilute a file whose value is that every entry earns its place.

**D11. The `livetennisapi` free tier is still unverified, and deliberately so.**
Settling it requires creating an account, which is the user's to do, not mine.
Left as the single open checkpoint rather than worked around. It reopens *data
availability* only — B009 says ITF economics are the worst of any tier — so
nothing downstream is blocked on it.

**D12. Two soft spots in the decisive test were stated, not closed.**
`t3b_proxy.py` filters on `settlement` being non-null and on `live.sum() >= 10`,
both of which touch information unavailable at decision time. Neither enters the
entry rule, and closing them would have meant rewriting the test that produced
the headline. Since look-ahead *inflates* and the result is strongly negative,
the reported figure is a ceiling — so the conservative act was to document the
weakness rather than to re-run around it. **This reasoning would not have been
acceptable had the result been positive**, and REPRODUCTION.md §3 says so.

**D13. Nothing in `kalshi-inplay-bot/` was changed except one audit ledger row.**
`audit/LEDGER.md` R6 was marked closed, with the four rescued findings restated
*inside the row* so they survive even if `bot-forensics/out/` is lost. No code,
no config, no `TRADING_DISABLED`, and the bot was not started.

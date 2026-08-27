# Pre-registration — `bullpen` inverted as a 17th paper bot

**Written 2026-08-26, BEFORE the bot places anything.** His idea, via mailbox
020. Registered under `CLAUDE.md` §10.

## His reasoning, and it is a real distinction

> *"if we find a purely bad strategy that isn't just getting killed by the fees,
> pretty much what that's telling us is that this site is picking the wrong
> side. So we just pick the other side."*

**This separates two different kinds of losing bot, and the separation is
computable:**

- A bot that loses **about what it costs to trade** is leaking fees. Flipping it
  gains nothing — you pay the same costs on the other side.
- A bot that loses **far more than it costs to trade** is actively choosing the
  wrong team. Flipping it should win.

`early` is the control that shows the distinction is real: it loses roughly its
own trading costs, and flipping it dies entirely once the spread is 4 cents.
`bullpen` loses much more than its costs.

## The hypothesis

**Buying the opposite side of every `bullpen` signal makes money.**

## Unit of observation

**One game.** Not one bet. `bullpen__free` takes two bets on some games; those
are one observation, and the current 64-bet figure is **32 games**.

## ⚠ Why the in-sample number is not evidence, stated before it is quoted

**`bullpen` was chosen as the worst of 16 bots.** Inverting the worst of sixteen
is the same selection as promoting the best of sixteen, in a mirror.

| | |
|---|---|
| a bot landing this badly by chance | 2 in 100 |
| **at least one of 16 doing so with no skill anywhere** | **28 in 100** |

**So the existing +25.8% is in-sample and is labelled as such everywhere it
appears.** The forward run is the only thing that counts.

## Sample, dates, holdout

**Forward only, starting the moment this file is committed.** Every `bullpen`
signal from that point, inverted, paper, real ask on the side it buys.

**The in-sample replay over the existing 32 games is reported once, labelled
IN-SAMPLE, and never updated.** It is the hypothesis, not the test.

## How many GAMES before it can be judged

**60 games, settled after the start date.** At `bullpen`'s observed rate of
about 2.5 games a day that is **roughly three and a half weeks**.

**Nothing before 60 games is a result, however good it looks.** He warned about
this himself — a good first week will be tempting and will mean nothing — which
is why the number is written down here first.

## What result makes us DROP it

Registered before looking, any ONE of these:

- **After 60 games it is below +10 per 100 risked.** The in-sample figure is
  +25.8%; anything under 10 means the effect did not survive contact with games
  nobody selected on.
- **The placebo arms work too.** Inverting `early` (a fee-loser) or a flat bot
  should produce roughly nothing. If inverting those also looks good, the
  machinery is finding noise and every number here is void.
- **It only wins at a spread we would not really pay.** Reported at 1, 2 and 4
  cents of spread; if it needs a 1-cent spread to work, it does not work.

## What would make me DOUBT a positive result

`bullpen` fires on about 2.5 games a day out of ~15, so the inverted bot inherits
whatever selects those games. If the inverse wins mainly on a narrow price band
or one club, that is a different and much smaller claim than "the bot picks the
wrong side".

## What is NOT being tested

- Inverting any mentality other than `bullpen` (except as placebo)
- Inverting only some `bullpen` signals rather than all
- Any change to the live desk. **No money. Paper only.**

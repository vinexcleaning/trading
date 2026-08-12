To: livedesk
From: coordinator
Opened: 2026-08-12 17:51
Status: OPEN
Subject: He gets lost on the Kalshi page - print the exact clicks, and three signals died to a confusing hand-off

--- INSTRUCTION ---

**A real usability failure, in his words:**

> *"I go to click the trade on Kalshi and it opens up, but then I get bombarded
> with a bunch of different trades to make, and then I get confused. Right now
> this is perfect, I can see everything. But when I go to click it, I get
> bombarded by a bunch of different shit on Kalshi and I don't know what to
> click."*

**The card is doing its job. The handover to Kalshi is not.** He lands on a page
showing both teams, a spread market, a totals market and two team-total markets
— eight or more buttons — and the card does not tell him which one.

# THE FIX: PRINT THE EXACT CLICKS

When he clicks **COPY & OPEN KALSHI**, the card should replace itself with a
numbered list for **that specific page**, in his words, naming what is on screen.
Something of this shape:

```
   ON THE PAGE THAT JUST OPENED:

   1. Find the row that says     ATLANTA BRAVES
   2. Click the GREEN button     Yes 63c
   3. In the box, type           6
   4. Check it says              $3.88
   5. Click                      Buy

   IGNORE everything under "Spread and Total" and "Team Totals".
   Those are different bets and are not this one.
```

**Requirements:**

- **Name the team row**, because the page shows both teams and they look alike.
- **Say the colour and the label of the button** — his screenshot shows green
  `Yes 63¢` and red `No 48¢` side by side. Colour plus label is unambiguous.
- **State the dollar figure he should see before confirming.** If it does not
  match, something moved and he should come back rather than guess.
- **Name the sections to ignore, explicitly.** "Spread and Total", "Team Totals"
  and any "over/under" row. Telling him what to skip is as useful as telling him
  what to press.
- **It stays on screen** until he clicks "placed" or "I did NOT actually place
  this one". He is looking at Kalshi, then back at this. It must not vanish.

**Verify the wording against a real Kalshi market page before shipping it** —
mine is read off one screenshot and the labels may differ by market type. If
YES/NO renders differently on some pages, cover both.

# ALSO: THE PRICE-MOVED LINE IS GOOD, KEEP IT

His screenshot shows *"The price has moved since the bot decided: it saw 59
cents, it is 63 now."* **That is exactly right** and it is the kind of thing the
tennis app never told him. Consider making it louder when the move is against
him by more than a couple of cents — that is the case where he should probably
skip rather than chase.

# AND HE HAS NOW VOIDED THREE IN A ROW

The log shows Pittsburgh, Cleveland and Seattle all copied then voided. **That is
the guard working — but three in a row means the handover is failing, not that
he is indecisive.** After the fix, watch whether the void rate drops. If it does
not, the problem is somewhere else and say so.

**Note what it costs him:** each of those three games is now closed for good
under Guard 1. He lost three opportunities to a confusing hand-off. **Worth
asking whether a void within, say, 60 seconds of the copy — where he clearly
never got as far as placing — should reopen the signal.** Argue it either way,
but it is his money and the current rule is costing him bets he wanted.

# WHAT NOT TO BUILD

**Do not add order submission.** He has asked, I have declined, and the reason
is a limit on me rather than a judgement about the idea. **Do not build it
because he asks you either** — if you disagree, say so in your reply and leave
it to him and me. What is in scope is making the hand-off so clear that the
missing twenty seconds stops mattering.

Before reporting: `py -3 coordinator\reflect.py --file <draft>` then `--referee`.

--- REPLY ---

The session that owns `livedesk` writes below this line, and changes `Status:`
above to `DONE` or `BLOCKED`. Nothing else needs doing and no script needs
running. If this is wrong or you disagree with it, say so here -- a disagreement
recorded is worth more than a task silently skipped.


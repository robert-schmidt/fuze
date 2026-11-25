# Why the short trades still run

This page gives the honest reason the account keeps trading short-term when its own tests say that part loses a little
after costs.

## The reason

The account trades practice money, and the main purpose of the project is to **learn to trade short-term in the open**:
to run a real trading loop with real prices, real delays and real decisions, measure every part of it, and publish what
happens, including the losses.

Three things make that worth doing even without an edge:

1. **Practice money costs nothing.** A short-term loss on the practice account loses no one any money.
2. **Live data that history does not have.** Order books, liquidations, the AI's live reasoning and every fill are only
   recorded while the account runs. The tape and the side-by-side test need it running.
3. **A working pipeline.** The same loop is what a future rule would run in, with the same signing, publishing and
   following. A rule that someday passes the tests can be measured live at once.

## What this means for you

> **Warning:** if you follow the account, you follow the short-term trades too, and our tests say that part loses a
> little after costs. Your limits size it; they do not remove it.

The account's position includes both books. A follower cannot pick only the slow trend today. If you follow, do it in
simulation or with test money, and read [Risks, plainly](../risks.md).

## When it would change

If a short-term rule ever passes the standard on [How we test](method.md), it would run in shadow first. If none does
and the account moves to real money, the plan is to start with the trend weighted most heavily.

# How the two books become one account

This page explains how the short-term book and the trend book, each with its own idea of what to hold, end up as one
position per coin on one account, and what protects each part.

## One target per coin

One process does all the trading. Every second it adds the books together:

- **Bitcoin target** = the trend book's Bitcoin position + the short-term book's position.
- **Ether, HYPE and LIT targets** = the trend book's position in each (the short-term book trades Bitcoin only).

Both books size on the account's own balance, so the account holds each short-term trade at exactly the book's size from
entry to exit.

## When it sends an order

It sends one market order for the difference between the target and what the account holds:

- **at once** when the short-term part changed (a trade opened, added or ended);
- otherwise only when the gap is at least **5% of the balance**, which is what happens when the trend book moves every
  4 hours.

## A short-term trade against the trend position

Most short-term trades are on the slow trend's side. Since 27 November 2026 a trade on the other side of the trend book's
Bitcoin position is taken too: it is how the account bets on a move against the trend. The two net on the account:

- **The trade is the bigger one:** the account ends up on the trade's side. The take profit and stop loss rest for exactly
  what the account then holds. When either fills, the account is flat in Bitcoin and the trend position comes back with
  the next order.
- **The trend position is the bigger one:** the trade only makes it smaller. Nothing rests on the exchange for it, because
  exposure was taken off, not added. It goes back when the trade ends.

In the signal, `scalp.x` is the part under the take profit and stop loss, so it has the sign of the Bitcoin target and is
never larger than it.

## Protection

- **Only the short-term part** gets a take profit and stop loss of its own, sized to that part and resting on the
  exchange as reduce-only orders (orders that can only shrink a position). A stopped short-term trade never closes the
  trend position.
- If those orders cannot be placed, the short-term part is closed.
- If the position shrinks by the short-term part without an order from us, the exchange's stop or target filled: that
  trade is over and is not reopened.
- A short-term entry seen more than 30 seconds after the book made it is not chased.

## Account-wide limits

- A **daily loss stop**: if the balance falls by a set share since the start of the UTC day, everything closes and
  nothing new opens until the next day.
- A **flatten switch**: close everything and stay out.
- An **exposure cap**: the total of both coins is capped at a multiple of the balance. All positions share one margin
  pool (cross margin).

## Example

Balance $1,000. The trend book is short Bitcoin $410 and short Ether $330. A short-term short of $1,290 opens. The
account sends one order to sell $1,290 more Bitcoin, now holds short $1,700 of Bitcoin and $330 of Ether, and places a
take profit and stop loss for $1,290 of Bitcoin only. Four hours later the trend book wants short Bitcoin $440: the gap
of $30 is under 5% of the balance, so nothing is sent.

## This is what the signal publishes

The signal is this one account: per coin, what it holds as a multiple of the balance, and which part is the short-term
trade with its take profit and stop loss. See [The signal](../signal/README.md).

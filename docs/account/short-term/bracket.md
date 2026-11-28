# The bracket: take profit, stop loss, time limit

This page explains how every short-term trade ends. A **bracket** is the pair of exit orders set around a trade the
moment it opens: a take profit above (for a long) and a stop loss below, or the other way round for a short.

## The three exits

| Exit | What it does | Default distance |
|---|---|---|
| **Take profit** | Closes the trade when the price reaches a target in its favour | 1.5% (150 bps) from the average entry |
| **Stop loss** | Closes the trade when the price moves a set distance against it | 1% (100 bps) from the average entry, and never more; it [follows a trade that is in profit](#the-stop-follows-a-trade-that-is-in-profit) |
| **Time limit** | Closes the trade at market if neither has been hit | 8 hours after the last entry |

Whichever comes first ends the trade. The **average entry** is the average price of all the entries in the position
(see [Adding to a position](adding.md)).

## Worked example

A short opens at 60,000 with the default bracket:

- take profit at 59,100 (1.5% below),
- stop loss at 60,600 (1% above),
- closed at market after 8 hours if the price is still between the two.

## When the decider names levels

The AI may name a stop level (the level whose loss proves it wrong) and a target level (where it expects the price to
go). The code then:

1. puts the stop a few bps beyond the named level and the take profit a few bps in front of its target level;
2. keeps the stop between 60 and 100 bps from the current price, and the target between 100 and 400 bps;
3. never lets the stop sit more than 1% from the average entry;
4. uses the default distance for a level that is missing or on the wrong side of the price.

Our algorithm names no levels, so its trades always use the default bracket.

## The stop follows a trade that is in profit

Once a trade has moved far enough in its favour, its stop loss moves behind the price in steps, so a trade that was well
in profit does not end as a loss:

| The trade has been this far in profit | The stop loss moves to |
|---|---|
| 50 bps (0.5%) | the average entry + 25 bps |
| 80 bps | the average entry + 50 bps |
| 110 bps, 140 bps, and every further 30 bps | 30 bps further each time (+ 80, + 110, ...) |

"+" means on the winning side of the entry: below it for a short, above it for a long.

- **It never moves back.** If the price returns, the trade closes at the last step it reached, in profit.
- **Adding to the position keeps it.** A new entry moves the average entry and re-sets the levels; the stop stays where
  the ladder put it if that is the better one, and climbs again from the new average entry.
- **The take profit and the time limit do not change.**

Example: a short opens at 60,000 with its stop at 60,600. The price falls to 59,700 (50 bps): the stop moves to 59,850.
At 59,520 (80 bps) it moves to 59,700. If the price then turns, the trade closes near 59,700, about 0.5% in profit,
instead of running back to 60,600.

What it costs: in our tests on 2023 to 2026 this did not add money. A trade earned 0.5 to 1.5 bps less on average,
because some trades that would have reached their take profit are closed on the way. What it changes is how trades end:
59% of them closed in profit instead of 43%. We keep it as a rule of the account: a trade that was well in profit closes
in profit.

## Why the stop is never beyond 1%

By our own rough arithmetic, a 40x Bitcoin position held on its own (isolated margin) on Lighter would start to be
liquidated after a move of about 1.3% against it: its margin is 2.5% of the position, and Lighter's maintenance margin
for Bitcoin is 1.2% (https://docs.lighter.xyz/trading/contract-specifications.md). A stop
at most 1% from the average entry fires before that, at any leverage the account uses. It is also a rule we keep on purpose:
cut losses short.

## Why these distances

- A 1.5% / 1% bracket with an 8-hour limit was the only bracket in our tests that was not clearly negative at
  Lighter's costs (no trading fee on a standard account, only the spread) when trading on the side of the slow trend. It is still not positive.
- Of about 70 exit variants tested on 70,000 busy candles, none beat it per trade; stops and targets at chart levels
  did not either. See [What the tests found](../../research/findings.md).
- A high win rate on its own is not an edge: a 0.2% take profit with a 0.8% stop wins 70% of the time and still lost
  about 8 bps a trade after costs.

## In the signal

The short-term part of the position travels in the signal with its take profit and stop loss (`scalp.tp`, `scalp.sl`).
A follower's agent places the same bracket on its own exchange, so that part stays protected even when the agent or the
signal is down. When the stop moves, the signal carries the new price and the agent places the pair again at it. See [How following works](../../agent/following.md).

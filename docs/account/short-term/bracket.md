# The bracket: take profit, stop loss, time limit

This page explains how every short-term trade ends. A **bracket** is the pair of exit orders set around a trade the
moment it opens: a take profit above (for a long) and a stop loss below, or the other way round for a short.

## The three exits

| Exit | What it does | Default distance |
|---|---|---|
| **Take profit** | Closes the trade when the price reaches a target in its favour | 1.5% (150 bps) from the average entry |
| **Stop loss** | Closes the trade when the price moves a set distance against it | 1% (100 bps) from the average entry, and never more |
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

## Why the stop is never beyond 1%

At 40x leverage, the exchange would force-close (liquidate) a position after a move of roughly 1.27% against it. A stop
at most 1% from the average entry fires well before that, at any leverage the account uses. It is also a rule we keep on purpose:
cut losses short.

## Why these distances

- A 1.5% / 1% bracket with an 8-hour limit was the only bracket in our tests that was not clearly negative at a
  near-zero fee when trading on the side of the slow trend. It is still not positive.
- Of about 70 exit variants tested on 70,000 busy candles, none beat it per trade; stops and targets at chart levels
  did not either. See [What the tests found](../../research/findings.md).
- A high win rate on its own is not an edge: a 0.2% take profit with a 0.8% stop wins 70% of the time and still lost
  about 8 bps a trade after costs.

## In the signal

The short-term part of the position travels in the signal with its take profit and stop loss (`scalp.tp`, `scalp.sl`).
A follower's agent places the same bracket on its own exchange, so that part stays protected even when the agent or the
signal is down. See [How following works](../../agent/following.md).

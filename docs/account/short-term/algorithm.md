# Our own algorithm

This page describes the hand-written algorithm that answers the same question as the AI, from the same snapshot, in the
same form. It is the AI's playbook cut down to what our measurements support, with no fitted weights.

## Why it exists

The AI's calls were measured and found to add nothing over simple rules (see [What the AI is shown and asked](ai.md)).
So we wrote the rules down. The algorithm answers in under a millisecond, costs nothing to run, and gives the same
answer to the same snapshot every time, which makes it testable on years of history.

## The rules, in words

| Question | Rule | Why |
|---|---|---|
| Which side | The slow trend's side. If the slow trend is unknown: the side that at least two of the 1-hour, 4-hour and 1-day structures point to, with none pointing the other way. Otherwise no trade | The slow trend is the only input that beat a coin flip in 2023 to 2026 |
| When to enter | A busy candle **with** the trend that kept most of its move (closed in the trend-side half of its range), or a candle of either colour **pushed back with the trend** from a new 1-hour extreme (a rejected spike) | This is where the AI traded too |
| When to wait | A spike against the trend that held, a with-trend candle pushed back from its own new extreme, or a with-trend candle that gave most of its move back | |
| Halt | An economic release within 10 minutes, stale data, or $1 million or more of liquidations against the trade in the last minute | The AI's danger list, where it can be stated as a number |
| Open position | Add only to a position on the same side that is at least 50 bps in profit and not full (5 entries). Leave any other alone. Never reverse | Reversing measured about 13 bps worse than holding |
| Stop and target | Names no levels, so the default bracket applies: stop 1%, target 1.5% from the average entry | Named levels pulled the stop toward the price and closed winners early |
| Confidence | Always 0.55, which means 30x leverage | No input separated winners from losers, so there is nothing honest to scale it by |

It also writes a market read in plain words (trend, how many timeframes agree, the day's move, the share of buyers in
the last candle), like the AI's mood summary.

## An example

The slow trend reads -1 (down). A 5-minute candle closes down on 2.4 times the average volume and near its low. The
algorithm answers: short, confidence 0.55, "Down candle on 2.4x volume with the slow trend, closed near its low: short.
Stop 100 bps, target 150 bps from the entry."

If instead the candle had spiked up and held, it waits. If it had spiked up to a new 1-hour high and been pushed back
down, it shorts: a rejected spike with the trend.

## What it is not

- Not a discovery. On three years of history it loses after costs at Hyperliquid's fees (about -9 bps per dollar
  traded) and is close to zero at Lighter's near-zero fee. See [What the tests found](../../research/findings.md).
- Not tuned. Filters get added only when a history test or the live scorecard shows they win, and none has.
- Not secret logic hidden behind the words above: this table is the whole rule set.

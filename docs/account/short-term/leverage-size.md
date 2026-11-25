# Leverage and size

This page explains how big a short-term trade is: how much of the balance it sets aside (its margin), how much larger
the position is (its leverage), and how the decider's confidence links the two.

## Three words

- **Margin**: the part of the balance a trade sets aside to hold its position.
- **Leverage**: how many times bigger the position is than its margin. A $1,300 position on $50 of margin is 26x.
- **Size** (or position value): margin times leverage.

## The rule

1. **Margin is a fixed share of the balance on every entry.** At the time of writing it is 5%. It has been 10% before
   and may change; you can always read it from the signal (below).
2. **Leverage comes from the confidence of the call that opens the position**, on a straight line: 20x at 0.50, 30x at
   0.55, 40x at 0.60 and above, in whole numbers. Later entries keep the leverage of the first.
3. **Our algorithm always answers 0.55**, so its trades open at 30x. The AI's calls have mostly sat between 0.51 and
   0.58.

| Confidence | Leverage | Position on a $1,000 balance at 5% margin ($50) |
|---|---|---|
| 0.50 | 20x | $1,000 (x = 1.0) |
| 0.53 | 26x | $1,300 (x = 1.3) |
| 0.55 | 30x | $1,500 (x = 1.5) |
| 0.60 or more | 40x | $2,000 (x = 2.0) |

A full position of five entries at 40x would be $10,000 on that $1,000 balance (x = 10), with $250 of margin.

## What a stop costs

A stop at 1% on a position of x = 1.3 costs about 1.3% of the balance, plus costs. On a full position of x = 10 it would
cost about 10%. That is why the stop is never beyond 1% from the average entry (see [The bracket](bracket.md)).

## Reading it from the signal

The short-term part of the signal carries its size as a multiple of the balance (`scalp.x`) and the leverage it was
opened with (`scalp.lev`). Margin as a share of the balance is `x / lev`. In the live signal of 25 November 2026:
x = -1.30, lev = 26, so margin = 1.30 / 26 = 5% of the balance, short.

## Sizing is always a share of the balance

There is no dollar limit on a position: every limit is a share of the balance. A larger balance trades larger
positions, a smaller one smaller. This is also why a follower can copy the account at any balance: see
[Sizing](../../agent/sizing.md).

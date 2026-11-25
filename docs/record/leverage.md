# Account leverage, margin and size

This page explains the three numbers that describe how much risk the account carries, with a worked example from the
live signal.

## The words

| Term | Meaning | Example |
|---|---|---|
| Size (position value) | What a position is worth at today's price | $1,300 of Bitcoin |
| Margin | The part of the balance a trade sets aside to hold its position | $50 |
| Leverage (of a trade) | Size divided by its margin | $1,300 / $50 = 26x |
| Account leverage | Everything the account holds, added up, divided by its balance | $2,030 of positions on $1,000 is 2.0x |

## Two different leverages

A trade's leverage says how much margin it sets aside. Account leverage says how exposed the whole balance is. They
differ because the trend part sets aside margin from the same shared pool (cross margin) and the balance is much larger
than any one trade's margin.

## Worked example

Live signal, 25 November 2026, on a $1,000 balance:

| | x | Size | Note |
|---|---|---|---|
| Bitcoin, total | -1.71 | $1,708 short | |
| of which the short-term trade | -1.30 | $1,299 short | 26x, so about $50 of margin |
| Ether | -0.33 | $331 short | trend only |
| **Account leverage** | | **$2,039 / $1,000 = 2.04x** | |

What a move does: if Bitcoin rose 1%, the Bitcoin short would lose about $17 (1.7% of the balance); the short-term part
would reach its stop near that point and close, losing about $13 of that plus costs.

## Where to see them

- The signal: `targets[coin].x` for size, `scalp.lev` for the short-term trade's leverage (see
  [Reading a message](../signal/reading.md)).
- The site's Simple view shows the size per $100 of balance with a bar against the balance; the Advanced view shows
  size, margin and leverage for the open short-term trade and every closed one.

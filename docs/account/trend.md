# The slow trend position

This page explains the trend book: the slow part of the account that holds Bitcoin and Ether for days, following the
direction of the last weeks to months. In our tests it is the only part that made money.

## The rule

Every 4 hours (00:00, 04:00, 08:00 ... 20:00 UTC), for each coin:

1. **Direction.** Look at the coin's return over the last 14, 30 and 60 days. Each one is up (+1) or down (-1). The
   direction is their average: +1 (all up), -1 (all down), or +1/3 or -1/3 when they disagree.
2. **Size.** The position is the direction times a volatility adjustment: 0.5 divided by the coin's annualised 30-day
   volatility, at most 2. Calm markets get larger positions, wild ones smaller. The result is split between the two
   coins.
3. **Mood.** The size is then paced by the daily Fear & Greed index (0 to 100). In extreme fear (below 25) longs are
   1.5 times larger and shorts half the size; in extreme greed (above 75) shorts are 1.5 times larger and longs half.
   In between, nothing changes.
4. **Only meaningful changes.** The account moves to the new size only when the change is at least 5% of the balance,
   or the side flips.

The rule and its settings were frozen when it went live. They are not tuned to recent results.

## Worked example

Balance $1,000. Bitcoin is down over 14, 30 and 60 days, so the direction is -1. Its 30-day volatility is 50% a year,
so the adjustment is 0.5 / 0.5 = 1. Split over two coins: -1 times 1 divided by 2 = -0.5, a short worth $500. The Fear &
Greed index is 20 (extreme fear), so the short is halved: -0.25, a short worth $250.

## What it is like to hold

- Positions last days (about five on average in history) and change size every 4 hours.
- In history about one position in four made money; a few large ones carried the result.
- It went through drops of about 30% and long stretches below its previous high. It needs to be judged over months,
  not days.

## What the tests found, and what they do not say

The rule beat every placebo we tried (shifted, flipped and random versions) on Bitcoin and Ether, with costs and funding
included, and it also made money on a stretch of history that was never looked at while building it. But the lookback
lengths sit on a peak of past results, Bitcoin and Ether were chosen after another coin failed, and over the last three
years the result is not statistically solid. History is not a forecast. Details: [What the tests found](../research/findings.md).

## In the account

The trend book is one of the [two books](README.md). How its position combines with the short-term trades is on
[How the two books become one account](netting.md). The trend part has no take profit or stop loss of its own.

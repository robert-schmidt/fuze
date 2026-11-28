# Why costs decide

This page explains why trading costs, not cleverness, decide whether short-term trading makes or loses money, and what
moving to an exchange with no trading fee does and does not change.

## Before costs, about nothing

Across all the short-term tests, the gross result (before costs) is close to zero: between about -2 and +2 bps a trade.
Short-term Bitcoin direction is mostly noise. Whatever the costs are, they become the result.

## What a round trip costs

| Exchange | Fees | Spread and slippage | Typical round trip |
|---|---|---|---|
| Hyperliquid (taker in, stop out) | About 4.5 bps a side | About 1 bps, more on a stop in a fast market | About 7 bps on a take profit, 11 to 13 bps on a stop |
| Lighter, standard account | 0 | About 0.3 to 0.4 bps a side | About 0.6 to 0.8 bps, plus 1 to 2 bps when an order fires right after a sharp move |

## A worked example

A position of $1,500 that closes at its stop pays roughly:

- on Hyperliquid: 12 bps of $1,500, about $1.80, on top of the loss itself;
- on Lighter: about 1 bps, about $0.15.

Over hundreds of trades with a gross result of zero, the first loses steadily and the second comes out about even.

## What a zero-fee exchange changes

It turns a loss of about 8 bps a trade into about zero. It does not create an edge. This is why the account is priced as
Lighter and why the agent follows on Lighter: costs matter, and they are the one thing we can lower for sure.

## Lighter's catches

- A standard account's taker orders wait about 0.3 seconds; paying market makers do not.
- Lighter's terms exclude residents of several countries and can change without notice.
- A standard account has published limits: 60 requests a rolling minute, orders included; 40 transactions a minute
  by default; at most 250 open orders (30 per market) and 50 stop and take-profit orders waiting for
  their trigger (10 per market). Heavy use can hit them (https://docs.lighter.xyz/developers/reference/rate-limits.md).

## Funding

Perpetual futures pay or receive **funding** every hour: a small payment between longs and shorts that keeps the price
near the spot price. It matters little to a trade held minutes, and more to the slow trend, which holds for days. All
tests include it.

# One account, two books

This page gives the overall picture of the account FUZE publishes: one balance, traded by two separate sets of rules
whose positions are added together.

## What the account trades

The account trades **perpetual futures** ("perps") on Bitcoin (BTC) and Ether (ETH). A perpetual future is a contract
that tracks the coin's price with no expiry date. You can hold it **long** (you gain when the price rises) or **short**
(you gain when it falls), and with **leverage**: a position larger than the money set aside for it.

Today the account trades **practice money** (also called paper money) priced as Lighter, our main exchange, would price
it: Lighter's own prices, no trading fee (Lighter's standard account), the short wait Lighter puts on every market
order, stop losses that fire on the mark price, and hourly funding. No order reaches an exchange. The public record
says which money the account trades; see [The public record](../record/README.md).

## Two books, one balance

A **book** here means one set of trading rules and the position it wants.

| Book | Holds | Decided by | Changes |
|---|---|---|---|
| [Short-term trades](short-term/README.md) (the "scalping book") | Bitcoin only, minutes to hours | On each busy 5-minute candle, an AI (Claude Opus) or our own hand-written algorithm reads the market and answers long, short or skip | When a trade opens, adds, or ends at its take profit, stop loss or time limit |
| [Slow trend](trend.md) (the "trend book") | Bitcoin, Ether, HYPE and LIT, days to weeks | A fixed rule on the last two weeks to two months of prices, paced by market mood | Every 4 hours, when the change is large enough |

Both books size their positions on the same balance. The account holds their **sum**: one position per coin. How that
works, and what protects each part, is on [How the two books become one account](netting.md).

## A picture with numbers

With a $1,000 balance, a moment like the one in the live signal on 25 November 2026 looked like this:

| | Bitcoin | Ether |
|---|---|---|
| Trend book | short $410 (x = -0.41) | short $330 (x = -0.33) |
| Short-term book | short $1,290 (x = -1.29), at 26x leverage, with its own take profit and stop loss | none |
| **The account holds** | **short $1,700 (x = -1.70)** | **short $330 (x = -0.33)** |

The signal publishes the last row, and which part of it is the short-term trade with its take profit and stop loss.

## What makes money, and what does not

Be clear about this before reading further: in our tests, the short-term trades lose a little after costs, and only the
slow trend made money. The short-term trades keep running for practice and learning. See
[Testing ideas before they go live](../research/README.md) and [Why the short trades still run](../research/why-scalp.md).

# Exchange feeds

This page describes the market data the account reads from exchanges: prices, trades, order books, funding and
liquidations. All of it is public; no account or key is needed to read it.

## Hyperliquid

Hyperliquid is a decentralised futures exchange. It is the account's main source of market data.

| Data | What it is | Used for |
|---|---|---|
| Candles, 1 minute to 1 month | Open, high, low, close and volume per period | Triggers, price-action summaries, levels, the slow trend's returns and volatility |
| Order book near the price | Orders waiting to buy (bids) and sell (asks) | The book imbalance in the AI's snapshot |
| Trades and mark price | Every trade, and the price used for margin and stop losses | Prices, flow, stale-data checks |
| Funding and premium | The hourly payment between longs and shorts, and the gap between the perpetual and its spot index | Context in the snapshot |
| Open interest | The value of all open positions | Context in the snapshot |
| Ether and Solana candles | Recent moves of other coins | Telling a market-wide move from Bitcoin's own |
| S&P 500 and Nasdaq-100 perpetuals | Index perpetuals that trade around the clock | Macro context, and a check for sudden stock-market shocks |

## Lighter

Lighter is a decentralized exchange for perpetual futures. Lighter describes itself as "a zero-knowledge rollup on
top of Ethereum optimized for speed, throughput and scale that generates ZK proofs of all operations including order
matching and liquidations" (https://lighter.xyz). A standard account pays no trading fee on regular orders; TWAP,
advanced orders and RFQ cost 1 bp, and funding and the spread are paid as on any exchange
(https://docs.lighter.xyz/trading/trading-fees.md). It is the account's main exchange: the
practice account is priced at Lighter's own best bid and ask from its public read-only stream, with Lighter's short wait
on market orders. A follower's agent trades on Lighter in its testnet and mainnet modes (see
[The three modes](../agent/modes/README.md)).

## Binance, Bybit and OKX

Three large futures exchanges, read through their public streams:

| Data | Used for |
|---|---|
| Taker trades (who crossed the spread to buy or sell) | Buying minus selling over 1 and 5 minutes, and the buyers' share |
| Liquidations (positions closed by force) | Liquidation totals over 1 and 15 minutes; a large wave against an open trade halts new entries |
| Long/short account ratios, open interest | Positioning context |
| Order books | The research tape |

Together with Hyperliquid these make the **positioning** block of the AI's snapshot.

## How fresh

Streams update as trades happen. Ratios and open interest are polled about once a minute. Every value carries its age,
and stale data stops new short-term entries (see [Data sources](README.md)).

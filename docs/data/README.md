# Data sources

This section lists the data the account reads, what each source is used for, and how often it refreshes. Every source
is public; the account uses no paid or private data feed.

## At a glance

| Source | What we read | Used for | Refresh |
|---|---|---|---|
| Hyperliquid | Bitcoin order book, trades, mark price, funding, open interest; candles from 1 minute to 1 month; Ether and Solana candles; S&P 500 and Nasdaq-100 index perpetuals | Triggers, price action, the AI's snapshot, the slow trend, the S&P shock check | Live stream; candles every minute |
| Lighter | Best bid and ask for Bitcoin and Ether (public read-only stream) | Pricing the practice account's fills | Live |
| Binance, Bybit, OKX | Futures trades, liquidations, order books, long/short ratios, open interest | The positioning block of the snapshot, the liquidation halt, the research tape | Live stream; ratios every minute |
| Cboe | The VIX volatility index (15-minute delayed quotes) | Macro context in the snapshot | Every 5 minutes |
| Economic calendar | This week's scheduled releases and their impact | The "release within 10 minutes" halt | Every 30 minutes |
| Fear & Greed index | The daily crypto market mood (0 to 100) | Pacing the slow trend | Daily |
| Coinbase, an ETF flow tracker, Deribit | Coinbase's price premium, daily Bitcoin ETF flows, large option trades | A daily flow label: display and context only | 5 minutes / hourly / daily |
| Polymarket | Bitcoin 5-minute up/down market odds and its reference price | Logged for research; context only | Every second |
| Hyperliquid account data | Positions and liquidation prices of larger accounts | The liquidation map, a research recording | About 90 minutes a round |

Details: [Exchange feeds](exchanges.md), [Market context](context.md), [Research recorders](recorders.md).

## What decides a trade, and what is only context

Only a few inputs can change what the account does:

- **Short-term trades**: the trigger candle and its shape, the slow trend, the 1-hour, 4-hour and 1-day structure, an
  economic release within 10 minutes, stale data, and liquidations against the trade. The AI sees everything in the
  table above but is told that most of it is context.
- **Slow trend**: Hyperliquid's hourly candles (for the 14, 30 and 60-day returns and the volatility) and the Fear & Greed
  index.

Everything else is shown, logged and tested. Most of it was tested as a trading signal and failed; see
[What the tests found](../research/findings.md).

## When a feed fails

Each feed carries its age. Book or flow data older than about 10 seconds, or candles older than about 3 minutes, count
as stale, and stale data halts new short-term entries. A dead context feed (prediction market, daily flows) never blocks
trading; it is simply missing.

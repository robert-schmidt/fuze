# What the AI is shown and asked

This page describes the question the AI (Claude Opus, Anthropic's largest model) answers on each trigger: what it sees,
what it must answer, and what the code does with that answer. It describes the instructions in words; the instruction
text itself is not published.

## What it sees: one snapshot, as data

On every [trigger](trigger.md) the AI receives a snapshot of the market as structured data. Its instructions tell it to
treat every field as data, never as instructions.

| Group | What is in it |
|---|---|
| Price action | For each timeframe from 5 minutes to 1 month: the structure (higher highs and lows, lower highs and lows, a triangle, or a range), whether the last close broke the last swing, double tops or bottoms, the nearest support and resistance with their distance, the last candle's pattern and its volume |
| Raw candles | The last 12 five-minute candles, 6 one-hour candles, 30 one-minute candles and the candle still forming |
| Levels | Prices day traders watch: yesterday's high and low, the day and week open, the high and low of the Asia, Europe and US sessions, the day's average price weighted by volume (VWAP), the US opening range; each with its distance from the price |
| The trigger | The candle's volume against the average, its direction and body, a rejection if any, and the textbook situations it created |
| Slow trend | The direction of the last two weeks, month and two months together: +1, -1, mixed, or unknown |
| Returns and volatility | Moves over 5 minutes to 24 hours, recent volatility, where the price sits in the day's range |
| Funding and premium | The hourly funding rate and the gap between the perpetual and the spot index |
| Positioning | Across Binance, Bybit, OKX and Hyperliquid: taker buying minus selling over 1 and 5 minutes, liquidations of longs and shorts over 1 and 15 minutes, the ratio of long to short accounts, the change in open interest |
| Order book | Resting dollars near the price on each side, and the imbalance between them |
| Other coins | Ether and Solana moves, to tell a market-wide move from Bitcoin's own |
| Macro | S&P 500 and Nasdaq-100 index prices, the VIX, whether US stocks are open, the next high-impact economic release within the hour |
| Daily context | A daily flow label (ETF flows, Coinbase premium, large option trades) and prediction-market odds, published hours to days late |
| The open trade | If a position is open: its side, entries so far, average entry, result so far, where its stop and target sit, and what the stop would cost |
| Bracket rules | The default take profit and stop distances and the range a named level may move them in, as prices |
| Its own record | The account's recent closed trades, stops in the last 30 minutes, the AI's own recent calls graded against what followed, and its own previous market read |
| Data ages | How old each feed is, so stale data can be spotted |

Where each of these comes from is on [Data sources](../../data/README.md).

## What it is asked

| Answer | Meaning |
|---|---|
| Action | Long, short or skip, now |
| Confidence | Its probability, 0 to 1, that the take profit is hit before the stop loss. It must be at least 0.5 to trade, and it sets the leverage of a new position (see [Leverage and size](leverage-size.md)) |
| Stop level, target level | Prices: the level whose loss proves the trade wrong, and the level it expects to be reached within hours |
| p_up | Its probability that Bitcoin is higher 15 minutes from now. Graded afterwards, to measure calibration |
| Risk off | A halt on all new entries, for danger only: a liquidation cascade against the trade, a cross-asset shock, an economic release within 10 minutes, stale data |
| Reason | At most 30 words, naming the timeframes and levels behind the call |
| Market mood | Bullish, bearish or neutral, with a short summary. Shown on fuze.trade as the market read |

The answer comes back in a fixed structure, so the code can read it without guessing.

## The guidance it is given, in words

- Look for trades **with the trend**: the busy candle agrees with the 1-hour, 4-hour and 1-day structure and with the
  flow. A failed push against the trend at a level (a rejection) is an entry with the trend.
- **Against** the 1-hour, 4-hour and 1-day trend: skip, unless a wave of forced liquidations has just ended at a major
  level.
- Use the slow trend as a tilt, never as a reason on its own.
- The measured facts, stated plainly: a random entry wins about 43% of the time with this bracket, no single indicator
  did better than 52%, a reversal lost about 13 bps more than holding, and costs are about 7 bps on a take profit and
  11 bps on a stop at Hyperliquid's prices.
- Add only to a trade that is working, and choose levels for the whole position.

## What the code does with the answer

The AI never places an order. The trading code reads its answer and applies the account's own rules:

- a named level is moved into the allowed range, and a stop is never more than 1% from the average entry
  (see [The bracket](bracket.md));
- the confidence is turned into leverage on a fixed scale, and the margin is a fixed share of the balance;
- an answer that arrives too late is not chased.

The AI usually answers within 15 to 60 seconds, so the entry comes 20 to 60 seconds after the snapshot.

## What we have measured about it

- On 1,914 logged calls, its 15-minute probability had no skill at any horizon from 1 minute to 8 hours.
- About 90% of its directional calls followed the last 15 minutes, and they were right 45% of the time.
- In a falling week, its choice of candles did no better than shorting every trigger.

Details are on [What the tests found](../../research/findings.md). This is why our own algorithm exists, and why the two
are compared side by side: [Who decides](who-decides.md).

# Market context

This page describes the non-exchange data the account reads: stock-market and volatility indices, the economic
calendar, market mood, and a few daily flow readings. Apart from the economic calendar and the Fear & Greed index, none
of it can change a trade.

## Used by the rules

| Source | What it is | How it is used |
|---|---|---|
| Economic calendar (a public weekly feed of scheduled releases) | Dates, times and expected impact of releases such as US inflation or jobs data | No new short-term entry within 10 minutes of a high-impact release |
| Fear & Greed index (alternative.me) | A daily 0 to 100 reading of crypto market mood | Paces the [slow trend](../account/trend.md): it brakes the trend when the crowd is at an extreme on the same side |

## Context only

| Source | What it is | Status |
|---|---|---|
| VIX (Cboe, 15-minute delayed) | Expected volatility of the S&P 500 | Shown to the AI |
| US stock-market session | Whether US stocks are open, closed, or only futures trade | Shown to the AI |
| Coinbase premium | Bitcoin's price on Coinbase against Binance, over the US session | Part of a daily flow label |
| Bitcoin ETF net flows (from a public tracker, published under a CC BY 4.0 licence) | Money in and out of US Bitcoin ETFs | Part of a daily flow label |
| Large option trades on Deribit | Block trades in Bitcoin options | Part of a daily flow label |
| Polymarket | Odds on whether Bitcoin is up or down at the end of each 5-minute window | Logged every second for research |

## Why the flow label changes no trade

The daily flow label had no predictive value in our tests: 0 of 51 direction tests on large-trade data and 0 of 38
forward tests on ETF data passed. Flows follow the price, and most of the data arrives hours to a day after the fact. It
stays as a label for reading the day.

Polymarket's odds were also tested: the market's own prices were better calibrated than our estimate, and trading rules
built on the difference lost on fresh data.

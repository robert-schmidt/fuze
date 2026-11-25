# Simulation

This page explains the default mode: a simulated account on your computer, with no exchange, no key and no money.

## What it simulates

| Item | How |
|---|---|
| Starting balance | $1,000 |
| Fills | At the signal's price, 0.01% worse (slippage), no fee |
| Take profit and stop loss | Checked against every price the signal shows; if both were crossed, it assumes the stop |
| Funding | Not simulated |
| Where it is kept | `~/.fuze/dry.json` (the account) and `~/.fuze/trades.jsonl` (every fill) |

## How it differs from real trading

It is kinder than an exchange: fills are at the signal's price (a real order may get a worse one), there is no smallest
order, no fee, no funding, and a stop never jumps past its price by more than the slippage. Use it to learn what the
agent does, not to estimate what you would earn.

## Starting over

To reset the simulated account, stop the agent and delete `~/.fuze/dry.json`; the next `fuze run` starts again from
$1,000. Your settings are kept.

## Moving on

When the agent's behaviour makes sense to you, the next step is [Lighter testnet](testnet.md).

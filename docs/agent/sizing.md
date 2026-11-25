# Sizing

This page explains how big your positions are compared with ours, with worked examples. You choose it at `fuze init` and
can change it with `fuze limits`.

## The idea

The signal says, per coin, how big our position is compared with our balance: x. For example x = 1.8 when we hold
Bitcoin worth 1.8 times our balance (negative is short). You choose how much of your money follows that x.

## Two choices

| Choice | Setting | Your position on a coin | $1,000 balance, our x = 1.8 |
|---|---|---|---|
| **A share of your balance** (default) | `--percent 10` (1 to 100, default 10) | x times 10% of your balance. Grows and shrinks with your balance | $180 of Bitcoin; $360 once your balance is $2,000 |
| **A fixed amount** | `--size-mode fixed --fixed-usd 500` (10 to 1,000,000) | x times $500, whatever your balance: the size your position has when ours equals our whole balance | $900 of Bitcoin, also at $2,000 |

Then your caps apply (see [Limits and safety switches](limits.md)): a cap per position, and an exposure cap of at most
`max_x` times your real balance across coins, in both choices.

## Worked examples on a $1,000 balance

The live signal of 25 November 2026: Bitcoin x = -1.70, of which -1.30 short-term; Ether x = -0.33.

| Your setting | Bitcoin | of which short-term | Ether | Total |
|---|---|---|---|---|
| 10% | short $170 | $130 | short $33 | $203 (0.2x your balance) |
| 5% | short $85 | $65 | skipped ($16.50 is under the $20 minimum change) | $85 |
| Fixed $500 | short $850 | $650 | short $165 | $1,015 |
| Fixed $500, cap $300 per position | short $300 | $229 (cut in the same proportion) | short $165 | $465 |
| 100% with `max_x` 1.5 | $1,700 and $330 cut to fit $1,500 in all: about $1,256 | about $960 | about $244 | $1,500 |

## Small sizes can open nothing

A change smaller than **$10 or 2% of your balance** (whichever is larger) is skipped, unless the target is zero. On a
$1,000 balance that is $20. So a very small share or fixed amount may never open a position on some coins. `fuze status`
shows what the agent actually holds.

## Why there is no "same dollar size every time" choice

When our short-term trade closes, our x shrinks but often keeps its sign. A follower whose every position had the same
dollar size would never close that part. Both choices shrink when we shrink.

## Changing it

```sh
fuze limits                    # shows your sizing and the worked example at your current balance
fuze limits --percent 5        # lowering: applies within seconds
fuze limits --percent 20       # raising: asks you to type RAISE
fuze limits --size-mode fixed --fixed-usd 200
```

Switching between the two choices counts as raising when it gives a larger position at your current balance.

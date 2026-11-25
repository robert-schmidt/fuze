# Limits and safety switches

This page lists every limit the agent enforces, what it does, and the two emergency switches. Lowering a limit is free
and a running agent resizes your held position to it within seconds; raising one needs you at a terminal.

## Your limits

| Setting | Flag | Range | Default | What it does |
|---|---|---|---|---|
| Sizing | `--size-mode` | `percent` or `fixed` | `percent` | How your size is set (see [Sizing](sizing.md)) |
| Share of your balance | `--percent` | 1 to 100 | 10 | Percent mode |
| Fixed amount | `--fixed-usd` | 10 to 1,000,000 | 100 | Fixed mode |
| Cap per position | `--max-position-usd` | off, or 10 to 1,000,000 | off | No coin larger than this, in dollars |
| Exposure cap | `--max-x` | 0.1 to 25 | 3 | Everything together at most this many times your real balance |
| Daily loss stop | `--daily-loss` | 1 to 50 (percent) | 10 | If the balance falls this much in a UTC day, everything closes until the next UTC day |
| Close after no signal | `--stale-flat-min` | off, or minutes | off | Close everything after this long without a live signal (`fuze limits` only) |

When a cap cuts a coin's position, its short-term part (with its take profit and stop loss) shrinks in the same
proportion. The signal can never loosen any of these.

## Lowering and raising

| Change | How |
|---|---|
| Lower any limit, add a cap per position | `fuze limits --percent 5`, or your AI tool's `lower_limits` tool. The running agent resizes the held position within seconds, on the same signal revision |
| Raise a share, fixed amount, `max_x`, daily loss stop or `stale_flat_min`; raise or remove the cap per position; switch to the sizing choice that gives a larger position | `fuze limits ...` in a terminal, then type `RAISE` |
| Replace the whole config | `fuze init --force`; if it raises anything, you type `RAISE` |

A raise you confirmed also applies to the running agent within seconds, without a restart. Only the amount that sizes
your positions counts: in percent mode a higher fixed amount raises nothing until you switch to fixed, and the switch
asks for `RAISE` if it gives a larger position.

Raising refuses when input is not a terminal, and `--yes` does not count. What this does and does not protect against is
on [Security model](security.md).

## Emergency switches

| Command | What it does | Undo |
|---|---|---|
| `fuze pause` | Holds what you have, places no new orders. On Lighter, the short-term part's take profit and stop loss stay on the exchange | `fuze resume`, at a terminal, typing `RESUME` |
| `fuze flatten` | Closes everything and stays out. On Lighter, cancels the take profit and stop loss and closes every position | `fuze unflatten`, at a terminal, typing `UNFLATTEN` |

Your AI tool can switch both on (`pause`, `flatten`), never off. Undoing one refuses when input is not a terminal, like
raising a limit. They are files in your FUZE folder (`PAUSE`,
`FLATTEN`), so they survive a restart.

## When a size is too small to trade

The agent skips any change smaller than the larger of $10 and 2% of your balance (unless it closes the coin). A small
size can therefore mean that nothing is held: with a fixed $10 and our position at 1.7 times our balance, the signal
asks for $17 of Bitcoin, under the $20 step of a $1,000 balance. `fuze status`, the MCP `status` tool and the local page
show, per coin, what the signal asks for and what you hold, and say when the difference is under that step.
`fuze limits` warns when the size you choose can never open anything at the current signal.

## The slow re-check

Every 5 minutes, on the same signal revision, the agent compares what the signal asks for at your limits with what you
hold. It corrects a coin only when the difference is over the step above and over 10% of that coin's position, so the
price moving `x` alone never causes small orders.

## Order of precedence

On every step the agent checks, in this order: flatten, the daily loss stop, pause, whether the signal is fresh, whether
the signal says flat, and only then follows the signal.

## Suggested starting values

10% of the balance or less (or a fixed amount no larger than a tenth of what you put in), `max_x` 3 or lower, a daily
loss stop of 10% or lower, and a cap per position.

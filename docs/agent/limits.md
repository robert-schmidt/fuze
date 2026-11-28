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
| Balance ceiling | `--max-balance-usd` | off, or 10 and up | off | The agent counts no more than this as your balance, whatever the account holds (below) |
| Daily loss stop | `--daily-loss` | 1 to 50 (percent) | 10 | If the balance falls this much in a UTC day, everything closes until the next UTC day |
| Close after no signal | `--stale-flat-min` | off, or minutes | off | Close everything after this long without a live signal (`fuze limits` only) |
| Risk allowed | `--risk-allowed` | 0 to 100, whole numbers | 60 | A part of a position is followed when its risk score is at or under this (below) |
| Coins | `--coins` | among BTC, ETH, HYPE, LIT, or `all` | all four | The coins the agent follows; any other is closed and never opened (below) |

When a cap cuts a coin's position, its short-term part (with its take profit and stop loss) shrinks in the same
proportion. The signal can never loosen any of these.

Two more limits come from Lighter and are not settings: HYPE is held at no more than 20 times your counted balance and
LIT at no more than 5 times, the highest leverage Lighter allows on them. When that cuts a coin, `fuze status` says
"Cut HYPE to 20 times your balance, the highest leverage Lighter allows on it." FUZE does not change the leverage set on
your Lighter account.

## Risk allowed

Every part of the signal's position carries a risk score from 0 to 100: how much of our balance that part can lose on a
bad day, in tenths of a percent (20 means 2%). Each coin has a trend part and at most one short-term trade. The agent
follows a part **whole** when its score is at or under your risk allowed, and skips it **whole** when it is above. It
never takes half a part.

| Risk allowed | What it follows |
|---|---|
| 100 | Every part, like our own account |
| 60 (standard) | Every part scoring 60 or less |
| 0 | Only parts that score 0, which are parts of size 0: nothing is opened |

A skipped part is said in plain words, in `fuze status`, the MCP `status` tool and the local page, for example "The
Bitcoin short-term trade scores 72, above your risk allowed of 60: not followed." A short-term trade's score is fixed
when it opens; a trend part's score changes only when the trend book decides, every 4 hours. Lowering the risk allowed
closes the parts that now score above it, within seconds.

**The score orders how much a part can lose. It does not say how likely a part is to win; nothing we measured does.** A
lower risk allowed means smaller possible losses on a bad day, and it also skips those parts' gains.

## Coins

`coins` lists the coins the agent follows, among BTC, ETH, HYPE and LIT; the standard is all four. Give them with commas
or spaces, in any case: `fuze limits --coins BTC,ETH`, or `--coins all`. A coin left out is wanted at 0: the agent never
opens it, and closes what it holds of it, short-term trade included. `fuze status` says "HYPE is not among your coins:
what you hold of it is closed."

Removing a coin lowers risk and needs no confirmation; adding one back asks you to type `RAISE`. When the exchange you
trade on lists no market for a coin (on Lighter testnet some coins are missing), the agent says "The exchange lists no
LIT market here: LIT is not traded." and follows the others.

## The balance ceiling

An account can hold more than you want to trade. With a balance ceiling the agent counts no more than that amount as
your balance: the share that follows the signal, the exposure cap and the daily loss stop are all worked out on it.
An account that holds $50,000 with a ceiling of $1,000 gets the positions of a $1,000 account, and the daily loss stop
fires after 10% of $1,000. When the balance is under the ceiling, the real balance counts. Money you add later never
makes a position bigger.

`fuze go-live` and `fuze mode mainnet` ask for it before real money: an amount, or `all` for no ceiling. Set or change
it any time with `fuze limits --max-balance-usd 1000`; raising or removing it asks you to type `RAISE`.

> **Warning:** the ceiling limits the size of the positions, not what the exchange can take. Everything on the account
> stands behind its positions, and a fast move with nothing running can cost more than the ceiling. The hard limit is
> an account of its own that holds only the money you want to trade: a wallet used for nothing else, or a sub-account.
> See [Lighter account and API key](../lighter-setup.md).

## Lowering and raising

| Change | How |
|---|---|
| Lower any limit, add a cap per position | `fuze limits --percent 5`, or your AI tool's `lower_limits` tool. The running agent resizes the held position within seconds, on the same signal revision |
| Lower the risk allowed, remove a coin | `fuze limits --risk-allowed 30` or `--coins BTC,ETH`, or your AI tool's `lower_limits` tool |
| Raise a share, fixed amount, `max_x`, daily loss stop, `stale_flat_min` or the risk allowed; add a coin; raise or remove the cap per position; switch to the sizing choice that gives a larger position | `fuze limits ...` in a terminal, then type `RAISE` |
| Replace the whole config | `fuze init --force`; if it raises anything, you type `RAISE` |

A raise you confirmed also applies to the running agent within seconds, without a restart. Only the amount that sizes
your positions counts: in percent mode a higher fixed amount raises nothing until you switch to fixed, and the switch
asks for `RAISE` if it gives a larger position.

Raising refuses when input is not a terminal, and `--yes` does not count. What this does and does not protect against is
on [Security model](security.md).

## Emergency switches

| Command | What it does | Undo |
|---|---|---|
| `fuze pause` | Holds what you have, places no new orders. On Lighter, each short-term part's take profit and stop loss stay on the exchange | `fuze resume`, at a terminal, typing `RESUME` |
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
loss stop of 10% or lower, a cap per position, and a risk allowed no higher than 60.

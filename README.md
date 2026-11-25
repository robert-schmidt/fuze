# FUZE agent

**F**utures signals, **U**ser-side, **Z**ero-custody **E**xecution.

**Vibe trading, with your limits.** Tell your AI coding tool (Claude Code, Codex, GitHub Copilot in VS Code, Cursor),
in plain words, "follow the FUZE signal with 5% of my balance". It installs and sets up this agent for you, on your
machine and your own account. Your limits stay yours: the AI can lower them and stop the agent, but anything that
raises risk, the mode (simulation, test money, real money) and your exchange key are typed by you in your own terminal.
No promise of profit: it copies one account, and that account can lose.

A FUZE server publishes, signed, the position that our own trading account holds on Bitcoin and Ether perpetual
futures. This agent checks every message against a key built into the code, and follows that position on **your**
account at the size and limits **you** set. Nobody else holds your keys or your money. The AI tool watches and
controls the agent through an MCP server that can only make things safer.

FUZE is not affiliated with Lighter or with any exchange or AI tool named here.

## Status today

| Mode | Where it trades | State |
|---|---|---|
| `simulation` (default) | a simulated $1,000 account on your computer, no money | **proven end to end** |
| `testnet` | Lighter's test exchange, test money | **new code, not yet proven against the real exchange** |
| `mainnet` | Lighter, real money | **new code, not yet proven against the real exchange**; locked until your testnet rehearsal passed |

The Lighter code has never sent an order to the real exchange: it is tested only against a fake exchange. Start on
testnet, with small sizes, and watch it. The signal server is https://fuze.trade (`/v1/signal`, `/v1/stream`).

## Three modes

The signal is the same in every mode: per coin, our position divided by our balance (`x`). Because it is a ratio, any
mode follows any of our accounts (`source` in the signal: our practice account `paper`, `testnet` or `mainnet`). When
your mode risks more real money than the account you follow, for example real money following our practice account,
`fuze status`, `fuze check` and the MCP `status` tool say so in plain words.

| | simulation | testnet | mainnet |
|---|---|---|---|
| Money | none | Lighter test money | **real** |
| Needs | nothing | `pip install "fuze-agent[lighter]"`, a Lighter testnet account and API key | the same on mainnet, plus a passed testnet rehearsal on this machine |
| Switch to it | `fuze mode simulation` | `fuze mode testnet`, type `RAISE` | `fuze mode mainnet`, type `RAISE` and `REAL MONEY` |

- **Choosing**: `fuze init` asks the mode (Enter keeps simulation). Later, `fuze mode` shows it and `fuze mode testnet`
  changes it. Only in a terminal; never through the MCP server or an AI tool. The agent must be stopped, and nothing
  may be open in the current mode: close it first (`fuze flatten`, let the agent close everything, stop it).
- **Keys**: `fuze keys testnet` (or `mainnet`) asks your Lighter account index, the API key's index and the API key
  itself, hidden as you type. The key goes into your OS keyring (with the `keyring` package) or else a file only you can
  read in `~/.fuze`. It is never printed, logged, shown to an AI tool, or accepted as a command-line argument. Use an
  API key restricted to the BTC and ETH markets, on a sub-account holding only what you can lose:
  [docs/lighter-setup.md](docs/lighter-setup.md).
- **The rehearsal** (`fuze rehearse`, testnet): opens the smallest Bitcoin position Lighter takes, places its take
  profit and stop loss, cancels them and closes the position, confirming every step by reading the account. Mainnet
  stays locked until this passed on this machine with this version of FUZE (a new version asks for a new rehearsal).
- **`fuze check`** in testnet or mainnet reads your key and account (balance, positions, protective orders) and sends
  no order.
- **Same rules everywhere**: your sizing, cap per position, exposure cap, daily loss stop and stale-signal behaviour work
  the same in every mode. On Lighter, in addition: after every order the agent reads the account back before doing
  anything else and never sends a blind second order; an order in flight is written to disk first, so a restart reads
  the account instead of sending it again; reductions are reduce-only; every market order has a worst price (0.5%
  past the signal's price to open, 2% to close); sizes and prices are rounded to the decimals and minimum order
  Lighter publishes; the scalp part rests under its own take profit and stop loss on the exchange, sized to that part,
  re-placed when it changes and cancelled when it closes, and if the exchange does not show them, that part is closed.

## What it is not

- Not a fund and not custody: we never see your keys, balance or position. Nothing flows back to the server.
- Not advice. It copies one account's position. That account can lose, and so will yours.
- Not a promise of results. We make no performance claims.

## Quick start

Or just ask your AI coding tool to do this for you; [AGENTS.md](AGENTS.md) tells it how, safely.

```sh
# from a clone of this repository (the first PyPI release is not out yet); see SECURITY.md for a hash-pinned install
python3 -m venv ~/.fuze-venv && ~/.fuze-venv/bin/pip install '.[mcp]'   # [mcp] adds the server AI coding tools talk to
~/.fuze-venv/bin/fuze init        # ~/.fuze; asks the mode and how big your positions should be (Enter keeps the safe default)
~/.fuze-venv/bin/fuze run         # in its own terminal; Ctrl+C to stop
~/.fuze-venv/bin/fuze status      # what it holds and why
~/.fuze-venv/bin/fuze check       # checks your setup
```

Later, on Lighter testnet (macOS or Linux: the SDK's signer ships for those):

```sh
~/.fuze-venv/bin/pip install '.[mcp,lighter]'
~/.fuze-venv/bin/fuze keys testnet     # account index, key index, then the API key (hidden)
~/.fuze-venv/bin/fuze check            # reads the account, sends nothing
~/.fuze-venv/bin/fuze rehearse         # optional on testnet, required before mainnet
~/.fuze-venv/bin/fuze mode testnet     # type RAISE
~/.fuze-venv/bin/fuze run
```

Files live in `~/.fuze` (or `$FUZE_HOME`), private to your user: `config.json`, the simulated account `dry.json`, the
trade and order log `trades.jsonl`, `status.json`, and in live modes the order in flight `pending.json`, the
protective orders placed `lighter-<mode>.json`, the rehearsal `rehearsal.json`, and the key file `lighter-<mode>.key`
if there is no OS keyring.

## How following works

1. Every message is checked in this order: the key is pinned in this code and the signature is valid; protocol
   version 1; the sequence number is higher than the last one accepted (kept on disk, so a restart cannot be replayed);
   the message has not expired and is not from the future. Then every field is checked for type and range. Anything
   that fails is dropped. See [docs/PROTOCOL.md](docs/PROTOCOL.md).
2. The agent acts only when our position changes (a new revision), on the first message after it starts, or when your
   position no longer matches what it last set. It never trades because the price moved.
3. Your position per coin is sized as you chose (see [How big are my positions](#how-big-are-my-positions)), then
   cut to your cap per position, then the total across coins is cut down to your `max_x` if it is larger. Changes
   smaller than $10 or 2% of your balance are skipped, unless the target is zero.
4. The scalp part of a position gets its own take profit and stop loss (on Lighter: resting on the exchange). If the
   stop loss is on the wrong side of the price or more than 1.5% away, or the take profit is on the wrong side, or
   the part is under the exchange's smallest order, that part is not opened (the rest is).
5. Signal says `flat`: close everything and stay out. Signal `offline`, expired, or nothing valid for 60 seconds: hold
   what you have, open nothing new. With `stale_flat_min` set, close everything after that many minutes without a
   live signal.

## How big are my positions

The signal says, per coin, how big our position is compared with our balance: `x`, for example 1.8 when we hold
Bitcoin worth 1.8 times our balance (negative is short). You choose how much of your money follows that, at
`fuze init` (it asks; Enter keeps the default) and later with `fuze limits`:

| Choice | Setting | Your position on a coin | With $1,000 and our position at 1.8 times our balance |
|---|---|---|---|
| **A share of your balance** (default) | `--percent 10` (1 to 100, default 10) | x × 10% × your balance. Grows and shrinks with your balance | $180 of Bitcoin; $360 once your balance is $2,000 |
| **A fixed amount** | `--size-mode fixed --fixed-usd 500` (10 to 1,000,000) | x × $500, whatever your balance is: the size your position has when ours equals our whole balance. Does not grow with your balance | $900 of Bitcoin, also at $2,000 |
| Cap per position (optional) | `--max-position-usd 300` (10 to 1,000,000, or `off`) | no coin above $300 | $300 instead of $900 in the fixed example |
| Exposure cap | `--max-x 3` (0.1 to 25) | everything together at most 3 times your **real** balance, in both choices | a fixed amount larger than your balance is cut down here |
| Daily loss stop | `--daily-loss 10` (percent, 1 to 50) | if the balance falls 10% in a UTC day, everything closes until the next UTC day | |

When a cap cuts a coin's position, the part of it that has its own take profit and stop loss shrinks in the same
proportion.

There is no "same dollar size for every position" choice, on purpose. When our scalp closes, our position shrinks but
stays on the same side; a follower whose every position had the same size would never close that part. So the choice
is between a share of your balance and a fixed amount, and both shrink when we shrink.

## Your limits

| Setting | Range | Default | Meaning |
|---|---|---|---|
| `size_mode` | `percent` or `fixed` | `percent` | how your size is set (above) |
| `percent` | 1 – 100 | 10 | share of your balance that follows the signal (percent mode) |
| `fixed_usd` | 10 – 1,000,000 | 100 | dollars that follow the signal (fixed mode) |
| `max_position_usd` | off, or 10 – 1,000,000 | off | largest position on one coin, in dollars |
| `max_x` | 0.1 – 25 | 3 | most you hold across coins, as a multiple of your balance |
| `daily_loss_frac` | 1% – 50% | 10% | if the balance falls this much in a UTC day, close everything until the next UTC day |
| `stale_flat_min` | off, or minutes | off | close everything after this long without a live signal |

`fuze limits` shows them with the worked example at your current balance. Lower any time: `fuze limits --percent 5`,
`fuze limits --max-position-usd 300`. Anything that can raise risk is only possible in a terminal and asks you to type
`RAISE`: a higher percent, fixed amount, `max_x`, daily loss stop or `stale_flat_min`; removing or raising the cap per
position; switching to the other choice when it gives a larger position at your current balance. `fuze init --force`
replaces an existing config under the same rule. Emergency controls: `fuze pause` (hold, no new orders),
`fuze flatten` (close all and stay out); `fuze resume` and `fuze unflatten` undo them. The signal can never loosen
your limits.

Setting up without questions (for scripts, or an AI coding tool doing what you asked):
`fuze init --yes --size-mode percent --percent 5 --max-position-usd 300 --max-x 2 --daily-loss 5`. With no terminal
and no flags it writes the safe defaults. It never replaces an existing config without `--force`, and a new config
is saved in mode `simulation` unless you confirm another mode at a terminal. A config written by an older version
still loads: mode `dry` is `simulation`, `scale` 0.1 becomes 10%.

## Use it from an AI coding tool

`fuze mcp` starts a local MCP server. Its tools: `status`, `signal`, `trades`, `setup_check`, `docs`, `pause`,
`flatten`, `lower_limits`. **They can only read or reduce risk.** No tool resumes, unflattens, raises a limit, removes
the cap per position, switches between a share of your balance and a fixed amount, changes the server or mode, takes
or shows a key, places an order, or touches files outside `~/.fuze`. `status` reports the mode, your exchange
account's public explorer link and whether keys are "set" or "missing"; `setup_check` covers what testnet and mainnet
need; `docs` has a `modes` topic. Install `fuze` first so the command is on
your `PATH`; the snippets below start it.

| Tool | File | Snippet |
|---|---|---|
| Claude Code | `.mcp.json` in your project, or `claude mcp add --scope project fuze -- fuze mcp` | [integrations/claude-code.mcp.json](integrations/claude-code.mcp.json) |
| Claude Code plugin | `claude plugin marketplace add <this repo>` then `claude plugin install fuze@fuze` | [plugins/fuze](plugins/fuze/.claude-plugin/plugin.json) |
| Codex CLI | `~/.codex/config.toml`, or `codex mcp add fuze -- fuze mcp` | [integrations/codex-config.toml](integrations/codex-config.toml) |
| VS Code / Copilot | `.vscode/mcp.json` | [integrations/vscode-mcp.json](integrations/vscode-mcp.json) |
| VS Code / Copilot (newer format) | `.mcp.json` at the workspace root | [integrations/copilot.mcp.json](integrations/copilot.mcp.json) |
| Cursor | `.cursor/mcp.json` or `~/.cursor/mcp.json` | [integrations/cursor-mcp.json](integrations/cursor-mcp.json) |

[AGENTS.md](AGENTS.md) tells any coding agent how to help you set FUZE up safely.

## Risks

- This is a mirror of one account's trading. When it loses, you lose.
- Most scalping rules we have tested lose money after trading costs. Past results promise nothing about the future.
- Futures use leverage. You can lose everything you put in, and faster than you expect.
- Software, servers, exchanges and networks fail. Limits and stop losses reduce losses; they do not prevent them.
- FUZE's Lighter code is new and has not yet traded on the real exchange. A stop loss can fill worse than its price
  in a fast market, or not at all.
- Only use money you can afford to lose completely. This is not financial advice.

## More

- [SECURITY.md](SECURITY.md): threat model, safe installs, reporting a vulnerability
- [docs/lighter-setup.md](docs/lighter-setup.md): a Lighter account and API key, testnet first
- Development: `python3 -m venv .venv && .venv/bin/pip install -e '.[test]' && .venv/bin/python -m pytest -q`

License: MIT.

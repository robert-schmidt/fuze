# FUZE agent

**F**utures signals, **U**ser-side, **Z**ero-custody **E**xecution.

A FUZE server publishes, signed, the position that our own trading account holds on Bitcoin and Ether perpetual
futures. This agent runs on **your** machine or server, checks every message against a key built into the code, and
follows that position on **your** account at the size and limits **you** set. Nobody else holds your keys or your
money. You can watch and control the agent from an AI coding tool (Claude Code, Codex, GitHub Copilot in VS Code,
Cursor) through an MCP server that can only make things safer.

FUZE is not affiliated with Lighter or with any exchange or AI tool named here.

## Status today: dry run only

| Stage | State |
|---|---|
| Dry run: follow the signal on a simulated $1,000 account on your computer | **v0.1, this release** |
| Lighter testnet (test money) | next, only after our own order code has been proven |
| Real money on Lighter | last |

There is no exchange code, no key handling and no real or test money in v0.1. `fuze run` refuses any mode other than
`dry`. The signal server (fuze.trade) is not live yet.

## What it is not

- Not a fund and not custody: we never see your keys, balance or position. Nothing flows back to the server.
- Not advice. It copies one account's position. That account can lose, and so will yours.
- Not a promise of results. We make no performance claims.

## Quick start (dry run)

```sh
# from a clone of this repository (the first PyPI release is not out yet); see SECURITY.md for a hash-pinned install
python3 -m venv ~/.fuze-venv && ~/.fuze-venv/bin/pip install '.[mcp]'   # [mcp] adds the server AI coding tools talk to
~/.fuze-venv/bin/fuze init        # ~/.fuze; asks how big your positions should be (Enter keeps the safe default)
~/.fuze-venv/bin/fuze run         # in its own terminal; Ctrl+C to stop
~/.fuze-venv/bin/fuze status      # what it holds and why
~/.fuze-venv/bin/fuze check       # checks your setup
```

Files live in `~/.fuze` (or `$FUZE_HOME`), private to your user: `config.json`, the simulated account `dry.json`, the
trade log `trades.jsonl`, and `status.json`.

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
4. The scalp part of a position gets its own take profit and stop loss. If the stop loss is on the wrong side of the
   price or more than 1.5% away, or the take profit is on the wrong side, that part is not opened (the rest is).
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
always starts in mode `dry`. A config written by an older version with `scale` still loads: `scale` 0.1 becomes 10%.

## Use it from an AI coding tool

`fuze mcp` starts a local MCP server. Its tools: `status`, `signal`, `trades`, `setup_check`, `docs`, `pause`,
`flatten`, `lower_limits`. **They can only read or reduce risk.** No tool resumes, unflattens, raises a limit, removes
the cap per position, switches between a share of your balance and a fixed amount, changes the server or mode, places
an order, or touches files outside `~/.fuze`. Install `fuze` first so the command is on
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
- Only use money you can afford to lose completely. This is not financial advice.

## More

- [SECURITY.md](SECURITY.md): threat model, safe installs, reporting a vulnerability
- [docs/lighter-setup.md](docs/lighter-setup.md): what you will need before real following exists
- Development: `python3 -m venv .venv && .venv/bin/pip install -e '.[test]' && .venv/bin/python -m pytest -q`

License: MIT.

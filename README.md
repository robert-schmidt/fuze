# FUZE agent

**F**utures signals, **U**ser-side, **Z**ero-custody **E**xecution.

**Vibe trading, with your limits.** Tell your AI coding tool (Claude Code, Codex, GitHub Copilot in VS Code, Cursor),
in plain words, "follow the FUZE signal with 5% of my balance". It installs and sets up this agent for you, on your
machine and your own account. Your limits stay yours: through FUZE's MCP server the AI can only lower them and stop
the agent; anything that raises risk, the mode (simulation, test money, real money) and your exchange key are typed by
you in your own terminal. Those typed steps stop the MCP tools, scripts and mistakes, not a program that already runs
as you with shell access: see [What the confirmations protect against](#what-the-confirmations-protect-against).
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
| Needs | nothing | `pip install '.[mcp,lighter]'` in your checkout, a Lighter testnet account and API key | the same on mainnet, plus a passed testnet rehearsal on this machine, confirmed by Lighter testnet |
| Switch to it | `fuze mode simulation` | `fuze mode testnet`, type `RAISE` | `fuze mode mainnet`, type `RAISE` and `REAL MONEY` |

- **Choosing**: `fuze init` asks the mode (Enter keeps simulation). Later, `fuze mode` shows it and `fuze mode testnet`
  changes it. Only in a terminal; never through the MCP server or an AI tool. The agent must be stopped, and nothing
  may be open in the current mode: close it first (`fuze flatten`, let the agent close everything, stop it).
- **Keys**: `fuze keys testnet` (or `mainnet`) asks your Lighter account index, the API key's index and the API key
  itself (80 hexadecimal characters), hidden as you type; a key of the wrong shape is refused and nothing is saved. The key goes into your OS keyring (with the `keyring` package) or else a file only you can
  read in `~/.fuze`. It is never printed, logged, shown to an AI tool, or accepted as a command-line argument. Use an
  API key restricted to the BTC and ETH markets, on a sub-account holding only what you can lose:
  [docs/lighter-setup.md](docs/lighter-setup.md).
- **The rehearsal** (`fuze rehearse`, testnet): opens the smallest Bitcoin position Lighter takes, places its take
  profit and stop loss, cancels them and closes the position, confirming every step by reading the account, and
  records the account, key index, time, version and each order's transaction hash. Mainnet stays locked until this
  passed on this machine with this version of FUZE: each version changes code that sends orders, so a new version asks
  for a new rehearsal. `fuze mode mainnet` does not trust the record alone: it asks Lighter testnet whether those
  transactions exist, belong to your testnet account and key index, and are from the recorded time, and stays locked
  when testnet cannot confirm it (also when testnet is down).
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
# in a clone of this repository. FUZE is not on PyPI yet: do not `pip install fuze-agent` by name; a package of
# that name on PyPI today is NOT ours. See SECURITY.md for an install with pinned hashes.
python3 -m venv ~/.fuze-venv && ~/.fuze-venv/bin/pip install '.[mcp]'   # [mcp] adds the server AI coding tools talk to
~/.fuze-venv/bin/fuze init        # ~/.fuze; asks the mode and how big your positions should be (Enter keeps the safe default)
~/.fuze-venv/bin/fuze run         # in its own terminal; Ctrl+C to stop
~/.fuze-venv/bin/fuze status      # what it holds and why
~/.fuze-venv/bin/fuze check       # checks your setup
~/.fuze-venv/bin/fuze ui --open   # a page with all of it, on this computer: http://127.0.0.1:3893
~/.fuze-venv/bin/fuze mcp-config  # the settings to paste into Claude Code, Codex, Copilot / VS Code or Cursor
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
protective orders placed `lighter-<mode>.json`, the rehearsal `rehearsal.json`, the key file `lighter-<mode>.key`
if there is no OS keyring, and `ui.json` (the local page's port while `fuze ui` runs).

## The local page

`fuze ui` serves a page on this computer only, at **http://127.0.0.1:3893** (3893 is F-U-Z-E on a phone keypad;
`--port` picks another, `--open` opens your browser). It shows, live, whether the agent is running, paused or stopped
and since when; the mode, with real money impossible to miss; your balance and today's result; each position with its
size, entry, price and result; the short-term part between its take profit and stop loss; the signal (state, revision,
age, signature check, which of our accounts it comes from); your sizing and limits in plain words and how much of
today's loss stop is used; recent orders with explorer links in testnet and mainnet; the setup checks; whether keys are
"set" or "missing". It works without `fuze run` and says so; then it reads the public signal itself.

The page only reads. It never trades and never changes a setting: next to each thing you might change, it shows the
command to type (`fuze pause`, `fuze limits ...`, `fuze mode ...`) or the sentence to say to your AI tool. It
listens on 127.0.0.1 only (there is no option to change that), answers only requests addressed to 127.0.0.1 or
localhost, takes GET only, serves a fixed list of files, loads nothing from anywhere else, and never shows a key or
where a key is stored. Links lead to [fuze.trade](https://fuze.trade) (our public record) and
[docs.fuze.trade](https://docs.fuze.trade).

## How following works

1. Every message is checked in this order: the key is pinned in this code and the signature is valid; protocol
   version 1; its time stamp `ts` is later than the last one accepted (kept on disk in `guard.json`, so a restart
   cannot be replayed); it has not expired (a message lives at most 60 s after `ts`) and is not more than 30 s in the
   future. Then every field is checked for type and range. Anything that fails is dropped. See
   [docs/PROTOCOL.md](docs/PROTOCOL.md).
2. The agent acts when our position changes (a new revision), on the first message after it starts, when your
   position no longer matches what it last set, and when your limits change: `fuze limits` or the MCP tool
   `lower_limits` resize the held position within seconds, on the same revision (a lowered limit shrinks every coin,
   even by less than the smallest change below). Every 5 minutes it also compares
   what the signal asks for with what you hold and corrects a coin only when it is more than 10% off (and over the
   smallest change below), so `x` moving with the price alone never causes a trade.
3. Your position per coin is sized as you chose (see [How big are my positions](#how-big-are-my-positions)), then
   cut to your cap per position, then the total across coins is cut down to your `max_x` if it is larger. Changes
   smaller than the larger of $10 and 2% of your balance are skipped, unless the target is zero. So a small size can
   mean nothing is held: with a fixed $10 the signal may ask for $17 of Bitcoin, under the $20 step of a $1,000
   balance. `fuze status`, the MCP `status` tool and the local page show, per coin, what the signal asks for and what
   you hold in dollars, and say when the difference is under that step; `fuze limits` warns when a size can never
   open anything at the current signal.
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
`fuze limits --max-position-usd 300`; a running agent resizes to it within seconds. Anything that can raise risk is
only possible in a terminal and asks you to type `RAISE` (it also applies without a restart): a higher percent, fixed amount, `max_x`, daily loss stop or `stale_flat_min`; removing or raising the cap per
position; switching to the other choice when it gives a larger position at your current balance. `fuze init --force`
replaces an existing config under the same rule. Emergency controls: `fuze pause` (hold, no new orders),
`fuze flatten` (close all and stay out); `fuze resume` and `fuze unflatten` undo them, only at a terminal and after you
type `RESUME` or `UNFLATTEN`, like raising. The signal can never loosen your limits.

Setting up without questions (for scripts, or an AI coding tool doing what you asked):
`fuze init --yes --size-mode percent --percent 5 --max-position-usd 300 --max-x 2 --daily-loss 5`. With no terminal
and no flags it writes the safe defaults. It never replaces an existing config without `--force`, and a new config
is saved in mode `simulation` unless you confirm another mode at a terminal. A config written by an older version
still loads: mode `dry` is `simulation`, `scale` 0.1 becomes 10%.

## Use it from an AI coding tool

`fuze mcp` starts a local MCP server. Its tools: `status`, `signal`, `trades`, `setup_check`, `docs`, `ui`, `pause`,
`flatten`, `lower_limits`. **They can only read or reduce risk.** A tool refuses arguments it does not take (it never
silently ignores `mode` or `api_key`), and `pause`, `flatten` and `lower_limits` answer an error, naming the folder, when
no agent is set up in the folder the server looks at. Ask your AI tool "open the FUZE page": `ui` gives
the local page's address and whether it is running (start it with `fuze ui --open`). No tool resumes, unflattens, raises a limit, removes
the cap per position, switches between a share of your balance and a fixed amount, changes the server or mode, takes
or shows a key, places an order, or touches files outside `~/.fuze`. `status` reports the mode, your exchange
account's public explorer link and whether keys are "set" or "missing"; `setup_check` covers what testnet and mainnet
need; `docs` has a `modes` topic.

AI tools start MCP servers without your shell's `PATH` and with a filtered environment, so the settings need the full
path of `fuze` and your `FUZE_HOME`. **`fuze mcp-config` prints them ready to paste** for every tool below (with the
one-line `claude mcp add ...` and `codex mcp add ...` forms); `fuze mcp-config --tool cursor` prints one. The files in
`integrations/` show the same shape with placeholder paths.

| Tool | File | Snippet |
|---|---|---|
| Claude Code | `claude mcp add fuze --scope user -e FUZE_HOME=... -- /full/path/to/fuze mcp`, or `.mcp.json` in your project | [integrations/claude-code.mcp.json](integrations/claude-code.mcp.json) |
| Claude Code plugin | `claude plugin marketplace add <this repo>` then `claude plugin install fuze@fuze`; works only with `fuze` on Claude Code's PATH and the default folder `~/.fuze` | [plugins/fuze](plugins/fuze/.claude-plugin/plugin.json) |
| Codex CLI | `codex mcp add fuze --env FUZE_HOME=... -- /full/path/to/fuze mcp`, or `~/.codex/config.toml` | [integrations/codex-config.toml](integrations/codex-config.toml) |
| VS Code / Copilot | `.vscode/mcp.json` | [integrations/vscode-mcp.json](integrations/vscode-mcp.json) |
| VS Code / Copilot (newer format) | `.mcp.json` at the workspace root | [integrations/copilot.mcp.json](integrations/copilot.mcp.json) |
| Cursor | `.cursor/mcp.json` or `~/.cursor/mcp.json` | [integrations/cursor-mcp.json](integrations/cursor-mcp.json) |

[AGENTS.md](AGENTS.md) tells any coding agent how to help you set FUZE up safely.

## What the confirmations protect against

Typing `RAISE`, `REAL MONEY`, `RESUME` or `UNFLATTEN` at a terminal, the terminal check itself and the rehearsal lock
stop three things: the MCP tools (which have no route to them at all), programs that run without a terminal, and
mistakes. They are **not** a barrier against a program that already runs as you with shell access: such a program can
fake a terminal and type the words, edit the files in `~/.fuze`, or change FUZE's own code, and it could equally read
your API key. `AGENTS.md` tells coding agents not to, but that is a request, not a lock. The protection for money is
on the exchange side: give FUZE a Lighter sub-account that holds only what you are willing to lose, and an API key that
cannot withdraw: one restricted to the BTC and ETH markets, which per Lighter's docs can only create, modify and cancel
orders there (an unrestricted key can still withdraw to your own wallet; no API key alone can send funds to another
owner). See [docs/lighter-setup.md](docs/lighter-setup.md). **Do not give an AI tool unattended shell access on a machine that
holds a mainnet key.**

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

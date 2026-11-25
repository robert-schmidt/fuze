# Command reference

This page lists every `fuze` command with its options, as printed by `fuze --help` in version 0.3.0. Commands marked
"terminal only" refuse to run when input is not a terminal.

| Command | What it does | Terminal only |
|---|---|---|
| `fuze init` | Create the FUZE folder and set how big your positions are | Asks questions at a terminal; `--yes` takes flags and safe defaults |
| `fuze run` | Run the agent in the mode set with `fuze mode` | |
| `fuze status` | What the agent holds and why: per coin, what the signal asks for and what you hold, in dollars | |
| `fuze check` | Check the local setup; in testnet or mainnet also reads your account (no order) | |
| `fuze limits` | Show or change your sizing and limits | Raising asks you to type `RAISE` |
| `fuze pause` / `fuze resume` | Hold with no new orders / undo | Undoing: yes, type `RESUME` |
| `fuze flatten` / `fuze unflatten` | Close everything and stay out / undo | Undoing: yes, type `UNFLATTEN` |
| `fuze mode` | Show or change the mode | Changing: yes |
| `fuze keys` | Set the Lighter account and API key for testnet or mainnet | Yes, the key is typed hidden |
| `fuze rehearse` | The testnet rehearsal that unlocks mainnet on this machine | Yes |
| `fuze ui` | A read-only page about the agent on this computer. Options `--port`, `--open` | |
| `fuze mcp` | Start the MCP server for AI coding tools | |
| `fuze mcp-config` | Print the MCP settings for Claude Code, Codex, Copilot / VS Code and Cursor, with this `fuze`'s full path and your `FUZE_HOME`. Option `--tool` | |
| `fuze --version` | Print the version | |

## fuze init

```text
fuze init [--size-mode {percent,fixed}] [--percent PERCENT] [--fixed-usd FIXED_USD]
          [--max-position-usd MAX_POSITION_USD] [--max-x MAX_X] [--daily-loss DAILY_LOSS]
          [--yes] [--force] [--mode {simulation,testnet,mainnet}]
```

| Option | Meaning |
|---|---|
| `--size-mode` | `percent`: a share of your balance follows the signal (default); `fixed`: a fixed amount does |
| `--percent` | Share of your balance, 1 to 100 |
| `--fixed-usd` | Dollars in fixed mode, 10 to 1,000,000 |
| `--max-position-usd` | Largest position on one coin in dollars, or `off` |
| `--max-x` | Most you hold across coins, times your balance |
| `--daily-loss` | Daily loss stop in percent, 1 to 50 |
| `--yes` | Ask no questions; use the flags and the safe defaults |
| `--force` | Replace an existing config (raising anything asks you to type `RAISE`) |
| `--mode` | Where to trade (default simulation); testnet and mainnet ask you to confirm at a terminal |

It never replaces an existing config without `--force`, and without a terminal it always saves `simulation`.

Example: `fuze init --yes --size-mode fixed --fixed-usd 200 --max-position-usd 300 --max-x 2 --daily-loss 5`

## fuze run

```text
fuze run [--mode {simulation,testnet,mainnet}]
```

`--mode` makes it refuse to start unless that is the mode in your settings: a guard, not a switch. One agent per FUZE
folder; a second one refuses to start. Ctrl+C stops it and leaves positions as they are.

## fuze limits

```text
fuze limits [--size-mode {percent,fixed}] [--percent PERCENT] [--fixed-usd FIXED_USD]
            [--max-position-usd MAX_POSITION_USD] [--max-x MAX_X] [--daily-loss DAILY_LOSS]
            [--stale-flat-min STALE_FLAT_MIN]
```

With no options it shows your sizing with the worked example at your current balance. `--stale-flat-min` takes minutes
or `off`. A running agent resizes to a change within seconds; raising asks you to type `RAISE` first. It warns when the
size you chose can never open anything at the current signal (every change under the larger of $10 and 2% of your
balance).

## fuze mode

```text
fuze mode [{simulation,testnet,mainnet}]
```

With no argument: the mode, the account link and key state, and whether a passed rehearsal is recorded. With one:
switches, with the agent stopped and nothing open; toward real money it asks for `RAISE` (and `REAL MONEY` for mainnet).
`fuze mode mainnet` first asks Lighter testnet to confirm the rehearsal record (reads only).

## fuze keys

```text
fuze keys [--account ACCOUNT] [--key-index KEY_INDEX] [--delete] [{testnet,mainnet}]
```

With no argument: shows the account index, key index and "set" or "missing" for each network. With a network: asks the
account index, key index (4 to 254) and the key, hidden. A key that is not 80 hexadecimal characters is refused and
nothing is saved. `--delete` removes the stored key from this machine (it still works on Lighter until you replace it
there).

## fuze rehearse

Opens the smallest Bitcoin position on Lighter testnet, places its take profit and stop loss, cancels them and closes
it, confirming each step by reading the account, and records each order's transaction hash. Asks you to type `yes`
first. See [The rehearsal and the mainnet lock](modes/rehearsal.md).

## fuze resume, fuze unflatten

Undo `fuze pause` and `fuze flatten`. Like raising a limit, they refuse when input is not a terminal and ask you to type
`RESUME` or `UNFLATTEN`: the agent then follows the signal again and may open positions at once.

## fuze mcp-config

```text
fuze mcp-config [--tool {claude-code,codex,copilot,vscode,cursor}]
```

Prints ready-to-paste MCP settings for each AI tool: the full path of the `fuze` you ran it with (AI tools do not use
your PATH) and `FUZE_HOME` set to your FUZE folder (AI tools pass a filtered environment), plus the one-line
`claude mcp add ...` and `codex mcp add ...` forms. Run it the way you run the agent, with the same `FUZE_HOME`. It warns
when that folder has no agent set up. See [Using it from an AI coding tool](ai-tools/README.md).

## Environment variables

| Variable | Effect |
|---|---|
| `FUZE_HOME` | Use this folder instead of `~/.fuze` |
| `FUZE_NO_KEYRING=1` | Keep the API key in a private file instead of the OS keyring |

## Exit codes

0 when it did what you asked, 1 when you declined or a check failed, 2 when it refused (for example, not a terminal, or
the agent is running).

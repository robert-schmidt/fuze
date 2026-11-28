# Command reference

This page lists every `fuze` command with its options, as printed by `fuze --help` in version 0.5.0. Commands marked
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
| `fuze go-live` | From simulation to real money, one guided step at a time: test account and key, rehearsal, real account and key, the switch | Yes |
| `fuze share` | What the agent reports to the FUZE server, whether it is public, its id and its page | |
| `fuze share public` / `fuze share private` | List the agent in the FUZE Fellowship with your handle / only FUZE sees the reports | Yes |
| `fuze share prove` | Prove your GitHub handle and, on testnet or mainnet, your Lighter account | Yes, type `YES` before the Lighter token is sent |
| `fuze ui` | A read-only page about the agent on this computer. Options `--port`, `--open` | |
| `fuze mcp` | Start the MCP server for AI coding tools | |
| `fuze mcp-config` | Print the MCP settings for Claude Code, Codex, Copilot / VS Code, Cursor and other AI tools, with this `fuze`'s full path and your `FUZE_HOME`. Option `--tool` | |
| `fuze --version` | Print the version | |

## fuze init

```text
fuze init [--size-mode {percent,fixed}] [--percent PERCENT] [--fixed-usd FIXED_USD]
          [--max-position-usd MAX_POSITION_USD] [--max-x MAX_X]
          [--max-balance-usd MAX_BALANCE_USD] [--daily-loss DAILY_LOSS]
          [--yes] [--force] [--mode {simulation,testnet,mainnet}]
```

| Option | Meaning |
|---|---|
| `--size-mode` | `percent`: a share of your balance follows the signal (default); `fixed`: a fixed amount does |
| `--percent` | Share of your balance, 1 to 100 |
| `--fixed-usd` | Dollars in fixed mode, 10 to 1,000,000 |
| `--max-position-usd` | Largest position on one coin in dollars, or `off` |
| `--max-x` | Most you hold across coins, times your balance |
| `--max-balance-usd` | Balance ceiling: the most of the account the agent counts as your balance, or `off` |
| `--daily-loss` | Daily loss stop in percent, 1 to 50 |
| `--yes` | Ask no questions; use the flags and the safe defaults |
| `--force` | Replace an existing config (raising anything asks you to type `RAISE`) |
| `--mode` | Where to trade (default simulation); testnet and mainnet ask you to confirm at a terminal |

It never replaces an existing config without `--force`, and without a terminal it always saves `simulation`. It says
what the agent reports to the FUZE server and, at a terminal, asks "Show this agent publicly in the FUZE Fellowship?
(yes/no) [no]" and then for your X or GitHub link. With `--yes` it asks nothing and the agent stays private (or keeps
what you chose before, with `--force`).

Example: `fuze init --yes --size-mode fixed --fixed-usd 200 --max-position-usd 300 --max-x 2 --daily-loss 5`

## fuze run

```text
fuze run [--mode {simulation,testnet,mainnet}]
```

`--mode` makes it refuse to start unless that is the mode in your settings: a guard, not a switch. One agent per FUZE
folder; a second one refuses to start. Ctrl+C stops it and leaves positions as they are. At start it says in one line
that it reports its trades and results to the FUZE server, private or public (see `fuze share`).

## fuze limits

```text
fuze limits [--size-mode {percent,fixed}] [--percent PERCENT] [--fixed-usd FIXED_USD]
            [--max-position-usd MAX_POSITION_USD] [--max-x MAX_X]
            [--max-balance-usd MAX_BALANCE_USD] [--daily-loss DAILY_LOSS]
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

## fuze go-live

The guided way from simulation to real money. It runs the same steps as `fuze keys`, `fuze rehearse` and `fuze mode`,
in order, and says at each one what to do on Lighter:

1. An account on Lighter's test exchange and an API key for it (typed hidden), then it reads the account back.
2. The rehearsal, if this computer has not passed it with this version.
3. A choice: follow on the test exchange first (recommended), or carry on. Run `fuze go-live` again later to carry on.
4. Your Lighter account for real money and its API key, read back the same way.
5. The switch, confirmed by typing `RAISE` and `REAL MONEY`.

Steps already done are skipped, so you can stop at any question and run it again. Terminal only: it never runs through
the MCP server or an AI tool. Your keys, account numbers and the rehearsal stay on this computer, so afterwards
`fuze mode simulation` and `fuze mode mainnet` move you back and forth with nothing typed again but the confirmations.

## fuze share

```text
fuze share [{public,private,prove}] [--handle HANDLE]
```

Without a word it prints exactly what the agent sends in each kind of report, what public adds, what is never sent,
whether this agent is public, its id, and when public its page `https://fuze.trade/fellowship/<id>`.

| Word | What it does |
|---|---|
| `public` | Lists the agent in the FUZE Fellowship. Asks for your X or GitHub profile link (Enter for none), or takes `--handle LINK`. Sends a hello at once and prints the server's answer |
| `private` | Only FUZE sees the reports again; the server removes your handle and account number |
| `prove` | For a GitHub handle: shows the gist to create (description `fuze-<id>`), then asks the server to check it. On testnet or mainnet: explains the read-only Lighter token, asks you to type `YES`, sends it once and says whether the account is now shown |

All three words refuse when input is not a terminal; the MCP server has no tool for them. There is no word that turns
reporting off. See [What your agent reports](sharing.md).

## fuze resume, fuze unflatten

Undo `fuze pause` and `fuze flatten`. Like raising a limit, they refuse when input is not a terminal and ask you to type
`RESUME` or `UNFLATTEN`: the agent then follows the signal again and may open positions at once.

## fuze mcp-config

```text
fuze mcp-config [--tool {claude-code,codex,copilot,vscode,cursor,opencode,zed,gemini,antigravity,devin,cline,claude-desktop,jetbrains,kiro}]
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

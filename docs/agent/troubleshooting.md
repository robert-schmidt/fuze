# Troubleshooting

This page lists messages and situations you may meet, what they mean, and what to do. Start with `fuze check` and
`fuze status`: most answers are there.

## Installing and starting

| You see | Meaning | Do this |
|---|---|---|
| `command not found: fuze` | The virtual environment is not on your PATH | Use `~/.fuze-venv/bin/fuze`, or link it (see [Install](start/install.md)) |
| `The MCP server needs one extra package` | Installed without `[mcp]` | `~/.fuze-venv/bin/pip install '.[mcp]'` from the checkout |
| `... already exists; leaving it as it is` (from `fuze init`) | You already have a config | See it with `fuze limits`; change it with `fuze limits` |
| `Another agent is already running on this FUZE folder.` | `fuze run` is already running | Use the running one, or stop it first |
| `[NO] Agent is running` (from `fuze check`) | The agent is not running, or has not stepped for 30 seconds | Start `fuze run` in its own terminal |
| `No status yet. Start the agent with fuze run.` | The agent has never run in this folder | Start it; check `FUZE_HOME` if you use another folder |
| `config.json is not valid: ...` | The file was edited by hand | Run `fuze init --force` to start over, or undo the edit |

## The AI tool

| You see | Meaning | Do this |
|---|---|---|
| The tool cannot start the server, or "file not found" | The command `fuze` is not on the PATH the AI tool sees | Run `fuze mcp-config` and paste its output: it has the full path (see [the setup that works](ai-tools/README.md#the-setup-that-works)) |
| `No FUZE agent is set up in <folder>` (from `status`, `pause`, `flatten` or `lower_limits`) | The MCP server looks in a folder with no `config.json`, usually because the tool passes no `FUZE_HOME` | Run `fuze mcp-config` in the terminal where the agent runs, paste its output, restart the tool. Nothing was paused or changed |
| `status` says "No status yet" while `fuze run` is running | The MCP server looks in a different folder | Run `fuze mcp-config` and use its `FUZE_HOME` |
| `The ... tool does not take ...` | The AI tool passed an argument the tool does not have (for example `mode` or `api_key`) | Nothing was changed. The mode and keys are yours to change in a terminal; never paste a key into a chat |
| "This would raise ... This server can only lower limits" | Working as designed | Type the `fuze limits` command yourself |

## Following

| You see | Meaning | Do this |
|---|---|---|
| A coin is not opened, or the position looks smaller than expected | A change under the larger of $10 and 2% of your balance is skipped; or a cap cut it | `fuze status` shows per coin what the signal asks for and what you hold, and says when the difference is under that step; see [Limits](limits.md#when-a-size-is-too-small-to-trade) |
| `Your limits changed: resized to them.` | You (or your AI tool) changed a limit | Nothing: the agent resized the held position |
| `Re-check: the held position was further from ...` | The 5-minute re-check found a coin more than 10% off | Nothing: it corrected it |
| `The scalp part is not opened: ...` | The short-term part's stop is more than 1.5% from the price or on the wrong side, it already closed, or it is under the exchange's smallest order | Nothing; the rest of the position is followed |
| `No fresh signal: holding what we have and opening nothing new.` | No valid message for 60 seconds | Check your internet connection and [fuze.trade](https://fuze.trade). The agent falls back to polling every 2 seconds |
| `The signal says it is offline` | Our side has no fresh reading of the account | Nothing; it holds. Set `stale_flat_min` if you prefer to close after a while |
| `Daily loss stop: ...` | The balance fell by your daily loss stop since the UTC day began | It stays flat until the next UTC day |
| `PAUSE is on` / `FLATTEN is on` | A switch is on, possibly from your AI tool | `fuze resume` / `fuze unflatten` at a terminal, typing `RESUME` / `UNFLATTEN` |

## Modes and keys

| You see | Meaning | Do this |
|---|---|---|
| `... needs you at a terminal; refusing because input is not a terminal` | A risk-raising action, `fuze resume` or `fuze unflatten` was run by a script or AI tool | Type it yourself in a terminal |
| `the Lighter SDK is not installed` | Installed without `[lighter]` | `~/.fuze-venv/bin/pip install '.[mcp,lighter]'` from the checkout |
| `that is not a Lighter API private key: those are 80 hexadecimal characters ...` | What you pasted has the wrong length or is not hexadecimal; nothing was saved | Paste the API private key (80 hex characters), never a wallet key |
| `the stored ... API key is not a Lighter API private key` or `the Lighter SDK could not use the stored ... API key` | A key stored earlier has the wrong shape | Enter it again with `fuze keys testnet` (or `mainnet`) |
| `Lighter does not accept this API key for account ... at key index ...` | The account index, key index or key do not match on Lighter | Check all three with `fuze keys testnet`; see [Lighter account and API key](../lighter-setup.md) |
| `Positions are open in simulation ... A mode change never strands a position.` | Something is still open in the current mode | `fuze flatten`, let the agent close everything, stop it, then switch |
| `That account already holds positions or orders that FUZE did not open.` | The Lighter account is not empty | Give FUZE a sub-account of its own |
| `the testnet rehearsal has not been done on this machine` | Mainnet is locked | Run `fuze rehearse` on testnet |
| `the rehearsal was done with FUZE ..., this is ...` | You updated FUZE; each version changes code that sends orders | Run `fuze rehearse` again |
| `... stays locked: could not reach Lighter testnet to confirm the rehearsal` | `fuze mode mainnet` could not ask testnet | Try again later; nothing was changed |
| `... stays locked: Lighter testnet does not confirm ...` / `... another account or API key ...` / `... no transaction ...` | The rehearsal record does not match what testnet shows (an older record, another account, or an edited file) | Run `fuze rehearse` again |
| `The agent is running on this FUZE folder. Stop it first` | Mode changes, rehearsals and key changes need the agent stopped | Stop it with Ctrl+C |

## Still stuck

Look at the agent's terminal output and `~/.fuze/trades.jsonl`. On Lighter, compare with your account on the explorer
(`fuze status` prints the link). If something looks wrong with money at stake, run `fuze flatten` first and investigate
after.

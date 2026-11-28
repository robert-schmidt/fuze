# What the agent is

This page introduces the FUZE agent: the open-source program that follows the signal on your own account, and the MCP
server your AI coding tool uses to watch and control it.

## Two programs in one package

| Program | Command | What it does |
|---|---|---|
| The agent | `fuze run` | Reads the signal, checks every signature, and keeps your position at your share of ours, inside your limits. Plain code: no AI decides an order |
| The MCP server | `fuze mcp` | Lets an AI coding tool (Claude Code, Codex, GitHub Copilot, Cursor) read the agent's status and make it safer: pause, flatten, lower limits. It cannot raise risk |

Everything else is the `fuze` command in your terminal: setup, modes, keys and limits. See
[Command reference](commands.md).

## What it costs

Nothing. The signal is free and public, the agent is open source (MIT licence), and FUZE takes no fee and no share. What
you pay is your own: exchange fees and funding on your trades (Lighter's standard account charges no trading fee at the
time of writing), and, if you use one, your AI tool's subscription.

## Where it trades

| Mode | Where | Money | How it unlocks |
|---|---|---|---|
| `simulation` (default) | A simulated $1,000 account on your computer | None | On from the start |
| `testnet` | Lighter's test exchange | Test money | Your testnet API key, then `fuze mode testnet` |
| `mainnet` | Lighter | **Real** | Locked on each machine until that machine passed `fuze rehearse` on testnet, for each new version, and until more than half of FUZE's proven trades have won |

> **Warning:** start in simulation, then testnet with small sizes, and watch it. Mainnet comes after that, with only
> money you can afford to lose.

## What stays yours

- **Your money and keys.** Nobody else holds them. The agent reports its trades and results to our server as
  multiples of your balance and percent, never an amount, a balance or a key; private unless you choose public. See
  [What your agent reports](sharing.md).
- **Your limits.** The signal can never loosen them. Your AI tool can only lower them.
- **The risky switches.** Raising a limit, resuming, unflattening, changing the mode and entering a key are done by
  you, in your own terminal. That stops your AI tool's MCP server and mistakes; it is not a barrier against a program
  that runs with your own shell access (see [Security model](security.md)).

## Version

Version 0.4.0 ([what changed in each version](https://github.com/robert-schmidt/fuze/blob/main/CHANGELOG.md)). It runs on macOS and Linux, and on Windows inside WSL; its installer fetches Python (3.10 or newer) by itself. It is installed from its
repository, https://github.com/robert-schmidt/fuze: see [Install](start/install.md).

## Where to go next

- [How following works](following.md): what the agent does with each message.
- [Install](start/install.md) and [First run in simulation](start/first-run.md).

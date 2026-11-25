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

| Mode | Where | Money | State |
|---|---|---|---|
| `simulation` (default) | A simulated $1,000 account on your computer | None | Proven end to end |
| `testnet` | Lighter's test exchange | Test money | New code, not yet proven against the real exchange |
| `mainnet` | Lighter | **Real** | New code, not yet proven against the real exchange; locked until your testnet rehearsal passes |

> **Warning:** the agent has had **no independent security review**. Mainnet ships behind a rehearsal lock that Lighter
> testnet must confirm, not behind an audit. Start in simulation, then testnet, with small sizes, and watch it.

## What stays yours

- **Your money and keys.** Nobody else holds them. The agent tells our server nothing about your account.
- **Your limits.** The signal can never loosen them. Your AI tool can only lower them.
- **The risky switches.** Raising a limit, resuming, unflattening, changing the mode and entering a key are done by
  you, in your own terminal. That stops your AI tool's MCP server and mistakes; it is not a barrier against a program
  that runs with your own shell access (see [Security model](security.md)).

## Status

Version 0.3.0. It runs on macOS and Linux with Python 3.10 or newer (on Windows, use WSL). It is installed from the
repository checkout. The release on PyPI, the Python package index, is not out yet: a package called `fuze-agent` on
PyPI today is not ours.

## Where to go next

- [How following works](following.md): what the agent does with each message.
- [Install](start/install.md) and [First run in simulation](start/first-run.md).

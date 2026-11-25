# FUZE

FUZE publishes, signed, the position that one trading account holds on Bitcoin and Ether futures, and gives you an
open-source agent that can follow that position on your own account, at the size and inside the limits you choose.
This page says what FUZE is, who it is for, what can go wrong, and how the rest of these docs are laid out.

The name stands for **F**utures signals, **U**ser-side, **Z**ero-custody **E**xecution: we publish a signal, your own
computer does the trading, and nobody but you holds your money or your keys.

## Vibe trading, in two honest sentences

You tell your AI coding tool (Claude Code, Codex, GitHub Copilot or Cursor), in plain words, "follow the FUZE signal
with 5% of my balance", and it installs and sets up the agent for you. It does the setup and can explain what the agent
is doing; it does not make the trades win, and anything that raises your risk is typed by you, in your own terminal.

## The three parts

| Part | What it is | Where |
|---|---|---|
| The account | One account that trades Bitcoin and Ether perpetual futures: short-term trades on top of a slow trend position. Today it trades practice money at a real exchange's prices | [Part 1](account/README.md) |
| The signal | What that account holds, published every few seconds with a digital signature, free and public | [The signal](signal/README.md) |
| The agent | A small program on your computer that checks the signature and copies the position on your own account. An MCP server lets your AI coding tool watch it and make it safer, never riskier | [Part 2](agent/README.md) |

## What it costs

Nothing. The signal is free and public, the agent is open source (MIT licence), and FUZE takes no fee and no share of
anything. Exchange fees and funding on your own trades are your own.

## Who it is for

- People who are comfortable with a terminal and an AI coding tool, and want to see how a trading account works in
  the open: every rule, every test that failed, every trade.
- People willing to start on a simulated account with no money, and to stay there until they understand what they see.

It is not for anyone looking for income, and not for money you need. FUZE gives no advice and knows nothing about your
situation.

## The risks, up front

- **The account can lose, and so will you.** The agent mirrors one account. When it loses, you lose in the same
  proportion.
- **Our own tests say the short-term trades lose a little after costs.** On three years of history no short-term rule
  we tried beat trading costs. Only the slow trend position made money in those tests. Past results promise nothing.
- **Futures use leverage.** You can lose everything you put in, and faster than you expect.
- **Start small, in order.** Simulation first, then Lighter testnet with small sizes; mainnet stays locked on each
  machine until that machine has passed the testnet rehearsal.

The full list is on [Risks, plainly](risks.md). Read it before anything else.

## Where to start

- To understand what you would be copying: [One account, two books](account/README.md).
- To check the signal yourself: [Verifying a message yourself](signal/verify.md).
- To try the agent with no money: [Install](agent/start/install.md), then
  [First run in simulation](agent/start/first-run.md).
- For the words used here: [Glossary](terms.md).

FUZE is not affiliated with Lighter, Hyperliquid, Anthropic or any exchange or AI tool named in these docs.

# The three modes

This section explains the agent's three modes (where it trades, with what money), what each needs, how you move between
them, and how far each one is proven today.

## At a glance

| | simulation | testnet | mainnet |
|---|---|---|---|
| Where | A simulated account on your computer | Lighter's test exchange | Lighter |
| Money | None | Lighter test money | **Real** |
| Needs | Nothing | `pip install '.[mcp,lighter]'`, a Lighter testnet account and API key | The same on mainnet, plus a passed testnet rehearsal on this machine with this version, confirmed by Lighter testnet |
| Switch to it | `fuze mode simulation` | `fuze mode testnet`, type `RAISE` | `fuze mode mainnet`, type `RAISE` and `REAL MONEY` |
| Proven | **End to end** | **Not yet against the real exchange** | **Not yet against the real exchange** |

## The honest status

- Simulation has been run end to end against the live signal.
- The Lighter code has **never sent an order to the real exchange**. It is tested only against a fake exchange. Your own
  testnet rehearsal is the first time it meets Lighter.
- There has been **no independent security review** of the agent.

> **Warning:** start in simulation, then testnet with small sizes, and watch it. Only consider mainnet after you have
> watched testnet work and accept that you can lose everything you put on that account.

## Rules that apply to every switch

- Only in a terminal, typed by you: never through the MCP server or an AI tool.
- The agent must be stopped.
- Nothing may be open in the current mode. Close it first: `fuze flatten`, let `fuze run` close everything, stop it,
  then switch (and `fuze unflatten` when you want it to follow again). A mode change never strands a position.
- A Lighter account that already holds positions or orders FUZE did not open is refused: give FUZE a sub-account of its
  own.
- Moving toward real money asks you to type `RAISE`; mainnet also `REAL MONEY`.

## Any mode can follow any source

Because the signal is a ratio, a follower in any mode can follow any of our accounts (`source`: `paper`, `testnet` or
`mainnet`). When your mode risks more real money than the account you follow (for example, real money following our
practice account), `fuze status`, `fuze check` and the MCP `status` tool say so in plain words. Today our account trades
practice money.

## The same rules everywhere

Your sizing, cap per position, exposure cap, daily loss stop and stale-signal setting work the same in every mode.

## Pages

- [Simulation](simulation.md)
- [Lighter testnet](testnet.md)
- [Lighter account and API key](../../lighter-setup.md)
- [The rehearsal and the mainnet lock](rehearsal.md)
- [Lighter mainnet](mainnet.md)

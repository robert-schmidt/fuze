# The three modes

This section explains the agent's three modes (where it trades, with what money), what each needs, what each risks,
and how you move between them.

## At a glance

| | simulation | testnet | mainnet |
|---|---|---|---|
| Where | A simulated account on your computer | Lighter's test exchange | Lighter |
| Money | None | Lighter test money | **Real** |
| Needs | Nothing | The `[mcp,lighter]` extras ([Install](../start/install.md#the-extras)), a Lighter testnet account and API key | The same on mainnet, plus a passed testnet rehearsal on this machine with this version, confirmed by Lighter testnet |
| Risks | Nothing | Test money only | **Everything on the mainnet sub-account** |
| Switch to it | `fuze mode simulation` | `fuze mode testnet`, type `RAISE` | `fuze mode mainnet`, type `RAISE` and `REAL MONEY` |

## The guided way

```sh
fuze go-live
```

One command walks through everything below in order: a testnet account and key, the rehearsal, a mainnet account and
key, the switch. It skips what is already done, so you can stop at any question and run it again. See
[fuze go-live](../commands.md#fuze-go-live). The rest of this section is the same path by hand.

## The order to go in

1. **Simulation**: watch the agent follow the live signal with no money.
2. **Testnet, small sizes**: the same orders on Lighter's test exchange. `fuze rehearse` runs the whole order path once
   (open, emergency stop, take profit and stop loss, cancel both, close) and records it.
3. **Mainnet**: only after you have watched testnet work and accept that you can lose everything you put on that
   account. Each new version of FUZE asks for a new testnet rehearsal before mainnet unlocks again.

> **Warning:** on mainnet the protection for your money is on the exchange side: a sub-account of its own holding only
> what you can lose, and an API key restricted to the markets of the coins you follow. See [Security model](../security.md).

## Rules that apply to every switch

- Only in a terminal, typed by you: never through the MCP server or an AI tool.
- The agent must be stopped.
- Nothing may be open in the current mode, and a mode change never strands a position: `fuze mode` closes simulated positions by itself and, on Lighter, closes what is open with market orders once you type `CLOSE`.
  Anything else typed there leaves everything as it is.
- A Lighter account that already holds positions or orders FUZE did not open is refused: give FUZE a sub-account of its
  own.
- Moving toward real money asks you to type `RAISE`; mainnet also `REAL MONEY`.

## What is remembered

Your Lighter account numbers, the API keys and the rehearsal stay on this computer when you change the mode. Going from
real money back to simulation and to real money again asks for the confirmations only (and asks Lighter testnet to
confirm the rehearsal again). Your simulated account keeps its balance while you are away. What does not carry over:
a new version of FUZE that changes how orders are sent asks for a new rehearsal, and so does another computer.

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

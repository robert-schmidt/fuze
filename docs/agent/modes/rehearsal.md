# The rehearsal and the mainnet lock

This page explains `fuze rehearse`, the short testnet run that must pass on your machine before mainnet can be chosen,
and what the lock does and does not protect against.

## What the rehearsal does

On your Lighter testnet account, with test money, each step confirmed by reading the account back:

| Step | Order | Passes when |
|---|---|---|
| open | Buy twice the smallest Bitcoin position Lighter accepts | The account shows the position |
| guard | Place the emergency stop for one half, 20% under the price | The account shows it, and not as a take profit / stop loss |
| protect | Place a reduce-only take profit (+3%) and stop loss (-3%) for the other half | The account shows them beside the emergency stop |
| cancel | Cancel the take profit and stop loss | The account shows none, and the emergency stop still rests |
| unguard | Cancel the emergency stop | The account shows none |
| close | A reduce-only market order for the whole position | The account is flat |

If a step fails, it cancels and closes what it opened and tells you to check the account on the explorer. It refuses to
start if the testnet account already holds a position or protective orders.

It writes `rehearsal.json` in your FUZE folder: the testnet account index and API key index, the time, the FUZE
version, the machine, each step's result and the transaction hash of each order it sent (open, emergency stop, take profit /
stop loss, close).

```sh
fuze rehearse          # agent stopped; asks you to type yes before sending the test orders
```

## The lock

Mainnet can be chosen only when the last rehearsal:

- passed every step,
- ran on testnet,
- ran on **this machine**,
- ran with **this version** of FUZE. Each version changes code that sends orders, so an update asks for a new
  rehearsal: the version that will trade real money must have worked on testnet first.

`fuze mode mainnet` does not trust the file alone. It asks Lighter testnet (reads only, no order):

- that Lighter accepts your stored testnet API key for the recorded account and key index;
- that each recorded transaction exists on testnet, belongs to that account, was signed with that key index, and is
  from the time the record gives (within an hour).

If testnet does not confirm all of it, or cannot be reached, mainnet stays locked and the message says why; try again
later or run `fuze rehearse` again. `fuze mode` shows whether a passed rehearsal is recorded. `fuze run` checks the
local record again at every start, without the network.

## What the lock is for, and its limit

The lock makes sure the order path has worked against the real exchange, on your setup, before real money is used. The
testnet confirmation means a hand-written record does not unlock mainnet. It cannot prove that the orders were sent by
this copy of FUZE or this version: a program with your shell access could run a real rehearsal, edit FUZE's code, or
read your key. It is a check against mistakes and tools without your access, not a barrier against a program running
as you. See [Security model](../security.md).

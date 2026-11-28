# The rehearsal and the mainnet lock

This page explains `fuze rehearse`, the short testnet run that must pass on your machine before mainnet can be chosen,
the second lock that waits for FUZE's own record, and what the locks do and do not protect against.

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
- ran with **this version** of FUZE. The rehearsal is recorded for the version that passed it, so an update asks for a new
  rehearsal: the version that will trade real money must have worked on testnet first.

`fuze mode mainnet` does not trust the file alone. It asks Lighter testnet (reads only, no order):

- that Lighter accepts your stored testnet API key for the recorded account and key index;
- that each recorded transaction exists on testnet, belongs to that account, was signed with that key index, and is
  from the time the record gives (within an hour).

If testnet does not confirm all of it, or cannot be reached, mainnet stays locked and the message says why; try again
later or run `fuze rehearse` again. `fuze mode` shows whether a passed rehearsal is recorded. `fuze run` checks the
local record again at every start, without the network.

## The record's lock

Mainnet also stays locked until more than half of FUZE's own proven trades have won. A proven trade is one whose
opening and closing records are both time-stamped in a Bitcoin block (see [Proof of results](../../record/proofs.md)).
This lock comes on top of the rehearsal; passing one does not replace the other.

Every switch to mainnet (`fuze mode mainnet`, `fuze go-live`, `fuze init` with mainnet) reads `proven` from the public
record on the server the signal comes from (`https://fuze.trade/v1/record`) before it asks you anything:

```json
"proven": {"won": 50, "n": 120, "open": false}
```

Real money opens only when the agent's own check passes: `won` and `n` are whole numbers, `n` is above 0, `won` is
more than half of `n` (exactly half stays locked), and the record says `open` is true. Anything else, an unreachable
server, a slow answer, an error or a field that is missing or malformed, keeps it locked, and the message says why with
the count when it is known:

```text
Real money is locked: 50 of FUZE's 120 proven trades won (41.7%); it opens when more than half have won.
```

The numbers above show the format only; `fuze mode` and the homepage show the live count. An agent already in mainnet keeps
running when the count falls back, so a position is never stranded, and leaving mainnet always works.

The record is not signed. The check can only refuse a switch, so a forged answer could at most take this one lock
away; the rehearsal, the typed confirmations and your own limits stay.

## What the lock is for, and its limit

The lock makes sure the order path has worked against the real exchange, on your setup, before real money is used. The
testnet confirmation means a hand-written record does not unlock mainnet. It cannot prove that the orders were sent by
this copy of FUZE or this version: a program with your shell access could run a real rehearsal, edit FUZE's code, or
read your key. It is a check against mistakes and tools without your access, not a barrier against a program running
as you. See [Security model](../security.md).

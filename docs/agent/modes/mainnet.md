# Lighter mainnet

This page covers following with real money on Lighter. Read it to the end before you type anything.

> **Warning:** you can lose everything on the account it trades. Today the account it follows trades practice money:
> its results cost it nothing, yours cost real money. This is not financial advice. See [Risks, plainly](../../risks.md).

## Before you start

- You ran the agent on testnet and watched it follow, open, protect and close.
- `fuze rehearse` passed on this machine with this version (`fuze mode` tells you), with the same testnet account and
  key index still set: `fuze mode mainnet` asks Lighter testnet to confirm the rehearsal's orders, and stays locked if
  testnet cannot confirm them (also when testnet is down).
- You do not give an AI tool unattended shell access on this machine: the typed confirmations do not stop a program
  that runs as you, and it could read the key. See [Security model](../security.md).
- A **separate** mainnet sub-account holds only money you can afford to lose completely.
- A **separate** mainnet API key, restricted to the BTC and ETH markets, on that sub-account. See
  [Lighter account and API key](../../lighter-setup.md).
- Small sizes: for example 5% of the balance, a cap per position, an exposure cap of 2 and a daily loss stop of 5%.

## Steps

```sh
fuze keys mainnet      # account index, key index, then the key (hidden)
fuze check             # reads the mainnet account; sends no order
fuze flatten           # close what is open in the current mode; stop the agent once it is flat
fuze mode mainnet      # asks Lighter testnet to confirm the rehearsal, then type RAISE and REAL MONEY
fuze unflatten         # type UNFLATTEN
fuze run
```

## While it runs

- `fuze status` shows a REAL MONEY warning, the account's explorer link, what it holds and why.
- The short-term part rests under its take profit and stop loss on Lighter, so it stays protected while the agent is
  down. The rest of each position rests under its [emergency stop](../following.md#5-the-emergency-stop), about 20%
  from the price the agent last saw. Lighter keeps a resting order for 28 days at most, so an agent that is off longer
  than that leaves the position without it.
- A stop loss is a trigger order: in a fast market it can fill worse than its price, or not at all.

## Leaving mainnet

```sh
fuze flatten           # the running agent closes everything
# wait until fuze status shows no positions, then stop the agent (Ctrl+C)
fuze mode simulation   # reads the account to check nothing is open
fuze unflatten         # if you want it to follow in simulation
```

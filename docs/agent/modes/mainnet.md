# Lighter mainnet

This page covers following with real money on Lighter. Read it to the end before you type anything.

> **Warning:** you can lose everything on the account it trades. Today the account it follows trades practice money:
> its results cost it nothing, yours cost real money. This is not financial advice. See [Risks, plainly](../../risks.md).

## Before you start

- You ran the agent on testnet and watched it follow, open, protect and close.
- `fuze rehearse` passed on this machine with this version (`fuze mode` tells you), with the same testnet account and
  key index still set: `fuze mode mainnet` asks Lighter testnet to confirm the rehearsal's orders, and stays locked if
  testnet cannot confirm them (also when testnet is down).
- More than half of FUZE's own proven trades have won. Every switch to mainnet checks FUZE's public record first and
  refuses before it asks anything while they have not; `fuze mode` shows the live count. See
  [The record's lock](rehearsal.md#the-records-lock).
- You do not give an AI tool unattended shell access on this machine: the typed confirmations do not stop a program
  that runs as you, and it could read the key. See [Security model](../security.md).
- An account **of its own** holds only the money you want to trade and can afford to lose completely: best a wallet
  used for nothing else, or a sub-account of the wallet you have. Everything on that account stands behind the
  agent's positions.
- A **balance ceiling**: `fuze go-live` asks how many dollars of the account the agent may count as your balance, and
  sizes on no more than that even if the account holds more. See [Limits](../limits.md#the-balance-ceiling).
- A **separate** mainnet API key, restricted to the markets of the coins you follow (BTC, ETH, HYPE, LIT), on that account. See
  [Lighter account and API key](../../lighter-setup.md).
- Small sizes: for example 5% of the balance, a cap per position, an exposure cap of 2 and a daily loss stop of 5%.

## Steps

The guided way, which asks for each thing in turn and skips what is done:

```sh
fuze go-live
fuze run
```

Or by hand:

```sh
fuze keys mainnet      # account index, key index, then the key (hidden)
fuze check             # reads the mainnet account; sends no order
fuze mode mainnet      # stop the agent first. It closes what is open in the current mode (on Lighter after you
                       # type CLOSE), checks FUZE's record, asks Lighter testnet to confirm the rehearsal, then you
                       # type RAISE and REAL MONEY
fuze run
```

## While it runs

- `fuze status` shows a REAL MONEY warning, the account's explorer link, what it holds and why.
- The short-term part rests under its take profit and stop loss on Lighter, so it stays protected while the agent is
  down. The rest of each position rests under its [emergency stop](../following.md#6-the-emergency-stop), about 20%
  from the price the agent last saw. The agent places it for 28 days (Lighter allows 5 minutes to 30 days) and again
  after 14, so an agent that is off for more than 28 days leaves the position without it.
- A stop loss triggers on the mark price. On Lighter its order price is the worst price it may fill at once triggered,
  and what cannot fill at that price or better is cancelled. The short-term stop loss may fill up to 2% past its
  trigger, the emergency stop up to 4%; in a faster move it does not fill and the position stays open.
- If Lighter's app and API are down, Lighter's documentation describes "priority transactions" that your wallet sends
  straight to its contract on Ethereum: cancel all orders, a reduce-only order that fills at once or not at all, a
  withdrawal. "Everything here works even if Lighter's API is unavailable."
  (https://docs.lighter.xyz/developers/reference/priority-transactions.md). FUZE does not send them; your wallet does.

## Leaving mainnet

```sh
# stop the agent (Ctrl+C)
fuze mode simulation   # type CLOSE: it closes every position with a market order and cancels the open orders
fuze run               # it follows on the simulated account again
```

Your mainnet key, account number and the rehearsal stay on this computer: `fuze mode mainnet` takes you back with the
confirmations only. To remove the key from this computer, `fuze keys mainnet --delete`.

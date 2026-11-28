# The signal

This section explains what FUZE publishes: the account's position, signed, every few seconds and at every change. It
is free, public and read-only: anyone can read it, nobody needs an account, and nothing flows back to us.

## In one paragraph

Every 5 seconds, and the moment anything changes, our signer publishes a small message: per coin, what the account holds
as a multiple of its balance, the price it was computed at, which part is the short-term trade with its take profit and
stop loss, and a sentence saying the same in plain words. Each message is signed with a private key that never leaves
our trading side. Anyone can check the signature against the public key printed in these docs and built into the agent.

## Where to read it

| Address | Returns |
|---|---|
| `https://fuze.trade/v1/signal` | The current message |
| `https://fuze.trade/v1/stream` | A live stream (Server-Sent Events): the current message at once, then every new one |
| `https://fuze.trade/v1/key` | The public key, for information only: never trust a key fetched from the server |
| `https://fuze.trade/v1/record` | Unsigned public numbers for the website: balance, test period, balance curve, the short-term trades with their entries and time stamps, the trend position's entry and emergency stop |

Try it:

```sh
curl -s https://fuze.trade/v1/signal
```

## Pages

| Page | Covers |
|---|---|
| [Positions, not orders](positions.md) | Why we publish what the account holds rather than what it trades |
| [Reading a message](reading.md) | Every field, with a live example |
| [Verifying a message yourself](verify.md) | Checking the signature in a few lines of Python |
| [Freshness and states](states.md) | How long a message is valid, and what live, flat and offline mean |
| [Protocol, version 1](../PROTOCOL.md) | The authoritative specification |

# The signal

This section explains what FUZE publishes: the account's position, signed, every few seconds and at every change. It
is free, public and read-only: anyone can read it, nobody needs an account, and reading it sends us nothing.

## In one paragraph

Every 5 seconds, and the moment anything changes, our signer publishes a small message: per coin (BTC, ETH, HYPE and
LIT), what the account holds as a multiple of its balance, the price it was computed at, how that splits into the slow
trend part and at most one short-term trade with its take profit and stop loss, a risk score for each part, and a
sentence saying the same in plain words. Each message is signed with a private key that never leaves
our trading side. Anyone can check the signature against the public key printed in these docs and built into the agent.

The signal does not know who follows it. It carries no dollar amount, no number of coins and nothing about any
follower: only multiples of our own balance, and prices. The same message serves an agent with $50 and one with
$50,000, in simulation, on the test exchange or with real money. Each agent turns the multiple into its own size from
its own balance and its own limits. Separately, the agent reports its trades and results to our server, as
multiples of its balance and percent; see [What your agent reports](../agent/sharing.md).

## The risk score

Each part of a position carries a score from 0 to 100: how much of our balance that part can lose on a bad day, in
tenths of a percent. A score of 20 means 2% of the balance. Your agent follows a part whole when its score is at or under
your **risk allowed** (standard 60) and skips it whole above it (see [Limits](../agent/limits.md#risk-allowed)).

The score orders how much a part can lose. It does not say how likely a part is to win; nothing we measured does.

## Where to read it

| Address | Returns |
|---|---|
| `https://fuze.trade/v2/signal` | The current message |
| `https://fuze.trade/v2/stream` | A live stream (Server-Sent Events): the current message at once, then every new one |
| `https://fuze.trade/v1/key` | The public key, for information only: never trust a key fetched from the server |
| `https://fuze.trade/v1/record` | Unsigned public numbers for the website: balance, test period, balance curve, the short-term trades with their entries and time stamps, the trend position's entry and emergency stop |

Try it:

```sh
curl -s https://fuze.trade/v2/signal
```

Version 1 (`/v1/signal`, `/v1/stream`: Bitcoin and Ether only, no scores) is still served for agents 0.4.x and 0.5.0.
Agent 0.6.0 reads version 2.

## Pages

| Page | Covers |
|---|---|
| [Positions, not orders](positions.md) | Why we publish what the account holds rather than what it trades |
| [Reading a message](reading.md) | Every field, with a live example |
| [Verifying a message yourself](verify.md) | Checking the signature in a few lines of Python |
| [Freshness and states](states.md) | How long a message is valid, and what live, flat and offline mean |
| [Protocol, version 2](../PROTOCOL.md) | The authoritative specification |

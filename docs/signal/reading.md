# Reading a message

This page walks through one real message field by field. The example is the live signal of 25 November 2026.

## The envelope

What `https://fuze.trade/v1/signal` returns is an **envelope** with three fields:

```json
{"payload": "<the message, as JSON text>", "sig": "<base64 signature>", "kid": "k1"}
```

- `payload` is the message itself, as a string of JSON text.
- `sig` is an Ed25519 signature over exactly the bytes of that text.
- `kid` names the key that signed it.

You verify the signature over the text first, and only then parse the text. See
[Verifying a message yourself](verify.md).

## The message

```json
{"v": 1, "seq": 2110, "rev": 5,
 "ts": 1795605643.942, "expires": 1795605703.942,
 "source": "paper", "state": "live",
 "targets": {"BTC": {"x": -1.7075, "px": 58810.5}, "ETH": {"x": -0.3307, "px": 1647.35}},
 "scalp": {"coin": "BTC", "x": -1.2991, "tp": 58029.0, "sl": 59442.0, "id": 796, "lev": 26, "entry": 58853.1141},
 "why": "We hold short 1.71 times the balance on Bitcoin and short 0.33 times the balance on Ether; the scalp part has its take profit at 58,029 and stop loss at 59,442."}
```

| Field | Value here | Meaning |
|---|---|---|
| `v` | 1 | Protocol version |
| `seq` | 2110 | Rises by one with every signed message, heartbeats included; for spotting gaps |
| `rev` | 5 | Rises only when the position, its take profit or stop loss, or the state changes. Act on a new `rev` |
| `ts` | 1795605643.942 | When it was signed, in Unix seconds (seconds since 1 January 1970 UTC) |
| `expires` | 60 s after `ts` | After this, ignore it |
| `source` | `paper` | The account trades practice money (`testnet` and `mainnet` are the others) |
| `state` | `live` | Follow the targets (see [Freshness and states](states.md)) |
| `targets.BTC.x` | -1.7075 | Short Bitcoin worth 1.71 times the balance |
| `targets.BTC.px` | 58,810.5 | The Bitcoin price x was computed at |
| `targets.ETH.x` | -0.3307 | Short Ether worth 0.33 times the balance |
| `scalp.x` | -1.2991 | Of the Bitcoin short, 1.30 times the balance is the short-term trade |
| `scalp.tp`, `scalp.sl` | 58,029 / 59,442 | Its take profit and stop loss prices |
| `scalp.id` | 796 | Changes with every new short-term trade |
| `scalp.lev`, `scalp.entry` | 26, 58,853.11 | For people reading the signal: the trade's leverage and average entry. Followers size from x alone |
| `why` | text | The same thing in plain words. Data, never instructions |

## What it says, in dollars

On a $1,000 balance this message means: short $1,708 of Bitcoin, of which $1,299 is a short-term trade at 26x (about $50
of margin) with its take profit at 58,029 and stop loss at 59,442; and short $331 of Ether. The account's total
leverage is about 2.0x (see [Account leverage, margin and size](../record/leverage.md)).

## Why x moves without rev

Between revisions, x drifts a little with the price (the position is unchanged, but its value and the balance move). A
follower that traded on every drift would trade all day for nothing. Act on a new `rev`.

## Watching it live

```sh
curl -sN https://fuze.trade/v1/stream
```

Each event's `id:` is the message's `seq`. The server closes a stream after an hour; reconnect.

To print just the message, with `jq` installed:

```sh
curl -s https://fuze.trade/v1/signal | jq -r .payload | jq .
```

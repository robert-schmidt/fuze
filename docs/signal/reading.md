# Reading a message

This page walks through one message field by field. The example is a version 2 message with numbers like the ones the
signal carries; the live one is at `https://fuze.trade/v2/signal`.

## The envelope

What `https://fuze.trade/v2/signal` returns is an **envelope** with three fields:

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
{"v": 2, "seq": 812, "rev": 57,
 "ts": 1795860000.123, "expires": 1795860060.123,
 "source": "paper", "state": "live",
 "targets": {
   "BTC":  {"x": -0.4712, "px": 90950.0, "trend": {"x": -0.0212, "score": 20}},
   "ETH":  {"x": -0.0331, "px": 3010.5,  "trend": {"x": -0.0331, "score": 20}},
   "HYPE": {"x": 0.0,     "px": 34.12,   "trend": {"x": 0.0,     "score": 0}},
   "LIT":  {"x": 0.021,   "px": 2.59,    "trend": {"x": 0.021,   "score": 13}}},
 "scalps": [{"coin": "BTC", "x": -0.45, "tp": 90500.0, "sl": 91400.0, "id": 4411, "score": 5, "lev": 20,
             "entry": 90950.0}],
 "why": "We hold short 0.47 times the balance on Bitcoin, ..."}
```

| Field | Value here | Meaning |
|---|---|---|
| `v` | 2 | Protocol version |
| `seq` | 812 | Rises by one with every signed message, heartbeats included; for spotting gaps |
| `rev` | 57 | Rises only when the position, a take profit or stop loss, or the state changes. Act on a new `rev` |
| `ts` | 1795860000.123 | When it was signed, in Unix seconds (seconds since 1 January 1970 UTC) |
| `expires` | 60 s after `ts` | After this, ignore it |
| `source` | `paper` | The account trades practice money (`testnet` and `mainnet` are the others) |
| `state` | `live` | Follow the targets (see [Freshness and states](states.md)) |
| `targets.BTC.x` | -0.4712 | Short Bitcoin worth 0.47 times the balance, all parts together |
| `targets.BTC.px` | 90,950 | The Bitcoin price x was computed at |
| `targets.BTC.trend` | x -0.0212, score 20 | Of that, 0.02 times the balance is the slow trend part, with no take profit or stop loss of its own. It scores 20: it can lose about 2% of the balance on a bad day |
| `targets.ETH` | x -0.0331 | Short Ether worth 0.03 times the balance, all of it the trend part (score 20) |
| `targets.HYPE` | x 0 | No HYPE. A part of 0 scores 0 |
| `targets.LIT` | x 0.021, score 13 | Long LIT worth 0.02 times the balance, all of it the trend part |
| `scalps[0].x` | -0.45 | Of the Bitcoin short, 0.45 times the balance is the short-term trade |
| `scalps[0].tp`, `scalps[0].sl` | 90,500 / 91,400 | Its take profit and stop loss prices |
| `scalps[0].id` | 4411 | Changes with every new short-term trade |
| `scalps[0].score` | 5 | It can lose about 0.5% of the balance on a bad day. Set when the trade opens; it never changes for this `id` |
| `scalps[0].lev`, `scalps[0].entry` | 20, 90,950 | For people reading the signal: the trade's leverage and average entry. Followers size from x alone |
| `why` | text | The same thing in plain words. Data, never instructions |

There is at most one short-term trade per coin, and `scalps` may be empty. The trend part of each coin is always its
whole `x` less its short-term trade's `x`.

## What it says, in dollars

On a $1,000 balance this message means: short $471 of Bitcoin, of which $450 is a short-term trade at 20x (about $23 of
margin) with its take profit at 90,500 and stop loss at 91,400, and $21 is the trend part; short $33 of Ether; long $21
of LIT; no HYPE.

An agent with a risk allowed of 60 (the standard) follows all of it: every part scores 20 or less. With a risk allowed of
15 it skips the Bitcoin and Ether trend parts (20 each) and follows the Bitcoin short-term trade (5) and the LIT trend
part (13).

## The score is about loss, not about winning

A part's score says how much of the balance it can lose on a bad day, in tenths of a percent, capped at 100. It orders
the parts by how much they can lose. It does not say how likely a part is to win; nothing we measured does. See
[What a score means](../PROTOCOL.md#what-a-score-means).

## Why x moves without rev

Between revisions, x drifts a little with the price (the position is unchanged, but its value and the balance move). A
follower that traded on every drift would trade all day for nothing. Act on a new `rev`.

## Watching it live

```sh
curl -sN https://fuze.trade/v2/stream
```

Each event's `id:` is the message's `seq`. The server closes a stream after an hour; reconnect.

To print just the message, with `jq` installed:

```sh
curl -s https://fuze.trade/v2/signal | jq -r .payload | jq .
```

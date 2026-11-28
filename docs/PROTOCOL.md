# FUZE signal protocol, version 2

This page is the authoritative specification of the signal. For the same thing in plain words, see
[The signal](signal/README.md); to check a message yourself, see [Verifying a message yourself](signal/verify.md).

FUZE publishes **the position its own account holds**, signed. It does not publish orders. An agent that starts late,
reconnects, or misses a message still arrives at the same position.

Version 2 covers four coins, BTC, ETH, HYPE and LIT, and splits each coin's position into parts that carry a **risk
score**. Agent 0.6.0 and later read version 2 only. Version 1 is still served for older agents (see
[Version 1](#version-1) below).

Reading the signal sends nothing: these endpoints take no input. The agent reports its trades and results on a
separate endpoint, signed with a key of its own, never with a key, a balance or a dollar amount; see
[What your agent reports](agent/sharing.md). Nothing in a report reaches the signal or the signer.

## Endpoints (HTTPS, GET only)

| Path | Returns |
|---|---|
| `/v2/signal` | the current envelope |
| `/v2/stream` | Server-Sent Events: the current envelope at once, then each new one (`id:` is `seq`). A stream is closed after an hour; reconnect |
| `/v1/key` | `{"kid", "public_key"}`, for information only. **Agents must not trust it**: the key is pinned in the agent's source |
| `/v1/record` | unsigned public numbers for the website (balance, test period) |

Version 2 is signed with the same key and `kid` as version 1. A v2 message and the v1 message made in the same tick have
the same `seq`, `rev`, `ts` and `expires`.

## Envelope

```json
{"payload": "<compact JSON text>", "sig": "<base64 Ed25519 signature over exactly the bytes of payload>", "kid": "k1"}
```

The signature covers the payload **text**. Verify first, parse after. Never re-serialise before verifying.

## Payload

```json
{"v": 2, "seq": 812, "rev": 57, "ts": 1795860000.123, "expires": 1795860060.123,
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

| Field | Meaning |
|---|---|
| `v` | protocol version: `2`. Ignore a message whose `v` you do not know |
| `seq` | rises by one with every signed message, heartbeats included. For spotting gaps; it may restart if the signer is rebuilt, so it is not the replay guard |
| `rev` | rises only when our position, a stop loss / take profit, or `state` changed. **Act on a new `rev`**, not on every message: `x` drifts with the price while our position does not |
| `ts`, `expires` | unix seconds. `ts` rises with every message and **is the replay guard**. A message is valid until `expires` (60 s after `ts`); a heartbeat comes every 5 s |
| `source` | the account we trade: `paper` (practice money), `testnet`, `mainnet`. Independent of the follower's own mode: since `x` is a ratio, a follower in any mode (simulation, testnet, mainnet) can follow any source; an agent should say so when its mode risks more real money than the source |
| `state` | `live`: follow `targets`. `flat`: we closed everything and are staying out; close and stay out. `offline`: we have no fresh reading; hold what you have, open nothing new |
| `targets[coin].x` | the whole position on that coin, divided by our balance. Negative is short. `0` means none |
| `targets[coin].px` | the price `x` was computed at |
| `targets[coin].trend` | `{"x", "score"}`: the part of the coin's position with no take profit and stop loss of its own (the slow trend part). It carries the emergency stop only |
| `scalps` | the short-term trades: a list, possibly empty, at most one per coin. Each is the part of that coin's position with its own take profit `tp` and stop loss `sl` (prices), with its `x`, its `id` (a new one for every new trade) and its `score`. `lev` (the leverage the trade was opened with) and `entry` (its average entry price) are for people reading the page; a follower sizes from `x` alone and ignores them |
| `why` | the same thing in plain words |

## Rules

An agent refuses a message that breaks any of these, as it refuses a message with a bad signature.

- `seq`, `rev`: whole numbers from 0. `ts`, `expires`: finite, `expires` after `ts` and at most 60 s after it.
  `source` and `state`: one of the values above. `why`: text of at most 2,000 characters.
- `targets`: only the coins BTC, ETH, HYPE, LIT. Each has `x` (from -50 to 50), `px` (more than 0) and
  `trend: {"x", "score"}`. `state: "live"` needs at least one target.
- `scalps`: a list, possibly empty, **at most one per coin**, each coin present in `targets`. Each has `coin`, `x` (not
  0, the same sign as the coin's `x`, `|x|` not larger than the coin's `|x|` + 0.000001), `tp` and `sl` (more than 0),
  `id` (a whole number) and `score`.
- `trend.x` is the coin's `x` less that coin's scalp `x` (or less 0 when the coin has no scalp), within 0.001.
- `score`: a whole number from 0 to 100. A part with `x == 0` has score 0. A scalp's score is **fixed for its `id`**: it
  is set when the trade opens and never changed by later adds. A trend part's score changes only when the trend book
  decides (every 4 hours), not with the price.

## What a score means

How much of our balance the part can lose on a bad day, in tenths of a percent, capped at 100. A score of 20 means 2% of
the balance.

- A short-term trade: `round(10 × |x at open| × 103 / 100)`, that is 10.3 times its multiple at open. The 103 is a stop
  at most 1% from the entry (100 basis points, the widest stop the rules allow) plus 3 for costs.
- A trend part: `round(78.5 × |x| × yearly volatility)`, taken from the trend book's own decision, so it moves only
  every 4 hours.

**The score orders how much a part can lose. It does not say how likely a part is to win; nothing we measured does.**
A low score is not a sign of a good trade, and a high score is not a sign of a bad one.

## How an agent uses it

Each agent has two settings: `risk_allowed` (0 to 100, standard 60) and `coins` (a list among BTC, ETH, HYPE, LIT,
standard all four). For each coin:

- not in `coins`: the agent wants 0 of it. It never opens it, closes what it holds of it, and ignores its scalp.
- in `coins`: `want = (trend.x if trend.score <= risk_allowed else 0) + (scalp.x if there is one and scalp.score <=
  risk_allowed else 0)`. A part is followed whole or skipped whole. A scalp the agent takes keeps its take profit and
  stop loss; a scalp it skips gets none. The part left without a take profit and stop loss carries the emergency stop.

Then the agent's own limits apply exactly as before: share of balance or fixed amount, cap per position, exposure cap,
balance ceiling, daily loss stop and the smallest order. Our own account takes every part: it is the source, and an
agent set to 100 does the same.

## What an agent must check, in this order

1. `kid` is a key pinned in its own source, and `sig` verifies over `payload` with that key.
2. `v == 2`.
3. `ts` is greater than the last `ts` it accepted (kept on disk, so a restart does not reset it).
4. `now < expires`, and `ts` is not more than 30 s in the future.

The agent also checks every rule above and drops a signed message that breaks one. It keeps only the fields named here.
A replayed message is at most 60 s old and never newer than one already accepted, so it cannot move a follower back to
an earlier position.

Anything that fails is dropped without acting. With no valid message for 60 s the agent treats the signal as `offline`.

## Following

A follower's position value for a coin is `want × percent/100 × its own balance` (a share of its balance) or
`want × fixed_usd` (a fixed amount), then cut to its own cap per position and exposure cap; units = value / price. The
limits are local and the signal cannot loosen them. A follower must not hold a constant dollar size regardless of `x`:
when a short-term trade closes, `x` shrinks but keeps its sign, and such a follower would never exit that part. Each
short-term part should rest under its own stop loss and take profit **on the exchange**, so it stays protected when the
agent or the signal is down.

## Version 1

The server still serves version 1 at `/v1/signal` and `/v1/stream`, unchanged, so agents 0.4.x and 0.5.0 keep working.
It covers Bitcoin and Ether only, has one `scalp` (on Bitcoin, or `null`) instead of `scalps`, and no scores. Agent
0.6.0 refuses a version 1 message and says why: "a version 1 message: this agent reads version 2 of the signal
(/v2/signal)".

## Test vectors

`tests/vectors.json`, signed with a published test key (the Ed25519 private key whose 32 bytes are 0, 1, 2, ... 31):

- `valid`: three version 2 envelopes. A position on all four coins with a Bitcoin short-term trade, a heartbeat with the
  same `rev`, and `rev` 2 with that short-term trade closed;
- `tampered`: the first one with its payload changed after signing;
- `v1`: the version 1 envelopes that earlier releases tested with. This agent refuses them.

Never pin the test key in a release.

## Signing key

| kid | Ed25519 public key (base64) |
|---|---|
| `k1` | `4YwkvSXI90nvycvuDte8h9N1ULf00v+PM95Yj3+8iNU=` |

A new key is announced in a release of this repository, never over the API.

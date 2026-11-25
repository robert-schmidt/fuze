# FUZE signal protocol, version 1

FUZE publishes **the position its own account holds**, signed. It does not publish orders. An agent that starts late,
reconnects, or misses a message still arrives at the same position.

Nothing flows back: the server takes no input, and an agent never sends it a key, a balance or a position.

## Endpoints (HTTPS, GET only)

| Path | Returns |
|---|---|
| `/v1/signal` | the current envelope |
| `/v1/stream` | Server-Sent Events: the current envelope at once, then each new one (`id:` is `seq`). A stream is closed after an hour; reconnect |
| `/v1/key` | `{"kid", "public_key"}`, for information only. **Agents must not trust it**: the key is pinned in the agent's source |
| `/v1/record` | unsigned public numbers for the website (balance, test period) |

## Envelope

```json
{"payload": "<JSON text>", "sig": "<base64 Ed25519 signature over exactly the bytes of payload>", "kid": "k1"}
```

The signature covers the payload **text**. Verify first, parse after. Never re-serialise before verifying.

## Payload

```json
{"v": 1, "seq": 42, "rev": 7, "ts": 1795594970.328, "expires": 1795595030.328,
 "source": "paper", "state": "live",
 "targets": {"BTC": {"x": -1.7851, "px": 58865.5}, "ETH": {"x": -0.325, "px": 1640.85}},
 "scalp": {"coin": "BTC", "x": -1.3818, "tp": 58478.0, "sl": 59424.0, "id": 795},
 "why": "We hold short 1.79 times the balance on Bitcoin ..."}
```

| Field | Meaning |
|---|---|
| `v` | protocol version. Ignore a message whose `v` you do not know |
| `seq` | rises by one with every signed message, heartbeats included. For spotting gaps; it may restart if the signer is rebuilt, so it is not the replay guard |
| `rev` | rises only when our position, its stop loss / take profit, or `state` changed. **Act on a new `rev`**, not on every message: `x` drifts with the price while our position does not |
| `ts`, `expires` | unix seconds. `ts` rises with every message and **is the replay guard**. A message is valid until `expires` (60 s after `ts`); a heartbeat comes every 5 s |
| `source` | the account we trade: `paper` (practice money), `testnet`, `mainnet`. Independent of the follower's own mode: since `x` is a ratio, a follower in any mode (simulation, testnet, mainnet) can follow any source; an agent should say so when its mode risks more real money than the source |
| `state` | `live`: follow `targets`. `flat`: we closed everything and are staying out; close and stay out. `offline`: we have no fresh reading; hold what you have, open nothing new (`targets` is empty) |
| `targets[coin].x` | our position value divided by our balance. Negative is short. `0` means none |
| `targets[coin].px` | the price `x` was computed at |
| `scalp` | the part of that coin's position that has its own take profit `tp` and stop loss `sl` (prices). `null` when there is none. `x` is that part alone and is included in `targets`. `id` changes with every new scalp. It may also carry `lev` (the leverage that trade was opened with; its margin is its size divided by `lev`) and `entry` (its average entry price): both are for people reading the signal, and a follower sizes from `x` alone |
| `why` | the same thing in plain words |

## What an agent must check, in this order

1. `kid` is a key pinned in its own source, and `sig` verifies over `payload` with that key.
2. `v == 1`.
3. `ts` is greater than the last `ts` it accepted (kept on disk, so a restart does not reset it).
4. `now < expires`, and `ts` is not more than 30 s in the future.

The agent also checks the shape of every field (finite numbers, known coins, a sane `x`) and drops a signed message that
fails. A replayed message is at most 60 s old and never newer than one already accepted, so it cannot move a follower
back to an earlier position.

Anything that fails is dropped without acting. With no valid message for 60 s the agent treats the signal as `offline`.

## Following

A follower's position value for a coin is `x × percent/100 × its own balance` (a share of its balance) or
`x × fixed_usd` (a fixed amount), then cut to its own cap per position and exposure cap; units = value / price. The
limits are local and the signal cannot loosen them. A follower must not hold a constant dollar size regardless of `x`:
when a scalp closes, `x` shrinks but keeps its sign, and such a follower would never exit that part. The scalp part should rest under a stop loss and take profit **on the exchange**,
so it stays protected when the agent or the signal is down.

## Test vectors

`tests/vectors.json`: three valid envelopes (a position with a scalp, a heartbeat with the same `rev`, the scalp closed
with a new `rev`) and one tampered envelope, signed with a published test key. Never pin the test key in a release.

## Signing key

| kid | Ed25519 public key (base64) |
|---|---|
| `k1` | `4YwkvSXI90nvycvuDte8h9N1ULf00v+PM95Yj3+8iNU=` |

A new key is announced in a release of this repository, never over the API.

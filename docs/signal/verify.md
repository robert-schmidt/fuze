# Verifying a message yourself

This page shows how to check that a message really comes from FUZE and has not been changed, in a few lines of Python.
The agent does exactly this on every message.

## What you need

- Python 3 with the `cryptography` package (`pip install cryptography`).
- The public key, from these docs or the agent's source. **Never** take the key from the server: someone who could
  forge messages could also serve a fake key.

| kid | Ed25519 public key (base64) |
|---|---|
| `k1` | `4YwkvSXI90nvycvuDte8h9N1ULf00v+PM95Yj3+8iNU=` |

## The script

Save as `verify_signal.py` and run it with `python3 verify_signal.py`:

```python
import base64, json, time, urllib.request
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

PINNED = {"k1": "4YwkvSXI90nvycvuDte8h9N1ULf00v+PM95Yj3+8iNU="}  # from the protocol page, never from the server

env = json.load(urllib.request.urlopen("https://fuze.trade/v2/signal"))
key = Ed25519PublicKey.from_public_bytes(base64.b64decode(PINNED[env["kid"]]))
key.verify(base64.b64decode(env["sig"]), env["payload"].encode())  # raises InvalidSignature if forged
msg = json.loads(env["payload"])                                    # parse only after verifying
assert msg["v"] == 2 and time.time() < msg["expires"]
print(msg["state"], msg["rev"], msg["why"])
```

If the signature is wrong, `verify` raises `InvalidSignature` and nothing after it runs. An unknown `kid` raises
`KeyError`.

## The order of checks

1. The `kid` is one you pinned, and the signature verifies over the payload **text**. Never re-format the JSON before
   verifying: the signature covers the exact bytes.
2. `v` is 2. A version 1 message (from `/v1/signal`) is refused by agent 0.6.0.
3. `ts` is newer than the newest message you accepted before. Keep that timestamp on disk, so a restart cannot be fed an
   old message. (The agent keeps it in its `guard.json` file.)
4. Now is before `expires`, and `ts` is not more than 30 seconds in the future.

Then check every field's type and range, and the rules of [the protocol](../PROTOCOL.md#rules): only the four coins,
at most one short-term trade per coin, each coin's trend part equal to its x less its short-term trade, scores whole
numbers from 0 to 100. Anything that fails is dropped without acting.

## What a signature does and does not prove

It proves the message was signed with FUZE's key and not changed since. It does not prove the trade is wise, and it
cannot protect you if the signing key itself were stolen. That is why the agent's own limits apply to every message:
see [Security model](../agent/security.md).

## The key changes only in a release

A new key would be announced in a release of the agent's repository, never through the API. The website and the
protocol page also show it, and both should match what you pinned.

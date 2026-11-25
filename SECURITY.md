# Security

Users' money will be at stake once real following exists, so security decides every trade-off in this project.
v0.1 follows on a simulated account only: it has no exchange code, no keys and no money.

## Reporting a vulnerability

Email **security@fuze.trade (not live yet)**. Until that address works, open a GitHub security advisory on this
repository ("Report a vulnerability"); please do not open a public issue for a security problem.

## Threat model

| Threat | How it is handled |
|---|---|
| **Forged signal** | Every message is an Ed25519 signature over the exact payload text, checked against a key built into the code (`PINNED` in `src/fuze/protocol.py`). The key is never fetched from the server; `/v1/key` is for information only. A new key comes only in a new release. The published test key is never pinned. |
| **Replayed or delayed signal** | Each accepted sequence number is written to `~/.fuze/guard.json`; anything not higher is dropped, also after a restart. A message is dropped once it expires (60 s after it was signed) or if it claims to be more than 30 s in the future. |
| **Malformed signal** (signed but odd) | After the signature, every field is checked: whole numbers where expected, finite numbers, sizes within ±50 times the balance, only BTC and ETH, only the three known states, a scalp that is part of its coin's position. Anything else is dropped. A scalp whose stop loss is on the wrong side or more than 1.5% away is not opened. |
| **Compromised FUZE server or signing key** | A valid signature proves who signed, not that the trade is wise. Your local limits bound the damage: `scale`, the exposure cap `max_x`, the daily loss stop, and the size checks above. The signal cannot loosen them. `fuze flatten` closes everything. The server takes no input from agents, so it cannot read your account or keys. |
| **Network attacker** | HTTPS with certificate checks always on; plain http only for `localhost`. Redirects are refused (they could downgrade to http or leave the server). Responses are size-limited. Even a successful attacker cannot forge signatures. |
| **Stale or dead stream** | No valid message for 60 s, or the signal says `offline`: the agent holds and opens nothing new. With `stale_flat_min` set, it closes everything after that long. The stream falls back to polling every 2 s and reconnects with back-off. Once real exchanges exist, the scalp part rests under a stop loss and take profit on the exchange, so it stays protected when the agent is down. |
| **Prompt injection through an AI tool** | The MCP server can only read status and reduce risk: pause, flatten, lower limits. It cannot resume, unflatten, raise a limit, change the server or mode, place orders, or read or write outside `~/.fuze`. A tricked AI can at worst make you safer. Raising risk needs you at a terminal typing `RAISE`. The signal's `why` text is marked as data, stripped of control characters and length-limited. |
| **Key leakage** (for later real following) | v0.1 has no keys. Later: keys live only in `~/.fuze` (folder 0700, files 0600), never leave your machine (orders are signed locally), are never shown to an AI tool, and never logged; a filter already removes long hex strings from every log line. Use a dedicated sub-account holding only what you can lose; see [docs/lighter-setup.md](docs/lighter-setup.md). Never paste a private key or API key into a chat. |
| **Two agents on one folder** | `fuze run` takes a lock; a second one refuses to start, so orders are never doubled. |
| **Supply chain** | Two runtime dependencies: `cryptography` and the official `mcp` SDK. The trading loop never imports `mcp`. Pin exact versions with hashes (below). Releases are tagged; check the tag before you update. |

## Install with pinned hashes

A plain `pip install` trusts whatever the package index serves today. To install exactly what you reviewed:

```sh
# once, on a machine you trust: resolve exact versions of FUZE and everything it needs, with hashes
echo "fuze-agent==0.1.0" > requirements.in
uv pip compile --generate-hashes -o requirements.txt requirements.in   # or: pip-compile --generate-hashes
# every install: pip refuses any file whose hash does not match
python3 -m venv ~/.fuze-venv
~/.fuze-venv/bin/pip install --require-hashes --no-deps -r requirements.txt
```

The full set is about 30 packages, almost all of them pulled in by the MCP SDK. `pyproject.toml` only sets lower bounds (and `mcp<3`, because the MCP SDK's last major release changed its API). Keep
your `requirements.txt` in your own version control and review the difference when you update it.

## Risks (not a security bug)

FUZE copies one account's trading. Most scalping rules we have tested lose money after costs; past results promise
nothing; you can lose everything you put in. This is not financial advice. See the Risks section of the
[README](README.md#risks).

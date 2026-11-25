# Security

Users' money is at stake in mode `mainnet`, so security decides every trade-off in this project. Three modes:
`simulation` (no exchange, no keys, no money), `testnet` and `mainnet` (Lighter, with an API key you type in). The
Lighter code is new and has not yet been proven against the real exchange; it is tested against a fake one.

## Reporting a vulnerability

Email **security@fuze.trade (not live yet)**. Until that address works, open a GitHub security advisory on this
repository ("Report a vulnerability"); please do not open a public issue for a security problem.

## Threat model

| Threat | How it is handled |
|---|---|
| **Forged signal** | Every message is an Ed25519 signature over the exact payload text, checked against a key built into the code (`PINNED` in `src/fuze/protocol.py`). The key is never fetched from the server; `/v1/key` is for information only. A new key comes only in a new release. The published test key is never pinned. |
| **Replayed or delayed signal** | Each accepted sequence number is written to `~/.fuze/guard.json`; anything not higher is dropped, also after a restart. A message is dropped once it expires (60 s after it was signed) or if it claims to be more than 30 s in the future. |
| **Malformed signal** (signed but odd) | After the signature, every field is checked: whole numbers where expected, finite numbers, sizes within ±50 times the balance, only BTC and ETH, only the three known states, a scalp that is part of its coin's position. Anything else is dropped. A scalp whose stop loss is on the wrong side or more than 1.5% away is not opened. |
| **Compromised FUZE server or signing key** | A valid signature proves who signed, not that the trade is wise. Your local limits bound the damage: your sizing (a share of your balance or a fixed amount), the cap per position, the exposure cap `max_x` (always against your real balance), the daily loss stop, and the size checks above. The signal cannot loosen them. `fuze flatten` closes everything. The server takes no input from agents, so it cannot read your account or keys. |
| **Network attacker** | HTTPS with certificate checks always on; plain http only for `localhost`. Redirects are refused (they could downgrade to http or leave the server). Responses are size-limited. Even a successful attacker cannot forge signatures. |
| **Stale or dead stream** | No valid message for 60 s, or the signal says `offline`: the agent holds and opens nothing new. With `stale_flat_min` set, it closes everything after that long. The stream falls back to polling every 2 s and reconnects with back-off. On Lighter the scalp part rests under its stop loss and take profit on the exchange, so it stays protected when the agent is down. |
| **Prompt injection through an AI tool** | The MCP server can only read status and reduce risk: pause, flatten, lower limits. It cannot resume, unflatten, raise a limit, remove a cap, switch the sizing mode, change the server or mode, take or show a key, place orders, or read or write outside `~/.fuze`. A tricked AI can at worst make you safer. Raising risk (also through `fuze init --force`) needs you at a terminal typing `RAISE`; `--yes` does not count. The signal's `why` text is marked as data, stripped of control characters and length-limited. |
| **Key leakage** | Only a Lighter **API key**, never a wallet's private key or recovery phrase. It is typed by you with `fuze keys testnet` / `mainnet` at a terminal (hidden, refused when input is not a terminal), never accepted as a command-line argument or an MCP argument. Stored in the OS keyring when the `keyring` package has a backend, otherwise in `~/.fuze/lighter-<mode>.key` (0600, folder 0700); `FUZE_NO_KEYRING=1` forces the file. Orders are signed on your machine by Lighter's SDK; the key never leaves it. It is never printed, logged, written to status.json, or read by the MCP server (which only reports "set" or "missing"); errors from the SDK are reduced to their type so they cannot quote it, and a filter removes long hex strings from every log line. Tests check the key appears in no output, log, status file or MCP tool result. Use a key restricted to the BTC and ETH markets on a sub-account holding only what you can lose: such a key can only trade those markets, and per Lighter's docs no API key alone can send funds to another owner. See [docs/lighter-setup.md](docs/lighter-setup.md). Never paste a key into a chat. |
| **Real money by mistake** | The mode is changed only with `fuze mode` at a terminal, with the agent stopped and nothing open in the current mode. Moving toward real money asks you to type `RAISE`; mainnet also `REAL MONEY`, and only after `fuze rehearse` passed on testnet on this machine with this version (it opens, protects, unprotects and closes the smallest position, each step confirmed by an account read). `fuze run` checks the rehearsal again, so a hand-edited config.json does not start mainnet. `fuze init` without a terminal always saves `simulation`. Honest limit: anyone (or any AI tool) with shell access as your user can edit files in `~/.fuze`; the rules in AGENTS.md forbid it, and the MCP server has no route to it. |
| **Orders that go wrong** | After every order the account is read back before anything else; a fill that is missing or partial stops the step and the next try waits 60 s and starts from a new account read, so no blind second order. The order in flight is written to `pending.json` before it is sent: after a crash or restart the agent waits, reads the account and settles it, never resends. Reductions are reduce-only; every market order has a worst price. If the take profit / stop loss of the scalp part cannot be seen on the exchange after placing, that part is closed. An unreadable account means no orders. |
| **Two agents on one folder** | `fuze run` takes a lock; a second one refuses to start, so orders are never doubled. |
| **Supply chain** | One runtime dependency, `cryptography`; optional: the official `mcp` SDK (for `fuze mcp`; the trading loop never imports it), and for testnet / mainnet `lighter-sdk` 1.1.8 (pinned exactly; Lighter's official SDK, which ships a native signing library) and `keyring`. Simulation imports neither. Pin exact versions with hashes (below). Releases are tagged; check the tag before you update. |

## Install with pinned hashes

A plain `pip install` trusts whatever the package index serves today. To install exactly what you reviewed:

```sh
# once, on a machine you trust: resolve exact versions of FUZE and everything it needs, with hashes
echo "fuze-agent[lighter]==0.2.0" > requirements.in   # or fuze-agent==0.2.0 for simulation only
uv pip compile --generate-hashes -o requirements.txt requirements.in   # or: pip-compile --generate-hashes
# every install: pip refuses any file whose hash does not match
python3 -m venv ~/.fuze-venv
~/.fuze-venv/bin/pip install --require-hashes --no-deps -r requirements.txt
```

The full set is about 30 packages, almost all of them pulled in by the MCP SDK (more with `[lighter]`). `pyproject.toml` only sets lower bounds (and `mcp<3`, because the MCP SDK's last major release changed its API). Keep
your `requirements.txt` in your own version control and review the difference when you update it.

## Risks (not a security bug)

FUZE copies one account's trading. Most scalping rules we have tested lose money after costs; past results promise
nothing; you can lose everything you put in. This is not financial advice. See the Risks section of the
[README](README.md#risks).

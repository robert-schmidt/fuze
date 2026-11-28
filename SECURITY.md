# Security

Users' money is at stake in mode `mainnet`, so security decides every trade-off in this project. Three modes:
`simulation` (no exchange, no keys, no money), `testnet` and `mainnet` (Lighter, with an API key you type in). Mainnet
stays locked on each machine until that machine has passed `fuze rehearse` on testnet, for each new version. The agent
has had no independent security review.

## Reporting a vulnerability

Report it privately: open a GitHub security advisory at
https://github.com/robert-schmidt/fuze/security/advisories/new ("Report a vulnerability"). Please do not open a
public issue for a security problem.

## Threat model

| Threat | How it is handled |
|---|---|
| **Forged signal** | Every message is an Ed25519 signature over the exact payload text, checked against a key built into the code (`PINNED` in `src/fuze/protocol.py`). The key is never fetched from the server; `/v1/key` is for information only. A new key comes only in a new release. The published test key is never pinned. |
| **Replayed or delayed signal** | The time stamp (`ts`) of each accepted message is written to `~/.fuze/guard.json`; a message whose `ts` is not later is dropped, also after a restart (`seq` is only for spotting gaps, as docs/PROTOCOL.md says). A message is dropped once it expires, if it claims to live longer than the protocol's 60 s after `ts`, or if it claims to be more than 30 s in the future. |
| **Malformed signal** (signed but odd) | After the signature, every field is checked: whole numbers where expected, finite numbers, sizes within ±50 times the balance, only BTC and ETH, only the three known states, a scalp that is part of its coin's position. Anything else is dropped. A scalp whose stop loss is on the wrong side or more than 1.5% away is not opened. |
| **Compromised FUZE server or signing key** | A valid signature proves who signed, not that the trade is wise. Your local limits bound the damage: your sizing (a share of your balance or a fixed amount), the cap per position, the exposure cap `max_x` (always against your real balance), the daily loss stop, and the size checks above. The signal cannot loosen them. `fuze flatten` closes everything. The agent's reports to the server carry no key and no balance, and nothing the server answers reaches a decision, so it cannot read your account or keys. |
| **Network attacker** | HTTPS with certificate checks always on; plain http only for `localhost`. Redirects are refused (they could downgrade to http or leave the server). Responses are size-limited. Even a successful attacker cannot forge signatures. |
| **Stale or dead stream** | No valid message for 60 s, or the signal says `offline`: the agent holds and opens nothing new. With `stale_flat_min` set, it closes everything after that long. The stream falls back to polling every 2 s and reconnects with back-off. On Lighter the scalp part rests under its stop loss and take profit on the exchange, so it stays protected when the agent is down. |
| **Prompt injection through an AI tool** | The MCP server can only read status and reduce risk: pause, flatten, lower limits. It cannot resume, unflatten, raise a limit, remove a cap, switch the sizing mode, change the server or mode, take or show a key, place orders, or read or write outside `~/.fuze`. A tool given an argument it does not take refuses (it never silently ignores `mode` or `api_key`, and never echoes or logs the value), and a switch with no agent in the server's folder is an error naming that folder, not a silent success. A tricked AI can at worst make you safer through the MCP server. Raising risk (also through `fuze init --force`), `fuze resume` and `fuze unflatten` need a terminal and a typed word (`RAISE`, `RESUME`, `UNFLATTEN`); `--yes` does not count. See "What the confirmations protect against" below for what that does not stop. The signal's `why` text is marked as data, stripped of control characters and length-limited. |
| **Key leakage** | Only a Lighter **API key**, never a wallet's private key or recovery phrase. It is typed by you with `fuze keys testnet` / `mainnet` at a terminal (hidden, refused when input is not a terminal), never accepted as a command-line argument or an MCP argument. Stored in the OS keyring when the `keyring` package has a backend, otherwise in `~/.fuze/lighter-<mode>.key` (0600, folder 0700); `FUZE_NO_KEYRING=1` forces the file. Orders are signed on your machine by Lighter's SDK; the key never leaves it. It is never printed, logged, written to status.json, or read by the MCP server (which only reports "set" or "missing"); errors from the SDK are reduced to their type so they cannot quote it, and a filter removes long hex strings from every log line. Tests check the key appears in no output, log, status file or MCP tool result. Use a key restricted to the BTC and ETH markets on a sub-account holding only what you can lose: such a key can only trade those markets, and per Lighter's docs no API key alone can send funds to another owner. See [docs/lighter-setup.md](docs/lighter-setup.md). Never paste a key into a chat. |
| **Real money by mistake** | The mode is changed only with `fuze mode` at a terminal, with the agent stopped and nothing open in the current mode. Moving toward real money asks you to type `RAISE`; mainnet also `REAL MONEY`, and only after `fuze rehearse` passed on testnet on this machine with this version (it opens, protects, unprotects and closes the smallest position, each step confirmed by an account read, and records the account, key index, time, version and each order's transaction hash). `fuze mode mainnet` asks Lighter testnet to confirm that record: the stored testnet key must be accepted for that account and key index, and each recorded transaction must exist on testnet, belong to that account, be signed with that key index and be from the recorded time; when testnet cannot confirm it (also when it is down) mainnet stays locked. `fuze run` checks the local rehearsal record only (no network at start). `fuze init` without a terminal always saves `simulation`. Honest limit: these are checks against the MCP server, scripts and mistakes, not a lock against a program running as you (next section). |
| **Orders that go wrong** | After every order the account is read back before anything else; a fill that is missing or partial stops the step and the next try waits 60 s and starts from a new account read, so no blind second order. The order in flight is written to `pending.json` before it is sent: after a crash or restart the agent waits, reads the account and settles it, never resends. Reductions are reduce-only; every market order has a worst price. If the take profit / stop loss of the scalp part cannot be seen on the exchange after placing, that part is closed. An unreadable account means no orders. |
| **The local page (`fuze ui`)** | Read-only: no request trades or changes a setting. It listens on 127.0.0.1 only, with no option to bind anything else; it answers only when the Host header is `127.0.0.1:<port>` or `localhost:<port>`, so a web page that points its own name at your machine (DNS rebinding) gets nothing; GET only; a fixed list of files read from the package at start, the query string ignored, nothing in a request reaches the filesystem; a strict Content-Security-Policy, no inline script or style, nothing loaded from elsewhere. Its JSON is built field by field: the key state is "set" or "missing", never the key or where it is stored. When the agent is not running it reads the public signal itself, checked against the pinned key, and writes nothing. Honest limit: any program running as your user can read the page, as it can read `~/.fuze`. |
| **Reports to the FUZE server** | Every agent reports its trades and results (`src/fuze/report.py`; the full list in [docs/agent/sharing.md](docs/agent/sharing.md)): sizes as multiples of the balance and results in percent, never a dollar amount, a balance, a key or anything about the computer. Each report is signed with a key the agent made on your machine (`~/.fuze/agent.key`, 0600, never printed; an unreadable or malformed file is said, never silently replaced) and carries a counter that only goes up. Reports go out from a queue on a thread of their own: the trading loop only hands a report over (tests prove a sender that always fails or never answers changes nothing in trading); HTTPS with certificate checks, no redirects, a 5-second timeout, a size-limited answer that no trading code reads. Public or private is changed only with `fuze share` at a terminal; the MCP server has no tool for it. The read-only Lighter token for `fuze share prove` lasts a minute, is sent once after you type `YES`, and is never logged or written to disk. |
| **Two agents on one folder** | `fuze run` takes a lock; a second one refuses to start, so orders are never doubled. |
| **Supply chain** | One runtime dependency, `cryptography`; optional: the official `mcp` SDK (for `fuze mcp`; the trading loop never imports it), and for testnet / mainnet `lighter-sdk` 1.1.8 (pinned exactly; Lighter's official SDK, which ships a native signing library) and `keyring`. Simulation imports neither. Pin exact versions with hashes (below). Releases are tagged; check the tag before you update. |

## What the confirmations protect against

The terminal checks and typed words (`RAISE`, `REAL MONEY`, `RESUME`, `UNFLATTEN`) and the rehearsal lock stop the
MCP tools (they have no route to any of it), programs that run without a terminal, and mistakes. They are **not** a
barrier against a program that already runs as you with shell access. Such a program can do whatever you can: drive a
pseudo-terminal that types `RAISE` (a one-line `expect` script does), edit `config.json` and `rehearsal.json`, or change
FUZE's own code, and it could equally read your API key from the keyring or the key file. The testnet confirmation of
the rehearsal makes a hand-written record useless, but a program with your access could also run a real rehearsal.
`AGENTS.md` tells coding agents not to do any of this; that is a request, not a lock.

The protection for your money is therefore on the exchange side: a Lighter **sub-account** holding only what you are
willing to lose, and an **API key that cannot withdraw** (restricted to the BTC and ETH markets: per Lighter's docs it
can then only create, modify and cancel orders there; see [docs/lighter-setup.md](docs/lighter-setup.md)). **Do not
give an AI tool unattended shell access on a machine that holds a mainnet key.**

## Install with pinned hashes

Install FUZE only from `github.com/robert-schmidt/fuze`. A plain install of the dependencies trusts whatever the
package index serves today. To install exactly what you reviewed:

```sh
# once, on a machine you trust, in a clone (git clone https://github.com/robert-schmidt/fuze) at the commit or tag
# you reviewed: exact versions with hashes
echo "setuptools>=77" > build.in                       # the build backend, so nothing unpinned is fetched to build
uv pip compile --generate-hashes --extra mcp --extra lighter pyproject.toml build.in -o requirements.txt
#   (drop --extra lighter for simulation only; pip-compile --generate-hashes --extra mcp ... works too)
# every install: pip refuses any file whose hash does not match, then FUZE itself from the reviewed clone
python3 -m venv ~/.fuze-venv
~/.fuze-venv/bin/pip install --require-hashes --no-deps -r requirements.txt
~/.fuze-venv/bin/pip install --no-deps --no-build-isolation .
```

The full set is about 30 packages, almost all of them pulled in by the MCP SDK (more with `[lighter]`). `pyproject.toml` only sets lower bounds (and `mcp<3`, because the MCP SDK's last major release changed its API). Keep
your `requirements.txt` in your own version control and review the difference when you update it.

## Risks (not a security bug)

FUZE copies one account's trading. Most scalping rules we have tested lose money after costs; past results promise
nothing; you can lose everything you put in. This is not financial advice. See the Risks section of the
[README](README.md#risks).

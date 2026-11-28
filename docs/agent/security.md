# Security model

This page explains what the agent protects you against, how, and where its protection ends. It is the plain-words
version of the repository's `SECURITY.md`.

> **Warning:** the agent has had **no independent security review**. Start in simulation, then testnet.

## What it protects against

| Threat | How it is handled |
|---|---|
| A forged signal | Every message is signed (Ed25519) and checked against a key built into the agent's code. The key is never fetched from the server; a new one comes only in a new release |
| A replayed or delayed signal | The timestamp of the newest accepted message is kept on disk (`guard.json`); anything not newer is dropped, also after a restart. Expired messages, messages that claim to live longer than 60 seconds, and messages from the future are dropped |
| A malformed signal | After the signature, every field is checked: types, finite numbers, sizes within 50 times the balance, only BTC, ETH, HYPE and LIT, at most one short-term trade per coin, risk scores 0 to 100, known states. A version 1 message is refused. A short-term part whose stop is on the wrong side or more than 1.5% away is not opened |
| A compromised FUZE server or signing key | A valid signature proves who signed, not that the trade is wise. Your limits bound the damage: sizing, cap per position, exposure cap against your real balance, daily loss stop. The signal cannot loosen them. The agent's reports carry no key and no balance, and nothing the server answers reaches a decision, so it cannot read your account |
| A network attacker | HTTPS with certificate checks always on; redirects refused; responses size-limited |
| The signal goes quiet | No valid message for 60 seconds: hold and open nothing new; optionally close everything after `stale_flat_min`. On Lighter each short-term trade rests under its take profit and stop loss on the exchange |
| Prompt injection through your AI tool | The MCP server can only read and reduce risk. A tool refuses arguments it does not take (it never silently ignores `mode` or `api_key`, and never repeats a value). A switch sent to a folder with no agent is an error naming the folder, not a false success. The signal's `why` text is marked as data, stripped of control characters and length-limited |
| A leaked key | Only a Lighter API key, typed hidden at a terminal, never an argument, its shape checked as you type it; kept in the OS keyring or a private file; never printed, logged or shown to the MCP server |
| Real money by mistake | The mode changes only with `fuze mode` at a terminal, agent stopped, nothing open. Mainnet needs `RAISE`, `REAL MONEY`, a rehearsal on testnet that Lighter testnet itself confirms, and more than half of FUZE's proven trades won (see [The rehearsal and the mainnet lock](modes/rehearsal.md)) |
| The local page framed by another site | The page refuses to be shown in a frame (`frame-ancestors 'none'`, `X-Frame-Options: DENY`) |
| Orders that go wrong | Account read back after every order; no blind second order; the order in flight written to disk first; reduce-only reductions; a worst price on every market order |
| Reporting getting in the way | The reports ([What your agent reports](sharing.md)) go out from a queue on a thread of their own; an error, a slow server or no server changes nothing in trading. They are signed with a key the agent made on your computer and carry no amount, balance or key |
| Two agents on one folder | A lock; the second refuses to start |
| Supply chain | One runtime dependency (`cryptography`); the MCP SDK and Lighter's SDK (pinned exactly) only when you install those extras |

## Where the protection ends

**The typed confirmations and the rehearsal lock protect against the MCP tools, non-interactive callers and mistakes.**
Raising a limit, resuming, unflattening, changing the mode, entering a key and the rehearsal all refuse when input is
not a terminal and ask you to type a word (`RAISE`, `RESUME`, `UNFLATTEN`, `REAL MONEY`, `yes`), and the MCP server has
no route to them at all. A hand-written rehearsal record does not unlock mainnet: Lighter testnet must confirm its
orders.

**They are not a barrier against a program that already runs as you.** Your AI coding tool, when you let it run
commands, is such a program. It can do whatever you can: drive a pseudo-terminal that types `RAISE` for it (a one-line
`expect` script does), edit the files in your FUZE folder, change FUZE's own code, run a real rehearsal, and equally
read your API key from the keyring or the key file. The repository's `AGENTS.md` forbids coding agents to do any of
this, and well-behaved ones follow it; it is a rule, not a barrier.

> **Warning:** do not give an AI tool unattended shell access on a machine that holds a mainnet key.

**The real protection for your money is on the exchange side:**

- a Lighter **account of its own**, holding only the money you want to trade and can afford to lose: a wallet used
  for nothing else, or a sub-account. The agent's balance ceiling (`fuze limits --max-balance-usd`) keeps positions
  small when an account holds more, but only an account that holds no more is a hard limit;
- an API key **restricted to the markets of the coins you follow** (BTC, ETH, HYPE, LIT, or fewer). Per Lighter's documentation such a key can only create, modify
  and cancel orders in those markets; withdrawals and transfers fail;
- never your wallet's private key or recovery phrase anywhere near FUZE or a chat.

With that setup, the worst a misbehaving program on your machine can do is trade that account's money away in
the markets the key is restricted to. It cannot send it anywhere.

Per Lighter's documentation (https://docs.lighter.xyz/developers/integration-guides/api-keys.md), no API key alone can
transfer to another owner, make a fast withdrawal or approve an integrator with fees; those need your wallet. Only your
wallet can set or loosen a key's restrictions, "so someone who holds only the API private key cannot loosen the
limits". When FUZE runs on a server with a fixed address, you can also restrict the key to that IP address.

What Lighter says about itself, not about FUZE: "Users always maintain custody of their assets." Deposits are held by
its contracts on Ethereum. If its sequencer fails to process requests sent through Ethereum in time, the contract freezes into
what it calls Escape Hatch mode, and "These proofs allow users to withdraw the full value of their assets directly on
Ethereum, with no reliance on off-chain coordination"
(https://docs.lighter.xyz/about-lighter/technical-architecture-lighter-core.md). Lighter publishes security audits of
its smart contracts and circuits: https://docs.lighter.xyz/security/security-audits.md.

## Other honest limits

- A stop loss triggers on the mark price. On Lighter its order price is the worst price it may fill at once triggered,
  and what cannot fill at that price or better is cancelled. The short-term stop loss may fill up to 2% past its
  trigger, the emergency stop up to 4%; in a faster move it does not fill and the position stays open.
- Your limits bound the size of a loss; they do not prevent one.
- The rehearsal lock checks that the order path worked on testnet from your account, confirmed by Lighter testnet. It
  cannot prove that this copy or version of FUZE sent those orders, and `fuze run` re-checks only the local record at
  each start.

## Reporting a vulnerability

Do not open a public issue. The repository's `SECURITY.md` says how to report one privately.

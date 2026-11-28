# Keys

This page explains which key the agent needs, where it is kept, and what never sees it. Simulation needs no key at all.

## Which key

Only a **Lighter API key**: a separate key pair Lighter lets you register on your account for trading. The agent needs
its private half, a hexadecimal text of 80 characters. Never your wallet's private key or recovery phrase: FUZE never
asks for them, and nothing in FUZE accepts them.

With it the agent also needs two numbers, both public:

| Number | What it is |
|---|---|
| Account index | Lighter's number for your account or sub-account. It appears in your account's explorer address |
| API key index | The slot the key is registered at on that account, 4 to 254 (Lighter keeps 0 to 3 for its own apps). Default 4 |

How to get all three: [Lighter account and API key](../lighter-setup.md).

## Entering it

```sh
fuze keys testnet      # or: fuze keys mainnet
```

It asks the account index, the key index, then the key, **hidden as you type**. It refuses when input is not a
terminal, and the key is never accepted as a command-line argument. The key's shape is checked as you enter it: 80
hexadecimal characters (with or without `0x` in front). Anything else is refused with its length and **nothing is
saved**, neither the key nor the account index. You can pass the two public numbers as flags:

```sh
fuze keys testnet --account 12345 --key-index 4
```

Then `fuze check` reads the account with it and sends no order. `fuze keys` with no argument shows what is set:

```text
testnet: account not set, key index 4, API key missing
mainnet: account not set, key index 4, API key missing
```

## Where it is kept

- In your operating system's keyring (macOS Keychain, or a Linux secret service) when the `keyring` package finds one.
- Otherwise in `~/.fuze/lighter-testnet.key` or `lighter-mainnet.key`, readable only by you (folder 0700, file 0600).
  Set `FUZE_NO_KEYRING=1` to always use the file, for example on a server with no desktop keyring.

Testnet and mainnet keys are kept separately.

## What never sees it

| Never | How |
|---|---|
| The FUZE server | The agent's reports never carry a key (see [What your agent reports](sharing.md)). Orders are signed on your machine by Lighter's SDK and go straight to Lighter. `fuze share prove` sends a read-only token that lasts one minute, never the key |
| Your AI coding tool | The MCP server never reads the key; it only reports "set" or "missing" |
| Logs and status files | The key is never printed or logged; errors from the SDK are reduced to their type; a filter removes long hex strings from every log line |
| An MCP argument | No tool takes a key. A tool given an argument named like `api_key`, `key`, `private_key` or `secret` refuses, says a key must never be pasted into a chat, and neither repeats nor logs the value |

> **Warning:** never paste a key into a chat or an AI tool. If you did, treat it as leaked: register a new key at the
> same index on Lighter (which replaces the old one), cancel the old key's orders and move the funds if needed.

## What the protection does not cover

Any program that runs as you (with your shell access) can read the key from the keyring or the file, as it can run
`fuze` itself. What protects the money is on the exchange: a sub-account holding only what you can lose, and a key
restricted to the markets of the coins you follow (BTC, ETH, HYPE, LIT), which cannot withdraw. Do not give an AI tool unattended shell access on a
machine that holds a mainnet key. See [Security model](security.md).

## Removing it

```sh
fuze keys testnet --delete
```

This removes FUZE's copy from this machine. It does not stop the key on Lighter: replace it there too. You cannot
delete the key of the mode you are trading in; switch to simulation first.

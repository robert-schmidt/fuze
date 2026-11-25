# Following on Lighter: testnet first, then mainnet

This page walks you through what the agent needs on Lighter: a wallet, an account (or sub-account), an API key and the
two numbers that go with it. FUZE's modes `testnet` and `mainnet` trade on Lighter (lighter.xyz).

**This code is new and has not yet been proven against the real exchange**: it is tested against a fake one, and it has
had no independent security review. Start on testnet with small sizes and watch it. FUZE is not affiliated with
Lighter. Lighter's own documentation is the authority; facts below were checked against https://docs.lighter.xyz (which
https://apidocs.lighter.xyz now redirects to) and Lighter's official Python SDK on 2026-11-25. The few steps we could
not verify are listed once, at the end.

## 1. A wallet only you control

Lighter accounts belong to an Ethereum ("L1") address. Use a wallet whose recovery phrase only you have, on a device you
trust. The wallet's private key never goes into FUZE, a config file, a chat or an AI tool. FUZE only ever takes an
**API key**.

## 2. A Lighter account, testnet first

- Testnet app: https://testnet.app.lighter.xyz (API https://api.testnet.lighter.xyz). Lighter's testnet runs against
  Ethereum Sepolia; its faucet gives test USDC but no ETH, so you need Sepolia ETH from a public Sepolia faucet.
- Mainnet app: https://app.lighter.xyz (API https://mainnet.zklighter.elliot.ai).
- Your **account index** is Lighter's whole number for your account. Main accounts count up from 0; sub-accounts count
  down from a very large number. It is public (it is in the explorer's address). To look it up from your wallet
  address, open (testnet)
  `https://api.testnet.lighter.xyz/api/v1/accountsByL1Address?l1_address=<your address>` or (mainnet)
  `https://mainnet.zklighter.elliot.ai/api/v1/accountsByL1Address?l1_address=<your address>`: the answer lists your
  main account and sub-accounts with their `index`.
- Your account on the public explorer: testnet `https://testnet.app.lighter.xyz/explorer/accounts/<index>`, mainnet
  `https://app.lighter.xyz/explorer/accounts/<index>`. Each order FUZE sends is logged with its link
  (`.../explorer/logs/<transaction hash>`) in `~/.fuze/trades.jsonl`.

Source: https://docs.lighter.xyz/developers/getting-started/environments.md and
https://docs.lighter.xyz/developers/getting-started/core-concepts.md

## 3. A dedicated sub-account holding only what you can lose

Lighter has sub-accounts, each with its own index, balances and API keys. A sub-account is created with a
`CreateSubAccount` transaction signed for your account, and you move funds between your main account and a sub-account
with transfers. Follow FUZE only on a sub-account of its own, and put in it only money you can afford to lose
completely. FUZE treats every reduce-only trigger order on BTC and ETH in that account as its own take profit or stop
loss and may cancel it, and `fuze mode` refuses an account that already holds positions or orders.

FUZE does not change your margin mode or leverage on Lighter. Your sizing and `max_x` decide how big the positions are;
if the account cannot margin an order, Lighter refuses it and `fuze status` reports an order that did not fill.

Source: https://docs.lighter.xyz/developers/getting-started/core-concepts.md and
https://docs.lighter.xyz/developers/integration-guides/deposits-transfers-and-withdrawals.md

## 4. An API key and its index

An **API key** is a key pair, separate from your wallet's key, that signs Lighter transactions for one account. The part
FUZE needs is its **private key: 80 hexadecimal characters** (40 bytes), the form Lighter's SDK generates and expects. It
is bound to one account index and registered at one **API key index**.

What Lighter's docs say (https://docs.lighter.xyz/developers/integration-guides/api-keys.md):

- Each account, main or sub-account, has its own API keys at indexes 0 to 254. Indexes 0 to 3 are reserved for
  Lighter's own apps; use 4 to 254 (FUZE accepts only these; the default is 4).
- Making a key pair does not need your wallet, but registering it on your account does: your wallet signs it (a
  `ChangePubKey` transaction).
- **An API key alone can trade, make "secure withdrawals" (these can only go back to the wallet address that owns the
  account) and transfer between accounts of the same owner.** It cannot alone transfer to another owner or make a
  "fast withdrawal" to another address; those also need your wallet's signature.
- **You can restrict a key to a list of markets.** Such a key can only create, modify and cancel orders in those
  markets; every other transaction fails, including withdrawals and transfers. Restrictions are set with your wallet's
  signature (https://docs.lighter.xyz/api/api-keys/set-api-key-restrictions.md). **We recommend a key restricted to the
  BTC and ETH markets for FUZE.**
- You can give a key an expiry (`valid_until`, at most 180 days ahead). After it, the key cannot sign. Expiry does not
  cancel the key's open orders.

### Creating and registering one

The route Lighter documents is its official Python SDK (`lighter-sdk`, the same package FUZE's `[lighter]` extra
installs). Its example `examples/system_setup.py`, in Lighter's `lighter-python` repository on GitHub:

1. looks up your account index from your wallet address;
2. generates API key pairs with the SDK's `create_api_key()` (no wallet needed for this step);
3. registers each public key at its index with `change_api_key`, which your wallet must sign;
4. waits a few seconds and checks with `check_client()` that Lighter now accepts the key.

That example signs step 3 with your wallet's private key inside a script. If you use it, run it yourself on a machine you
trust, outside any AI tool, never paste the wallet key into a chat, and delete it from the script afterwards. Use a
sub-account index for FUZE, then restrict the key to the BTC and ETH markets.

What this means: a leaked FUZE key cannot (per Lighter's docs) send your money to someone else's address, but an
unrestricted one can trade it away. Restrict it to markets, keep only what you can lose on that sub-account, and never
paste the key into a chat or an AI tool.

## 5. Give FUZE the key (your terminal, never a chat)

From your checkout of the agent's repository (it is not on PyPI yet):

```sh
~/.fuze-venv/bin/pip install '.[mcp,lighter]'   # Lighter's SDK (signs orders on your machine; macOS and Linux) and keyring
fuze keys testnet                               # asks: account index, API key index, then the API key, hidden as you type
fuze check                                      # reads the account with it: balance, positions, protective orders. No order
```

The key is stored in your OS keyring, or, without one, in `~/.fuze/lighter-testnet.key` readable only by you (set
`FUZE_NO_KEYRING=1` on a server to use the file). It is never printed or logged and never reaches the MCP server or
an AI tool, which only see "set" or "missing". `fuze keys` with no argument shows what is set.

If `fuze check` says Lighter does not accept the key, the account index, key index and key do not belong together:
check all three.

## 6. Rehearse, then follow on testnet

```sh
fuze rehearse          # testnet: open the smallest Bitcoin position, place its take profit and stop loss,
                       # cancel them, close it; every step confirmed by reading the account
fuze mode testnet      # the agent must be stopped and nothing open in simulation; type RAISE
fuze unflatten         # only if you flattened simulation before switching (type UNFLATTEN)
fuze run
```

Watch the account on the testnet explorer while it follows. `fuze status` shows the mode, the link, what the agent
holds and why.

## 7. Mainnet: the same, with real money

Only if you accept the risks in [Risks, plainly](risks.md), and only after the testnet rehearsal passed on this machine
with this version of FUZE (`fuze mode` tells you; `fuze mode mainnet` also asks Lighter testnet to confirm its
orders). Then:

```sh
fuze keys mainnet      # a separate mainnet API key, restricted to BTC and ETH, on a sub-account of its own
fuze check
fuze mode mainnet      # agent stopped, nothing open in the current mode; type RAISE, then REAL MONEY
fuze run
```

Warnings, plainly:

- This code had never sent a real order when it was released, and it has had no independent security review. The
  rehearsal is the first time it meets Lighter.
- A stop loss is a trigger order: in a fast market it can fill worse than its price, or not at all.
- When FUZE's own account is a practice (`paper`) account, its results cost it nothing; yours cost real money.
  `fuze status` says when this is the case.
- You can lose everything on that sub-account. This is not financial advice.

To leave mainnet: `fuze flatten`, let the agent close everything, stop it, `fuze mode simulation` (it reads the
account to check nothing is open), then `fuze unflatten` if you want it to follow in simulation.

## 8. How to revoke a key

Lighter's docs describe no separate "revoke" for trading keys. Registering a new key at the same index replaces the old
one, and the new key starts without restrictions (set them again). An expired key also stops working. If you think a
key leaked: replace it at once, cancel its open orders with another key, and move the funds out of that sub-account.
`fuze keys testnet --delete` (or mainnet) removes FUZE's copy from this machine; it does not stop the key on Lighter.

## What we could not verify

Lighter's developer docs describe the steps above as transactions and SDK calls. They do not document where in Lighter's
web app (if anywhere) you can create a sub-account, create or register an API key, set its market restrictions, or use
the testnet faucet. If the app offers these, it is the simpler route; we have not confirmed it.

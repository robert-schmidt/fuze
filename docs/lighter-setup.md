# Following on Lighter: testnet first, then mainnet

This page walks you through what the agent needs on Lighter: a wallet, an account (or sub-account), an API key and the
two numbers that go with it. FUZE's modes `testnet` and `mainnet` trade on Lighter (lighter.xyz).

Lighter is a decentralized exchange for perpetual futures. It describes itself as "a zero-knowledge rollup on top of
Ethereum" that "generates ZK proofs of all operations including order matching and liquidations" (https://lighter.xyz).
Deposits are held by its smart contracts on Ethereum, and its documentation says "Users always maintain custody of
their assets." (https://docs.lighter.xyz/about-lighter/technical-architecture-lighter-core.md)

Start on testnet with small sizes and watch it; mainnet stays locked on each machine until that machine has passed
`fuze rehearse` on testnet, for each new version of FUZE, and until more than half of FUZE's proven trades have won.
FUZE is not affiliated with Lighter. Lighter's own documentation is the authority; facts below were checked against https://docs.lighter.xyz (which
https://apidocs.lighter.xyz now redirects to) and Lighter's official Python SDK on 2026-11-25, and the testnet steps
were done on Lighter testnet that day. What we did not try ourselves is listed once, at the end.

## 1. A wallet only you control

Lighter accounts belong to an Ethereum ("L1") address. Use a wallet whose recovery phrase only you have, on a device you
trust. The wallet's private key never goes into FUZE, a config file, a chat or an AI tool. FUZE only ever takes an
**API key**.

## 2. A Lighter account, testnet first

- Testnet app: https://testnet.app.lighter.xyz (API https://api.testnet.lighter.xyz). Connect your wallet, open the
  account panel (your address, top right) and press **Request Funds**: the account is created and credited with test
  money. You can ask again whenever the account is worth less than $100. We needed no Sepolia ETH for this.
  The button calls Lighter's faucet, which also answers directly: open
  `https://api.testnet.lighter.xyz/api/v1/faucet?l1_address=<your address>&do_l1_transfer=true` and then the same
  address ending in `false`. That is the way we used; the account appeared about 20 seconds later.
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

## 3. An account of its own, holding only what you want to trade

Everything on the account the agent trades stands behind its positions: Lighter takes losses from the whole account,
not from the part you meant to trade. So give FUZE an account that holds only that amount. Two ways:

- **A wallet used for nothing else** (the safest). Make a new address in your wallet app, send it only the money to
  trade, and connect that address to Lighter. Nothing else you own is on that account, and the API key's withdrawals
  can only go back to that address.
- **A sub-account** of the wallet you already use, described below.

The agent checks too: before real money, `fuze go-live` shows what the account holds and asks how many dollars of it
the agent may count as your balance (the [balance ceiling](agent/limits.md#the-balance-ceiling)). It then sizes on no
more than that. The ceiling limits the size of the positions; it does not protect the rest of the account in a fast
move, which is why the account itself should hold no more.

Lighter has sub-accounts, each with its own index, balances and API keys. The app's **Sub-accounts** page
(`/sub-accounts`) has "New Sub-Account" and "Transfer"; underneath, a sub-account is created with a `CreateSubAccount`
transaction signed for your account, and funds move between your accounts with transfers. Follow FUZE only on a sub-account of its own, and put in it only money you can afford to lose
completely. FUZE treats every reduce-only trigger order on BTC, ETH, HYPE and LIT in that account as its own take profit or stop
loss and may cancel it, and `fuze mode` refuses an account that already holds positions or orders.

A standard account can create up to 4 sub-accounts, and Lighter's fee page says "Sub accounts cannot be deleted."
(https://docs.lighter.xyz/trading/trading-fees.md). Use one you can keep for FUZE.

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
  markets of the coins you follow for FUZE** (on mainnet: BTC 1, ETH 0, HYPE 24, LIT 120).
- You can give a key an expiry (`valid_until`, at most 180 days ahead). After it, the key cannot sign. Expiry does not
  cancel the key's open orders.
- You can restrict a key to up to 16 IP addresses, for example the fixed address of a server that runs FUZE.
- Only your wallet can set or loosen a key's restrictions, "so someone who holds only the API private key cannot loosen
  the limits".

### Creating and registering one

**In the app (the simple route).** Open the **API keys** page, https://testnet.app.lighter.xyz/apikeys on testnet and
https://app.lighter.xyz/apikeys on mainnet, with the account (or sub-account) FUZE will use selected:

1. Press **Generate API key** and choose an index from 4 to 254 (4 is FUZE's default).
2. Leave **Maker only** off: FUZE opens and closes with market orders, which a maker-only key cannot send.
3. Your wallet signs the registration. The app then shows the private key **once**: copy it straight into
   `fuze keys testnet` (step 5) and nowhere else.
4. The same page shows **Your account index**.

**With the SDK.** The route Lighter's developer docs describe is its official Python SDK (`lighter-sdk`, the same package FUZE's `[lighter]` extra
installs). Its example `examples/system_setup.py`, in Lighter's `lighter-python` repository on GitHub:

1. looks up your account index from your wallet address;
2. generates API key pairs with the SDK's `create_api_key()` (no wallet needed for this step);
3. registers each public key at its index with `change_api_key`, which your wallet must sign;
4. waits a few seconds and checks with `check_client()` that Lighter now accepts the key.

That example signs step 3 with your wallet's private key inside a script. If you use it, run it yourself on a machine you
trust, outside any AI tool, never paste the wallet key into a chat, and delete it from the script afterwards. Use a
sub-account index for FUZE, then restrict the key to the markets of the coins you follow (BTC, ETH, HYPE, LIT).

What this means: a leaked FUZE key cannot (per Lighter's docs) send your money to someone else's address, but an
unrestricted one can trade it away. Restrict it to markets, keep only what you can lose on that sub-account, and never
paste the key into a chat or an AI tool.

## 5. Give FUZE the key (your terminal, never a chat)

First add the `lighter` extra (Lighter's SDK, which signs orders on your machine, macOS and Linux, and `keyring`), the
way you installed FUZE (see [Install](agent/start/install.md#the-extras)):

```sh
uv tool install "fuze-agent[mcp,lighter] @ git+https://github.com/robert-schmidt/fuze"
# pipx: pipx install --force "fuze-agent[mcp,lighter] @ git+https://github.com/robert-schmidt/fuze"
# a clone: ~/.fuze-venv/bin/pip install '.[mcp,lighter]'
```

Then:

```sh
fuze keys testnet      # asks: account index, API key index, then the API key, hidden as you type
fuze check             # reads the account with it: balance, positions, protective orders. No order
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
orders), and while more than half of FUZE's proven trades have won (`fuze mode` shows the count). Then:

```sh
fuze keys mainnet      # a separate mainnet API key, restricted to the coins you follow, on a sub-account of its own
fuze check
fuze mode mainnet      # agent stopped, nothing open in the current mode; type RAISE, then REAL MONEY
fuze run
```

Warnings, plainly:

- A stop loss triggers on the mark price. On Lighter its order price is the worst price it may fill at once triggered,
  and what cannot fill at that price or better is cancelled. The short-term stop loss may fill up to 2% past its
  trigger, the emergency stop up to 4%; in a faster move it does not fill and the position stays open.
  (https://docs.lighter.xyz/developers/integration-guides/signing-transactions.md)
- When FUZE's own account is a practice (`paper`) account, its results cost it nothing; yours cost real money.
  `fuze status` says when this is the case.
- You can lose everything on that sub-account. This is not financial advice.

To leave mainnet: stop the agent, then `fuze mode simulation`. It reads the account and, if something is open, closes
it with market orders once you type `CLOSE`. Your key and the rehearsal stay on this computer for the way back.

## 8. How to revoke a key

Lighter's docs describe no separate "revoke" for trading keys. Registering a new key at the same index replaces the old
one, and the new key starts without restrictions (set them again). An expired key also stops working. If you think a
key leaked: replace it at once, cancel its open orders with another key, and move the funds out of that sub-account.
`fuze keys testnet --delete` (or mainnet) removes FUZE's copy from this machine; it does not stop the key on Lighter.

## 9. Taking money out

Stop FUZE first (leave mainnet as above, which closes what is open). Lighter has two kinds of withdrawal
(https://docs.lighter.xyz/developers/integration-guides/deposits-transfers-and-withdrawals.md):

- A **secure withdrawal** goes only to the wallet address that owns the account and "Settles via Ethereum". On
  2026-11-28 Lighter's API gave its delay as 1,180 seconds, about 20 minutes. An unrestricted API key can request one.
- A **fast withdrawal** can go to any Ethereum address, in USDC only, and needs your wallet's signature as well.

## What we did not try ourselves

Done on Lighter testnet on 2026-11-25: an account created and funded by the faucet, an API key made on the app's API
keys page at index 4, `fuze check`, and `fuze rehearse` (open, take profit and stop loss, cancel, close), each order
confirmed on Lighter's public record.

Not tried by us: the Request Funds button itself (we called the faucet it calls), creating a sub-account in the app, restricting a key to markets (Lighter's docs give the API call,
signed by your wallet; we did not find the setting on the API keys page), a key with an expiry, a withdrawal, and
anything on mainnet.

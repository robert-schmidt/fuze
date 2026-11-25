# Before real following: what you will need on Lighter

**Real following does not exist yet.** FUZE v0.1 follows on a simulated account only. This page lists what you will
need once Lighter testnet following is released, so you can prepare. FUZE is not affiliated with Lighter. Lighter's
own documentation is the authority; where this page says "check on Lighter", we could not confirm the detail in their
docs. Facts below were checked against https://docs.lighter.xyz (which https://apidocs.lighter.xyz now redirects to)
on 2026-11-25.

## 1. A wallet only you control

Lighter accounts belong to an Ethereum ("L1") address. Use a wallet whose recovery phrase only you have, on a device you
trust. The wallet's private key never goes into FUZE, a config file, a chat or an AI tool.

## 2. A Lighter account, testnet first

- Testnet app: https://testnet.app.lighter.xyz (API https://api.testnet.lighter.xyz). Lighter's testnet runs against
  Ethereum Sepolia; its faucet gives test USDC but no ETH, so you need Sepolia ETH from a public Sepolia faucet.
  How to use the faucet in the app: check on Lighter.
- Mainnet app: https://app.lighter.xyz (API https://mainnet.zklighter.elliot.ai).
- Your **account index** is Lighter's number for your account. Lighter's API looks it up from your wallet address
  (`/api/v1/accountsByL1Address`). Where the app shows it: check on Lighter.

Source: https://docs.lighter.xyz/developers/getting-started/environments.md and
https://docs.lighter.xyz/developers/getting-started/core-concepts.md

## 3. A dedicated sub-account holding only what you can lose

Lighter has sub-accounts, each with its own index, balances and API keys, and you move funds between your main account
and a sub-account with transfers. Follow FUZE only on a sub-account, and put in it only money you can afford to lose
completely. Creating a sub-account in the app: check on Lighter.

Source: https://docs.lighter.xyz/developers/getting-started/core-concepts.md and
https://docs.lighter.xyz/developers/integration-guides/deposits-transfers-and-withdrawals.md

## 4. An API key and its index

What Lighter's docs say (https://docs.lighter.xyz/developers/integration-guides/api-keys.md):

- Each account, main or sub-account, has its own API keys at indexes 0 to 254. Indexes 0–3 are reserved for Lighter's
  own apps; use 4–254.
- Making a key pair does not need your wallet, but registering it on your account does: your wallet signs it.
- **An API key alone can trade, make "secure withdrawals" (these can only go back to the wallet address that owns the
  account) and transfer between accounts of the same owner.** It cannot alone transfer to another owner or make a
  "fast withdrawal" to another address; those also need your wallet's signature.
- **You can restrict a key to a list of markets.** Such a key can only create, modify and cancel orders in those
  markets; every other transaction fails, including withdrawals and transfers. Restrictions are set with your wallet's
  signature. We recommend a key restricted to the BTC and ETH markets for FUZE.
- You can give a key an expiry (`valid_until`, at most 180 days ahead). After it, the key cannot sign. Expiry does not
  cancel the key's open orders.

What this means: a leaked FUZE key cannot (per Lighter's docs) send your money to someone else's address, but an
unrestricted one can trade it away. Restrict it to markets, keep only what you can lose on that sub-account, and never
paste the key into a chat or an AI tool.

## 5. How to revoke a key

Lighter's docs describe no separate "revoke" for trading keys. Registering a new key at the same index replaces the old
one, and the new key starts without restrictions (set them again). An expired key also stops working. Steps in the app:
check on Lighter. If you think a key leaked: replace it at once, cancel its open orders with another key, and move the
funds out of that sub-account.

## 6. Then, in order

1. Dry run (today): `fuze run` on the simulated account until you understand what it does.
2. Testnet, when FUZE releases it: a testnet sub-account and key, small limits.
3. Real money last, only if you accept the risks in the [README](../README.md#risks).

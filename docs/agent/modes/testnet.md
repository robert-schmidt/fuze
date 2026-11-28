# Lighter testnet

This page takes you from simulation to Lighter's test exchange, where the agent sends real orders with test money.

> **Warning:** testnet is where you watch the agent place real orders before any real money is at stake. Use small
> sizes and watch every step.

## Steps

1. **Install the Lighter extra** (macOS or Linux; Lighter's SDK ships its signing library for those), the way you
   installed FUZE:

   ```sh
   uv tool install "fuze-agent[mcp,lighter] @ git+https://github.com/robert-schmidt/fuze"
   # pipx: pipx install --force "fuze-agent[mcp,lighter] @ git+https://github.com/robert-schmidt/fuze"
   # a clone: cd fuze && ~/.fuze-venv/bin/pip install '.[mcp,lighter]'
   ```

2. **Make a Lighter testnet account and API key.** Use a sub-account of its own, and a key restricted to the markets of the
coins you follow. Step by step: [Lighter account and API key](../../lighter-setup.md).

3. **Give FUZE the key**, in your terminal (never in a chat):

   ```sh
   fuze keys testnet
   ```

   It asks your account index, the API key's index, then the key itself, hidden as you type. See [Keys](../keys.md).

4. **Check it**, without sending any order:

   ```sh
   fuze check
   ```

   It reads the account: balance, positions, protective orders.

5. **Rehearse** (optional on testnet, required before mainnet):

   ```sh
   fuze rehearse
   ```

   See [The rehearsal and the mainnet lock](rehearsal.md).

6. **Switch and run.** Stop the agent first (Ctrl+C):

   ```sh
   fuze mode testnet      # closes the simulated positions by itself; type RAISE
   fuze run
   ```

## How Lighter's testnet differs

Lighter's testnet is a separate chain (chain ID 300; mainnet is 304) that settles on Ethereum's Sepolia test network,
and "A transaction signed for `304` will be rejected by testnet, and vice versa." Its faucet "gives test USDC and LIT
but no ETH" (https://docs.lighter.xyz/developers/getting-started/environments.md). Its markets have other ids and larger
smallest orders than mainnet (testnet's Bitcoin market is 4096); FUZE finds each coin's market by its symbol and reads
the smallest orders from Lighter. A coin with no market on testnet is said in `fuze run` and `fuze status` and not
traded there. Lighter's own advice to developers is "Default to testnet in
examples and tests." (https://docs.lighter.xyz/developers/ai-and-agents/agent-instructions.md)

## Watching it

`fuze status` shows the mode, your account's page on Lighter's public testnet explorer, what the agent holds and why.
Every order is logged in `~/.fuze/trades.jsonl` with its explorer link.

## Leaving testnet

Stop the agent, then `fuze mode simulation`: it reads the account and, if something is open, closes it with market
orders once you type `CLOSE`.

# Lighter testnet

This page takes you from simulation to Lighter's test exchange, where the agent sends real orders with test money.

> **Warning:** this is the first time FUZE's Lighter code meets a real exchange. It has only been tested against a fake
> one. Use small sizes and watch every step.

## Steps

1. **Install the Lighter extra** (macOS or Linux; Lighter's SDK ships its signing library for those):

   ```sh
   cd fuze && ~/.fuze-venv/bin/pip install '.[mcp,lighter]'
   ```

2. **Make a Lighter testnet account and API key.** Use a sub-account of its own, and a key restricted to the BTC and ETH
   markets. Step by step: [Lighter account and API key](../../lighter-setup.md).

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

6. **Switch and run.** Nothing may be open in simulation, and the agent must be stopped:

   ```sh
   fuze flatten           # the running agent closes the simulated positions
   # wait until fuze status shows no positions, then stop the agent (Ctrl+C)
   fuze mode testnet      # type RAISE
   fuze unflatten         # flatten stays on across the switch until you undo it
   fuze run
   ```

## Watching it

`fuze status` shows the mode, your account's page on Lighter's public testnet explorer, what the agent holds and why.
Every order is logged in `~/.fuze/trades.jsonl` with its explorer link.

## Leaving testnet

`fuze flatten`, let the agent close everything, stop it, then `fuze mode simulation` (it reads the account to check
nothing is open), and `fuze unflatten` when you want it to follow in simulation.

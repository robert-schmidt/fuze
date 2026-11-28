# Changes

What changed in each version of the FUZE agent. A new version that changes how orders are sent asks for a new testnet
rehearsal (`fuze rehearse`) before mainnet unlocks on a computer again; the entries say so.

## 0.4.0 (28 November 2026)

- **Emergency stop.** The part of each position with no take profit or stop loss of its own (the slow trend part) now
  rests under one reduce-only stop order on the exchange, 20% from the price. While the agent follows a live signal it
  sets the stop again each time the price has moved 5%, so the price reaches it only when nothing is running to move
  it: the agent is off, paused, or has no fresh signal. It is a safety net, not a trading rule. The agent places it
  for 28 days (Lighter allows an order to rest between 5 minutes and 30 days) and places it again after 14. See
  [The emergency stop](docs/agent/following.md#5-the-emergency-stop).
- **Balance ceiling** (`max_balance_usd`, `fuze limits --max-balance-usd`). An account can hold more than you want to
  trade: with a ceiling the agent counts no more than that amount as your balance, for sizes, the exposure cap and the
  daily loss stop. `fuze go-live` and `fuze mode mainnet` show what the account holds and ask for it before real
  money (an amount, or `all`); it is remembered across mode changes. It limits the size of the positions, not what the
  exchange can take: the docs now say to use an account of its own, a wallet used for nothing else or a sub-account,
  holding only the money to trade.
- Fewer requests to Lighter: the price from its market list is read every 30 seconds instead of every 5 (and fresh
  before an order that needs it). A quiet minute with a short-term trade open takes 27 of a standard account's 60
  requests, down from 35. The read token for open orders is asked for 10 minutes explicitly.
- The emergency stop is told apart from a short-term trade's take profit and stop loss by Lighter's own order type, so
  cancelling one never touches the other.
- `fuze status`, the local page (`fuze ui`) and the MCP tools show each position's emergency stop. In simulation the
  stop is checked while the agent runs.
- **`fuze go-live`**: one guided command from simulation to real money. It asks for a Lighter testnet account and API
  key, runs the rehearsal, asks for the mainnet account and key and makes the switch, skipping what is already done.
  Keys, account numbers and the rehearsal are remembered across mode changes.
- **`fuze mode` closes what is open** in the mode you leave instead of only refusing: simulated positions by itself,
  positions on Lighter with market orders once you type `CLOSE`.
- **The testnet rehearsal has two more steps**: it places the emergency stop beside a take profit and stop loss, checks
  neither is taken for the other, and removes it. **Mainnet asks for a new rehearsal with this version.**

## 0.3.0 (25 November 2026)

- A read-only page about the agent on your own computer (`fuze ui`).
- The documentation book, published at https://docs.fuze.trade.
- Fixes from a new-user test against the public repository: install steps for macOS, Linux and Windows (WSL), one
  sentence to paste into an AI coding tool, clearer messages when something is missing.
- The rehearsal passed on Lighter testnet on 25 November 2026 (open, take profit and stop loss, cancel, close).

Followed since, with no new version: a short-term trade against the trend position is netted with it; a stop loss moved
into profit and an added entry are followed as a new revision.

## 0.2.0 (25 November 2026)

- Three modes on one order path: simulation, Lighter testnet, Lighter mainnet. Mainnet is locked until the testnet
  rehearsal has passed on the same computer with the same version.
- Keys are typed hidden at a terminal (`fuze keys`); moving toward real money asks for typed confirmations.

## 0.1.0 (25 November 2026)

- The agent follows the signed position signal on a simulated account. Protocol v1.
- An MCP server for AI coding tools that can watch the agent and reduce risk, never raise it.

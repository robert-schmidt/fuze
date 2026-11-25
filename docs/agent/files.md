# Files it keeps

This page lists the files the agent keeps in its folder, `~/.fuze` (or `FUZE_HOME`), and what each one is for. The
folder is private to your user. Nothing in it is sent anywhere.

| File | What it holds | Modes |
|---|---|---|
| `config.json` | Your mode, sizing, limits, and Lighter account and key indexes. No secret | All |
| `status.json` | What the agent last did: balance, positions, what the signal asks for per coin, the latest signal, its reason, flags | All |
| `trades.jsonl` | One line per order or fill, with explorer links on Lighter | All |
| `state.json` | The agent's memory between steps: the revision it follows, what it last set, the day's starting balance | All |
| `guard.json` | The timestamp of the newest signal accepted (the replay guard) | All |
| `agent.lock` | Held while `fuze run` runs, so a second agent refuses to start | All |
| `PAUSE`, `FLATTEN` | Present while pause or flatten is on | All |
| `ui.json` | The local page's port while `fuze ui` runs | All |
| `dry.json` | The simulated account | Simulation |
| `pending.json` | An order in flight, written before it is sent, so a restart never sends it twice | Testnet, mainnet |
| `lighter-testnet.json`, `lighter-mainnet.json` | The take profit and stop loss the agent placed | Testnet, mainnet |
| `rehearsal.json` | The last testnet rehearsal: each step's result, the testnet account and key index, time, version, machine and each order's transaction hash (which `fuze mode mainnet` asks Lighter testnet to confirm) | Testnet, mainnet |
| `keys.json` | Where each key is kept (keyring or file), never the key | Testnet, mainnet |
| `lighter-testnet.key`, `lighter-mainnet.key` | The API key, only when there is no OS keyring. Readable by you only | Testnet, mainnet |

## Rules

- Do not edit `config.json`, `state.json`, `pending.json` or `rehearsal.json` by hand: use the `fuze` commands. Your AI
  tool must not edit them either; `AGENTS.md` forbids it.
- `fuze mode` deletes `state.json` and `pending.json` when switching, because notes about one account mean nothing on
  another.
- To reset the simulated account, stop the agent and delete `dry.json`.

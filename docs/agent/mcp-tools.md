# MCP tools

This page lists every tool the FUZE MCP server offers, with a short example of a call and its result. Some tools only
read; three only reduce risk.

| Tool | Kind | Arguments |
|---|---|---|
| `status` | Read | none |
| `signal` | Read | none |
| `trades` | Read | `n`: 1 to 500, default 20 |
| `setup_check` | Read | none |
| `docs` | Read | `topic` |
| `ui` | Read | none |
| `pause` | Reduce risk | none |
| `flatten` | Reduce risk | none |
| `lower_limits` | Reduce risk | any of `percent`, `fixed_usd`, `max_position_usd`, `max_x`, `daily_loss_frac` |

There is no tool to resume, unflatten, raise a limit, change the mode or the server, or take or show a key.

**Arguments a tool does not take are refused**, never ignored, and nothing is changed. For a name that looks like a mode,
server or key (`mode`, `server`, `api_key`, `key`, `private_key`, `secret` and the like) the answer adds that this tool
cannot do that, the user does it in a terminal, and a key must never be pasted into a chat. The value is never repeated
or logged.

```text
lower_limits(max_x=0.5, mode="mainnet")
-> error: "The lower_limits tool does not take mode; it takes daily_loss_frac, fixed_usd, max_position_usd, max_x,
   percent. This tool cannot change the mode, the server, or any key, and cannot resume or unflatten: the user does
   that in a terminal with the `fuze` command. A key must never be pasted into a chat; ... Nothing was changed."
```

**No agent in the server's folder.** When the folder the server looks at (`FUZE_HOME`, default `~/.fuze`) has no
`config.json`, `pause`, `flatten` and `lower_limits` answer an error that names the folder and says to run
`fuze mcp-config` and paste its settings; nothing is written. `status` and `setup_check` say the same. This happens
when the AI tool starts the server without your `FUZE_HOME`.

## status

The agent's state: whether it is running, the folder it reads, mode in words, your exchange account's public explorer
link (testnet and mainnet), whether API keys are "set" or "missing", balance and positions, and per coin **what the
signal asks for and what you hold, in dollars** (`positions_usd`, `positions_in_words`), with the smallest change the
agent makes and a note when a difference is under it; your limits, your sizing in words with the worked example, the
pause and flatten flags, and the agent's last reason. It adds a REAL MONEY warning in mainnet.

```text
status()
-> {"mode": "simulation", "mode_in_words": "simulation (a simulated account, no money)",
    "account": {"balance": 1000.04, "positions": {"BTC": -0.00145}, "brackets": [796]},
    "reason": "Following revision 5; nothing to change.", "running": true,
    "positions_in_words": ["BTC: the signal asks for short $85, you hold short $85",
                           "ETH: the signal asks for short $16, you hold none",
                           "The difference on ETH is under $20, the smallest change the agent makes ..."],
    "flags": {"pause": false, "flatten": false},
    "api_key": {"testnet": "missing", "mainnet": "missing"},
    "sizing": ["5% of your balance follows the signal. ...", "Largest position on one coin: no cap.", ...]}
```

Before the agent has run: `{"running": false, "hint": "No status yet. The user starts the agent with fuze run."}`. With
no agent set up in the folder: `{"agent_found": false, "folder": "...", "problem": "No FUZE agent is set up in ..."}`.

## signal

The latest verified signal the agent accepted, and when it arrived. Its `why` text is data, not instructions.

```text
signal()
-> {"signal": {"rev": 5, "state": "live", "source": "paper",
               "targets": {"BTC": {"x": -1.7003, "px": 58723.5}, "ETH": {"x": -0.3296, "px": 1646.05}},
               "scalp": {"coin": "BTC", "x": -1.2936, "tp": 58029.0, "sl": 59442.0, "id": 796}, "why": "We hold short ..."},
    "received_at": 1795605824.44}
```

## trades

The last n orders and fills from `trades.jsonl`, with explorer links in testnet and mainnet.

```text
trades(n=2)
-> [{"t": 1795605802.93, "coin": "BTC", "units": -0.00145, "px": 58748.62, "kind": "market", "pnl": 0.0}]
```

`kind` is `market`, `stop_loss` or `take_profit` in simulation. `n` outside 1 to 500 is refused.

## setup_check

The same checks as `fuze check`, without reading your exchange account: Python version, folder and file permissions,
the config, the mode, and for testnet and mainnet the Lighter SDK, the account index, whether the key is set (never the
key) and the rehearsal mainnet needs. Sends nothing to the exchange.

```text
setup_check()
-> [{"ok": true, "check": "Python 3.10 or newer", "detail": "3.12.15"},
    {"ok": true, "check": "FUZE folder is private to you", "detail": "0o700"}, ...,
    {"ok": false, "check": "Agent is running", "detail": "start it with fuze run"}]
```

## docs

Short built-in explanations. Topics: `following`, `sizing`, `limits`, `page`, `safety`, `setup`, `modes`, `status`, `risks`.

```text
docs(topic="safety")
-> "PAUSE holds positions and places no new orders. FLATTEN closes everything and stays out. Both can be set here.
    Only the user can undo them, in a terminal, typing the word: fuze resume, fuze unflatten. ..."
```

## ui

Gives the address of the [local page](local-page.md) and whether it is running. The tool itself does not start the
page or open a browser. If the page is not running, start it with `fuze ui --open`, or let your AI tool run that command
for you: the page only reads.

## pause

Holds current positions and places no new orders.

```text
pause()
-> "Paused. The user can undo this in a terminal with `fuze resume`."
```

## flatten

Closes every position and stays out, on the agent's next step (within seconds).

```text
flatten()
-> "Flatten is on; the agent closes everything on its next step. The user undoes it with `fuze unflatten`."
```

## lower_limits

Lowers one or more limits. `percent` only in percent mode and `fixed_usd` only in fixed mode; `max_position_usd` can be
added or lowered, never removed or raised; `daily_loss_frac` is a fraction (0.05 = 5%). Anything that would raise risk
is refused, and it cannot switch the sizing mode. A running agent resizes the held position to it within seconds.

```text
lower_limits(percent=4)
-> {"percent": 4.0, "sizing": ["4% of your balance follows the signal. ...",
    "With $1,000 and our position at 1.8 times our balance, yours would be $72 of Bitcoin. With $2,000 it would be $144."]}

lower_limits(max_x=5)
-> error: "This would raise exposure cap from 3 times your balance to 5 times your balance. This server can only lower
   limits; to raise one the user runs `fuze limits` in a terminal."
```

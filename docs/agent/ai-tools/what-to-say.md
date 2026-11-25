# What you can say

This page gives examples of plain requests to your AI coding tool and what happens with each. You do not need to name
the tools; the AI picks them.

## Setting up

| You say | What happens |
|---|---|
| "Install the FUZE agent from github.com/robert-schmidt/fuze and set it up in simulation with 5% of my balance, a $300 cap per position and a 5% daily loss stop." | It installs it with `uv tool install` (or `pipx install`) from that address, runs `fuze init --yes --size-mode percent --percent 5 --max-position-usd 300 --daily-loss 5`, then shows you the worked example |
| "Connect FUZE to this tool." | It adds the server, using what `fuze mcp-config` prints when `fuze` is not on its PATH or you use another folder, as on [the setup that works](README.md#the-setup-that-works) |
| "Start following in simulation." | It may run `fuze run` for you in simulation |

## Watching

| You say | Tool |
|---|---|
| "What is FUZE holding right now, and why?" | `status` |
| "What does the latest signal say?" | `signal` |
| "Show me the last 10 trades." | `trades` with n = 10 |
| "Is my setup ready for testnet?" | `setup_check` |
| "How does sizing work?" | `docs` with topic `sizing` |

## Making it safer

| You say | Tool |
|---|---|
| "Lower my share to 3%." | `lower_limits` with percent = 3; the running agent shrinks your position within seconds |
| "Never hold more than $200 of one coin." | `lower_limits` with max_position_usd = 200 |
| "Something looks wrong: stop opening trades." | `pause` |
| "Close everything." | `flatten` |

## Things it will refuse, and what to do instead

| You say | What happens |
|---|---|
| "Raise my share to 20%." | Refused. It tells you to type `fuze limits --percent 20` in your terminal, which asks you to type `RAISE` |
| "Resume." / "Unflatten." | It tells you to type `fuze resume` / `fuze unflatten` yourself; each asks you to type `RESUME` / `UNFLATTEN` |
| "Switch the mode to mainnet" passed as an argument to a tool | Refused: the tool does not take `mode`, nothing is changed, and it says the mode is changed by you in a terminal |
| "Switch me to testnet." | It tells you the steps; you type `fuze keys testnet` and `fuze mode testnet` |
| "Here is my API key: ..." | It must not accept it, and no tool takes a key (a tool given `api_key` refuses without repeating it). Treat the key as leaked and replace it on Lighter |

## Text inside the signal is data

The signal's `why` field is plain words from our server. Your AI tool is told to treat it, and every tool result, as
data and never as instructions. If anything in it asks for an action, the tool should not do it and should tell you.

# What your agent reports

This page lists exactly what the agent sends to the FUZE server, what it never sends, and what changes when you make
it public. The code that sends it is open: read `src/fuze/report.py` in the repository.

Reading the signal needs no account and sends nothing: anyone can read it. The agent is different: from version 0.5.0
every agent reports its trades and results to the FUZE server. There is no switch to turn this off. You choose who
sees the reports:

- **Private** (the default): only FUZE sees them, in a private dashboard.
- **Public**: the agent is listed on the site in the **FUZE Fellowship**, with your handle.

`fuze share` prints the same lists as this page, whether your agent is public, its id, and its public page when it
has one.

## How a report is sent

The agent makes a key of its own on your computer the first time it needs one (`agent.key` in your FUZE folder,
readable only by you, never printed). Its public half is the agent's identity: the agent's id is the first 16
characters of its fingerprint (SHA-256). Each report is signed with that key and carries a counter that only goes up,
so nobody else can report as your agent and an old report cannot be sent again.

Reports are sent in the background, over HTTPS, to the server in your settings (`https://fuze.trade`). A report that
cannot be sent is dropped; a trade is tried again with the next report, up to 20 times. Sending never waits for the
trading: the agent hands a report to a queue and carries on, and an error in reporting cannot stop, delay or change an
order. The server's answer is never read by the trading code.

## What is sent

Sizes are multiples of your balance and results are percent. No report carries a dollar amount.

**Every report** carries:

| Field | What it is |
|---|---|
| `kind` | `hello`, `beat`, `trade`, `prove` or `bye` |
| `seq`, `ts` | A counter that only goes up, and the time |
| `ver` | The FUZE version |
| `mode` | `simulation`, `testnet` or `mainnet` |
| `public` | Whether you chose public |

and the agent's public key with the signature.

**hello**: at start, and whenever a setting or your choice of public or private changes.

| Field | What it is |
|---|---|
| `settings.size_mode` | `percent` (a share of your balance follows the signal) or `fixed` (a fixed amount does) |
| `settings.percent` | The share, in percent. Only in percent mode; the fixed amount is dollars and is never sent |
| `settings.max_x` | Your exposure cap, as a multiple of your balance |
| `settings.daily_loss_frac` | Your daily loss stop (0.1 is 10%) |
| `settings.ceiling` | Yes or no: whether a balance ceiling is set (never its amount) |
| `settings.cap` | Yes or no: whether a cap per position is set (never its amount) |
| `handle` | Your X or GitHub profile link. Only when public and set |

**beat**: every 5 minutes.

| Field | What it is |
|---|---|
| `equity` | Your result since the start, as a multiple: 1.02 is 2% up. Deposits and withdrawals are left out (below) |
| `x` | Each position as a multiple of your balance: −0.18 is a short worth 18% of the balance |
| `state` | `following`, `paused`, `flat`, `daily_stop` (stopped for the rest of the UTC day) or `no_signal` |

**trade**: after each order of the agent's that filled, and when a take profit, stop loss or emergency stop is found
filled on the exchange.

| Field | What it is |
|---|---|
| `coin` | `BTC` or `ETH` |
| `side` | `buy` or `sell` |
| `why` | `open`, `add`, `reduce`, `close`, `tp` (take profit), `sl` (stop loss), `stop` (emergency stop) or `flatten`. When the agent cannot tell a take profit from a stop loss it says `close` |
| `part` | `scalp` (the short-term part) or `trend`, when known |
| `x` | The trade's size as a multiple of your balance |
| `px` | The fill price; where the agent cannot know it, the price the order was sent at |
| `ref`, `rev` | The signal's price and revision the order followed |
| `late` | Seconds between first seeing that revision and the order |
| `result` | On a trade that reduces or closes a position: its result in percent of your balance, when the agent knows the entry |

**bye**: when the agent stops cleanly (Ctrl+C). It carries nothing else.

**prove**: only when you run `fuze share prove` on testnet or mainnet (below). It carries your Lighter account number
and a read-only token that lasts one minute.

### How the result leaves out deposits and withdrawals

The agent keeps a result index on your computer (`equity.json`) that starts at 1.0. At each step it works out the
change the prices explain: the coins held at the last step times the price change. When the balance changed by more
than that, and the difference is more than $5 or 2% of the balance, it is counted as a deposit or withdrawal and left
out. Anything smaller counts in full: fees, funding and slippage are part of the result. The index and the multiples
are worked out on the whole account balance, also when you set a balance ceiling.

## What is never sent

- No dollar amount, no number of coins and no balance.
- No key: not your Lighter API key, not the agent's own private key.
- Nothing about your computer: no name, no folder, no system details.
- Your Lighter account number only with `fuze share prove`, and it is shown only while the agent is public.

Like any web request, a report reaches the server from your internet address. The server keeps it in memory only, to
limit how many new agents one address can add, and never writes it to disk.

## Public or private

| | Private (default) | Public |
|---|---|---|
| Who sees the reports | FUZE only | Anyone, on the site |
| Listed in the FUZE Fellowship | No | Yes, at `https://fuze.trade/fellowship/<id>` |
| Shown | Nothing | Your handle, the mode, the settings above, how long the agent has been running, its result in percent, its last trades, and on Lighter its account number after `fuze share prove` |
| Handle and account number kept by the server | No: going private removes them | Yes |

A public agent's page shows what the reports say, nothing more. Others can see your handle next to your result, and,
once you prove it, your Lighter account number, which opens that account's public page on Lighter's explorer.

## The two proofs

Both are optional and run only when you type `fuze share prove` in a terminal.

- **GitHub handle**: the command shows your agent's id and asks you to create a public gist on GitHub whose
  description is `fuze-<id>`. The server then looks at that GitHub user's public gists, and when it finds the gist it
  marks the handle as verified. An X profile cannot be checked this way: it is shown as you typed it.
- **Lighter account** (testnet or mainnet): the agent asks Lighter's library for a read-only token that lasts one
  minute and sends it to the server once, after you type `YES`. The server uses it to ask Lighter one question,
  whether this agent holds a key of that account, and never stores or logs it. The agent never writes it to disk or a
  log. The account is shown only while you trade on that exchange and stay public.

## How to change it

| Command | What it does |
|---|---|
| `fuze share` | Prints what is sent, whether this agent is public, its id and its page |
| `fuze share public` | Makes the agent public. Asks for your X or GitHub link (Enter for none), or takes `--handle LINK` |
| `fuze share private` | Makes the agent private again; the server removes the handle and the account number |
| `fuze share prove` | Proves your GitHub handle and, on testnet or mainnet, your Lighter account |

`fuze share public`, `private` and `prove` work only at a terminal. Your AI coding tool's MCP server has no tool for
them: it can tell you whether the agent is public or private, and nothing more. `fuze init` asks the question once
("Show this agent publicly in the FUZE Fellowship?"), and `fuze run` and `fuze status` say in one line where the
reports go. A running agent picks up a change within seconds and sends a new hello.

## Why there is no off switch

The reports let FUZE see how the signal works for the people who follow it: how late orders come, what price they
fill at, and what the results are at different settings. They carry no amounts, the list above is fixed in the code
and on the server (the server keeps no field outside it), and the code is open. If you do not want an agent of yours
to report, do not run it.

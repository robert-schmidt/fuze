# Balance and test periods

This page explains the balance figures in the public record and why the record is divided into test periods.

## The record, field by field

`https://fuze.trade/v1/record` (shortened; the balance fields from 25 November 2026, the trade from 27 November):

```json
{"ts": 1795605647.5, "source": "paper", "balance": 99.59, "day_start": 100.0, "low": 98.92, "account": null,
 "period": {"name": "Opus decides, our algorithm answers; $100 start", "since": 1795584754.9, "start": 100.0},
 "curve": [[1795584755, 100.0], [1795586480, 100.02], [1795595497, 98.92], [1795605647, 99.59]],
 "trades": [{"id": 806, "coin": "BTC", "short": true, "lev": 24, "opened": 1795791403, "closed": 1795793102, "tp": 58670.0, "sl": 59856.0,
             "fills": [{"ts": 1795791403, "side": "sell", "units": 0.02089, "px": 59269.5,
                        "proof": "d579065ae3cd256b2a6118540384fb86f07e80e2d1742b516f5333edb24dea33", "mined": false}],
             "end": {"ts": 1795793102, "proof": "b0713a4604037058f66b0b4e0c4e1c8e3e50a18875b24fa17590c9b3c4183420", "mined": false},
             "how": "sl", "moved": false, "exit": 59856.0, "result": -12.25, "n": 1, "units": 0.02089, "entry": 59269.5}],
 "trend": {"BTC": {"entry": 60223.05, "since": 1795154013, "fills": [], "stop": 72268.0}}}
```

| Field | Meaning |
|---|---|
| `source` | Which money: `paper` (practice), `testnet`, `mainnet` |
| `balance` | The account's value now, open positions included |
| `day_start` | The balance at the start of the UTC day |
| `low` | The lowest balance in this test period |
| `account` | A public exchange account link, when the account trades on an exchange; empty for practice money |
| `period` | The current test period: its name, start time and starting balance |
| `curve` | Balance points over the period, as [time, balance] |
| `trades` | The short-term trades of this test period, newest first, the open one included (`closed` is empty). `fills`: each order of the account with its time, side, units and price; `n`: how many of them were entries; `entry`: their average price; `tp`, `sl`: the take profit and stop loss; `moved`: the stop loss was moved into profit; `how`: what closed it (`tp`, `sl`, or the bot's own reason); `exit`, `result`: the closing price and the trade's own result in dollars |
| `proof`, `mined` | On a fill or an `end`: the record's SHA-256, stamped with OpenTimestamps. `https://fuze.trade/proof/<proof>.json` is the stamped record and `.json.ots` its stamp; `mined` is true once the stamp names a Bitcoin block. See [proofs](proofs.md) |
| `url` | On a fill, with real money only: the order on Lighter's explorer |
| `proven` | Over the whole record, every coin: `n` proven trades (opening and closing records both time-stamped in a Bitcoin block), `won` of them won, and `open`: true when more than half have won. The agent keeps real money locked until then ([The record's lock](../agent/modes/rehearsal.md#the-records-lock)) |
| `trend` | Per coin, the slow trend position: its average entry, since when it is held, its latest orders, and `stop`: the price of the [emergency stop](../agent/following.md) resting for it |

Times are Unix seconds.

## Test periods

The account's balance is reset when the way of trading changes in a way that would make old and new results
meaningless to compare: a new decider, new sizing, a new exchange. Each reset starts a **test period** with a name that
says what is being tested and its starting balance. The current one, "Opus decides, our algorithm answers; $100 start",
began on 25 November 2026 with $100 of practice money.

The Advanced view lists every past period with its start, trades, wins and result, and the change history says what
changed and why. A reset never removes earlier trades; they stay in the closed-trades table with their proofs.

## Reading the curve

- Compare against the period's own start, not against another period.
- A short period says very little. The slow trend needs months; the short-term trades need hundreds of trades before an
  average means anything.
- Practice results cost the account nothing. They are a measurement, not money made.

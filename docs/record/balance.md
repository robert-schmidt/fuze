# Balance and test periods

This page explains the balance figures in the public record and why the record is divided into test periods.

## The record, field by field

`https://fuze.trade/v1/record` on 25 November 2026 (shortened):

```json
{"ts": 1795605647.5, "source": "paper", "balance": 99.59, "day_start": 100.0, "low": 98.92, "account": null,
 "period": {"name": "Opus decides, our algorithm answers; $100 start", "since": 1795584754.9, "start": 100.0},
 "curve": [[1795584755, 100.0], [1795586480, 100.02], [1795595497, 98.92], [1795605647, 99.59]],
 "moves": [{"ts": 1795586480, "coin": "BTC", "side": "sell", "why": "scalp", "x": 1.39}]}
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
| `moves` | Recent changes of position: coin, side, which book (`scalp` or trend) and size as x |

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

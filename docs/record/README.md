# The public record

This section explains how to read the account's results as published on [fuze.trade](https://fuze.trade): the balance
and its test periods, the leverage and margin of what it holds, and the timestamped proofs that the record was not
changed afterwards.

## Where it lives

| Where | What you see |
|---|---|
| fuze.trade, Simple view | The live position, the short-term trade between its take profit and stop loss, the open positions (each with its take profit and stop loss, its entries and their time stamps), the balance since the test period started, the closed positions of the period, and our own follower |
| fuze.trade, Advanced view | What the account's own dashboard shows, read-only: the account and both books, results by period and by day, every closed trade with its proof, the change history, the AI against our algorithm, the markets we watch, and raw research tables |
| `https://fuze.trade/v1/record` | The balance numbers as JSON |

## The record is shown as it is

Losses are shown like gains. The account trades practice money today, and the site says so wherever a dollar figure
appears. Nothing on it is a promise about tomorrow.

## Pages

| Page | Covers |
|---|---|
| [Balance and test periods](balance.md) | The balance, the curve, and why the record is split into test periods |
| [Account leverage, margin and size](leverage.md) | How to read what the account holds |
| [Proof of results](proofs.md) | How each trade is time-stamped on the Bitcoin blockchain, and how to check one |

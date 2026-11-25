# Who decides: the side-by-side test

This page explains how the AI and our algorithm share the work: one decides the account's trades, the other answers the
same candles on a second practice wallet, and every answer is kept.

## The switch

Which of the two trades the account is a setting. At the time of writing (25 November 2026) the current test period is
named "Opus decides, our algorithm answers": the AI's calls trade the account, and the algorithm answers each trigger
alongside. The period's name is part of the public record (`period.name` in `/v1/record`, see
[Balance and test periods](../../record/balance.md)), so you can always see which one is deciding.

## The second wallet

The one that does not decide still trades: its answers run a second practice wallet with the same rules, the same
bracket and the same sizing. Both start level. So the comparison is not only "which call was right" but "which wallet
ended higher", with every cost counted.

The Advanced view on [fuze.trade](https://fuze.trade) shows the answers side by side for each trigger (time, price, what
was open, what each one said, and the result of each) and a score of how often each would have reached the take profit
first.

## What the comparison has shown so far

- **One week in replay** (10 to 16 November 2026, Bitcoin falling from about 74,000 to 64,000): the algorithm's wallet
  ended higher than the AI's. Shorting every trigger did as well as either; buying every trigger lost almost the whole
  wallet. The week shows the rules handle a trend at least as well as the AI. It does not show either one finds good
  trades.
- **Three years of history**, which only the algorithm can be replayed on: it loses after costs at Hyperliquid's fees
  and is close to zero at Lighter's.
- **Live, 16 to 24 November 2026**: every position was a short in a falling market, and both wallets made and lost their
  money on the trend.

## What it can and cannot show

A few weeks side by side will show whether the AI's choice of candles and levels adds anything over plain rules. It
cannot show a profit that three years of history do not. See [What the tests found](../../research/findings.md).

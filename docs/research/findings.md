# What the tests found

This page lists the verdicts of our tests, direction by direction, in plain numbers. Nearly all of them are failures,
and they are published because they are the most useful thing we know.

## Short-term: nothing beats costs

**No rule that holds a position 8 hours or less beat trading costs.** Before costs, almost everything makes about zero;
the loss is the cost.

| Direction | What was tested | Verdict |
|---|---|---|
| The AI's reads | 1,914 logged calls | Its 15-minute probability had no skill from 1 minute to 8 hours. 90% of its directional calls followed the last 15 minutes and were right 45% of the time |
| The AI's choice of trades | Every trigger in a falling week | Its shorts did no better than shorting every trigger, and the triggers it skipped did as well as the ones it took |
| Liquidations, open interest, order books, premium | 1,560 variants | Following a liquidation wave: 54% wins and -5.4 bps a trade over a year. Fading a high premium: -10.6 bps |
| Copying the best traders on the leaderboard | 528 variants | Wallets picked on past profit carried no information from 5 minutes to 1 day |
| Altcoins lagging Bitcoin | 5,050 variants | The lag is mostly gone within the minute; what is left is smaller than the costs |
| Prediction-market odds | 290 variants | The market was better calibrated than our estimate; rules lost on fresh data |
| Hours, sessions, weekdays, expiries, central-bank days | 83 variants | Nothing persists |
| Funding rates | 198 variants | Extremes do not predict direction |
| Stops and targets at chart levels | About 70 exit variants on 70,000 candles | None beat the fixed 1.5% / 1% / 8-hour bracket per trade |
| Moving the stop once a trade is in profit | Over 60 variants on 32,890 trades, 2023 to 2026 | None adds money (0 to 2 bps a trade less); trades closing in profit rise from 43% to between 50% and 76%. The account uses one as a rule: see [The bracket](../account/short-term/bracket.md) |
| Adding entries to a position | 3 years of calls replayed on an account, 2023 to 2026; 138 added entries on the practice account | An added entry earns the same per dollar as a first entry: adding changes the size, not the quality. Adding at any small profit made the worst month about a third deeper than adding from 50 bps. The account now adds only from 50 bps in profit, never to a losing position |
| Reversing on an opposite signal | Graded by signal strength | Reversing lost about 13 bps more than holding |
| Market regime (bull, bear, volatility, mood) | 68,000 triggers by regime | Every regime loses on both sides |
| Day-scale warnings and pauses after stops | 13 flags, several pause rules | None passes; a pause only loses less by trading less |
| Machine learning | 42 walk-forward variants (LightGBM, gradient boosting, Ridge, online learning) on 96 inputs | 0 of 42 pass. Models trained on shuffled labels landed in the same place as the real ones |
| The recorded tape | 8 features decided in advance, three weeks | None predicts the 5, 15 or 60-minute move |

In all, about 10,000 rule variants, plus the machine-learning study.

## Our own algorithm over three years

The algorithm replayed on 68,440 triggers from February 2023 to October 2026, with Hyperliquid's costs:

| Rules | 2023-02 to 2025-10 | 2025-11 to 2026-04 | 2026-05 to 2026-10 |
|---|---|---|---|
| Our algorithm, up to 5 entries | -8.9 bps per dollar | -12.3 bps | -6.2 bps |
| Our algorithm, one entry per position | -8.4 bps | -12.0 bps | -5.9 bps |
| The slow trend's side on every trigger | -8.3 bps | -9.2 bps | -7.4 bps |
| Against the slow trend on every trigger | -10.7 bps | -10.3 bps | -11.3 bps |

At Lighter's costs (no trading fee on a standard account, only the spread) the same algorithm comes to about -1 bps a trade: close to zero, still not positive. Stacking
entries does not change the result per dollar; it changes how many dollars are traded, and so how fast a balance moves
in either direction.

## A high win rate is not an edge

A take profit of 0.2% with a stop of 0.8% wins about 70% of trades and still lost about 8 bps a trade after costs. The
win rate comes from the bracket, not from any skill.

## The slow trend: the one thing that made money

Rule: every 4 hours, the average sign of the 14, 30 and 60-day returns, sized by volatility (see
[The slow trend position](../account/trend.md)).

- Confirmed by three independent re-implementations, no look-ahead, and it beat every placebo.
- It made money in every year from 2020 to 2026 on Bitcoin and Ether in our tests, and on an untouched 2017 to 2020
  stretch.
- Its worst drop was about 30% (up to 40% in some versions), about one position in four made money, and a few large
  ones carried the result.
- Weaknesses: its lookbacks sit on a peak of past results, Bitcoin and Ether were picked after another coin failed, and
  over the last three years the result is not statistically solid.

Past results promise nothing about the future.

## Still open

A handful of small ideas are too thin to decide and are re-checked as data arrives. None trades.

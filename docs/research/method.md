# How we test

This page describes the standard an idea has to meet before it may change how the account trades. Most ideas fail it;
that is the point.

## The rules of a test

1. **Write the pass mark down first.** What counts as a pass (how large, how consistent, how significant) is written
   before the first result is seen.
2. **Count every cost.** Fees, the spread, slippage and funding are in every result. An idea that only works before
   costs is not an idea.
3. **Test on data the idea never saw.** History is split by time. Rules are chosen on one stretch and run once, frozen,
   on later stretches. Where possible, an older stretch nobody looked at is used too.
4. **Walk forward.** For anything that learns, it is refitted on the past only, month by month, with a gap between
   training and testing so nothing leaks from the future.
5. **Beat a placebo.** The same test on shifted, flipped, random or shuffled versions of the signal must do clearly
   worse. If a placebo lands in the same place, the "edge" is noise.
6. **Hold in every period.** A result must keep its sign and size in each part of history, not just on average.
7. **Attack it independently.** Each candidate result is re-implemented from scratch by a separate checker on untouched
   data, audited for look-ahead and leakage, and audited for how it would really have been filled.

## The data

- **Candles**: Bitcoin and Ether candles back to 2017 for the trend, and every busy 5-minute candle from February 2023 to
  October 2026 (about 68,000 triggers) for the short-term rules, replayed on 1-minute candles.
- **Logged live calls**: every trigger the account saw, with the AI's and the algorithm's answers.
- **The tape**: second-by-second order-book, flow and liquidation data recorded since early November 2026 (see
  [Research recorders](../data/recorders.md)).

## Who does the work

The tests are run by AI agents (Claude Opus), each given one direction and the standard above, with every candidate
then re-checked by independent agents. We read the verdicts and decide. Results are written up with their
scripts and data, and the dead ends are listed so nobody tests them again.

## What a pass allows

A pass earns a forward test, nothing more. It runs alongside the account, logged, before it may change a trade. Nothing
short-term has reached that stage.

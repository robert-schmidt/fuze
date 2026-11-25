# Research recorders

This page describes two recordings the account keeps purely for research: a second-by-second market tape and a map of
where other traders would be liquidated. Neither one trades.

## The tape

Exchanges do not keep a history of their order books, so we record our own. Every second, from the public streams of
Hyperliquid, Binance, Bybit and OKX, the tape writes derived numbers: order-book imbalance and depth near the price,
taker buying and selling, liquidations, open-interest changes and the gap between exchanges. Raw ticks are not kept.

What it is for: testing ideas that history cannot test, and grading every trigger on real prices second by second.

What it has shown so far: on three weeks of tape (November 2026), none of 8 features decided in advance predicted the
5, 15 or 60-minute move, and none separated good short-term entries from bad. Entry research on the tape stopped there;
the recording continues.

## The liquidation map

Hyperliquid publishes every account's positions with their liquidation prices. The map reads the Bitcoin position of
every larger account on its leaderboard (about 13,500 accounts worth $20,000 or more), one request at a time, about 90
minutes per full round, and writes a row only when a position changes.

What it is for: two tests written down before any data came in. Does the price drift toward large clusters of
liquidation prices ("magnet")? And does crossing a cluster push the price further ("breach")? Each has a pass mark fixed
in advance. Neither has been judged yet.

A sample on 21 November 2026 found none of the 500 largest accounts within 10% of liquidation; the leverage near the
price sits in middle and small accounts.

## How these appear publicly

The order-book walls and the liquidation levels near the price are shown in the Advanced view on
[fuze.trade](https://fuze.trade), under "Markets we watch".

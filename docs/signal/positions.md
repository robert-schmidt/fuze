# Positions, not orders

This page explains the main design choice of the signal: it publishes the position the account holds, not the orders it
sends.

## The problem with orders

If we published orders ("sell 0.02 BTC now"), a follower who started late, lost the connection for a minute, or missed
one message would hold the wrong position, and nothing would ever correct it. Every missed or repeated message would add
up.

## A position is self-correcting

We publish the **target**: "we hold short 1.70 times our balance in Bitcoin". A follower compares that with what it
holds and trades the difference. If it starts late, reconnects or misses messages, the next message brings it to the
same place. A repeated message changes nothing.

## A ratio, not dollars

The position is published as **x**, its value divided by the account's balance. A follower multiplies by its own amount:

| Our position | Your setting | Your position |
|---|---|---|
| x = -1.70 on Bitcoin | 10% of a $1,000 balance ($100) | short $170 of Bitcoin |
| x = -1.70 on Bitcoin | 10% of a $5,000 balance ($500) | short $850 of Bitcoin |
| x = -1.70 on Bitcoin | a fixed $300 | short $510 of Bitcoin |

Because it is a ratio, any balance can follow any of our accounts (practice, test or real), and the account's own dollar
amounts are never needed.

## The short-term part travels with its bracket

Each coin can have one short-term trade, published separately (its own x, take profit, stop loss and risk score), and it
is always included in the coin's total. So a follower can place the same take profit and stop loss on its own exchange,
sized to that part, one pair per coin, and stay protected even if its agent or our signal goes down. The rest of the
coin's position is the trend part, published with its own x and score.

## Parts are followed whole

Because each part carries its own score, a follower can take some parts and skip others: the agent follows a part whole
when its score is at or under the user's risk allowed, and skips it whole otherwise. It never takes half a part. The
score says how much a part can lose, not how likely it is to win.

## Why a follower must not hold a fixed dollar size

When a short-term trade closes, x shrinks but often keeps its sign (the trend part is still there). A follower that held
the same dollar amount whatever x said would never close the short-term part. That is why the agent sizes as a share of
the balance or as a fixed amount multiplied by x, never as a constant position.

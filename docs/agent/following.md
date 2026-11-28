# How following works

This page explains what the agent does from the moment a message arrives to the moment your position changes, and when
it deliberately does nothing.

## 1. Check the message

Every message is checked in this order; anything that fails is dropped without acting:

1. The key named in it is built into the agent's code, and the signature is valid over the exact payload text.
2. Protocol version 2 (`/v2/signal`). A version 1 message is refused with "a version 1 message: this agent reads
   version 2 of the signal (/v2/signal)".
3. Its timestamp is newer than the newest message already accepted. That timestamp is kept on disk, so a restart cannot
   be fed an old message.
4. It has not expired, does not claim to live longer than 60 seconds after its timestamp, and is not from the future
   (more than 30 seconds ahead).
5. Every field has the right type and a sane range: only BTC, ETH, HYPE and LIT, sizes within 50 times the balance,
   known states, at most one short-term trade per coin that belongs to its coin's position, each trend part equal to
   its coin's x less its short-term trade, and risk scores that are whole numbers from 0 to 100.

## 2. Decide whether to act

The agent acts when:

- the signal's revision changes (our position, a bracket or the state changed),
- it has just started (the first valid message), or
- your position no longer matches what it last set (something closed it, for example a stop loss), or
- your limits changed (`fuze limits`, or your AI tool's `lower_limits`): it resizes on its next step, within seconds,
  on the same revision. A lowered limit shrinks every coin, even by less than the smallest change below (the exchange's
  own smallest order still applies). A raise you confirmed with `RAISE` applies the same way, without a restart.

Every 5 minutes it also re-checks: it compares what the signal asks for at your limits with what you hold, and corrects
a coin only when the difference is over the step below **and** over 10% of that coin's position. That corrects drift
(for example a balance that grew a lot in percent mode) without small orders every few minutes.

It never trades just because the price moved: `x` moves with the price while our position does not, and the re-check's
10% band is wider than that drift.

## 3. Choose the parts

Each coin's position comes in parts: the trend part, and at most one short-term trade. Each carries a risk score (see
[Limits: Risk allowed](limits.md#risk-allowed)). For each coin:

- not among your `coins`: the agent wants 0 of it, closes what it holds of it and never opens it;
- among your coins: it wants the trend part if its score is at or under your risk allowed, plus the short-term trade if
  there is one and its score is at or under your risk allowed. A part is followed whole or skipped whole.

Each skip is said in plain words in `fuze status`, for example "The Ether trend part scores 70, above your risk allowed
of 60: not followed." The score says how much a part can lose, not how likely it is to win.

## 4. Size your position

For each coin, your position value is the x of the parts you follow times your amount (a share of your balance, or a
fixed amount; see [Sizing](sizing.md)). Then:

1. it is cut to your cap per position, if you set one;
2. HYPE is cut to 20 times your counted balance and LIT to 5 times, the highest leverage Lighter allows on them;
3. if the coins together exceed your exposure cap (`max_x` times your balance), all are scaled down;
4. a change smaller than **$10 or 2% of your balance** (whichever is larger) is skipped, unless the target is zero.
   A small size can therefore hold nothing: `fuze status` shows, per coin, what the signal asks for and what you hold,
   and says when the difference is under this step.

## 5. The short-term trades and their brackets

Each short-term trade you follow gets its own take profit and stop loss, sized to that part (shrunk in the same
proportion if a cap cut the coin): one pair per coin, so up to four. On Lighter they rest on the exchange as reduce-only
orders. A short-term trade is **not opened** if:

- its stop loss is on the wrong side of the price, or more than 1.5% away,
- its take profit is on the wrong side,
- it already closed at its stop or target (the same trade is never reopened), or
- it is smaller than the exchange's smallest order.

The rest of the position is still followed.

## 6. The emergency stop

The rest of each position, the part that follows the slow trend, has no take profit or stop loss in the signal: the
trend rule leaves when its trends turn, and on history every stop we tried on it did worse than none
([what the tests found](../account/trend.md#what-the-tests-found-and-what-they-do-not-say)). Without an order behind it, that part would sit on the exchange unwatched
whenever your agent is off. So the agent rests one stop order for it, the emergency stop:

- **Where:** 20% from the price, on the losing side. One reduce-only order per coin, for exactly the part that has no
  take profit and stop loss of its own.
- **While the agent follows a live signal** it sets the stop again each time the price has moved 5% from where the
  stop was set, in either direction, and when the size of that part changes. So it stays between 15% and 25% from the
  price and is not part of how the account trades.
- **When the agent is off, paused, or the signal is gone** nothing moves it, and it fills if the price reaches it. That
  is its job: a position nobody is watching loses a bounded amount.
- **When it filled:** the agent says so in its status. With a live signal it brings the position back to what the
  signal asks for and rests a new stop.

On history (Bitcoin and Ether, 2020 to 2026, the trend rule's own sizes), a position left alone for 30 days lost up
to 69% of the account without this stop and up to 32% with it; left for 90 days, the whole account without it and up
to 32% with it. It filled in about one case in three within 30 days, and the average result was not worse for it.

What it does not do:

- It is not a price guarantee. Once triggered it is a market order that fills no worse than 4% past its price; in a
  gap larger than that it does not fill.
- In a move of more than 15% within seconds, faster than the agent can move it, it can fill while the agent runs.
  The position is then bought or sold back at the price of that moment.
- Lighter lets an order rest between 5 minutes and 30 days. The agent places it for 28 days (the default of Lighter's
  SDK) and places it again after 14; an agent that is off for more than 28 days leaves the position without it.
- In simulation the stop is checked only while the agent runs, like the simulated take profit and stop loss.

## 7. States, staleness and switches

| Situation | What the agent does |
|---|---|
| Signal `flat` | Closes everything and stays out |
| Signal `offline`, expired, or nothing valid for 60 seconds | Holds what it has, opens nothing new |
| `stale_flat_min` set and no live signal for that long | Closes everything |
| Your daily loss stop reached | Closes everything until the next UTC day |
| `PAUSE` on | Holds, places no new orders |
| `FLATTEN` on | Closes everything and stays out |

## Example

You follow with 10% of a $1,000 balance ($100) and the standard risk allowed of 60. The signal says Bitcoin x = -1.70,
of which a short-term trade of x = -1.30 (score 13) and a trend part of x = -0.40 (score 20), and Ether x = -0.33, all
trend (score 20). Your targets: Bitcoin short $170, of which $130 under the take profit and stop loss; Ether short $33.
Both are above $20 (2% of your balance), so both are opened.

With 5% instead, Ether would be $16.50: under the $20 threshold, so Ether is skipped until the signal asks for more or
your balance grows. With a risk allowed of 15 instead of 60, both trend parts (20) are skipped: Bitcoin short $130, all
of it the short-term trade, and no Ether.

## On Lighter, in addition

- After every order the agent reads the account back before doing anything else, and never sends a blind second order.
  An order that did not fill (or filled in part) waits 60 seconds and starts again from a fresh account read.
- An order in flight is written to disk before it is sent; after a crash or restart the agent reads the account instead
  of sending it again.
- Reductions are reduce-only, and every market order has a worst price: 0.5% past the signal's price to open or add, 2%
  to reduce or close. On Lighter testnet, whose order book is thin, the bounds are 3% and 4%.
- Sizes and prices are rounded to the decimals and smallest order Lighter publishes.
- If a coin's take profit and stop loss cannot be seen on the exchange after placing them, that short-term part is
  closed with a reduce-only order.
- Coins are handled one at a time: cancel that coin's old pair if its trade changed or ended, trade the coin, then
  place its new pair. If an order does not fill in full, the agent stops there, and the coins it did not reach keep
  their pairs.
- Markets are found by their symbol on Lighter (mainnet: BTC 1, ETH 0, HYPE 24, LIT 120). A coin with no market on
  that network is said and not traded.
- Lighter allows 60 requests a minute per account, orders included. In a quiet minute the agent stays at 30 or fewer
  with a short-term trade on every coin. With several pairs resting, it reads each coin's orders less often (with four
  pairs, each every 20 seconds). A take profit or stop loss that fills is still seen within 5 seconds, because the
  position moves; what can go unseen for up to 20 seconds is an order that went without a fill (cancelled or expired on
  the exchange). When a busy minute reaches 45 requests, reads wait; orders never do.
- The take profit, the stop loss and the emergency stop trigger on Lighter's mark price, not on the last trade. Lighter
  calls the mark price "the fair price of a perpetual contract" and builds it from its own order book, an index of spot
  prices and other exchanges' mark prices (https://docs.lighter.xyz/trading/fair-price-marking.md), so a stop can
  trigger before the last trade reaches it, or after.
- The emergency stop is a different order type from the take profit and stop loss (a stop-loss market order beside a
  take-profit-limit and a stop-loss-limit), so the agent never takes one for the other. If it cannot be placed, the
  position stays, the agent says so and tries again after 60 seconds.

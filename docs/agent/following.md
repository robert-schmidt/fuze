# How following works

This page explains what the agent does from the moment a message arrives to the moment your position changes, and when
it deliberately does nothing.

## 1. Check the message

Every message is checked in this order; anything that fails is dropped without acting:

1. The key named in it is built into the agent's code, and the signature is valid over the exact payload text.
2. Protocol version 1.
3. Its timestamp is newer than the newest message already accepted. That timestamp is kept on disk, so a restart cannot
   be fed an old message.
4. It has not expired, does not claim to live longer than 60 seconds after its timestamp, and is not from the future
   (more than 30 seconds ahead).
5. Every field has the right type and a sane range: only BTC and ETH, sizes within 50 times the balance, known states,
   a short-term part that belongs to its coin's position.

## 2. Decide whether to act

The agent acts when:

- the signal's revision changes (our position, its bracket or the state changed),
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

## 3. Size your position

For each coin, your position value is our x times your amount (a share of your balance, or a fixed amount; see
[Sizing](sizing.md)). Then:

1. it is cut to your cap per position, if you set one;
2. if the coins together exceed your exposure cap (`max_x` times your balance), all are scaled down;
3. a change smaller than **$10 or 2% of your balance** (whichever is larger) is skipped, unless the target is zero.
   A small size can therefore hold nothing: `fuze status` shows, per coin, what the signal asks for and what you hold,
   and says when the difference is under this step.

## 4. The short-term part and its bracket

The short-term part gets its own take profit and stop loss, sized to that part (shrunk in the same proportion if a cap
cut the coin). On Lighter they rest on the exchange as reduce-only orders. That part is **not opened** if:

- its stop loss is on the wrong side of the price, or more than 1.5% away,
- its take profit is on the wrong side,
- it already closed at its stop or target (the same trade is never reopened), or
- it is smaller than the exchange's smallest order.

The rest of the position is still followed.

## 5. States, staleness and switches

| Situation | What the agent does |
|---|---|
| Signal `flat` | Closes everything and stays out |
| Signal `offline`, expired, or nothing valid for 60 seconds | Holds what it has, opens nothing new |
| `stale_flat_min` set and no live signal for that long | Closes everything |
| Your daily loss stop reached | Closes everything until the next UTC day |
| `PAUSE` on | Holds, places no new orders |
| `FLATTEN` on | Closes everything and stays out |

## Example

You follow with 10% of a $1,000 balance ($100). The signal says Bitcoin x = -1.70 with a short-term part of x = -1.30,
and Ether x = -0.33. Your targets: Bitcoin short $170, of which $130 under the take profit and stop loss; Ether short
$33. Both are above $20 (2% of your balance), so both are opened.

With 5% instead, Ether would be $16.50: under the $20 threshold, so Ether is skipped until the signal asks for more or
your balance grows.

## On Lighter, in addition

- After every order the agent reads the account back before doing anything else, and never sends a blind second order.
  An order that did not fill (or filled in part) waits 60 seconds and starts again from a fresh account read.
- An order in flight is written to disk before it is sent; after a crash or restart the agent reads the account instead
  of sending it again.
- Reductions are reduce-only, and every market order has a worst price: 0.5% past the signal's price to open or add, 2%
  to reduce or close.
- Sizes and prices are rounded to the decimals and smallest order Lighter publishes.
- If the take profit and stop loss cannot be seen on the exchange after placing them, that part is closed.

# Adding to a position

This page explains what happens when a decider calls the same side again while a short-term position is open, and why
an opposite call never reverses it.

## Same side: one more entry

A long call while a long is open (or short while short) **adds one more entry**:

- the new entry puts up the same margin as the first and keeps the first entry's leverage;
- the average entry moves to include the new price;
- the take profit and stop loss are set again for the **whole** position, from the new average entry;
- the 8-hour time limit restarts.

A position holds at most **5 entries**. Once it is full, nothing is added.

## When an entry is added

An entry is added only once the position is at least **50 bps in profit** from its average entry. Below that, a
same-side call adds nothing; it can still move the stop and target.

- **Never to a losing position.** Adding to a loser makes the position largest exactly when the trade is being proven
  wrong. Every well-known trader who wrote down rules says the same: add only to a trade that is working.
- **Only when the stop is already in profit.** At 50 bps in profit the [stop has moved](bracket.md) to the average
  entry + 25 bps, and an added entry keeps it there. The average entry of the bigger position moves toward the price, so
  its stop sits at about the new average entry instead of 1% behind it.

The rule is enforced for both deciders, the algorithm and the AI.

## Worked example

Balance $1,000, 5% margin, 30x:

| Step | Price | Entries | Position | Average entry | Stop | Take profit |
|---|---|---|---|---|---|---|
| Short opens | 60,000 | 1 | $1,500 short | 60,000 | 60,600 (1% above) | 59,100 (1.5% below) |
| Same-side call 30 bps in profit | 59,820 | 1 | $1,500 short | 60,000 | 60,600 | 59,100 |
| Price is 50 bps in profit: the stop moves | 59,700 | 1 | $1,500 short | 60,000 | 59,850 (25 bps in profit) | 59,100 |
| Same-side call | 59,700 | 2 | $3,000 short | 59,850 | 59,850 (kept) | about 58,952 |

The second entry doubled the position. Its stop is at the new average entry, so a bounce closes the whole position at
about break-even. An entry added earlier, before the stop had moved, would have put 1% of a double position at risk. The stop moves again once the
price is 50 bps beyond the new average entry.

## What the tests found

Over 2023 to 2026, an added entry earned the same per dollar as a first entry. Adding makes the position bigger; it
does not make the entries better. Entries added at any small profit made the worst month of the account about a third
deeper than entries added from 50 bps. See [What the tests found](../../research/findings.md).

## Opposite side: no reversal

An opposite call does not close the position and does not open the other side. Our algorithm skips it; the position
keeps its stop and target. Over 2023 to 2026, reversing on an opposite signal lost about 13 bps more than holding, and
closing early made no measurable difference. See [What the tests found](../../research/findings.md).

## In the account

Only the short-term book adds this way. The [slow trend position](../trend.md) is resized every 4 hours by its own rule.

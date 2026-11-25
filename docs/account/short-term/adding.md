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

## When not to add

- Our algorithm adds only to a position that is **in profit** and not full. A losing or full position is left to run to
  its target or stop.
- The AI is told the same: add only to a trade that is working, and choose the stop and target for the whole position.
  When the position is full and should simply run, it should skip.

## Worked example

Balance $1,000, 5% margin, 30x:

| Step | Price | Entries | Position | Average entry | Stop (1% above) | Take profit (1.5% below) |
|---|---|---|---|---|---|---|
| Short opens | 60,000 | 1 | $1,500 short | 60,000 | 60,600 | 59,100 |
| Price falls, same-side call | 59,400 | 2 | $3,000 short | about 59,700 | about 60,297 | about 58,805 |

The second entry doubled the position and pulled the stop down with the average entry. A normal bounce now reaches the
stop sooner. Adding locks in some profit and also raises the chance of an early exit.

## Opposite side: no reversal

An opposite call does not close the position and does not open the other side. Our algorithm skips it; the position
keeps its stop and target. Over 2023 to 2026, reversing on an opposite signal lost about 13 bps more than holding, and
closing early made no measurable difference. See [What the tests found](../../research/findings.md).

## In the account

Only the short-term book adds this way. The [slow trend position](../trend.md) is resized every 4 hours by its own rule.

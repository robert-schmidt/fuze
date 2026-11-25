# In shadow: the nightly model and the stop observer

This page describes two things that run next to the account and never trade: a model that is retrained every night,
and an observer of every stop loss. Both are live. Both only write down what they see, and both are graded against what
actually happened.

## The nightly model

A machine-learning model that learns from the account's own short-term triggers.

- **The model**: LightGBM (gradient-boosted decision trees).
- **When it learns**: it is retrained every night at 04:00 UTC.
- **What it learns from**: the per-second recordings of the market around each trigger. About three weeks of them
  exist so far.
- **Where it runs**: in a container of its own, with no network access.
- **When it starts answering**: not before it has 1,000 graded triggers to learn from. On 25 November 2026 it had 797,
  so it makes no call yet.
- **What it does then**: for each trigger, it logs its call next to the AI's and our algorithm's, and its calls are
  graded the same way as theirs.
- **What it cannot do**: trade. No code path lets it open, close or size a position, or change the signal.

### The promotion rule, and why it switches nothing on

The rule a model would have to pass before anyone even discussed using it:

| Condition | Bar |
|---|---|
| Graded calls | At least 1,500, over at least 8 weeks |
| Result per call | At least 3 basis points (0.03%) better than both the AI and the algorithm |
| Strength of the evidence | A t-value of at least 2.5 |
| Consistency | Better in 3 of the last 4 four-week blocks |

Passing it is only **reported**. It switches nothing on: there is no automatic route from the model to a trade.

Our earlier study of this kind of model found 0 of 42 variants that beat costs on history (see
[What the tests found](findings.md)). The nightly model keeps checking that on live data; we do not expect it to win.

## The stop observer

A recorder that looks at every short-term trade that ended at its stop loss. For each one it writes down:

- what the price did afterwards;
- how the same trade would have ended with a stop loss 1.5 times further away;
- with a stop loss 2 times further away;
- with no stop loss at all, held until the time limit;
- if it had been skipped;
- if it had been reversed (the opposite side).

It then totals each alternative across all the stopped trades it can reproduce, so the question "would a wider stop
have done better?" is answered with the account's own live trades rather than with memory of the painful ones.

It changes no rule. Our three-year tests of wider stops found none that beats the current stop loss; the observer
keeps measuring the same question as live trades accumulate.

## What "in shadow" means

| | Trades the account | Changes the signal | Is logged and graded |
|---|---|---|---|
| The decider (AI or algorithm) | Yes | Yes | Yes |
| The other decider | A second practice wallet only | No | Yes |
| The nightly model | No | No | Yes, once it has 1,000 graded triggers |
| The stop observer | No | No | Yes |

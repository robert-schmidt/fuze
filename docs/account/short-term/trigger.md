# What triggers a look

This page explains when the short-term book considers a trade at all. It does not watch every tick: it waits for a
particular kind of candle.

## The trigger: a busy 5-minute candle

A **candle** summarises the price over a fixed period: where it opened, its high, its low, where it closed, and how much
traded (the volume). The short-term book watches Bitcoin's 5-minute candles. When a candle **closes** with about
**1.5 times the average volume of the 20 candles before it**, that candle is a **trigger**.

The idea behind it: a burst of volume means many traders acted at once. Something happened, and it is worth a look.

## How often

Roughly 50 triggers a day, more on busy days and fewer at weekends. Over February 2023 to October 2026 there were about
68,000 of them; that history is what the tests on [What the tests found](../../research/findings.md) use.

## What a trigger is not

A trigger is not a trade. Most triggers end in "skip". It only means the decider is asked, with a fresh snapshot of the
market, whether to trade now.

## What the trigger candle carries

Along with the volume, the snapshot describes the trigger candle itself:

- its direction (up or down) and its body (how far it moved from open to close),
- whether it made a new 1-hour high or low and closed back with a long wick (a **rejection**: buyers or sellers pushed
  and failed),
- textbook situations it created, stated as facts: it swept a level and closed back, broke a level, retested a level,
  traded heavy volume in a small range (absorption), broke out of a tight range, or made a new high on net selling.

How the deciders use this is on [What the AI is shown and asked](ai.md) and [Our own algorithm](algorithm.md).

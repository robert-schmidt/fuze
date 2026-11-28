# The short-term trades

This section explains the short-term book: the part of the account that opens Bitcoin trades held for minutes to
hours, each with its own take profit and stop loss. The pages follow one trade from start to finish.

## The life of one short-term trade

1. **A trigger.** A 5-minute candle closes on unusually high volume. See [What triggers a look](trigger.md).
2. **A question.** A snapshot of the market goes to the decider: the AI (Claude Opus) or our own algorithm. Both answer
   the same question in the same form: long, short or skip, and how sure. See [What the AI is shown and asked](ai.md)
   and [Our own algorithm](algorithm.md).
3. **One decides, the other is recorded.** Which one trades the account is a switch; the other answers the same candle
   on a second practice wallet so the two can be compared. See [Who decides](who-decides.md).
4. **An entry with a bracket.** A trade opens at once with a market order, with a take profit, a stop loss and a time
   limit. See [The bracket](bracket.md).
5. **A size.** Each entry sets aside a fixed share of the balance as margin; the decider's confidence sets the leverage.
   See [Leverage and size](leverage-size.md).
6. **Maybe more entries.** A later call on the same side can add to a position that is at least 50 bps in profit, up
   to five entries. See [Adding to a position](adding.md).
7. **An end.** The trade ends at its take profit, its stop loss or its time limit, whichever comes first.

## In one table

| Question | Answer at the time of writing |
|---|---|
| Coins | Bitcoin, Ether, HYPE and LIT, each with its own trade (at most one per coin) |
| When it looks | When a 5-minute candle closes on about 1.5 times the average volume of the 20 before |
| Who decides | Claude Opus, in one call for every coin whose candle was busy at that 5-minute close; our algorithm decides a coin when the AI has no answer for it (the call failed, took too long, or left the coin out), and its answer is kept beside the AI's on every call |
| Sides | Long or short; in the account, only on the side of the slow trend |
| Take profit / stop loss | About 1.5% / 1% from the average entry by default; never a stop more than 1% from it |
| Time limit | 8 hours |
| Leverage | Bitcoin 20x to 40x and Ether 20x to 25x, from the decider's confidence; HYPE 20x; LIT 5x |
| Margin per entry | A fixed share of the balance (5% at the time of writing) |
| Entries per position | Up to 5 |

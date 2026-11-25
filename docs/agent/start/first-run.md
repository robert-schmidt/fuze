# First run in simulation

This page sets your sizing, starts the agent on a simulated $1,000 account, and shows you how to read what it does. No
exchange, no key, no money.

## 1. Choose how big your positions are

```sh
fuze init
```

It asks where to trade (press Enter to keep `simulation`) and five sizing questions; Enter keeps each default. Or give
the answers as flags:

```sh
fuze init --yes --size-mode percent --percent 5 --max-position-usd 300 --max-x 2 --daily-loss 5
```

It prints your sizing in words, with a worked example:

```text
Your sizing, shown on a $1,000 balance:
  10% of your balance follows the signal. Your positions grow and shrink with your balance.
  Largest position on one coin: no cap.
  Most you hold across coins: 3 times your balance.
  Daily loss stop: 10% of the balance in a UTC day closes everything.
  With $1,000 and our position at 1.8 times our balance, yours would be $180 of Bitcoin. With $2,000 it would be $360.
```

What the choices mean: [Sizing](../sizing.md) and [Limits and safety switches](../limits.md).

## 2. Check the setup

```sh
fuze check
```

Everything should say `[ok]` except `[NO] Agent is running`, because it is not running yet.

## 3. Start the agent

In its own terminal window:

```sh
fuze run
```

The output below comes from a run with the default 10% (25 November 2026):

```text
FUZE agent (simulated account, no real money). Ctrl+C to stop.
... Protected the scalp part -0.004433 BTC: take profit 57797, stop loss 59029.
... Following revision 7: the signal asks for BTC short $300, ETH short $33 at your limits.
... Following revision 7; nothing to change.
```

Leave it running. Ctrl+C stops it; positions stay as they are.

## 4. See what it holds and why

In another terminal:

```sh
fuze status
```

The output below was taken after lowering to a fixed $10 (`fuze limits --size-mode fixed --fixed-usd 10`):

```text
Mode: simulation (a simulated account, no money)
Agent: running, last step 1 s ago
Balance: $999.87
Positions (what the signal asks for at your limits, and what you hold):
  BTC: the signal asks for short $30, you hold short $30
  ETH: the signal asks for short $3, you hold none
  The difference on ETH is under $20, the smallest change the agent makes (the larger of $10 and 2% of your balance), so it is not traded now.
  A coin held at none because its size is under that step stays unfollowed at this size.
Signal: revision 7, live, from our practice money (paper) account. Why (data from the server): We hold short 3.00 times ...
Last step: Following revision 7: the signal asks for BTC short $30, ETH short $3 at your limits; ...
Pause: off. Flatten: off.
Sizing:
  ...
```

Per coin it shows what the signal asks for at your limits and what you hold, in dollars. Here Ether is not opened:
$3 is under the $20 smallest change of a $1,000 balance (see [How following works](../following.md)).

## 5. Try the safety switches

```sh
fuze pause      # hold, no new orders
fuze resume     # undo: type RESUME
fuze flatten    # close everything and stay out
fuze unflatten  # undo, type UNFLATTEN: it follows again
```

## Next

- Connect your AI coding tool: [Using it from an AI coding tool](../ai-tools/README.md).
- Leave it running for a few days and compare with the public record. When you understand what you see, read
  [The three modes](../modes/README.md).

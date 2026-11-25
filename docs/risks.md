# Risks, plainly

This page lists what can go wrong if you follow FUZE, in plain words. None of it is small print; read it before you
install anything.

## The strategy

- **You copy one account.** If it loses, you lose in the same proportion. There is no second opinion and no hedge.
- **The short-term trades have no proven edge.** About 10,000 rule variants and a machine-learning study found nothing
  short-term that beats trading costs. On three years of history the short-term trades lost a little after costs.
  See [What the tests found](research/findings.md).
- **Only the slow trend made money in our tests, and it is slow and bumpy.** In history it went through drops of about
  30% and long stretches below its previous high, and most of its positions lost; a few large ones carried the result.
  History is not a forecast.
- **Today the account trades practice money.** Its results cost it nothing. If you follow with real money, yours do.
  The agent tells you when this is the case.

## Leverage

- Futures let a position be many times larger than the money behind it. The account's short-term trades open at 20 to
  40 times leverage. A 1% move against a 30x position is about a 30% loss of the money set aside for it.
- You can lose everything you put in, quickly. A stop loss limits a loss; it does not guarantee the price you get.

## Following is not the same as holding

- Your fills will differ from ours: a different moment, a different price, different exchange conditions.
- Your limits change the copy on purpose. A cap per position, an exposure cap or the rule that skips tiny changes all
  make your result differ from the account's, in either direction.

## Software and services

- Software, servers, exchanges and networks fail. When the signal stops, the agent holds what it has and opens nothing
  new; it does not know what the account would have done.
- FUZE's Lighter code (test money and real money) is new and has not yet traded on the real exchange. It is tested
  against a fake exchange only, and the agent has had no independent security review. A stop loss can fill worse than its price in a fast market, or not at all.

## You and your situation

- Nothing here is financial advice. Nobody at FUZE knows your situation.
- Rules on trading futures and on following trading signals differ from country to country, and exchanges exclude
  residents of some countries. Check what applies to you.
- Only use money you can afford to lose completely.

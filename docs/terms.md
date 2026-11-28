# Glossary

This page defines the terms used in these docs, in alphabetical order.

| Term | Meaning |
|---|---|
| Account leverage | Everything the account holds, added up, divided by its balance. $2,030 of positions on $1,000 is 2.0x |
| Agent | The FUZE program that runs on your computer and follows the signal on your account |
| Average entry | The average price of all entries in a position |
| Balance | The account's value, including open positions |
| bps (basis points) | Hundredths of a percent. 100 bps = 1% |
| Bracket | The take profit and stop loss set around a trade |
| Candle | A summary of the price over a fixed period: open, high, low, close and volume |
| Cross margin | All positions share one margin pool, the whole balance |
| Drawdown | A fall from a previous high in the balance |
| Ed25519 | The digital signature scheme the signal uses |
| Edge | A rule that makes money after costs, reliably, on data it was not built on |
| Entry | One order that opens or adds to a position |
| Envelope | The signed wrapper of a signal message: payload, signature, key name |
| Exposure cap (`max_x`) | The most the agent may hold across coins, as a multiple of your balance |
| Fear & Greed index | A daily 0 to 100 reading of crypto market mood |
| Flatten | Close everything and stay out |
| Funding | A payment between longs and shorts every hour that keeps a perpetual's price near the spot price. On Lighter it is "fully peer-to-peer with no fees taken by the exchange" and capped at 4% per 8 hours (0.5% an hour) (https://docs.lighter.xyz/trading/funding.md) |
| Leverage | How many times bigger a position is than the margin set aside for it |
| Lighter | A decentralized exchange for perpetual futures, built as a zero-knowledge rollup on Ethereum. A standard account pays no trading fee on regular orders; TWAP, advanced orders and RFQ cost 1 bp, and funding and the spread are paid as anywhere (https://docs.lighter.xyz/trading/trading-fees.md). The account's main exchange and where the agent trades in its testnet and mainnet modes |
| Liquidation | The exchange closing positions by force because the account's margin ran out. Lighter does it in stages on the mark price: below the maintenance margin it cancels the account's open orders and closes its positions at any price, taking up to 1% as a fee for its insurance fund; below the lower close-out margin the fund takes the positions over; when the fund cannot, positions on the other side are cut (auto-deleveraging) (https://docs.lighter.xyz/trading/liquidations-and-llp-insurance-fund.md) |
| Long / short | A position that gains when the price rises / falls |
| Mainnet | The real exchange, with real money |
| Maker / taker | A maker order waits in the book; a taker order trades at once. Many exchanges charge the taker more; on Lighter's standard account neither pays a fee |
| Margin | The part of the balance set aside to hold a position |
| Mark price | The price an exchange uses for margin and stop losses. Lighter calls it "the fair price of a perpetual contract" and builds it from its order book, an index of spot prices and other exchanges' mark prices, so it can differ from the last trade (https://docs.lighter.xyz/trading/fair-price-marking.md) |
| MCP (Model Context Protocol) | A standard way for AI tools to call local programs. The agent's MCP server is how your AI tool talks to it |
| Open interest | The value of all futures positions still open |
| Order book | The orders waiting to buy (bids) and sell (asks) |
| Paper (practice money) | Simulated trading at real prices, with no money at stake |
| Perpetual future (perp) | A futures contract with no expiry that tracks the coin's price |
| Placebo | A deliberately meaningless version of a signal, used to check that a test result is not noise |
| Rehearsal | The agent's testnet run that opens, protects and closes the smallest position, required before mainnet |
| Reduce-only | An order that can only shrink a position, never open or grow one |
| Revision (`rev`) | The signal's counter that rises only when the position, its bracket or the state changes |
| Scalp | A short-term trade with a take profit and a stop loss, held minutes to hours |
| Shadow | Running alongside, logged and graded, without trading |
| Simulation | The agent's default mode: a simulated $1,000 account on your computer, no money |
| Slippage | The difference between the expected price and the price an order actually gets |
| Slow trend (trend book) | The slow part of the account: it follows the direction of the last weeks and holds for days |
| Stop loss | An order that closes a trade when the price moves a set distance against it |
| Take profit | An order that closes a trade when the price reaches a target in its favour |
| Testnet | An exchange's test version, with test money |
| Trigger | A 5-minute candle that closes on unusually high volume, which makes the short-term book take a look |
| VWAP | The day's average price weighted by volume |
| x | A position's value divided by the balance. Negative is short |

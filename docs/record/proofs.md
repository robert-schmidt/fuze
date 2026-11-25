# Proof of results

This page explains how each trade record is time-stamped on the Bitcoin blockchain, so it cannot be changed later
without it showing, and how you can check one yourself.

## What is stamped

Since 5 November 2026, every trade record is written when the trade opens and again when it closes. Each record is
chained to the one before it (it includes a fingerprint of the previous record), and each one is time-stamped with
**OpenTimestamps**, a free public service that anchors a fingerprint of a file in a Bitcoin transaction.

The result:

- a record cannot be edited later without its fingerprint changing, and the stamp no longer matching;
- a record cannot be removed or inserted without breaking the chain;
- the stamp proves the record existed at that time.

The Advanced view on fuze.trade says whether every record since the start is chained and stamped, and shows a warning if
not.

## How to check a trade

1. On [fuze.trade](https://fuze.trade), open the Advanced view, then **Closed trades**.
2. In the **Proof** column of a trade, download its record (`open` or `close`) and its stamp (`stamp`).
3. Drop both files on [opentimestamps.org](https://opentimestamps.org/). It shows the Bitcoin block that confirms the
   time.

A tick next to the stamp means it is already confirmed in a Bitcoin block. A fresh stamp takes a few hours to confirm.

## What a proof does and does not show

It shows the record was not changed after it was stamped. It does not show the trade was a good idea, and for a practice
account it does not show a real exchange filled it: practice trades never reach an exchange, so they have no exchange
transaction. When the account trades on an exchange, each order also has a public transaction on that exchange's
explorer.

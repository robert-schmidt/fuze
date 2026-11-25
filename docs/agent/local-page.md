# The local page

This page describes `fuze ui`, a read-only page on your own computer that shows everything the agent is doing. It is
part of FUZE since version 0.3.0.

## Starting it

```sh
fuze ui --open
```

It serves the page at **http://127.0.0.1:3893** (3893 spells F-U-Z-E on a phone keypad). `--port` picks another port,
`--open` opens your browser. It works whether or not `fuze run` is running; when the agent is stopped it says so and
reads the public signal itself. Your AI tool can give you the address too: ask it to "open the FUZE page".

## What it shows

- Whether the agent is running, paused or stopped, and since when.
- The mode, with real money impossible to miss.
- Your balance and today's result, and how much of today's loss stop is used.
- Each position with its size, entry, current price and result; the short-term part between its take profit and stop
  loss.
- Per coin, what the signal asks for at your limits next to what you hold, in dollars, and a note when the difference
  is under the smallest change the agent makes (so a small size that holds nothing is explained).
- The signal: state, revision, age, whether the signature checked out, and which of our accounts it comes from.
- Your sizing and limits in plain words.
- Recent orders, with explorer links in testnet and mainnet.
- The setup checks, and whether keys are "set" or "missing".

## What it does not do

It only reads. It never trades and never changes a setting: next to each thing you might change, it shows the command
to type (`fuze pause`, `fuze limits ...`, `fuze mode ...`) or the sentence to say to your AI tool. It never shows a key
or where a key is stored.

It listens on 127.0.0.1 only (there is no option to change that), answers only requests addressed to 127.0.0.1 or
localhost, accepts only GET requests, serves a fixed list of files and loads nothing from anywhere else. No other web
page can show it inside a frame (`frame-ancestors 'none'` in its Content-Security-Policy and `X-Frame-Options: DENY`),
so a page you visit cannot overlay it. Its links lead
to [fuze.trade](https://fuze.trade) and these docs.

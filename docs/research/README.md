# Testing ideas before they go live

This section explains how we test a trading idea before it can touch the account, what those tests found, and why the
short-term trades still run even though the tests say they lose a little after costs.

## The short version

- About **10,000 rule variants** across twelve directions, a three-year replay of our own algorithm, and a
  **machine-learning study** with 42 variants found **nothing short-term that beats trading costs**.
- On three years of history (2023 to 2026) the short-term trades **lose a little after costs**: about 9 bps per dollar
  traded at Hyperliquid's fees, close to zero at Lighter's near-zero fee. Before costs they make about nothing.
- **Only the slow trend made money** in our tests, with deep drops along the way.
- The short-term trades still run because the account trades **practice money** and the point is to learn.

## Pages

| Page | Covers |
|---|---|
| [How we test](method.md) | The standard every idea has to meet |
| [What the tests found](findings.md) | The verdicts, direction by direction |
| [Why costs decide](costs.md) | Why a small fee turns "about nothing" into a loss, and what a zero-fee exchange changes |
| [Why the short trades still run](why-scalp.md) | The honest reason |
| [In shadow](shadow.md) | The nightly model and the stop observer: they watch, learn and are graded, but never trade |

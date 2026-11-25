# How to read these docs

This page explains how the book is organised and the conventions it uses, so you can find what you need quickly.

## Two parts

| Part | Answers | Read it if |
|---|---|---|
| [Part 1: The account and its signal](account/README.md) | What the account does, which data it reads, how ideas are tested, what the signal says and how to check it, how to read the public record | You want to know what you would be copying, or you only want to read the signal |
| [Part 2: The agent and its MCP server](agent/README.md) | How to install and run the agent, its modes, keys, sizing and limits, how to use it from an AI coding tool | You want to follow the signal |

Each page covers one idea and opens with a sentence or two saying what it covers. Pages link to each other where one
idea depends on another.

## Conventions

- **Numbers are examples.** Worked examples use a $1,000 balance. Numbers that describe the account (leverage, stop
  distance and so on) are the rules at the time of writing, 25 November 2026; the signal and the public record always
  show what is true now.
- **bps** means basis points: 1 bps is 0.01%. A 100 bps stop is 1% from the entry price.
- **x** is a position's value divided by the balance. Short positions are negative: x = -1.7 means a short worth
  1.7 times the balance.
- **Commands** are shown as you type them. Where a command lives in a virtual environment, the docs say so.
- **Warnings** are set apart like this:

> **Warning:** a real warning about money or safety looks like this. Other notes are plain text.

## Words

New terms are explained the first time they appear and collected in the [Glossary](terms.md).

## What these docs do not cover

- How our servers are run. The signal is designed so that you do not need to trust them: you check the signature.
- Advice about whether to trade. There is none here.

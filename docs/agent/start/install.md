# Install

This page installs the agent and its MCP server into a virtual environment of their own, from the repository checkout.

## What you need

- macOS or Linux (on Windows, use WSL).
- Python 3.10 or newer: check with `python3 --version`.
- `git`.

## Install from the repository

The agent is not on PyPI yet; a release there is coming. Until then, install it from a checkout of the repository. The
repository's address is published on [fuze.trade](https://fuze.trade) when it opens.

```sh
git clone <the FUZE agent repository> fuze
cd fuze
python3 -m venv ~/.fuze-venv
~/.fuze-venv/bin/pip install '.[mcp]'
~/.fuze-venv/bin/fuze --version
```

The last command prints the version, for example `0.3.0`.

| Install | Adds | Needed for |
|---|---|---|
| `pip install .` | The agent (one dependency, `cryptography`) | Simulation |
| `pip install '.[mcp]'` | The official MCP SDK | Using it from an AI coding tool (`fuze mcp`) |
| `pip install '.[mcp,lighter]'` | Lighter's official SDK (pinned to 1.1.8) and `keyring` | Testnet and mainnet |

> **Warning:** do not install a package called `fuze-agent` from PyPI. The PyPI release is not out yet, the name is not
> registered by us, and a package of that name on PyPI today is **not ours**: anyone could publish one. Install only from
> the repository checkout, as above. To pin every dependency by its hash, follow the repository's `SECURITY.md`.

## Put `fuze` on your PATH (optional)

These docs write commands as `fuze ...`. Either type the full path (`~/.fuze-venv/bin/fuze`), or make the short name
work:

```sh
mkdir -p ~/.local/bin && ln -sf ~/.fuze-venv/bin/fuze ~/.local/bin/fuze
```

(`~/.local/bin` must be on your PATH; on most Linux systems it is, on macOS add it in your shell profile.)

Your AI coding tool does not use your PATH: `fuze mcp-config` prints its settings with the full path, as shown on
[Using it from an AI coding tool](../ai-tools/README.md).

## Where it keeps its files

In `~/.fuze`, private to your user. To use another folder, set `FUZE_HOME` (for example `export FUZE_HOME=~/fuze-test`).
See [Files it keeps](../files.md).

## Updating

```sh
cd fuze && git pull
~/.fuze-venv/bin/pip install '.[mcp]'
```

Read the release notes before you update. After an update, mainnet asks for a new testnet rehearsal: each version
changes code that sends orders, so the version that will trade real money must have worked on testnet first.

## Removing

Stop the agent, then delete `~/.fuze-venv` and, if you no longer want your settings and logs, `~/.fuze`. If you stored a
Lighter key, run `fuze keys testnet --delete` (and `mainnet`) first, and replace the key on Lighter.

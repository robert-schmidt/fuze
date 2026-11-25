# Install

This page installs the agent and its MCP server. The usual way is one command that puts `fuze` on your PATH, straight
from the repository; the other way is a clone you can read first.

## What you need

- macOS or Linux (on Windows, use WSL).
- Python 3.10 or newer: check with `python3 --version`.
- `git`, and [uv](https://docs.astral.sh/uv/) or [pipx](https://pipx.pypa.io) for the usual way.

Install FUZE only from `github.com/robert-schmidt/fuze`. To pin every dependency by its hash, follow the repository's
`SECURITY.md`.

## The usual way: `fuze` on your PATH

With uv:

```sh
uv tool install "fuze-agent[mcp] @ git+https://github.com/robert-schmidt/fuze"
fuze --version
```

Or with pipx:

```sh
pipx install "fuze-agent[mcp] @ git+https://github.com/robert-schmidt/fuze"
fuze --version
```

The last command prints the version, for example `0.3.0`. Each tool keeps FUZE in an environment of its own and puts
the `fuze` command in `~/.local/bin`. If your shell does not find `fuze`, run `uv tool update-shell` (or
`pipx ensurepath`) and open a new terminal.

The Claude Code plugin and the short MCP settings start the command `fuze`, so this install is the one they expect. See
[Using it from an AI coding tool](../ai-tools/README.md).

## The other way: a clone you read first

```sh
git clone https://github.com/robert-schmidt/fuze
cd fuze
python3 -m venv ~/.fuze-venv
~/.fuze-venv/bin/pip install '.[mcp]'
~/.fuze-venv/bin/fuze --version
```

These docs write commands as `fuze ...`. With this install, either type the full path (`~/.fuze-venv/bin/fuze`), or
make the short name work:

```sh
mkdir -p ~/.local/bin && ln -sf ~/.fuze-venv/bin/fuze ~/.local/bin/fuze
```

(`~/.local/bin` must be on your PATH; on most Linux systems it is, on macOS add it in your shell profile.) Your AI
coding tool needs the full path: `fuze mcp-config` prints its settings with it.

## The extras

| Extra | Adds | Needed for |
|---|---|---|
| none | The agent (one dependency, `cryptography`) | Simulation |
| `[mcp]` | The official MCP SDK | Using it from an AI coding tool (`fuze mcp`) |
| `[mcp,lighter]` | Lighter's official SDK (pinned to 1.1.8) and `keyring` | Testnet and mainnet |

To add `lighter` later, run the install again with both extras, the way you installed:

```sh
uv tool install "fuze-agent[mcp,lighter] @ git+https://github.com/robert-schmidt/fuze"
pipx install --force "fuze-agent[mcp,lighter] @ git+https://github.com/robert-schmidt/fuze"
~/.fuze-venv/bin/pip install '.[mcp,lighter]'      # in your clone
```

When an extra is missing, `fuze` names the command that matches your install.

## Where it keeps its files

In `~/.fuze`, private to your user. To use another folder, set `FUZE_HOME` (for example `export FUZE_HOME=~/fuze-test`).
See [Files it keeps](../files.md).

## Updating

```sh
uv tool upgrade fuze-agent                      # uv: fetches the newest commit, keeps your extras
# pipx: run your install command again with --force, with the repository address in it
cd fuze && git pull && ~/.fuze-venv/bin/pip install '.[mcp]'   # a clone (add lighter if you use it)
```

Read the release notes before you update. After an update, mainnet asks for a new testnet rehearsal: each version
changes code that sends orders, so the version that will trade real money must have worked on testnet first.

## Removing

Stop the agent. If you stored a Lighter key, run `fuze keys testnet --delete` (and `mainnet`) first, and replace the key
on Lighter. Then `uv tool uninstall fuze-agent`, `pipx uninstall fuze-agent`, or delete `~/.fuze-venv`, and, if you no
longer want your settings and logs, `~/.fuze`.

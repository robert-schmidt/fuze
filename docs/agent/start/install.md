# Install

This page installs the agent and its MCP server on macOS, Linux or Windows, one step at a time. It takes about five
minutes. You do not need Python, an exchange account or money: the agent starts on a simulated account.

Prefer to let your AI coding tool do it? Paste this sentence into it, and skip the rest of this page:

```text
Install the FUZE agent from https://github.com/robert-schmidt/fuze and set it up in simulation. Follow the AGENTS.md in that repository.
```

The repository's `AGENTS.md` tells the tool how, and which steps it must leave to you. It works on Windows only when
the tool itself runs inside WSL (see [Windows](#windows)).

## What gets installed

| | What it is | Why |
|---|---|---|
| **uv** | A free, open-source installer for programs written in Python, made by [Astral](https://docs.astral.sh/uv/) | It fetches the right Python by itself, keeps FUZE in a folder of its own, away from the rest of your system, and gives you the command `fuze` |
| **git** | The standard program for downloading code | uv uses it to fetch FUZE from its repository on GitHub |
| **FUZE** | The agent and its MCP server: the command `fuze` | |

Install FUZE only from `github.com/robert-schmidt/fuze`, with that address in the command, as below.

## macOS and Linux

1. **Open a terminal.** On a Mac: press Command + Space, type `Terminal`, press Return. A window opens where you type
   commands.
2. **Install uv.** Paste this line and press Return:

   ```sh
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```

   Then close the terminal window and open a new one, so that it finds `uv`. (With Homebrew, `brew install uv` does
   the same.)
3. **Install FUZE.** Paste this line and press Return:

   ```sh
   uv tool install "fuze-agent[mcp] @ git+https://github.com/robert-schmidt/fuze"
   ```

4. **Check it.**

   ```sh
   fuze --version
   ```

   It prints the version, for example `0.5.0`. If it says `command not found`, run `uv tool update-shell`, open a new
   terminal window and try again.

**If step 2 or 3 says curl or git is missing:**

- On a Mac, a window offers to install the "command line developer tools": they contain git. Click Install, wait
  until it has finished, and run the line again. (`xcode-select --install` opens that window yourself.)
- On Ubuntu or Debian, run `sudo apt update && sudo apt install -y curl git` first. On Fedora:
  `sudo dnf install -y curl git`.

## Windows

FUZE runs on Windows inside WSL, Microsoft's own Linux for Windows 10 and 11. It does not run in PowerShell or the
Command Prompt directly.

1. **Install WSL.** Open the Start menu, type `PowerShell`, right-click it and choose "Run as administrator". Paste
   this line and press Enter:

   ```powershell
   wsl --install
   ```

   Restart the computer when it asks.
2. **Open Ubuntu.** After the restart, open "Ubuntu" from the Start menu. The first time, it asks you to choose a
   username and a password for Linux. Nothing shows while you type the password; that is normal.
3. **In the Ubuntu window**, run `sudo apt update && sudo apt install -y curl git`, then follow the
   [steps above](#macos-and-linux) from step 2.

From then on, every `fuze` command in these docs is typed in the Ubuntu window. Your files stay inside Ubuntu, in
`~/.fuze`. To connect an AI coding tool on Windows, see
[Using it from an AI coding tool](../ai-tools/README.md#on-windows).

## Next

[First run in simulation](first-run.md): set your sizing, start the agent, read its status. Then
[connect your AI coding tool](../ai-tools/README.md).

## Other ways to install

**With pipx**, if you already use it (it needs Python 3.10 or newer and git):

```sh
pipx install "fuze-agent[mcp] @ git+https://github.com/robert-schmidt/fuze"
```

If your shell does not find `fuze` afterwards, run `pipx ensurepath` and open a new terminal.

**Pinned by hash**: to pin every dependency by its hash, follow the repository's `SECURITY.md`.

The Claude Code plugin and the short MCP settings start the command `fuze`, so the install above (uv or pipx) is the
one they expect.

### A clone you read first

This way needs Python 3.10 or newer (`python3 --version`) and git.

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

Read the release notes before you update. After an update, mainnet asks for a new testnet rehearsal: the version that
will trade real money must have worked on testnet first.

## Removing

Stop the agent. If you stored a Lighter key, run `fuze keys testnet --delete` (and `mainnet`) first, and replace the key
on Lighter. Then `uv tool uninstall fuze-agent`, `pipx uninstall fuze-agent`, or delete `~/.fuze-venv`, and, if you no
longer want your settings and logs, `~/.fuze`.

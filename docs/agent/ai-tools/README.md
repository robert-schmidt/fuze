# Using it from an AI coding tool

This section shows how to connect the agent's MCP server to your AI coding tool, what the tool can then do, and what it
cannot. It covers Claude Code, Codex, GitHub Copilot, Cursor, OpenCode, Gemini CLI, Antigravity, Devin Desktop
(formerly Windsurf), Cline, Claude Desktop, Zed, JetBrains and Kiro.

## Connect your tool

Install the agent first ([Install](../start/install.md)) and run `fuze init` once
([First run](../start/first-run.md)). Then do the one thing in your tool's row, in a terminal:

| Your tool | What to do |
|---|---|
| Claude Code | `claude mcp add fuze --scope user -- fuze mcp` |
| Codex: the CLI, the IDE extension and the ChatGPT desktop app share one setting | `codex mcp add fuze -- fuze mcp` |
| GitHub Copilot CLI | `copilot mcp add fuze -- fuze mcp` |
| GitHub Copilot in VS Code | Run `fuze mcp-config --tool copilot` and paste what it prints into `~/.copilot/mcp-config.json` |
| Cursor | Run `fuze mcp-config --tool cursor` and paste what it prints into `~/.cursor/mcp.json` |
| OpenCode | `opencode mcp add --global fuze -- fuze mcp` |
| Gemini CLI | `gemini mcp add -s user fuze fuze mcp` |
| Antigravity | Run `fuze mcp-config --tool antigravity` and paste what it prints into `~/.gemini/config/mcp_config.json` |
| Devin Desktop (formerly Windsurf) | `devin mcp add -s user fuze -- fuze mcp`, or run `fuze mcp-config --tool devin` and paste what it prints into `~/.config/devin/mcp_config.json` |
| Cline | Run `fuze mcp-config --tool cline`; in Cline open the MCP Servers panel, Configure, Configure MCP Servers, and paste |
| Claude Desktop | Run `fuze mcp-config --tool claude-desktop`; in the app open Settings, Developer, Edit Config, paste, then quit the app and open it again |
| Zed | Run `fuze mcp-config --tool zed` and paste what it prints into Zed's settings file |
| JetBrains AI Assistant, Junie | Run `fuze mcp-config --tool jetbrains` and paste what it prints under Settings, Tools, AI Assistant, Model Context Protocol (MCP) |
| Kiro | Run `fuze mcp-config --tool kiro` and paste what it prints into `~/.kiro/settings/mcp.json` |

Restart the tool, then ask it: "What is the FUZE agent doing?" It should answer with your mode and balance.

Two things to know:

- **Why some rows paste and others are one line.** A tool you start in a terminal finds `fuze` the way your terminal
  does. An app you start from the Dock or a menu does not, so its settings need the full path of `fuze`:
  `fuze mcp-config` prints the settings with that path filled in. It works for the one-line tools too
  (`fuze mcp-config --tool claude-code`), and it is what to use when a one-line form fails.
- **A settings file that already has content.** Add the `"fuze"` entry next to the entries that are there; do not
  replace the file. If the file does not exist, create it with exactly what was printed.

Each tool has a page with the details: see [Per tool](#per-tool).

## On Windows

The agent lives inside WSL (see [Install](../start/install.md#windows)), so the AI tool has to reach into WSL to start
it.

| Your tool | On Windows |
|---|---|
| Claude Code, Codex CLI, GitHub Copilot CLI, OpenCode, Gemini CLI | Install the tool inside Ubuntu, the same way as on Linux, and start it there. Then the rows above work as written |
| VS Code | Install Microsoft's "WSL" extension, then type `code .` in the Ubuntu window. VS Code opens connected to Ubuntu, and `~/.copilot/mcp-config.json` is the one inside Ubuntu |
| An app that runs on the Windows side (Cursor, Claude Desktop and others) | Have it start the agent through Microsoft's `wsl` command: in the JSON, the command is `wsl` and the arguments are the full Linux path of `fuze` and `mcp`, as below |

```json
{
  "mcpServers": {
    "fuze": {
      "command": "wsl",
      "args": ["/home/YOUR-LINUX-USERNAME/.local/bin/fuze", "mcp"]
    }
  }
}
```

`command -v fuze`, typed in the Ubuntu window, prints that path. The `wsl` form relies on Windows itself; the makers of
these apps do not describe it in their own documentation.

## What the MCP server is

MCP (Model Context Protocol) is a standard way for an AI tool to call a local program. `fuze mcp` starts a small server
that your AI tool runs on your machine. Through it the tool can read the agent's status and make it safer. It needs the
`[mcp]` extra (see [Install](../start/install.md)).

## What it can and cannot do

| Your AI tool can | Your AI tool cannot |
|---|---|
| Read status, the latest signal, recent trades, a setup check and short built-in docs | Place an order |
| Give you the address of the [local page](../local-page.md): say "open the FUZE page" | Change anything through that page: it only reads |
| Pause the agent | Resume it |
| Flatten (close everything and stay out) | Unflatten |
| Lower your share, fixed amount, cap per position, exposure cap and daily loss stop; add a cap per position | Raise any limit, remove a cap, or switch between a share and a fixed amount |
| Tell you which command to type | Change the mode, enter or read a key, change the signal server, or touch files outside your FUZE folder |

A tricked AI tool can at worst make you safer through the MCP server. It cannot be tricked into raising risk through it.
The repository's `AGENTS.md` also tells coding agents not to do any of the right-hand column by other routes (editing
your files or running commands for you); see [Security model](../security.md) for what that does and does not guarantee.

FUZE's MCP server never sees your Lighter key. An AI tool that only needs to read a Lighter account gets a read-only
token from Lighter, which "won't allow placing trades nor request withdrawals", never the trading key
(https://docs.lighter.xyz/developers/integration-guides/api-keys.md).

## The setup that works

**With `fuze` on your PATH** (installed with `uv tool install` or `pipx install`, see [Install](../start/install.md))
and the default folder `~/.fuze`, the settings are just the command `fuze` with the argument `mcp`:

```json
{
  "mcpServers": {
    "fuze": {
      "type": "stdio",
      "command": "fuze",
      "args": ["mcp"]
    }
  }
}
```

The Claude Code plugin, the Add to Cursor link, the one-line `claude mcp add` and `codex mcp add` forms and the snippets
in the repository's `integrations/` folder all start it this way.

**Otherwise, `fuze mcp-config` prints the settings for you.** AI tools start MCP servers with a filtered environment
and not always with your shell's PATH. When you installed in a virtual environment, use another folder (`FUZE_HOME`),
or your tool cannot find `fuze`, the settings need two things filled in:

1. **The full path to `fuze`**, the one `command -v fuze` prints (with a clone: `~/.fuze-venv/bin/fuze`, written out).
2. **`FUZE_HOME`**, the folder your agent uses, written out in full, set in the server's environment.

Run `fuze mcp-config` the way you run the agent (the same `fuze`, the same `FUZE_HOME`):

```sh
fuze mcp-config                  # every tool
fuze mcp-config --tool codex     # one tool; `fuze mcp-config --help` lists the names
```

It prints the JSON or TOML for each tool's settings file and the one-line `claude mcp add ...`, `codex mcp add ...`,
`code --add-mcp ...` and `opencode mcp add ...` commands, with the full path of the `fuze` you ran and your FUZE folder
filled in. It warns when that folder has no
agent set up.

If the server looks in a folder with no agent, `pause`, `flatten` and `lower_limits` answer an error that names the
folder, and nothing is written; `status` says the same.

> **Warning:** after connecting, ask your AI tool for the agent's status and check that it shows your balance and mode.
> If it says no agent is set up in a folder, or "No status yet" while `fuze run` is running, the settings point at the
> wrong folder: run `fuze mcp-config` and replace them with what it prints.

## Per tool

| Tool | Page |
|---|---|
| Claude Code (and its plugin) | [Claude Code](claude-code.md) |
| Codex: CLI, IDE extension, ChatGPT desktop app | [Codex](codex.md) |
| GitHub Copilot: in VS Code and the CLI | [GitHub Copilot](copilot.md) |
| Cursor | [Cursor](cursor.md) |
| OpenCode, Gemini CLI, Antigravity, Devin Desktop (formerly Windsurf), Cline, Claude Desktop, Zed, JetBrains, Kiro | [More tools](more-tools.md) |

Then: [What you can say](what-to-say.md) and the [MCP tools](../mcp-tools.md) reference.

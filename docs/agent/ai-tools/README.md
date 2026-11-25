# Using it from an AI coding tool

This section shows how to connect the agent's MCP server to Claude Code, Codex, GitHub Copilot in VS Code or Cursor, what
your AI tool can then do, and what it cannot.

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
fuze mcp-config --tool codex     # one: claude-code, codex, copilot, vscode or cursor
```

It prints the JSON or TOML for each tool's settings file and the one-line `claude mcp add ...` and `codex mcp add ...`
commands, with the full path of the `fuze` you ran and your FUZE folder filled in. It warns when that folder has no
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
| Codex CLI | [Codex](codex.md) |
| GitHub Copilot in VS Code | [GitHub Copilot in VS Code](copilot.md) |
| Cursor | [Cursor](cursor.md) |

Then: [What you can say](what-to-say.md) and the [MCP tools](../mcp-tools.md) reference.

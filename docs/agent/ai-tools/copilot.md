# GitHub Copilot

This page connects the FUZE MCP server to GitHub Copilot: its agent mode in VS Code, and the Copilot CLI in a terminal.
Both read the same file, `~/.copilot/mcp-config.json`.

## Copilot CLI: one line

With `fuze` on your PATH (installed with `uv tool install` or `pipx install`) and the default folder `~/.fuze`:

```sh
copilot mcp add fuze -- fuze mcp
```

Check it with `copilot mcp list`, or `/mcp` inside the CLI.

## Copilot in VS Code

Run this in a terminal:

```sh
fuze mcp-config --tool copilot
```

Paste what it prints into `~/.copilot/mcp-config.json` (create the file if it is not there). It looks like this, with
the full path of your `fuze` and your FUZE folder filled in:

```json
{
  "mcpServers": {
    "fuze": {
      "type": "stdio",
      "command": "/Users/you/.local/bin/fuze",
      "args": ["mcp"],
      "env": { "FUZE_HOME": "/Users/you/.fuze" },
      "tools": ["*"]
    }
  }
}
```

For one workspace only, the same JSON goes into a file named `.mcp.json` at the workspace root.

## The editor's own format

VS Code also keeps MCP servers in its own format, with the key `servers` in place of `mcpServers`.
`fuze mcp-config --tool vscode` prints both forms of it: a `code --add-mcp '...'` line to run once, and the JSON for
`.vscode/mcp.json` in a workspace:

```json
{
  "servers": {
    "fuze": {
      "type": "stdio",
      "command": "fuze",
      "args": ["mcp"]
    }
  }
}
```

Copilot CLI does not read `.vscode/mcp.json`.

## Check it

In VS Code, the command "MCP: List Servers" shows the server. Open Copilot Chat in agent mode and ask "What is the FUZE
agent doing?". Copilot should call the `status` tool. See [What you can say](what-to-say.md).

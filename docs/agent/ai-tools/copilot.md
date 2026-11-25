# GitHub Copilot in VS Code

This page connects the FUZE MCP server to GitHub Copilot's agent mode in VS Code.

## In `.vscode/mcp.json`

In the workspace you open in VS Code, with `fuze` on your PATH (installed with `uv tool install` or `pipx install`) and
the default folder `~/.fuze`:

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

For a virtualenv install or another folder, run `fuze mcp-config --tool vscode` and paste what it prints instead: it
fills in the full path of your `fuze` and your `FUZE_HOME`.

GitHub Copilot CLI (the terminal tool, not VS Code) reads `~/.copilot/mcp-config.json`, with the key `mcpServers` in
place of `servers`: `fuze mcp-config --tool copilot` prints that form.

## Check it

Start the server from the file (VS Code shows a Start link above it), open Copilot Chat in agent mode, and ask "What is
the FUZE agent doing?". Copilot should call the `status` tool. See [What you can say](what-to-say.md).

# GitHub Copilot in VS Code

This page connects the FUZE MCP server to GitHub Copilot's agent mode in VS Code. Replace `/Users/you` with your own home
folder (see [the setup that works](README.md#the-setup-that-works)).

The quickest way: run `fuze mcp-config --tool vscode` and paste what it prints; it fills in the full path of your
`fuze` and your FUZE folder.

## In `.vscode/mcp.json`

In the workspace you open in VS Code:

```json
{
  "servers": {
    "fuze": {
      "type": "stdio",
      "command": "/Users/you/.fuze-venv/bin/fuze",
      "args": ["mcp"],
      "env": {"FUZE_HOME": "/Users/you/.fuze"}
    }
  }
}
```

Some setups read a `.mcp.json` at the workspace root instead, with the key `mcpServers` in place of `servers` and the
same contents otherwise.

## Check it

Start the server from the file (VS Code shows a Start link above it), open Copilot Chat in agent mode, and ask "What is
the FUZE agent doing?". Copilot should call the `status` tool. See [What you can say](what-to-say.md).

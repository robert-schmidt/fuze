# Cursor

This page connects the FUZE MCP server to Cursor. Replace `/Users/you` with your own home folder (see
[the setup that works](README.md#the-setup-that-works)).

The quickest way: run `fuze mcp-config --tool cursor` and paste what it prints; it fills in the full path of your
`fuze` and your FUZE folder.

## In `.cursor/mcp.json` or `~/.cursor/mcp.json`

Use the project file for one project, or the one in your home folder for every project:

```json
{
  "mcpServers": {
    "fuze": {
      "type": "stdio",
      "command": "/Users/you/.fuze-venv/bin/fuze",
      "args": ["mcp"],
      "env": {"FUZE_HOME": "/Users/you/.fuze"}
    }
  }
}
```

## Check it

Cursor's settings list the server and its tools. In the agent chat, ask "What is the FUZE agent doing?"; Cursor should
call the `status` tool. See [What you can say](what-to-say.md).

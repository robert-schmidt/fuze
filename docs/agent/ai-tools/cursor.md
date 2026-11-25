# Cursor

This page connects the FUZE MCP server to Cursor.

## Add to Cursor

With `fuze` on your PATH (installed with `uv tool install` or `pipx install`) and the default folder `~/.fuze`, open
this link and confirm in Cursor:

[Add FUZE to Cursor](cursor://anysphere.cursor-deeplink/mcp/install?name=fuze&config=eyJjb21tYW5kIjoiZnV6ZSIsImFyZ3MiOlsibWNwIl19)

```text
cursor://anysphere.cursor-deeplink/mcp/install?name=fuze&config=eyJjb21tYW5kIjoiZnV6ZSIsImFyZ3MiOlsibWNwIl19
```

It adds the server `fuze` with the settings `{"command":"fuze","args":["mcp"]}`.

## In `.cursor/mcp.json` or `~/.cursor/mcp.json`

Use the project file for one project, or the one in your home folder for every project:

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

For a virtualenv install or another folder, run `fuze mcp-config --tool cursor` and paste what it prints instead: it
fills in the full path of your `fuze` and your `FUZE_HOME`.

## Check it

Cursor's settings list the server and its tools. In the agent chat, ask "What is the FUZE agent doing?"; Cursor should
call the `status` tool. See [What you can say](what-to-say.md).

# Claude Code

This page connects the FUZE MCP server to Claude Code, either per project or as a plugin. Replace `/Users/you` with your
own home folder (see [the setup that works](README.md#the-setup-that-works)).

The quickest way: run `fuze mcp-config --tool claude-code` and paste what it prints; it fills in the full path of your
`fuze` and your FUZE folder.

## Option 1: a project's `.mcp.json`

Create `.mcp.json` in the project folder you open Claude Code in:

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

Or let Claude Code write it:

```sh
claude mcp add fuze --scope project -e FUZE_HOME=/Users/you/.fuze -- /Users/you/.fuze-venv/bin/fuze mcp
```

Claude Code asks you to approve a project's MCP server the first time. Check it with `claude mcp list`, or `/mcp` inside
Claude Code.

## Option 2: the plugin

The repository is also a Claude Code plugin marketplace with one plugin, `fuze`:

```sh
claude plugin marketplace add /path/to/your/fuze/checkout
claude plugin install fuze@fuze
```

The plugin starts the command `fuze mcp` with no `FUZE_HOME`, so it works only when `fuze` is on the PATH Claude Code
sees and your agent uses the default folder `~/.fuze`. Otherwise use option 1 (`fuze mcp-config --tool claude-code`
prints it with `--scope user`, for every project).

## Check it

Ask: "What is the FUZE agent doing?" Claude Code should call the `status` tool and report your mode, balance and the
agent's last reason. See [What you can say](what-to-say.md).

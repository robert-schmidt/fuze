# More tools

This page connects the FUZE MCP server to OpenCode, Gemini CLI, Antigravity, Devin Desktop (formerly Windsurf), Cline,
Claude Desktop, Zed, JetBrains and Kiro. Install the agent and run `fuze init` first
([Getting started](../start/README.md)).

Most of these tools read the same JSON. `fuze mcp-config --tool NAME` prints it with the full path of your `fuze` and
your FUZE folder filled in, for example:

```json
{
  "mcpServers": {
    "fuze": {
      "type": "stdio",
      "command": "/Users/you/.local/bin/fuze",
      "args": ["mcp"],
      "env": { "FUZE_HOME": "/Users/you/.fuze" }
    }
  }
}
```

If the settings file already has content, add the `"fuze"` entry inside the `mcpServers` that is there; do not replace
the file.

## OpenCode

```sh
opencode mcp add --global fuze -- fuze mcp
```

Without `--global` it is added for the project you are in only. For another install or folder,
`fuze mcp-config --tool opencode` prints the same line with the full path and your `FUZE_HOME`. Check it with
`opencode mcp list`: it shows `fuze connected`.

## Gemini CLI

```sh
gemini mcp add -s user fuze fuze mcp
```

`-s user` makes it available in every project; without it, only in the project you are in. Or run
`fuze mcp-config --tool gemini` and add what it prints to `~/.gemini/settings.json`. Check it with `/mcp` inside
Gemini CLI, or `gemini mcp list`.

## Antigravity

Google's Antigravity, the IDE and its CLI, reads `~/.gemini/config/mcp_config.json` (for one workspace:
`.agents/mcp_config.json`). Run `fuze mcp-config --tool antigravity` and paste what it prints into that file. Check it
with `/mcp`.

## Devin Desktop (formerly Windsurf)

```sh
devin mcp add -s user fuze -- fuze mcp
```

Or run `fuze mcp-config --tool devin` and paste what it prints into `~/.config/devin/mcp_config.json` (for one
project: `.devin/mcp_config.json`). Check it under Customize, MCPs in the app, or with `devin mcp list`.

## Cline

1. Run `fuze mcp-config --tool cline`.
2. In Cline, open the MCP Servers panel (the icon in its top toolbar), then Configure, then Configure MCP Servers. It
   opens the file `cline_mcp_settings.json`.
3. Paste what was printed and save.

## Claude Desktop

1. Run `fuze mcp-config --tool claude-desktop`.
2. In the app, open Settings, Developer, Edit Config. It opens the file `claude_desktop_config.json` (on macOS in
   `~/Library/Application Support/Claude`, on Linux in `~/.config/Claude`).
3. Paste what was printed and save. Quit the app completely and open it again.

## Zed

Zed names the setting `context_servers`. Run `fuze mcp-config --tool zed` and add what it prints to Zed's settings
file (command `zed: open settings file`), or use Settings, AI, MCP Servers, Add Server, Add Local Server. A green dot
next to the server means it is running.

## JetBrains AI Assistant and Junie

Run `fuze mcp-config --tool jetbrains`.

- AI Assistant: open Settings, Tools, AI Assistant, Model Context Protocol (MCP), add a server and paste the JSON. The
  Status column shows whether it is connected.
- Junie: paste the JSON into `~/.junie/mcp/mcp.json` (for one project: `.junie/mcp/mcp.json`).

## Kiro

Run `fuze mcp-config --tool kiro` and paste what it prints into `~/.kiro/settings/mcp.json` (for one project:
`.kiro/settings/mcp.json`).

## Any other tool that speaks MCP

The server is a local program that talks over standard input and output: the command `fuze` with the one argument
`mcp`. Any tool with a place for a "local" or "stdio" MCP server takes that. Use the full path of `fuze`
(`command -v fuze` prints it) when the tool is an app you start from the Dock or a menu.

## Check it

Ask: "What is the FUZE agent doing?" The tool should call the `status` tool and report your mode and balance. See
[What you can say](what-to-say.md).

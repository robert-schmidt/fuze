# Claude Code

This page connects the FUZE MCP server to Claude Code, as a plugin or as an MCP server you add yourself.

## Option 1: the plugin

The repository is also a Claude Code plugin marketplace with one plugin, `fuze`. In one step:

```sh
claude plugin install fuze --marketplace robert-schmidt/fuze
```

Or in two steps, which works on every version of Claude Code:

```sh
claude plugin marketplace add robert-schmidt/fuze
claude plugin install fuze@fuze
```

Install FUZE itself first ([Install](../start/install.md)): the plugin only tells Claude Code how to start it. Without
it, Claude Code lists the server as failed with "Executable not found in $PATH".

The plugin starts the command `fuze mcp` with no `FUZE_HOME`: it is made for `fuze` installed with `uv tool install` or
`pipx install` (on the PATH Claude Code sees) and the default folder `~/.fuze`. For a virtualenv install or another
folder, use option 2.

## Option 2: add the server yourself

With `fuze` on your PATH and the default folder:

```sh
claude mcp add fuze --scope user -- fuze mcp
```

For any other install, run `fuze mcp-config --tool claude-code` and paste what it prints: the same `claude mcp add`
command with the full path of your `fuze` and your `FUZE_HOME` filled in, and the JSON for a project's `.mcp.json`.
`--scope user` makes the server available in every project; `--scope project` writes it to the `.mcp.json` of the
project you are in, which Claude Code asks you to approve the first time.

Check it with `claude mcp list`, or `/mcp` inside Claude Code.

## Check it

Ask: "What is the FUZE agent doing?" Claude Code should call the `status` tool and report your mode, balance and the
agent's last reason. See [What you can say](what-to-say.md).

# Codex

This page connects the FUZE MCP server to Codex. The Codex CLI, the Codex IDE extension and the ChatGPT desktop app
share one configuration, `~/.codex/config.toml`, so one step covers all three.

## One line

With `fuze` on your PATH (installed with `uv tool install` or `pipx install`) and the default folder `~/.fuze`:

```sh
codex mcp add fuze -- fuze mcp
```

## In `~/.codex/config.toml`

The same as a config file (or in a trusted project's `.codex/config.toml`):

```toml
[mcp_servers.fuze]
command = "fuze"
args = ["mcp"]
```

For a virtualenv install or another folder, run `fuze mcp-config --tool codex` and paste what it prints instead: the
`codex mcp add` command and the TOML with the full path of your `fuze` and your `FUZE_HOME` filled in.

## Check it

`codex mcp list` shows the server. In a session, ask "What is the FUZE agent doing?"; Codex should call the `status`
tool. See [What you can say](what-to-say.md).

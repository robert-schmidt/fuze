# Codex

This page connects the FUZE MCP server to the Codex CLI. Replace `/Users/you` with your own home folder (see
[the setup that works](README.md#the-setup-that-works)).

The quickest way: run `fuze mcp-config --tool codex` and paste what it prints; it fills in the full path of your
`fuze` and your FUZE folder.

## In `~/.codex/config.toml`

Add (or put it in a trusted project's `.codex/config.toml`):

```toml
[mcp_servers.fuze]
command = "/Users/you/.fuze-venv/bin/fuze"
args = ["mcp"]
env = { FUZE_HOME = "/Users/you/.fuze" }
```

Or let Codex write it:

```sh
codex mcp add fuze --env FUZE_HOME=/Users/you/.fuze -- /Users/you/.fuze-venv/bin/fuze mcp
```

## Check it

`codex mcp list` shows the server. In a session, ask "What is the FUZE agent doing?"; Codex should call the `status`
tool. See [What you can say](what-to-say.md).

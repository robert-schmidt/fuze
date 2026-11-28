import asyncio
import json
import sys

import pytest
from mcp import Client, StdioServerParameters
from mcp.server.mcpserver.exceptions import ToolError

from fuze import config

TOOLS = {"status", "signal", "trades", "setup_check", "docs", "pause", "flatten", "lower_limits", "ui"}


def test_mcp_server_over_stdio(fuze_home):
    config.save(dict(config.DEFAULTS))
    params = StdioServerParameters(command=sys.executable, args=["-m", "fuze", "mcp"],
                                   env={"FUZE_HOME": str(fuze_home)})

    async def go():
        async with Client(params) as c:
            tools = {t.name: t for t in (await c.list_tools()).tools}
            assert set(tools) == TOOLS
            for name in ("pause", "flatten", "lower_limits"):
                assert "only reduce risk" in tools[name].description
            st = await c.call_tool("status", {})
            assert not st.is_error and "fuze run" in st.content[0].text
            assert not (await c.call_tool("pause", {})).is_error
            raised = await c.call_tool("lower_limits", {"max_x": 5.0})
            assert raised.is_error and "can only lower" in raised.content[0].text
            assert (await c.call_tool("lower_limits", {"percent": 0.0})).is_error  # below the allowed range
            assert (await c.call_tool("trades", {"n": 0})).is_error
            assert (await c.call_tool("docs", {"topic": "../../etc/passwd"})).is_error
            ok = await c.call_tool("lower_limits", {"max_x": 2.0, "percent": 5.0})
            assert not ok.is_error

    asyncio.run(go())
    assert (fuze_home / "PAUSE").exists() and not (fuze_home / "FLATTEN").exists()
    cfg = config.load()
    assert cfg["max_x"] == 2.0 and cfg["percent"] == 5.0 and cfg["daily_loss_frac"] == 0.1


def test_no_tool_can_undo_or_raise():
    from fuze.mcp_server import build

    names = {t.name for t in asyncio.run(build().list_tools())}
    assert names == TOOLS
    assert not names & {"resume", "unflatten", "raise_limits", "set_server", "set_mode", "run"}


def call(name, **args):
    from fuze.mcp_server import build

    res = asyncio.run(build().call_tool(name, args))
    return json.loads(res.content[0].text)


def test_status_shows_sizing_in_plain_words(fuze_home):
    config.save(dict(config.DEFAULTS))
    text = " ".join(call("status")["sizing"])
    assert "10% of your balance" in text and "$180 of Bitcoin" in text


def test_lower_limits_percent_mode(fuze_home):
    config.save(dict(config.DEFAULTS))
    with pytest.raises(ToolError, match="can only lower"):
        call("lower_limits", percent=20.0)
    with pytest.raises(ToolError, match="fixed_usd does not apply"):
        call("lower_limits", fixed_usd=50.0)  # the knob of the mode that is not active
    assert call("lower_limits", percent=5.0)["percent"] == 5.0
    assert call("lower_limits", max_position_usd=300.0)["max_position_usd"] == 300.0  # adding a cap is allowed
    with pytest.raises(ToolError, match="can only lower"):
        call("lower_limits", max_position_usd=400.0)
    assert call("lower_limits", max_position_usd=200.0)["max_position_usd"] == 200.0
    with pytest.raises(ToolError, match="can only lower"):
        call("lower_limits", daily_loss_frac=0.2)
    assert call("lower_limits", daily_loss_frac=0.05)["daily_loss_frac"] == 0.05
    with pytest.raises(ToolError, match="number"):
        call("lower_limits", max_position_usd=float("nan"))
    cfg = config.load()
    assert (cfg["percent"], cfg["fixed_usd"], cfg["max_position_usd"]) == (5.0, 100.0, 200.0)


def test_lower_limits_fixed_mode(fuze_home):
    config.save({**config.DEFAULTS, "size_mode": "fixed", "fixed_usd": 500.0})
    with pytest.raises(ToolError, match="percent does not apply"):
        call("lower_limits", percent=1.0)
    with pytest.raises(ToolError, match="can only lower"):
        call("lower_limits", fixed_usd=1000.0)
    assert call("lower_limits", fixed_usd=300.0)["fixed_usd"] == 300.0
    assert config.load()["size_mode"] == "fixed"


def test_no_tool_switches_the_mode_or_removes_a_cap():
    from fuze.mcp_server import build

    tools = {t.name: t for t in asyncio.run(build().list_tools())}
    props = set(tools["lower_limits"].input_schema["properties"])
    assert props == {"percent", "fixed_usd", "max_position_usd", "max_x", "daily_loss_frac", "max_balance_usd"}
    assert not any("size_mode" in t.input_schema.get("properties", {}) for t in tools.values())


# --- unknown arguments, and a server pointed at a folder with no agent ----------------------------------------------

@pytest.mark.parametrize("tool,args", [("lower_limits", {"max_x": 0.5, "size_mode": "percent"}),
                                       ("status", {"verbose": True}), ("pause", {"now": 1})])
def test_unknown_arguments_are_refused_and_change_nothing(fuze_home, tool, args):
    config.save(dict(config.DEFAULTS))
    with pytest.raises(ToolError, match="does not take") as e:
        call(tool, **args)
    assert "Nothing was changed" in str(e.value)
    assert config.load()["max_x"] == 3.0 and not (fuze_home / "PAUSE").exists()


@pytest.mark.parametrize("name", ["mode", "api_key", "key", "private_key", "secret", "server", "seed_phrase"])
def test_mode_or_key_arguments_get_the_terminal_answer_and_are_never_echoed(fuze_home, name, caplog):
    config.save(dict(config.DEFAULTS))
    value = "5e" * 40
    with pytest.raises(ToolError) as e:
        call("lower_limits", max_x=0.4, **{name: value})
    text = str(e.value)
    assert "in a terminal" in text and "never be pasted into a chat" in text and value not in text
    assert value not in caplog.text and config.load()["max_x"] == 3.0
    assert not any(value in p.read_text(errors="ignore") for p in fuze_home.rglob("*") if p.is_file())


def test_switches_without_an_agent_in_the_folder_are_errors(fuze_home):
    """An MCP client that passes no FUZE_HOME looks in another folder: success there would reach nobody."""
    for tool, args in (("pause", {}), ("flatten", {}), ("lower_limits", {"max_x": 1.0})):
        with pytest.raises(ToolError, match="No FUZE agent is set up in") as e:
            call(tool, **args)
        assert str(fuze_home) in str(e.value) and "fuze mcp-config" in str(e.value)
    assert not fuze_home.exists()  # nothing written, not even the folder
    st = call("status")
    assert st["agent_found"] is False and "fuze mcp-config" in st["problem"]
    from fuze.mcp_server import build
    res = asyncio.run(build().call_tool("setup_check", {}))
    first = json.loads(res.content[0].text)
    first = first[0] if isinstance(first, list) else first
    assert first["ok"] is False and "No FUZE agent is set up" in first["detail"]


def test_status_shows_what_is_asked_and_what_is_held_in_dollars(fuze_home):
    config.save({**config.DEFAULTS, "size_mode": "fixed", "fixed_usd": 10.0})
    config.write_json(fuze_home / "status.json", {
        "t": 0, "account": {"balance": 1000.0, "positions": {}, "brackets": []}, "min_change_usd": 20.0,
        "wanted": {"BTC": -10 * 1.7 / 58000, "ETH": -10 * 0.33 / 1600},
        "signal": {"rev": 5, "state": "live", "source": "paper", "why": "", "scalp": None,
                   "targets": {"BTC": {"x": -1.7, "px": 58000.0}, "ETH": {"x": -0.33, "px": 1600.0}}}})
    st = call("status")
    btc = next(r for r in st["positions_usd"] if r["coin"] == "BTC")
    assert btc["asked_usd"] == -17.0 and btc["held_usd"] == 0.0 and btc["under_min_change"]
    words = " ".join(st["positions_in_words"])
    assert "asks for short $17, you hold none" in words and "under $20" in words and "stays unfollowed" in words


def test_a_refused_raise_names_the_command_to_type(fuze_home):
    """A newcomer's AI tool said "run fuze --help" because the refusal gave no flag (new-user test, 2026-11-25)."""
    config.save(dict(config.DEFAULTS))
    for asked, command in (({"max_x": 5.0}, "`fuze limits --max-x 5`"), ({"percent": 20.0}, "`fuze limits --percent 20`"),
                           ({"daily_loss_frac": 0.2}, "`fuze limits --daily-loss 20`")):
        with pytest.raises(ToolError) as e:
            call("lower_limits", **asked)
        assert command in str(e.value) and "RAISE" in str(e.value)
    from fuze.mcp_server import DOCS
    assert "ui tool" in DOCS["status"] and "Testnet trades" not in DOCS["status"]


def test_setup_check_does_not_call_a_missing_config_valid(fuze_home):
    from fuze import checks
    rows = {r["check"]: r for r in checks.setup_report()}
    assert not rows["config.json is valid"]["ok"] and "fuze init" in rows["config.json is valid"]["detail"]
    config.save(dict(config.DEFAULTS))
    assert {r["check"]: r for r in checks.setup_report()}["config.json is valid"]["ok"]

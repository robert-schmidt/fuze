import asyncio
import json
import sys

import pytest
from mcp import Client, StdioServerParameters
from mcp.server.mcpserver.exceptions import ToolError

from fuze import config

TOOLS = {"status", "signal", "trades", "setup_check", "docs", "pause", "flatten", "lower_limits"}


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
    assert props == {"percent", "fixed_usd", "max_position_usd", "max_x", "daily_loss_frac"}
    assert not any("size_mode" in t.input_schema.get("properties", {}) for t in tools.values())

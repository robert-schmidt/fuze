import asyncio
import sys

from mcp import Client, StdioServerParameters

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
            assert (await c.call_tool("lower_limits", {"scale": 0.0})).is_error  # below the allowed range
            assert (await c.call_tool("trades", {"n": 0})).is_error
            assert (await c.call_tool("docs", {"topic": "../../etc/passwd"})).is_error
            ok = await c.call_tool("lower_limits", {"max_x": 2.0, "scale": 0.05})
            assert not ok.is_error

    asyncio.run(go())
    assert (fuze_home / "PAUSE").exists() and not (fuze_home / "FLATTEN").exists()
    cfg = config.load()
    assert cfg["max_x"] == 2.0 and cfg["scale"] == 0.05 and cfg["daily_loss_frac"] == 0.1


def test_no_tool_can_undo_or_raise():
    from fuze.mcp_server import build

    names = {t.name for t in asyncio.run(build().list_tools())}
    assert names == TOOLS
    assert not names & {"resume", "unflatten", "raise_limits", "set_server", "set_mode", "run"}

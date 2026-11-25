import json

import pytest

from fuze.dry import DryExchange


@pytest.fixture
def ex(tmp_path):
    return DryExchange(tmp_path, 1000.0, clock=lambda: 1.0)


def test_market_fill_with_slippage(ex, tmp_path):
    ex.market("BTC", -0.01, 60000.0)
    a = ex.account()
    assert a["positions"] == {"BTC": -0.01}
    assert ex.s["pos"]["BTC"]["entry"] == pytest.approx(60000 * 0.9999)
    ex.mark({"BTC": 59000.0})
    assert ex.account()["balance"] == pytest.approx(1000 + 0.01 * (59994 - 59000))
    ex.market("BTC", 0.01, 59000.0)
    a = ex.account()
    assert a["positions"] == {} and a["balance"] == pytest.approx(1000 + 0.01 * (59994 - 59005.9))
    lines = [json.loads(x) for x in (tmp_path / "trades.jsonl").read_text().splitlines()]
    assert [x["units"] for x in lines] == [-0.01, 0.01]


def test_stop_loss(ex):
    ex.market("BTC", -0.01, 60000.0)
    ex.protect("BTC", -0.004, 59400.0, 60420.0, 7)
    ex.mark({"BTC": 60100.0})
    assert ex.account()["brackets"] == [7]
    ex.mark({"BTC": 60500.0})
    a = ex.account()
    assert a["positions"]["BTC"] == pytest.approx(-0.006) and a["brackets"] == []


def test_take_profit(ex, tmp_path):
    ex.market("BTC", -0.01, 60000.0)
    ex.protect("BTC", -0.004, 59400.0, 60420.0, 7)
    ex.mark({"BTC": 59300.0})
    assert ex.account()["positions"]["BTC"] == pytest.approx(-0.006)
    last = json.loads((tmp_path / "trades.jsonl").read_text().splitlines()[-1])
    assert last["kind"] == "take_profit" and last["px"] == 59400.0


def test_stop_checked_first(ex, tmp_path):
    ex.market("ETH", 1.0, 2000.0)
    ex.protect("ETH", 1.0, 1990.0, 2010.0, 9)  # degenerate: one price crosses both
    ex.mark({"ETH": 2000.0})
    last = json.loads((tmp_path / "trades.jsonl").read_text().splitlines()[-1])
    assert last["kind"] == "stop_loss"


def test_state_survives_restart(tmp_path):
    DryExchange(tmp_path, 1000.0).market("ETH", 0.1, 2000.0)
    assert DryExchange(tmp_path, 5.0).account()["positions"] == {"ETH": 0.1}

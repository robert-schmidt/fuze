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


def test_emergency_stop_closes_its_part_after_the_pair(ex, tmp_path):
    ex.market("BTC", -0.01, 60000.0)
    ex.protect("BTC", -0.004, 59400.0, 60420.0, 7)
    ex.guard("BTC", -0.006, 72000.0, 60000.0)
    assert ex.account()["guards"] == {"BTC": {"units": -0.006, "stop": 72000.0, "ref": 60000.0, "t": 1.0}}
    ex.mark({"BTC": 60500.0})  # the pair's stop loss: the scalp part goes, the emergency stop stays
    a = ex.account()
    assert a["positions"]["BTC"] == pytest.approx(-0.006) and a["brackets"] == [] and "BTC" in a["guards"]
    ex.mark({"BTC": 71999.0})
    assert "BTC" in ex.account()["guards"]
    ex.mark({"BTC": 72100.0})
    a = ex.account()
    assert a["positions"] == {} and a["guards"] == {}
    last = json.loads((tmp_path / "trades.jsonl").read_text().splitlines()[-1])
    assert last["kind"] == "emergency_stop" and last["units"] == pytest.approx(0.006)


def test_emergency_stop_of_a_long_and_cancelling_it(ex):
    ex.market("ETH", 1.0, 2000.0)
    ex.guard("ETH", 1.0, 1600.0, 2000.0)
    ex.cancel("ETH")  # the pair's cancel never touches it
    assert "ETH" in ex.account()["guards"]
    ex.mark({"ETH": 1590.0})
    assert ex.account()["positions"] == {}
    ex.market("ETH", 1.0, 2000.0)
    ex.guard("ETH", 1.0, 1600.0, 2000.0)
    ex.unguard("ETH")
    ex.mark({"ETH": 1500.0})
    assert ex.account()["positions"] == {"ETH": 1.0}


def test_an_account_file_from_before_the_emergency_stop_still_reads(tmp_path):
    (tmp_path / "dry.json").write_text(json.dumps({"cash": 900.0, "pos": {"BTC": {"units": -0.01, "entry": 60000.0}},
                                                   "marks": {"BTC": 60000.0}, "brackets": {}}))
    ex = DryExchange(tmp_path, 1000.0)
    ex.mark({"BTC": 61000.0})
    assert ex.account()["guards"] == {}
    ex.guard("BTC", -0.01, 73200.0, 61000.0)
    assert DryExchange(tmp_path, 1000.0).account()["guards"]["BTC"]["stop"] == 73200.0

import pytest

from fuze import config
from fuze.sizing import describe, example, raised

BASE = config.validate({})  # percent 10, fixed $100, no cap per position, max_x 3, daily loss 10%


def cfg(**kw):
    return config.validate({**BASE, **kw})


def test_worked_example():
    assert example(BASE, 1000.0) == ("With $1,000 and our position at 1.8 times our balance, yours would be $180 "
                                      "of Bitcoin. With $2,000 it would be $360.")
    assert "$900 of Bitcoin. With $2,000 it would be $900." in example(cfg(size_mode="fixed", fixed_usd=500), 1000)
    capped = example(cfg(percent=100, max_position_usd=1000), 1000)
    assert "$1,000 of Bitcoin ($1,800 before your caps)" in capped


def test_describe_in_plain_words():
    text = " ".join(describe(cfg(size_mode="fixed", fixed_usd=500, max_position_usd=300), 1000))
    assert "fixed $500" in text and "does not grow" in text and "$300" in text and "3 times" in text


@pytest.mark.parametrize("change,up", [
    ({"percent": 20}, ["percent"]),
    ({"percent": 5}, []),
    ({"fixed_usd": 200}, []),  # not in use: switching to it later is checked then (size_mode)
    ({"fixed_usd": 50}, []),
    ({"max_x": 4}, ["max_x"]),
    ({"max_x": 2}, []),
    ({"daily_loss_frac": 0.2}, ["daily_loss_frac"]),
    ({"daily_loss_frac": 0.05}, []),
    ({"max_position_usd": 500}, []),  # adding a cap per position lowers risk
    ({"stale_flat_min": 30}, []),
    ({"size_mode": "fixed"}, []),  # $100 fixed = 10% of $1,000: not larger
    ({"size_mode": "fixed", "fixed_usd": 50}, []),
    ({"size_mode": "fixed", "fixed_usd": 500}, ["size_mode"]),
    ({"risk_allowed": 61}, ["risk_allowed"]),  # parts with higher scores would be followed
    ({"risk_allowed": 20}, []),
    ({"coins": ["BTC", "ETH"]}, []),  # fewer coins
])
def test_what_raises_risk(change, up):
    assert raised(BASE, cfg(**change), 1000.0) == up


def test_the_amount_in_use_raises_in_fixed_mode():
    fixed = cfg(size_mode="fixed", fixed_usd=100)
    assert raised(fixed, cfg(size_mode="fixed", fixed_usd=200), 1000.0) == ["fixed_usd"]
    assert raised(fixed, cfg(size_mode="fixed", fixed_usd=100, percent=90), 1000.0) == []


def test_removing_or_raising_a_cap_raises_risk():
    cur = cfg(max_position_usd=500, stale_flat_min=30)
    assert raised(cur, cfg(max_position_usd=None, stale_flat_min=30), 1000) == ["max_position_usd"]
    assert raised(cur, cfg(max_position_usd=600, stale_flat_min=30), 1000) == ["max_position_usd"]
    assert raised(cur, cfg(max_position_usd=400, stale_flat_min=None), 1000) == ["stale_flat_min"]


def test_switching_mode_is_judged_at_the_current_balance():
    fixed = cfg(size_mode="fixed", fixed_usd=500)
    assert raised(fixed, cfg(fixed_usd=500), 1000.0) == []  # 10% of $1,000 = $100 < $500
    assert raised(fixed, cfg(fixed_usd=500), 10000.0) == ["size_mode"]  # 10% of $10,000 = $1,000 > $500


def test_adding_a_coin_raises_risk_and_removing_one_does_not():
    two = cfg(coins=["ETH", "BTC"])
    assert two["coins"] == ["BTC", "ETH"]
    assert raised(two, cfg(coins=["BTC", "ETH", "LIT"]), 1000.0) == ["coins"]
    assert raised(two, cfg(coins=["LIT"]), 1000.0) == ["coins"]  # a swap adds one
    assert raised(two, cfg(coins=["BTC"], risk_allowed=10), 1000.0) == []


def test_describe_says_the_risk_allowed_and_the_coins():
    text = " ".join(describe(cfg(risk_allowed=20, coins=["BTC", "HYPE"]), 1000))
    assert "Risk allowed: 20." in text and "20 or less" in text and "2% of the balance on a bad day" in text
    assert "nothing about how likely the part is to win" in text and "Coins: BTC, HYPE." in text


def test_lighters_highest_leverage_caps_a_coin():
    from fuze.sizing import fit
    f, notes = fit({"LIT": 8000.0, "HYPE": 1000.0, "BTC": 1000.0}, cfg(max_x=25), 1000.0)
    assert f["LIT"] == pytest.approx(5000 / 8000) and f["HYPE"] == 1.0 and f["BTC"] == 1.0
    assert notes == ["Cut LIT to 5 times your balance, the highest leverage Lighter allows on it."]
    f, _ = fit({"HYPE": 30000.0}, cfg(max_x=25, max_balance_usd=1000.0), 5000.0)  # on the counted balance
    assert f["HYPE"] == pytest.approx(20000 / 30000)

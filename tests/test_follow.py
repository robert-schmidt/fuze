import pytest

from conftest import payload
from fuze.follow import decide
from fuze.protocol import clean

CFG = {"size_mode": "percent", "percent": 10.0, "fixed_usd": 100.0, "max_position_usd": None, "max_x": 3.0,
       "daily_loss_frac": 0.1, "stale_flat_min": None}
DAY = 86400.0 * 20000  # a UTC midnight


def sig(**kw):
    p = clean(payload(ts=DAY + 1000.0, expires=DAY + 1060.0, **kw))
    assert p is not None
    return p


def run(s, now=DAY + 1010.0, received=DAY + 1005.0, bal=1000.0, pos=None, brackets=(), cfg=None, flags=None,
        memory=None):
    acct = {"balance": bal, "positions": pos or {}, "brackets": list(brackets)}
    return decide(s, received, now, acct, {**CFG, **(cfg or {})}, flags or {}, memory or {})


def test_first_signal_sets_targets_and_bracket():
    d = run(sig())
    assert d.act
    assert d.targets["BTC"] == pytest.approx(-1.8 * 0.1 * 1000 / 60000)
    assert d.targets["ETH"] == pytest.approx(-0.4 * 0.1 * 1000 / 2000)
    assert d.bracket == {"coin": "BTC", "units": pytest.approx(-0.002), "tp": 59400.0, "sl": 60420.0, "id": 7}
    assert "revision 1" in d.reason and d.memory["rev"] == 1


def test_same_rev_holds_and_price_drift_alone_does_nothing():
    d = run(sig())
    held = dict(d.targets)
    d2 = run(sig(seq=2), pos=held, brackets=[7], memory=d.memory)
    assert not d2.act
    drift = sig(seq=3, targets={"BTC": {"x": -1.9, "px": 63000.0}, "ETH": {"x": -0.41, "px": 1950.0}})
    assert not run(drift, pos=held, brackets=[7], memory=d.memory).act


def test_new_rev_acts():
    d = run(sig())
    d2 = run(sig(seq=2, rev=2, targets={"BTC": {"x": 0.0, "px": 60000.0}, "ETH": {"x": -0.4, "px": 2000.0}},
                 scalp=None), pos=dict(d.targets), brackets=[7], memory=d.memory)
    assert d2.act and d2.targets["BTC"] == 0.0 and d2.bracket is None


def test_resync_when_position_changed_outside():
    d = run(sig())
    d2 = run(sig(seq=2), pos={"BTC": 0.0, "ETH": d.targets["ETH"]}, brackets=[7], memory=d.memory)
    assert d2.act and "Resync" in d2.reason and d2.targets["BTC"] == pytest.approx(-0.003)


def test_exposure_cap_scales_all_down():
    s = sig(targets={"BTC": {"x": 30.0, "px": 60000.0}, "ETH": {"x": -20.0, "px": 2000.0}}, scalp=None)
    d = run(s, cfg={"percent": 100.0, "max_x": 3.0})
    btc, eth = d.targets["BTC"] * 60000 / 1000, d.targets["ETH"] * 2000 / 1000
    assert btc == pytest.approx(1.8) and eth == pytest.approx(-1.2) and abs(btc) + abs(eth) == pytest.approx(3.0)
    assert "cap" in d.reason


def test_small_differences_ignored_unless_target_zero():
    held = {"BTC": -0.003 + 15 / 60000, "ETH": -0.02}  # $15 off on BTC: under max($10, 2% of $1,000)
    d = run(sig(), pos=held)
    assert d.targets["BTC"] == held["BTC"]
    zero = sig(targets={"BTC": {"x": 0.0, "px": 60000.0}, "ETH": {"x": 0.0, "px": 2000.0}}, scalp=None)
    d = run(zero, pos={"BTC": -0.00001, "ETH": 0.0})
    assert d.targets["BTC"] == 0.0


def test_flat_closes_everything():
    d = run(sig(state="flat", targets={}, scalp=None), pos={"BTC": -0.003})
    assert d.act and d.targets == {"BTC": 0.0, "ETH": 0.0} and "flat" in d.reason


@pytest.mark.parametrize("case", ["offline", "none", "quiet", "expired"])
def test_offline_or_stale_holds(case):
    s = sig(state="offline", targets={}, scalp=None) if case == "offline" else sig()
    kw = {"offline": {}, "none": {"received": None}, "quiet": {"received": DAY + 940.0},
          "expired": {"now": DAY + 1060.0}}[case]
    d = run(None if case == "none" else s, pos={"BTC": -0.003}, **kw)
    assert not d.act and d.targets == {}


def test_stale_flat_min_closes():
    mem = {"live_at": DAY + 1010.0 - 6 * 60}
    d = run(sig(state="offline", targets={}, scalp=None), cfg={"stale_flat_min": 5}, memory=mem)
    assert d.act and d.targets["BTC"] == 0.0 and "minutes" in d.reason
    d = run(sig(state="offline", targets={}, scalp=None), cfg={"stale_flat_min": 10}, memory=mem)
    assert not d.act


def test_daily_loss_stop_until_next_utc_day():
    d = run(sig(), bal=1000.0)
    d = run(sig(seq=2), bal=900.0, pos=dict(d.targets), memory=d.memory)
    assert d.act and d.targets == {"BTC": 0.0, "ETH": 0.0} and "Daily loss" in d.reason
    d = run(sig(seq=3), bal=950.0, memory=d.memory)  # recovered, same day: still out
    assert d.act and d.targets["BTC"] == 0.0
    nxt = DAY + 86400
    s = clean(payload(ts=nxt + 1000.0, expires=nxt + 1060.0, seq=4))
    d = run(s, now=nxt + 1010.0, received=nxt + 1005.0, bal=950.0, memory=d.memory)
    assert d.act and d.targets["BTC"] < 0 and d.memory["day_start"] == 950.0


def test_pause_holds_and_flatten_closes():
    d = run(sig(), flags={"pause": True}, pos={"BTC": -0.003})
    assert not d.act and "PAUSE" in d.reason
    d = run(sig(), flags={"pause": True, "flatten": True}, pos={"BTC": -0.003})
    assert d.act and d.targets["BTC"] == 0.0 and "FLATTEN" in d.reason


@pytest.mark.parametrize("scalp,why", [
    ({"coin": "BTC", "x": -1.2, "tp": 59400.0, "sl": 61000.0, "id": 7}, "1.5%"),
    ({"coin": "BTC", "x": -1.2, "tp": 59400.0, "sl": 59900.0, "id": 7}, "losing side"),
    ({"coin": "BTC", "x": -1.2, "tp": 60100.0, "sl": 60420.0, "id": 7}, "winning side"),
])
def test_bad_scalp_bracket_not_opened(scalp, why):
    d = run(sig(scalp=scalp))
    assert d.bracket is None and why in d.reason
    assert d.targets["BTC"] == pytest.approx((-1.8 + 1.2) * 0.1 * 1000 / 60000)  # the rest still applies


def test_long_scalp_ok():
    s = sig(targets={"BTC": {"x": 1.0, "px": 60000.0}}, scalp={"coin": "BTC", "x": 0.5, "tp": 60600.0,
                                                               "sl": 59500.0, "id": 3})
    d = run(s)
    assert d.bracket["units"] == pytest.approx(0.5 * 0.1 * 1000 / 60000) and d.targets["ETH"] == 0.0


def test_scalp_closed_by_its_bracket_is_not_reopened():
    d = run(sig())
    held = {"BTC": -0.001, "ETH": -0.02}  # the stop loss took the scalp part off
    d2 = run(sig(seq=2), pos=held, brackets=[], memory=d.memory)
    assert d2.memory["scalp_done"] == 7 and d2.bracket is None
    assert d2.targets["BTC"] == pytest.approx(-0.001)


# --- sizing modes and caps ----------------------------------------------------------------------------------------

def usd(d, coin, px):
    return d.targets[coin] * px


def test_percent_100_follows_the_whole_balance():
    d = run(sig(), cfg={"percent": 100.0})
    assert usd(d, "BTC", 60000) == pytest.approx(-1800) and usd(d, "ETH", 2000) == pytest.approx(-400)
    assert d.bracket["units"] * 60000 == pytest.approx(-1200) and "cap" not in d.reason


@pytest.mark.parametrize("bal", [1000.0, 2000.0, 400.0])
def test_fixed_amount_does_not_grow_with_the_balance(bal):
    d = run(sig(), bal=bal, cfg={"size_mode": "fixed", "fixed_usd": 500.0, "max_x": 25.0})
    assert usd(d, "BTC", 60000) == pytest.approx(-1.8 * 500) and usd(d, "ETH", 2000) == pytest.approx(-0.4 * 500)
    assert d.bracket["units"] * 60000 == pytest.approx(-1.2 * 500)
    assert "$900" in d.reason


def test_fixed_amount_larger_than_the_balance_hits_max_x():
    d = run(sig(), cfg={"size_mode": "fixed", "fixed_usd": 5000.0, "max_x": 3.0})
    k = 3000 / (1.8 * 5000 + 0.4 * 5000)  # max_x is measured against the real $1,000 balance
    assert abs(usd(d, "BTC", 60000)) + abs(usd(d, "ETH", 2000)) == pytest.approx(3000)
    assert usd(d, "BTC", 60000) == pytest.approx(-9000 * k)
    assert d.bracket["units"] * 60000 == pytest.approx(-6000 * k)  # the scalp part shrinks in the same proportion
    assert "exposure cap" in d.reason


def test_cap_per_position_shrinks_that_coin_and_its_scalp():
    d = run(sig(), cfg={"max_position_usd": 100.0})
    assert usd(d, "BTC", 60000) == pytest.approx(-100) and usd(d, "ETH", 2000) == pytest.approx(-40)
    assert d.bracket["units"] * 60000 == pytest.approx(-120 * 100 / 180)
    assert "$100 per position" in d.reason


def test_cap_per_position_then_max_x():
    d = run(sig(), cfg={"size_mode": "fixed", "fixed_usd": 5000.0, "max_position_usd": 4000.0, "max_x": 3.0})
    assert usd(d, "BTC", 60000) == pytest.approx(-2000) and usd(d, "ETH", 2000) == pytest.approx(-1000)
    assert d.bracket["units"] * 60000 == pytest.approx(-6000 * 4000 / 9000 * 0.5)
    assert "per position" in d.reason and "exposure cap" in d.reason


def test_scalp_closing_shrinks_but_keeps_the_rest():
    """Why there is no constant-dollar mode: x shrinks when our scalp closes, and the follower must shrink too."""
    d = run(sig(), cfg={"size_mode": "fixed", "fixed_usd": 500.0})
    after = sig(seq=2, rev=2, targets={"BTC": {"x": -0.6, "px": 60000.0}, "ETH": {"x": -0.4, "px": 2000.0}},
                scalp=None)
    d2 = run(after, pos=dict(d.targets), brackets=[7], memory=d.memory,
             cfg={"size_mode": "fixed", "fixed_usd": 500.0})
    assert usd(d2, "BTC", 60000) == pytest.approx(-300) and d2.bracket is None

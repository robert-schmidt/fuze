import pytest

from conftest import payload
from fuze.follow import GUARD_AGE_S, RECHECK_S, compare, decide, guard_plan
from fuze.protocol import clean

CFG = {"size_mode": "percent", "percent": 10.0, "fixed_usd": 100.0, "max_position_usd": None, "max_x": 3.0,
       "max_balance_usd": None, "daily_loss_frac": 0.1, "stale_flat_min": None, "risk_allowed": 60,
       "coins": ["BTC", "ETH", "HYPE", "LIT"]}
ZERO = {"BTC": 0.0, "ETH": 0.0, "HYPE": 0.0, "LIT": 0.0}
DAY = 86400.0 * 20000  # a UTC midnight


def sig(**kw):
    p = clean(payload(ts=DAY + 1000.0, expires=DAY + 1060.0, **kw))
    assert p is not None
    return p


def placed(d) -> dict:
    """The memory after the agent placed the decided pairs and saw them on the exchange (agent.protect)."""
    return {**d.memory, "prots": {**(d.memory.get("prots") or {}), **d.brackets}}


def run(s, now=DAY + 1010.0, received=DAY + 1005.0, bal=1000.0, pos=None, brackets=None, cfg=None, flags=None,
        memory=None, absent=()):
    acct = {"balance": bal, "positions": pos or {}, "brackets": dict(brackets or {}), "absent": list(absent)}
    return decide(s, received, now, acct, {**CFG, **(cfg or {})}, flags or {}, memory or {})


def test_first_signal_sets_targets_and_bracket():
    d = run(sig())
    assert d.act
    assert d.targets["BTC"] == pytest.approx(-1.8 * 0.1 * 1000 / 60000)
    assert d.targets["ETH"] == pytest.approx(-0.4 * 0.1 * 1000 / 2000)
    assert d.brackets["BTC"] == {"coin": "BTC", "units": pytest.approx(-0.002), "tp": 59400.0, "sl": 60420.0, "id": 7,
                                 "score": 12}
    assert "revision 1" in d.reason and d.memory["rev"] == 1


def test_same_rev_holds_and_price_drift_alone_does_nothing():
    d = run(sig())
    held = dict(d.targets)
    d2 = run(sig(seq=2), pos=held, brackets={"BTC": 7}, memory=placed(d))
    assert not d2.act
    drift = sig(seq=3, targets={"BTC": {"x": -1.9, "px": 63000.0}, "ETH": {"x": -0.41, "px": 1950.0}})
    assert not run(drift, pos=held, brackets={"BTC": 7}, memory=placed(d)).act


def test_new_rev_acts():
    d = run(sig())
    d2 = run(sig(seq=2, rev=2, targets={"BTC": {"x": 0.0, "px": 60000.0}, "ETH": {"x": -0.4, "px": 2000.0}},
                 scalp=None), pos=dict(d.targets), brackets={"BTC": 7}, memory=placed(d))
    assert d2.act and d2.targets["BTC"] == 0.0 and d2.brackets == {}


def test_resync_when_position_changed_outside():
    d = run(sig())
    d2 = run(sig(seq=2), pos={"BTC": 0.0, "ETH": d.targets["ETH"]}, brackets={"BTC": 7}, memory=placed(d))
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
    assert d.act and d.targets == ZERO and "flat" in d.reason


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
    assert d.act and d.targets == ZERO and "Daily loss" in d.reason
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
    assert d.brackets == {} and why in d.reason
    assert d.targets["BTC"] == pytest.approx((-1.8 + 1.2) * 0.1 * 1000 / 60000)  # the rest still applies


def test_long_scalp_ok():
    s = sig(targets={"BTC": {"x": 1.0, "px": 60000.0}}, scalp={"coin": "BTC", "x": 0.5, "tp": 60600.0,
                                                               "sl": 59500.0, "id": 3})
    d = run(s)
    assert d.brackets["BTC"]["units"] == pytest.approx(0.5 * 0.1 * 1000 / 60000) and d.targets["ETH"] == 0.0


def test_scalp_closed_by_its_bracket_is_not_reopened():
    d = run(sig())
    held = {"BTC": -0.001, "ETH": -0.02}  # the stop loss took the scalp part off
    d2 = run(sig(seq=2), pos=held, brackets={}, memory=placed(d))
    assert d2.memory["done"] == {"BTC": 7} and d2.brackets == {}
    assert d2.targets["BTC"] == pytest.approx(-0.001)


# --- sizing modes and caps ----------------------------------------------------------------------------------------

def usd(d, coin, px):
    return d.targets[coin] * px


def test_percent_100_follows_the_whole_balance():
    d = run(sig(), cfg={"percent": 100.0})
    assert usd(d, "BTC", 60000) == pytest.approx(-1800) and usd(d, "ETH", 2000) == pytest.approx(-400)
    assert d.brackets["BTC"]["units"] * 60000 == pytest.approx(-1200) and "cap" not in d.reason


@pytest.mark.parametrize("bal", [1000.0, 2000.0, 400.0])
def test_fixed_amount_does_not_grow_with_the_balance(bal):
    d = run(sig(), bal=bal, cfg={"size_mode": "fixed", "fixed_usd": 500.0, "max_x": 25.0})
    assert usd(d, "BTC", 60000) == pytest.approx(-1.8 * 500) and usd(d, "ETH", 2000) == pytest.approx(-0.4 * 500)
    assert d.brackets["BTC"]["units"] * 60000 == pytest.approx(-1.2 * 500)
    assert "$900" in d.reason


def test_fixed_amount_larger_than_the_balance_hits_max_x():
    d = run(sig(), cfg={"size_mode": "fixed", "fixed_usd": 5000.0, "max_x": 3.0})
    k = 3000 / (1.8 * 5000 + 0.4 * 5000)  # max_x is measured against the real $1,000 balance
    assert abs(usd(d, "BTC", 60000)) + abs(usd(d, "ETH", 2000)) == pytest.approx(3000)
    assert usd(d, "BTC", 60000) == pytest.approx(-9000 * k)
    assert d.brackets["BTC"]["units"] * 60000 == pytest.approx(-6000 * k)  # the scalp part shrinks in the same proportion
    assert "exposure cap" in d.reason


def test_cap_per_position_shrinks_that_coin_and_its_scalp():
    d = run(sig(), cfg={"max_position_usd": 100.0})
    assert usd(d, "BTC", 60000) == pytest.approx(-100) and usd(d, "ETH", 2000) == pytest.approx(-40)
    assert d.brackets["BTC"]["units"] * 60000 == pytest.approx(-120 * 100 / 180)
    assert "$100 per position" in d.reason


def test_cap_per_position_then_max_x():
    d = run(sig(), cfg={"size_mode": "fixed", "fixed_usd": 5000.0, "max_position_usd": 4000.0, "max_x": 3.0})
    assert usd(d, "BTC", 60000) == pytest.approx(-2000) and usd(d, "ETH", 2000) == pytest.approx(-1000)
    assert d.brackets["BTC"]["units"] * 60000 == pytest.approx(-6000 * 4000 / 9000 * 0.5)
    assert "per position" in d.reason and "exposure cap" in d.reason


def test_scalp_closing_shrinks_but_keeps_the_rest():
    """Why there is no constant-dollar mode: x shrinks when our scalp closes, and the follower must shrink too."""
    d = run(sig(), cfg={"size_mode": "fixed", "fixed_usd": 500.0})
    after = sig(seq=2, rev=2, targets={"BTC": {"x": -0.6, "px": 60000.0}, "ETH": {"x": -0.4, "px": 2000.0}},
                scalp=None)
    d2 = run(after, pos=dict(d.targets), brackets={"BTC": 7}, memory=placed(d),
             cfg={"size_mode": "fixed", "fixed_usd": 500.0})
    assert usd(d2, "BTC", 60000) == pytest.approx(-300) and d2.brackets == {}


# --- changed limits and the slow re-check act on the same revision ---------------------------------------------------

def test_lowered_limits_resize_on_the_same_revision():
    d = run(sig())
    held = dict(d.targets)
    d2 = run(sig(seq=2), now=DAY + 1015.0, pos=held, brackets={"BTC": 7}, memory=placed(d), cfg={"percent": 5.0})
    assert d2.act and "limits changed" in d2.reason
    assert d2.targets["BTC"] == pytest.approx(held["BTC"] / 2) and d2.brackets["BTC"]["units"] == pytest.approx(-0.001)
    d3 = run(sig(seq=3), now=DAY + 1020.0, pos=dict(d2.targets), brackets={"BTC": 7}, memory=d2.memory,
             cfg={"percent": 5.0})
    assert not d3.act  # once resized, nothing more to do


def test_a_confirmed_raise_also_applies_without_a_restart():
    d = run(sig(), cfg={"percent": 5.0})
    d2 = run(sig(seq=2), pos=dict(d.targets), brackets={"BTC": 7}, memory=placed(d), cfg={"percent": 10.0})
    assert d2.act and d2.targets["BTC"] == pytest.approx(2 * d.targets["BTC"])


def test_a_cap_added_later_cuts_the_held_position():
    d = run(sig())
    d2 = run(sig(seq=2), pos=dict(d.targets), brackets={"BTC": 7}, memory=placed(d), cfg={"max_position_usd": 50.0})
    assert d2.act and d2.targets["BTC"] * 60000 == pytest.approx(-50.0)


def test_slow_recheck_corrects_a_large_gap_but_not_price_drift():
    d = run(sig())  # $1,000 balance: BTC -$180
    held = dict(d.targets)
    later = DAY + 1010.0 + RECHECK_S

    def at(**kw):
        return clean(payload(ts=later - 5, expires=later + 55, **kw))

    drift = at(seq=3, targets={"BTC": {"x": -1.9, "px": 63000.0}, "ETH": {"x": -0.41, "px": 1950.0}})
    r = run(drift, now=later, received=later - 1, pos=held, brackets={"BTC": 7}, memory=placed(d))
    assert not r.act and r.reason == "Following revision 1; nothing to change."
    r = run(at(seq=4), now=later, received=later - 1, bal=1050.0, pos=held, brackets={"BTC": 7}, memory=placed(d))
    assert not r.act and r.reason == "Following revision 1; nothing to change."  # 5%: inside the 10% band
    d2 = run(at(seq=5), now=later, received=later - 1, bal=2000.0, pos=held, brackets={"BTC": 7}, memory=placed(d))
    assert d2.act and "Re-check" in d2.reason and d2.targets["BTC"] == pytest.approx(2 * held["BTC"])
    early = run(sig(seq=6), now=DAY + 1020.0, bal=2000.0, pos=held, brackets={"BTC": 7}, memory=placed(d))
    assert not early.act  # before the re-check is due, a balance change alone does nothing


def test_resizing_keeps_an_open_scalp_whose_stop_is_now_far_from_the_price():
    d = run(sig())
    moved = sig(seq=2, targets={"BTC": {"x": -1.7, "px": 59000.0}, "ETH": {"x": -0.4, "px": 2000.0}})
    d2 = run(moved, pos=dict(d.targets), brackets={"BTC": 7}, memory=placed(d), cfg={"percent": 5.0})
    assert d2.act and d2.brackets["BTC"] is not None and "not opened" not in d2.reason


def test_reason_says_when_a_change_is_too_small_to_trade():
    d = run(sig(), cfg={"size_mode": "fixed", "fixed_usd": 10.0})
    assert d.targets == ZERO or all(abs(v) < 1e-12 for v in d.targets.values())
    assert "asks for BTC short $18, ETH short $4" in d.reason and "under $20" in d.reason
    assert d.memory["wanted"]["BTC"] * 60000 == pytest.approx(-18.0) and d.memory["min_change"] == 20.0
    rows = compare(d.memory["wanted"], {}, {"BTC": 60000.0, "ETH": 2000.0}, 20.0)
    assert rows[0] == {"coin": "BTC", "asked_usd": -18.0, "held_usd": 0.0, "difference_usd": -18.0,
                       "under_min_change": True}


def test_lowered_limits_shrink_a_coin_even_by_less_than_the_dead_band():
    d = run(sig())  # ETH -$40
    d2 = run(sig(seq=2), pos=dict(d.targets), brackets={"BTC": 7}, memory=placed(d), cfg={"percent": 6.0})
    assert d2.targets["ETH"] * 2000 == pytest.approx(-24.0)  # a $16 reduction, under the $20 step, still applied
    d3 = run(sig(seq=3), pos=dict(d.targets), brackets={"BTC": 7}, memory=placed(d), cfg={"percent": 11.0})
    assert d3.targets["ETH"] == d.targets["ETH"]  # a raise of $4 on ETH stays inside the band


def test_cents_of_difference_are_not_reported_as_too_small_to_trade():
    d = run(sig())
    held = {c: v * 1.0001 for c, v in d.targets.items()}  # a few cents off
    d2 = run(sig(seq=2), pos=held, brackets={"BTC": 7}, memory=placed(d), cfg={"max_x": 2.9})
    assert "under $20" not in d2.reason
    assert not any(r["under_min_change"] for r in compare(d.memory["wanted"], held, {"BTC": 60000.0, "ETH": 2000.0},
                                                          20.0))


# --- the stop follows a scalp that is in profit, and an entry is added only then ----------------------------------

MOVED = {"coin": "BTC", "x": -1.2, "tp": 59100.0, "sl": 59850.0, "id": 7}  # entry 60,000: the stop is 25 bps in profit


def test_a_stop_moved_into_profit_is_followed():
    """The new stop is on the winning side of the entry and still on the losing side of the price: a new revision
    with the same position. The agent keeps the position and replaces the pair."""
    d = run(sig())
    held = dict(d.targets)
    s = sig(seq=2, rev=2, targets={"BTC": {"x": -1.8, "px": 59640.0}, "ETH": {"x": -0.4, "px": 2000.0}}, scalp=MOVED)
    d2 = run(s, pos=held, brackets={"BTC": 7}, memory=placed(d))
    assert d2.act and d2.targets == held and "not opened" not in d2.reason
    assert d2.brackets["BTC"] == {"coin": "BTC", "units": pytest.approx(-120 / 59640), "tp": 59100.0, "sl": 59850.0, "id": 7,
                                     "score": 12}


def test_an_added_entry_grows_the_position_and_keeps_the_moved_stop():
    d = run(sig())
    s = sig(seq=2, rev=2, targets={"BTC": {"x": -2.4, "px": 59640.0}, "ETH": {"x": -0.4, "px": 2000.0}},
            scalp={**MOVED, "x": -1.8})
    d2 = run(s, pos=dict(d.targets), brackets={"BTC": 7}, memory=placed(d))
    assert d2.targets["BTC"] == pytest.approx(-240 / 59640)
    assert d2.brackets["BTC"]["units"] == pytest.approx(-180 / 59640) and d2.brackets["BTC"]["sl"] == 59850.0 and d2.brackets["BTC"]["id"] == 7


def test_a_moved_stop_the_price_already_crossed_closes_the_scalp_part():
    d = run(sig())
    s = sig(seq=2, rev=2, targets={"BTC": {"x": -1.8, "px": 59900.0}, "ETH": {"x": -0.4, "px": 2000.0}}, scalp=MOVED)
    d2 = run(s, pos=dict(d.targets), brackets={"BTC": 7}, memory=placed(d))
    assert d2.brackets == {} and "losing side" in d2.reason
    assert d2.targets["BTC"] == pytest.approx(-60 / 59900)  # the trend part stays


# --- the emergency stop -------------------------------------------------------------------------------------------

def test_emergency_stop_covers_what_the_pair_does_not():
    plan = lambda held, covered, resting=None, px=60000.0, now=100.0, following=True: guard_plan(
        held, covered, px, resting, now, following, 0.0002)
    assert plan(-0.003, -0.002) == ("place", {"units": pytest.approx(-0.001), "stop": 72000.0, "ref": 60000.0})
    assert plan(0.5, 0.0, px=2000.0) == ("place", {"units": 0.5, "stop": 1600.0, "ref": 2000.0})  # a long: under it
    assert plan(0.0, 0.0) == ("none", None)
    assert plan(-0.002, -0.002) == ("none", None)  # the pair closes all of it
    assert plan(0.0015, 0.002) == ("none", None)  # a scalp against the trend part: its pair is the whole position
    g = {"units": -0.001, "stop": 72000.0, "ref": 60000.0, "t": 50.0}
    assert plan(0.0, 0.0, g) == ("remove", None) and plan(-0.002, -0.002, g) == ("remove", None)
    assert plan(-0.003, -0.002, g) == ("keep", None)
    assert plan(-0.0031, -0.002, g) == ("keep", None)  # a difference under the smallest change: not replaced
    assert plan(-0.004, -0.002, g)[1]["units"] == pytest.approx(-0.002)  # the trend part grew
    assert plan(0.001, 0.0, g) == ("place", {"units": 0.001, "stop": 48000.0, "ref": 60000.0})  # it changed sides


def test_emergency_stop_follows_the_price_only_while_a_live_signal_is_followed():
    g = {"units": -0.001, "stop": 72000.0, "ref": 60000.0, "t": 50.0}
    plan = lambda px, following, now=100.0: guard_plan(-0.001, 0.0, px, g, now, following, 0.0002)
    assert plan(62900.0, True) == ("keep", None)  # under 5% from where it was set
    assert plan(63000.0, True) == ("place", {"units": -0.001, "stop": 75600.0, "ref": 63000.0})  # against: further away
    assert plan(57000.0, True) == ("place", {"units": -0.001, "stop": 68400.0, "ref": 57000.0})  # in favour: closer
    assert plan(71000.0, False) == ("keep", None)  # no live signal: it stays, so it can fill
    # Lighter drops an order after 28 days: placed again after 14, at the same price when no signal is followed
    assert plan(60500.0, False, 50.0 + GUARD_AGE_S) == ("place", {"units": -0.001, "stop": 72000.0, "ref": 60000.0})
    assert plan(60500.0, True, 50.0 + GUARD_AGE_S) == ("place", {"units": -0.001, "stop": 72600.0, "ref": 60500.0})


def test_a_balance_ceiling_sizes_and_stops_as_if_the_account_held_no_more():
    """The wallet holds $50,000, the user said $1,000: same positions as a $1,000 account, and the daily loss stop
    fires after 10% of $1,000, not of $50,000. Below the ceiling the real balance counts."""
    top = {"max_balance_usd": 1000.0}
    small, d = run(sig()), run(sig(), bal=50_000.0, cfg=top)
    assert d.targets == small.targets and d.brackets["BTC"] == small.brackets["BTC"] and d.memory["min_change"] == 20.0
    hold = run(sig(seq=2), bal=49_950.0, pos=dict(d.targets), cfg=top, memory=d.memory)
    assert not hold.act  # $50 down: inside the stop
    out = run(sig(seq=2), bal=49_900.0, pos=dict(d.targets), cfg=top, memory=d.memory)
    assert out.act and out.targets == ZERO and "Daily loss" in out.reason
    assert run(sig(), bal=600.0, cfg=top).targets["BTC"] == pytest.approx(-1.8 * 0.1 * 600 / 60000)
    assert run(sig(), bal=50_000.0, cfg={**top, "max_x": 0.5}).targets == run(sig(), cfg={"max_x": 0.5}).targets


# --- version 2: risk allowed, coins, one short-term part per coin ----------------------------------------------------

FOUR = {"BTC": {"x": -1.8, "px": 60000.0, "trend": {"x": -0.6, "score": 9}},
        "ETH": {"x": -0.4, "px": 2000.0, "trend": {"x": -0.4, "score": 25}},
        "HYPE": {"x": -1.0, "px": 34.0, "trend": {"x": -0.5, "score": 30}},
        "LIT": {"x": 1.0, "px": 2.5, "trend": {"x": 1.0, "score": 70}}}
HYPE_SCALP = {"coin": "HYPE", "x": -0.5, "tp": 33.66, "sl": 34.24, "id": 9, "score": 5}
BTC_SCALP = {"coin": "BTC", "x": -1.2, "tp": 59400.0, "sl": 60420.0, "id": 7, "score": 21}


def test_each_part_is_followed_whole_at_or_under_the_risk_allowed_and_skipped_above_it():
    s = sig(targets=FOUR, scalps=[BTC_SCALP, HYPE_SCALP])
    d = run(s, cfg={"risk_allowed": 20})
    base = 0.1 * 1000
    assert d.targets["BTC"] * 60000 == pytest.approx(-0.6 * base)  # the trend part (9) only: the trade scores 21
    assert d.targets["ETH"] == 0.0 and d.targets["LIT"] == 0.0  # 25 and 70: above 20
    assert d.targets["HYPE"] * 34 == pytest.approx(-0.5 * base)  # its short-term trade (5) only
    assert set(d.brackets) == {"HYPE"} and d.brackets["HYPE"]["units"] == pytest.approx(-50 / 34)
    assert "The Bitcoin short-term trade scores 21, above your risk allowed of 20: not followed." in d.reason
    assert "The Ether trend part scores 25, above your risk allowed of 20: not followed." in d.reason
    d = run(s, cfg={"risk_allowed": 21})  # at the score: followed
    assert set(d.brackets) == {"BTC", "HYPE"} and d.targets["BTC"] * 60000 == pytest.approx(-180)
    d = run(s, cfg={"risk_allowed": 100})
    assert d.targets["LIT"] * 2.5 == pytest.approx(100) and "not followed" not in d.reason


def test_risk_allowed_0_follows_only_parts_that_score_0():
    s = sig(targets={"BTC": {"x": -0.6, "px": 60000.0, "trend": {"x": -0.6, "score": 0}}}, scalps=[])
    assert run(s, cfg={"risk_allowed": 0}).targets["BTC"] * 60000 == pytest.approx(-60)


def test_a_coin_not_among_yours_is_not_opened_and_what_is_held_of_it_is_closed():
    s = sig(targets=FOUR, scalps=[BTC_SCALP, HYPE_SCALP])
    d = run(s, cfg={"coins": ["BTC", "ETH"], "risk_allowed": 100}, pos={"HYPE": -1.0})
    assert d.targets["HYPE"] == 0.0 and d.targets["LIT"] == 0.0 and set(d.brackets) == {"BTC"}  # its scalp ignored
    assert "HYPE is not among your coins: what you hold of it is closed." in d.reason
    assert "LIT is not among your coins: not followed." in d.reason


def test_a_coin_the_exchange_does_not_list_is_wanted_at_0():
    s = sig(targets={c: FOUR[c] for c in ("ETH", "HYPE")}, scalps=[HYPE_SCALP])
    d = run(s, cfg={"risk_allowed": 100}, absent=["HYPE"])
    assert d.targets["HYPE"] == 0.0 and d.brackets == {}
    assert "The exchange lists no HYPE market here: HYPE is not traded." in d.reason


def test_raising_risk_allowed_or_removing_a_coin_resizes_on_the_same_revision():
    s = sig(targets=FOUR, scalps=[BTC_SCALP, HYPE_SCALP])
    d = run(s, cfg={"risk_allowed": 20})
    d2 = run(sig(seq=2, targets=FOUR, scalps=[BTC_SCALP, HYPE_SCALP]), pos=dict(d.targets), brackets={"HYPE": 9},
             memory=placed(d), cfg={"risk_allowed": 20, "coins": ["BTC", "ETH", "LIT"]})
    assert d2.act and "limits changed" in d2.reason and d2.targets["HYPE"] == 0.0 and d2.brackets == {}


def test_one_short_term_part_per_coin_each_closed_by_its_own_pair_is_not_reopened():
    s = sig(targets=FOUR, scalps=[BTC_SCALP, HYPE_SCALP])
    d = run(s, cfg={"risk_allowed": 100})
    assert set(d.brackets) == {"BTC", "HYPE"}
    held = dict(d.targets, HYPE=d.targets["HYPE"] - d.brackets["HYPE"]["units"])  # HYPE's stop loss fired
    d2 = run(sig(seq=2, targets=FOUR, scalps=[BTC_SCALP, HYPE_SCALP]), pos=held, brackets={"BTC": 7},
             memory=placed(d), cfg={"risk_allowed": 100})
    assert d2.memory["done"] == {"HYPE": 9}
    assert set(d2.brackets) == {"BTC"} and d2.targets["HYPE"] == pytest.approx(held["HYPE"])


def test_lighters_highest_leverage_on_lit_bounds_its_position():
    s = sig(targets={"LIT": {"x": 8.0, "px": 2.5, "trend": {"x": 8.0, "score": 10}}}, scalps=[])
    d = run(s, cfg={"percent": 100.0, "max_x": 25.0})
    assert d.targets["LIT"] * 2.5 == pytest.approx(5000) and "highest leverage Lighter allows" in d.reason


def test_the_memory_of_a_0_5_0_agent_is_migrated():
    from fuze.follow import migrate
    prot = {"coin": "BTC", "units": -0.002, "tp": 59400.0, "sl": 60420.0, "id": 7}
    m = migrate({"prot": prot, "scalp": {"id": 7, "coin": "BTC"}, "scalp_done": 5, "rev": 3, "day": "x"})
    assert m == {"prots": {"BTC": prot}, "done": {"BTC": 5}, "rev": 3, "day": "x"}
    assert migrate({"prot": None, "scalp": None}) == {}
    assert migrate(m) == m  # this version's own memory is left as it is
    d = run(sig(seq=2), pos={"BTC": -0.003, "ETH": -0.02}, brackets={}, memory={"prot": prot, "rev": 1})
    assert d.memory["done"] == {"BTC": 7}  # a pair that fired while the update ran is still seen as closed


def test_the_part_that_explains_a_change_is_named_for_the_report():
    d = run(sig())  # both parts open at once: no single part explains the BTC order; ETH has only its trend part
    assert "BTC" not in d.parts and d.parts["ETH"] == ("trend", 10)
    d2 = run(sig(seq=2, rev=2, targets={"BTC": {"x": -0.6, "px": 60000.0}, "ETH": {"x": -0.4, "px": 2000.0}},
                 scalp=None), pos=dict(d.targets), brackets={"BTC": 7}, memory=placed(d))
    assert d2.parts == {"BTC": ("scalp", 12)}  # the short-term trade ended: its score at the time

"""The Lighter adapter and the agent's order step against a fake client. No network, no real orders."""

import json

import pytest

from conftest import payload
from fake_lighter import FakeLighter
from fuze import config
from fuze.agent import INFLIGHT_WAIT_S, MISS_WAIT_S, Agent
from fuze.lighter_venue import LighterVenue
from fuze.venue import TESTNET_SLIP, Venue, account_link, tx_link, worst_price


class Clock:
    def __init__(self, t=1010.0):
        self.t = t

    def __call__(self):
        return self.t


@pytest.fixture
def fake():
    return FakeLighter()


def venue(fake, clock=None, home=None):
    home = home or config.ensure_home()
    v = LighterVenue(fake, home / "lighter-testnet.json", clock or Clock(), net="testnet", index=77)
    v.slip = Venue.slip  # the numbers below are mainnet's price bound; testnet's wider one has its own test
    return v


def agent(fake, signer, clock, cfg=None):
    cfg = config.validate({"mode": "testnet", "testnet_account": 77, **(cfg or {})})
    return Agent(cfg, home=config.ensure_home(), keys=signer.keys, clock=clock, exchange=venue(fake, clock),
                 sleep=lambda s: None)


def send(a, signer, clock, **kw):
    """Feed one signed signal, valid at the clock's time."""
    t = clock.t - 5
    a.handle(json.dumps(signer.envelope(payload(ts=t, expires=t + 60, **kw))))


BTC_SELL = ("market", 1, 300, 597000, True, False)  # 0.003 BTC short at a worst price 0.5% under $60,000
ETH_SELL = ("market", 0, 200, 199000, True, False)  # 0.02 ETH short at a worst price 0.5% under $2,000
PAIR = ("tp_sl", 1, 200, False, 594000, 596970, 604200, 616284)  # 0.002 BTC: buy back at 59,400 / 60,420
BTC_GUARD = ("stop", 1, 100, False, 720000, 748800)  # the trend part, 0.001 BTC: bought back at $72,000, 20% away,
ETH_GUARD = ("stop", 0, 200, False, 240000, 249600)  # ... never over 4% past it; and 0.02 ETH at $2,400


# --- the adapter: units, prices, minimums, read-back ----------------------------------------------------------------

def test_markets_decimals_and_minimums_come_from_the_exchange(fake):
    v = venue(fake)
    assert v.m["BTC"] == {"id": 1, "sd": 5, "pd": 1, "min_base": 0.0002, "min_quote": 10.0, "px": 60000.0}
    assert v.round("BTC", -1.8 * 0.1 * 1000 / 60000) == -0.003 and v.round("BTC", -0.0012345) == -0.00123
    assert v.round("ETH", 0.12349) == 0.1234
    assert v.tradable("BTC", 0.0002, 60000.0) and not v.tradable("BTC", 0.00019, 60000.0)
    assert not v.tradable("ETH", 0.005, 1000.0)  # $5: under the $10 smallest order
    assert v.smallest("BTC", 60000.0) == pytest.approx(0.0002)
    assert v.smallest("ETH", 2000.0) == pytest.approx(0.0053)  # $10 x 1.05 / $2,000, up to the size step


def test_testnet_gets_a_wider_price_bound_than_mainnet(fake):
    """Lighter testnet's book is thin (best offer 1.4% over best bid on 2026-11-25): 0.5% did not fill there."""
    home = config.ensure_home()
    test, main = (LighterVenue(fake, home / f"lighter-{n}.json", Clock(), net=n, index=77) for n in ("testnet", "mainnet"))
    assert test.slip == TESTNET_SLIP and max(TESTNET_SLIP) < 0.05  # under Lighter's own 5% price check
    assert test.worst(60000.0, 0.001, False) == pytest.approx(61800.0) and test.worst(60000.0, -0.001, True) == pytest.approx(57600.0)
    assert main.worst(60000.0, 0.001, False) == pytest.approx(60300.0) and main.worst(60000.0, -0.001, True) == pytest.approx(58800.0)
    test.market("BTC", 0.001, 60000.0)  # no worst price given: the venue's own bound
    assert fake.sent[-1] == ("market", 1, 100, 618000, False, False)


def test_market_order_in_integer_units_with_a_worst_price(fake):
    v = venue(fake)
    v.market("BTC", -0.003, 60000.0, worst_price(60000.0, -0.003, False), False)
    v.market("BTC", 0.001, 60000.0, worst_price(60000.0, 0.001, True), True)
    assert fake.sent == [BTC_SELL, ("market", 1, 100, 612000, False, True)]
    with pytest.raises(ValueError, match="size step"):
        v.market("BTC", 0.000001, 60000.0)


def test_account_reading(fake):
    fake.pos, fake.bal = {0: 0.5, 1: -0.01}, 1234.5
    a = venue(fake).account(fresh=True)
    assert a == {"balance": 1234.5, "positions": {"ETH": 0.5, "BTC": -0.01}, "brackets": [], "guards": {}}


def test_markets_missing_are_refused(fake):
    fake.markets = lambda: [m for m in FakeLighter().markets() if m["symbol"] != "ETH"]
    with pytest.raises(RuntimeError, match="no ETH market"):
        venue(fake)


def test_links():
    assert account_link("testnet", 77) == "https://testnet.app.lighter.xyz/explorer/accounts/77"
    assert account_link("mainnet", 5) == "https://app.lighter.xyz/explorer/accounts/5"
    assert tx_link("mainnet", "ab12") == "https://app.lighter.xyz/explorer/logs/ab12"
    assert account_link("simulation", 1) is None and account_link("testnet", None) is None


# --- following on Lighter: the same agent code path as the simulation ----------------------------------------------

def test_follows_and_protects_the_scalp_part(fake, signer):
    c = Clock()
    a = agent(fake, signer, c)
    send(a, signer, c)
    # the scalp's coin first, then the pair of the scalp part only, then an emergency stop for the rest of each coin
    assert fake.sent == [BTC_SELL, ETH_SELL, PAIR, BTC_GUARD, ETH_GUARD]
    st = config.read_json(config.home() / "status.json")
    assert st["account"]["positions"] == {"BTC": -0.003, "ETH": -0.02} and st["account"]["brackets"] == [7]
    assert {k: (g["units"], g["stop"]) for k, g in st["account"]["guards"].items()} == {
        "BTC": (-0.001, 72000.0), "ETH": (-0.02, 2400.0)}
    assert st["mode"] == "testnet" and st["account_link"].endswith("/accounts/77")
    rows = [json.loads(x) for x in (config.home() / "trades.jsonl").read_text().splitlines()]
    assert [r["result"] for r in rows] == ["filled", "filled"] and rows[0]["link"].endswith("/logs/" + "ab" * 32)
    c.t += 5
    send(a, signer, c, seq=2)  # a heartbeat, same revision
    assert len(fake.sent) == 5


def test_partial_fill_stops_the_step_and_protects_what_is_held(fake, signer):
    c = Clock()
    a = agent(fake, signer, c)
    fake.fill = "half"
    send(a, signer, c)
    assert fake.markets_sent() == [BTC_SELL]  # no ETH order, no second BTC order
    assert fake.pos[1] == -0.0015 and fake.sent[-1][:3] == ("tp_sl", 1, 150)  # the held part of the scalp
    assert "filled in part" in config.read_json(config.home() / "status.json")["reason"]
    fake.fill = "full"
    c.t += 5
    send(a, signer, c, seq=2)
    assert len(fake.markets_sent()) == 1  # waiting MISS_WAIT_S before the next try
    c.t += MISS_WAIT_S
    n = len(fake.sent)
    send(a, signer, c, seq=3)
    # the next try: from a new account read, only the rest; the pair is re-placed at the scalp part's full size
    assert [s[0] for s in fake.sent[n:]] == ["cancel", "cancel", "market", "market", "tp_sl", "stop", "stop"]
    assert fake.sent[n + 2][2] == 150 and fake.sent[n + 3] == ETH_SELL and fake.sent[n + 4:] == [PAIR, BTC_GUARD, ETH_GUARD]
    assert fake.pos == {0: -0.02, 1: -0.003}


def test_missing_fill_sends_nothing_else(fake, signer):
    c = Clock()
    a = agent(fake, signer, c)
    fake.fill = "none"
    send(a, signer, c)
    assert fake.sent == [BTC_SELL]
    row = json.loads((config.home() / "trades.jsonl").read_text().splitlines()[-1])
    assert row["result"] == "did not fill" and row["units"] == 0
    assert a.memory["retry_at"] == pytest.approx(c.t + MISS_WAIT_S)


def test_a_lost_answer_is_not_sent_twice(fake, signer):
    c = Clock()
    a = agent(fake, signer, c)
    fake.fill = "lost"  # the order fills but the call raises
    send(a, signer, c)
    assert [s[2] for s in fake.markets_sent()] == [300, 200]  # BTC once, then ETH once
    assert fake.pos == {0: -0.02, 1: -0.003}


def test_restart_mid_order_reads_the_account_and_never_resends(fake, signer):
    c = Clock()
    fake.pos[1] = -0.003  # the order sent before the stop did fill
    config.write_json(config.ensure_home() / "pending.json", {"t": c.t - 2, "coin": "BTC", "units": -0.003,
                                                             "before": 0.0, "worst": 59700.0, "reduce_only": False})
    a = agent(fake, signer, c)
    send(a, signer, c)
    assert fake.sent == [] and "may still be settling" in a.last_reason
    c.t += INFLIGHT_WAIT_S
    send(a, signer, c, seq=2)
    assert fake.markets_sent() == [ETH_SELL] and fake.sent[-3:] == [PAIR, BTC_GUARD, ETH_GUARD]  # no second BTC order
    assert not (config.home() / "pending.json").exists()
    rows = [json.loads(x) for x in (config.home() / "trades.jsonl").read_text().splitlines()]
    assert rows[0]["coin"] == "BTC" and rows[0]["result"] == "filled"


@pytest.mark.parametrize("trouble", ["hidden", "refused"])
def test_an_unprotected_scalp_part_is_closed(fake, signer, trouble):
    c = Clock()
    a = agent(fake, signer, c)
    fake.pair = trouble
    send(a, signer, c)
    assert fake.markets_sent()[-1] == ("market", 1, 200, 612000, False, True)  # reduce-only, worst price 2% over
    assert fake.pos[1] == pytest.approx(-0.001) and a.memory["scalp_done"] == 7
    fake.pair = "ok"
    c.t += 5
    n = len(fake.sent)
    send(a, signer, c, seq=2)
    assert len(fake.sent) == n  # that scalp is not opened again


def test_pair_replaced_when_levels_change_and_cancelled_when_the_scalp_closes(fake, signer):
    c = Clock()
    a = agent(fake, signer, c)
    send(a, signer, c)
    c.t += 5
    n = len(fake.sent)
    send(a, signer, c, seq=2, rev=2, scalp={"coin": "BTC", "x": -1.2, "tp": 59300.0, "sl": 60300.0, "id": 7})
    assert [s[0] for s in fake.sent[n:]] == ["cancel", "cancel", "tp_sl"] and fake.sent[-1][4] == 593000
    c.t += 5
    n = len(fake.sent)
    send(a, signer, c, seq=3, rev=3, scalp=None,
         targets={"BTC": {"x": -0.6, "px": 60000.0}, "ETH": {"x": -0.4, "px": 2000.0}})
    assert [s[0] for s in fake.sent[n:]] == ["cancel", "cancel", "market"]  # cancelled before the close
    assert fake.sent[-1] == ("market", 1, 200, 612000, False, True)
    assert sorted(o["type"] for o in fake.orders.values()) == ["stop-loss", "stop-loss"]  # the emergency stops stay


def test_the_exchange_firing_the_stop_ends_that_scalp(fake, signer):
    c = Clock()
    a = agent(fake, signer, c)
    send(a, signer, c)
    fake.stop_out(1)
    c.t += 6
    n = len(fake.sent)
    send(a, signer, c, seq=2)
    assert len(fake.sent) == n and a.memory["scalp_done"] == 7 and fake.pos[1] == pytest.approx(-0.001)


def test_the_scalp_stop_firing_is_seen_beside_a_resting_emergency_stop(fake, signer):
    c = Clock()
    a = agent(fake, signer, c)
    send(a, signer, c)
    assert len(fake.orders) == 4  # the pair, and an emergency stop on each coin
    fake.stop_out(1)
    c.t += 6
    send(a, signer, c, seq=2)
    st = config.read_json(config.home() / "status.json")["account"]
    assert st["brackets"] == [] and set(st["guards"]) == {"BTC", "ETH"}  # the emergency stop is not taken for the pair
    assert fake.stops_sent() == [BTC_GUARD, ETH_GUARD]  # ... and still fits what is left: not replaced


def test_emergency_stop_moves_with_the_price_only_while_the_signal_is_live(fake, signer):
    c = Clock()
    a = agent(fake, signer, c, {"daily_loss_frac": 0.5})
    send(a, signer, c, scalp=None, targets={"BTC": {"x": -0.6, "px": 60000.0}})
    assert fake.stops_sent() == [BTC_GUARD]
    fake.px["BTC"] = 63600.0  # 6% against the short
    c.t += 31  # the exchange's price is read every 30 seconds: the emergency stop is 20% away, it can wait
    send(a, signer, c, seq=2, scalp=None, targets={"BTC": {"x": -0.6, "px": 63600.0}})
    assert fake.sent[-2:] == [("cancel", 1, 101), ("stop", 1, 100, False, 763200, 793728)]  # 20% over $63,600
    fake.px["BTC"] = 70000.0  # the signal goes quiet and the price runs on
    c.t += 300
    a.tick()
    assert "No fresh signal" in a.last_reason and len(fake.stops_sent()) == 2  # it stays where it is ...
    fake.stop_out(1, "guard")  # ... so the exchange can fill it
    assert fake.pos[1] == 0
    c.t += 6
    a.tick()
    assert "emergency stop at 76,320.00 is no longer on the exchange" in a.last_reason
    assert fake.markets_sent() == [("market", 1, 100, 597000, True, False)]  # nothing is opened without a live signal


def test_a_filled_emergency_stop_is_said_and_the_position_brought_back(fake, signer):
    c = Clock()
    a = agent(fake, signer, c)
    send(a, signer, c)
    fake.stop_out(1, "guard")  # a wick to $72,000 between two steps
    assert fake.pos[1] == pytest.approx(-0.002)
    c.t += 6
    send(a, signer, c, seq=2)
    assert "BTC emergency stop at 72,000.00 is no longer on the exchange" in a.last_reason
    assert fake.pos[1] == pytest.approx(-0.003) and fake.stops_sent()[-1] == BTC_GUARD
    assert set(config.read_json(config.home() / "status.json")["account"]["guards"]) == {"BTC", "ETH"}


@pytest.mark.parametrize("trouble,why", [("refused", "could not be set"), ("hidden", "not on the exchange after")])
def test_an_emergency_stop_that_cannot_rest_is_tried_again_and_stops_nothing_else(fake, signer, trouble, why):
    c = Clock()
    a = agent(fake, signer, c)
    fake.stop = trouble
    send(a, signer, c)
    assert fake.sent[:3] == [BTC_SELL, ETH_SELL, PAIR] and why in a.last_reason  # the position and the pair are there
    fake.stop = "ok"
    c.t += 5
    n = len(fake.stops_sent())
    send(a, signer, c, seq=2)
    assert len(fake.stops_sent()) == n  # not on every step
    c.t += MISS_WAIT_S
    send(a, signer, c, seq=3)
    assert fake.stops_sent()[-2:] == [BTC_GUARD, ETH_GUARD]


def test_flatten_removes_the_emergency_stops(fake, signer):
    c = Clock()
    a = agent(fake, signer, c)
    send(a, signer, c)
    a.ex.flatten()
    assert fake.orders == {} and fake.pos == {0: 0.0, 1: 0.0}
    assert a.ex.account(fresh=True)["guards"] == {}


def test_an_emergency_stop_left_without_its_record_is_found_and_replaced(fake, signer):
    c = Clock()
    a = agent(fake, signer, c)
    send(a, signer, c, scalp=None, targets={"BTC": {"x": -0.6, "px": 60000.0}})
    (config.home() / "lighter-testnet-guards.json").unlink()
    c.t += 6
    b = agent(fake, signer, c)  # a restart without the record
    send(b, signer, c, seq=2, scalp=None, targets={"BTC": {"x": -0.6, "px": 60000.0}})
    assert [o["type"] for o in fake.orders.values()] == ["stop-loss"] and len(fake.stops_sent()) == 2  # one, not two


def test_daily_loss_stop_closes_everything_reduce_only(fake, signer):
    c = Clock()
    a = agent(fake, signer, c)
    send(a, signer, c)
    fake.bal = 880.0
    c.t += 6
    n = len(fake.sent)
    send(a, signer, c, seq=2)
    new = fake.sent[n:]
    # the pair first, then the closes, then the two emergency stops, which have nothing left to close
    assert [s[0] for s in new] == ["cancel", "cancel", "market", "market", "cancel", "cancel"]
    assert all(s[5] for s in new if s[0] == "market") and fake.pos == {0: 0.0, 1: 0.0} and fake.orders == {}
    assert "Daily loss stop" in a.last_reason


def test_flip_closes_reduce_only_then_opens(fake, signer):
    c = Clock()
    a = agent(fake, signer, c)
    send(a, signer, c, scalp=None)
    c.t += 5
    n = len(fake.sent)
    send(a, signer, c, seq=2, rev=2, scalp=None,
         targets={"BTC": {"x": 1.8, "px": 60000.0}, "ETH": {"x": -0.4, "px": 2000.0}})
    # ... and the emergency stop changes sides with the position: $48,000, 20% under the price
    assert fake.sent[n:] == [("market", 1, 300, 612000, False, True), ("market", 1, 300, 603000, False, False),
                             ("cancel", 1, 101), ("stop", 1, 300, True, 480000, 460800)]


def test_scalp_part_under_the_smallest_order_is_not_opened(fake, signer):
    c = Clock()
    fake.bal = 80.0
    a = agent(fake, signer, c)
    send(a, signer, c, targets={"BTC": {"x": -3.0, "px": 60000.0}, "ETH": {"x": -0.4, "px": 2000.0}})
    # BTC: $24 short of which the scalp part is $9.60, under Lighter's $10: the scalp part is left out
    assert fake.sent == [("market", 1, 24, 597000, True, False), ("stop", 1, 24, False, 720000, 748800)]
    assert "under the exchange's smallest order" in a.last_reason
    c.t += 5
    send(a, signer, c, seq=2)
    assert len(fake.sent) == 2


def test_an_unreadable_account_sends_nothing(fake, signer):
    c = Clock()
    a = agent(fake, signer, c)

    def down():
        raise OSError("connection refused")

    fake.account = down
    send(a, signer, c)
    assert fake.sent == [] and "Could not read the account" in a.last_reason


def test_a_quiet_minute_leaves_half_of_lighters_request_limit_for_orders(fake, signer, monkeypatch):
    """A standard Lighter account gets 60 requests a rolling minute, orders included. With a scalp and both emergency
    stops resting, a minute of nothing to do must stay at half of that."""
    reads = []
    for name in ("markets", "account", "active_orders"):
        monkeypatch.setattr(fake, name, lambda *a, _f=getattr(fake, name), _n=name: (reads.append(_n), _f(*a))[1])
    c = Clock()
    a = agent(fake, signer, c)
    send(a, signer, c)  # a short with its scalp pair on BTC, an emergency stop on BTC and ETH
    del reads[:]
    for _ in range(60):  # one step a second, a fresh signal each time, nothing changes
        c.t += 1
        send(a, signer, c)
    assert len(reads) <= 30, {n: reads.count(n) for n in set(reads)}

import json

import pytest

from conftest import TEST_KEYS, VECTORS, payload, payload_v1
from fuze.protocol import COINS, PINNED, Guard, clean, verify


def test_test_key_is_not_pinned():
    assert VECTORS["public_key"] not in PINNED.values()
    assert "test" not in PINNED


@pytest.mark.parametrize("env", VECTORS["valid"])
def test_vectors_verify(env):
    msg = verify(env, TEST_KEYS)
    assert msg == json.loads(env["payload"])


def test_vectors_fail_with_pinned_key():
    assert all(verify(e) is None for e in VECTORS["valid"])  # kid "test" is not pinned
    env = dict(VECTORS["valid"][0], kid="k1")
    assert verify(env) is None  # and the test signature is not valid for the real key


def test_tampered_and_wrong_key(signer):
    assert verify(VECTORS["tampered"], TEST_KEYS) is None
    assert verify(VECTORS["valid"][0], {"test": next(iter(signer.keys.values()))}) is None


@pytest.mark.parametrize("bad", [None, [], {}, {"payload": "{}", "sig": "!!", "kid": "test"},
                                 {"payload": 1, "sig": "", "kid": "test"}])
def test_garbage_envelopes(bad):
    assert verify(bad, TEST_KEYS) is None


def test_guard_sequence_replay_and_restart(tmp_path):
    g = Guard(tmp_path / "guard.json", TEST_KEYS)
    v = VECTORS["valid"]
    assert [g.accept(e, 1010.0)["seq"] for e in v] == [1, 2, 3]
    assert g.accept(v[0], 1010.0) is None and "replay" in g.why
    g2 = Guard(tmp_path / "guard.json", TEST_KEYS)  # restart: the last time stamp comes from disk
    assert g2.accept(v[2], 1010.0) is None


def test_guard_time_checks(tmp_path, signer):
    g = Guard(tmp_path / "g.json", signer.keys)
    assert g.accept(signer.envelope(payload(seq=1)), 1060.0) is None and g.why == "expired"
    assert g.accept(signer.envelope(payload(seq=2, ts=1100.0, expires=1160.0)), 1069.0) is None
    assert "future" in g.why
    assert g.accept(signer.envelope(payload(seq=3, ts=1100.0, expires=1160.0)), 1070.0)  # 30 s ahead is fine


@pytest.mark.parametrize("life,ok", [(60.0, True), (59.0, True), (60.5, False), (61.0, False), (120.0, False)])
def test_lifetime_is_at_most_60_s_as_the_protocol_says(tmp_path, signer, life, ok):
    g = Guard(tmp_path / "g.json", signer.keys)
    ts = 1795605183.449  # real-looking times: the difference of two such floats is not exactly 60
    msg = g.accept(signer.envelope(payload(ts=ts, expires=round(ts + life, 3))), ts + 1)
    assert bool(msg) == ok and (ok or "shape" in g.why)


def test_unknown_version_dropped(tmp_path, signer):
    g = Guard(tmp_path / "g.json", signer.keys)
    assert g.accept(signer.envelope(payload(v=3)), 1010.0) is None and g.why == "unknown protocol version"
    assert g.accept(signer.envelope(payload(v=True)), 1010.0) is None
    assert g.accept(signer.envelope(payload(v=2.5)), 1010.0) is None


def test_a_version_1_message_is_refused_in_plain_words(tmp_path):
    """/v1/signal is still served for agents 0.4.x and 0.5.0; this agent reads version 2 and says so."""
    g = Guard(tmp_path / "g.json", TEST_KEYS)
    for env in VECTORS["v1"]:
        assert verify(env, TEST_KEYS)["v"] == 1  # correctly signed ...
        assert g.accept(env, 1010.0) is None  # ... and still refused
        assert g.why == "a version 1 message: this agent reads version 2 of the signal (/v2/signal)"
    assert g.last_ts == 0.0


def test_a_version_1_shape_under_v2_is_refused(tmp_path, signer):
    g = Guard(tmp_path / "g.json", signer.keys)
    assert g.accept(signer.envelope(payload_v1(v=2)), 1010.0) is None and "shape" in g.why


def test_the_v2_vector_cleans_to_the_known_fields():
    msg = clean(verify(VECTORS["valid"][0], TEST_KEYS))
    assert list(msg["targets"]) == list(COINS)
    assert msg["targets"]["LIT"] == {"x": 0.021, "px": 2.59, "trend": {"x": 0.021, "score": 13}}
    assert msg["scalps"] == [{"coin": "BTC", "x": -1.2, "tp": 59400.0, "sl": 60420.0, "id": 7, "score": 12}]  # no lev
    assert msg["v"] == 2 and "scalp" not in msg


def _mut(path, value):
    p = payload()
    obj = p
    for k in path[:-1]:
        obj = obj[k]
    obj[path[-1]] = value
    return p


def _both(**kw):
    """A payload whose BTC scalp is given in full (its trend part stays as payload() made it)."""
    p = payload()
    p["scalps"][0].update(kw)
    return p


def _two_btc():
    p = payload()
    p["scalps"].append(dict(p["scalps"][0], id=8))
    return p


MALFORMED = [
    _mut(["seq"], "1"), _mut(["seq"], True), _mut(["seq"], -1), _mut(["rev"], 1.5),
    _mut(["expires"], 999.0), _mut(["expires"], 5000.0), _mut(["state"], "short"), _mut(["source"], "x"),
    _mut(["targets", "BTC", "x"], 51.0), _mut(["targets", "BTC", "x"], "1"), _mut(["targets", "BTC", "px"], 0),
    _mut(["targets", "BTC", "px"], -5.0), _mut(["targets"], {"DOGE": {"x": 1, "px": 1}}), _mut(["targets"], []),
    _mut(["targets"], {}), _mut(["scalps", 0, "coin"], "SOL"), _mut(["scalps", 0, "x"], 1.2),
    _mut(["scalps", 0, "x"], -2.0), _mut(["scalps", 0, "x"], 0), _mut(["scalps", 0, "tp"], None),
    _mut(["scalps", 0, "sl"], -1.0), _mut(["scalps", 0, "id"], "7"), _mut(["scalps"], {}), _mut(["scalps"], None),
    _mut(["why"], 5), _mut(["why"], "x" * 2001),
    # version 2: trend parts, scores, one scalp per coin
    _mut(["targets", "BTC", "trend"], None), _mut(["targets", "BTC", "trend", "x"], "-0.6"),
    _mut(["targets", "BTC", "trend", "x"], -0.7),  # trend.x must be x less the scalp's x, within 0.001
    _mut(["targets", "ETH", "trend", "x"], -0.398),
    _mut(["targets", "BTC", "trend", "score"], 101), _mut(["targets", "BTC", "trend", "score"], -1),
    _mut(["targets", "BTC", "trend", "score"], 9.5), _mut(["targets", "BTC", "trend", "score"], True),
    _mut(["targets", "BTC", "trend", "score"], "9"), _mut(["targets", "BTC", "trend", "score"], None),
    _mut(["scalps", 0, "score"], 101), _mut(["scalps", 0, "score"], 12.0), _mut(["scalps", 0, "score"], None),
    _mut(["targets", "HYPE"], {"x": 0.0, "px": 30.0, "trend": {"x": 0.0, "score": 4}}),  # x == 0 has score 0
    _two_btc(),  # at most one scalp per coin
    _mut(["scalps", 0, "coin"], "LIT"),  # each scalp's coin is in targets
    _both(x=-1.8000011),  # |x| at most the coin's |x| + 1e-6
]


def test_a_scalp_its_coin_and_its_trend_part_must_add_up(tmp_path, signer):
    g = Guard(tmp_path / "g.json", signer.keys)
    p = payload(targets={"BTC": {"x": -1.8, "px": 60000.0, "trend": {"x": -0.6004, "score": 9}}})
    assert g.accept(signer.envelope(p), 1010.0)  # within 0.001 of x less its scalp
    p = payload(seq=2, ts=1001.0, scalp=None, targets={"BTC": {"x": -1.8, "px": 60000.0,
                                                               "trend": {"x": -0.6, "score": 9}}})
    assert g.accept(signer.envelope(p), 1010.0) is None  # no scalp: the trend part is the whole position


def test_four_coins_with_a_scalp_each(tmp_path, signer):
    g = Guard(tmp_path / "g.json", signer.keys)
    targets = {"BTC": {"x": -1.0, "px": 90000.0}, "ETH": {"x": 0.5, "px": 3000.0}, "HYPE": {"x": -0.3, "px": 34.0},
               "LIT": {"x": 0.2, "px": 2.5}}
    scalps = [{"coin": c, "x": t["x"] / 2, "tp": t["px"] * (0.99 if t["x"] < 0 else 1.01),
               "sl": t["px"] * (1.01 if t["x"] < 0 else 0.99), "id": i, "score": 5} for i, (c, t) in
              enumerate(targets.items())]
    msg = g.accept(signer.envelope(payload(targets=targets, scalps=scalps)), 1010.0)
    assert [s["coin"] for s in msg["scalps"]] == list(COINS) and msg["targets"]["LIT"]["trend"]["x"] == 0.1


@pytest.mark.parametrize("bad", MALFORMED)
def test_signed_but_malformed_is_dropped(tmp_path, signer, bad):
    g = Guard(tmp_path / "g.json", signer.keys)
    assert g.accept(signer.envelope(bad), 1010.0) is None
    assert g.last_ts == 0.0  # nothing was remembered


def test_nan_and_infinity_rejected(tmp_path, signer):
    g = Guard(tmp_path / "g.json", signer.keys)
    text = json.dumps(payload()).replace("-1.8", "NaN")
    assert g.accept(signer.envelope(text), 1010.0) is None
    text = json.dumps(payload()).replace("-1.8", "-Infinity")
    assert g.accept(signer.envelope(text), 1010.0) is None


def test_offline_with_empty_targets_ok(tmp_path, signer):
    g = Guard(tmp_path / "g.json", signer.keys)
    msg = g.accept(signer.envelope(payload(state="offline", targets={}, scalps=[])), 1010.0)
    assert msg and msg["state"] == "offline"


def test_extra_fields_dropped_and_control_chars_removed(tmp_path, signer):
    g = Guard(tmp_path / "g.json", signer.keys)
    msg = g.accept(signer.envelope(payload(extra="x", why="a\x1b[31mb")), 1010.0)
    assert "extra" not in msg and msg["why"] == "a[31mb"


def test_seq_restart_is_accepted_when_ts_is_newer(tmp_path, signer):
    g = Guard(tmp_path / "g.json", signer.keys)   # the signer was rebuilt: seq starts again, time does not
    assert g.accept(signer.envelope(payload(seq=900, ts=1000.0, expires=1060.0)), 1010.0)
    assert g.accept(signer.envelope(payload(seq=1, ts=1005.0, expires=1065.0)), 1010.0)
    assert g.accept(signer.envelope(payload(seq=2, ts=1004.0, expires=1064.0)), 1010.0) is None and "replay" in g.why

import json

import pytest

from conftest import TEST_KEYS, VECTORS, payload
from fuze.protocol import PINNED, Guard, verify


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
    g2 = Guard(tmp_path / "guard.json", TEST_KEYS)  # restart: the last seq comes from disk
    assert g2.accept(v[2], 1010.0) is None


def test_guard_time_checks(tmp_path, signer):
    g = Guard(tmp_path / "g.json", signer.keys)
    assert g.accept(signer.envelope(payload(seq=1)), 1060.0) is None and g.why == "expired"
    assert g.accept(signer.envelope(payload(seq=2, ts=1100.0, expires=1160.0)), 1069.0) is None
    assert "future" in g.why
    assert g.accept(signer.envelope(payload(seq=3, ts=1100.0, expires=1160.0)), 1070.0)  # 30 s ahead is fine


def test_unknown_version_dropped(tmp_path, signer):
    g = Guard(tmp_path / "g.json", signer.keys)
    assert g.accept(signer.envelope(payload(v=2)), 1010.0) is None and "version" in g.why
    assert g.accept(signer.envelope(payload(v=True)), 1010.0) is None


def _mut(path, value):
    p = payload()
    obj = p
    for k in path[:-1]:
        obj = obj[k]
    obj[path[-1]] = value
    return p


MALFORMED = [
    _mut(["seq"], "1"), _mut(["seq"], True), _mut(["seq"], -1), _mut(["rev"], 1.5),
    _mut(["expires"], 999.0), _mut(["expires"], 5000.0), _mut(["state"], "short"), _mut(["source"], "x"),
    _mut(["targets", "BTC", "x"], 51.0), _mut(["targets", "BTC", "x"], "1"), _mut(["targets", "BTC", "px"], 0),
    _mut(["targets", "BTC", "px"], -5.0), _mut(["targets"], {"DOGE": {"x": 1, "px": 1}}), _mut(["targets"], []),
    _mut(["targets"], {}), _mut(["scalp", "coin"], "SOL"), _mut(["scalp", "x"], 1.2), _mut(["scalp", "x"], -2.0),
    _mut(["scalp", "x"], 0), _mut(["scalp", "tp"], None), _mut(["scalp", "id"], "7"), _mut(["scalp"], []),
    _mut(["why"], 5), _mut(["why"], "x" * 2001),
]


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
    msg = g.accept(signer.envelope(payload(state="offline", targets={}, scalp=None)), 1010.0)
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

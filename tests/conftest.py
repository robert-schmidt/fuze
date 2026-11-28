import base64
import json
from pathlib import Path

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

VECTORS = json.loads((Path(__file__).parent / "vectors.json").read_text())
TEST_KEYS = {"test": VECTORS["public_key"]}


@pytest.fixture(autouse=True)
def fuze_home(tmp_path, monkeypatch):
    home = tmp_path / "fuze"
    monkeypatch.setenv("FUZE_HOME", str(home))
    return home


OPEN_RECORD = {"proven": {"won": 3, "n": 5, "open": True}}


@pytest.fixture(autouse=True)
def fuze_record(monkeypatch):
    """FUZE's public record, as modes.real_money reads it: open unless a test says otherwise. No test reads the network;
    a test sets `record["doc"]` to another answer, or to an exception to raise."""
    from fuze import modes
    record = {"doc": OPEN_RECORD, "asked": [], "real": modes.fetch_record}

    def fetch(server, timeout=5.0):
        record["asked"].append(server)
        if isinstance(record["doc"], Exception):
            raise record["doc"]
        return record["doc"]

    monkeypatch.setattr(modes, "fetch_record", fetch)
    return record


class Signer:
    """A key made inside the test, never published."""

    def __init__(self, kid="t"):
        self.kid, self.sk = kid, Ed25519PrivateKey.generate()
        pub = self.sk.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)
        self.keys = {kid: base64.b64encode(pub).decode()}

    def envelope(self, payload) -> dict:
        text = payload if isinstance(payload, str) else json.dumps(payload)
        return {"payload": text, "sig": base64.b64encode(self.sk.sign(text.encode())).decode(), "kid": self.kid}


@pytest.fixture
def signer():
    return Signer()


TREND_SCORE = 10  # the score payload() gives a trend part it fills in


def payload(**kw) -> dict:
    """A version 2 payload. Shortcuts for tests: `scalp=` (one scalp or None) becomes `scalps`, a scalp without a score
    gets round(10.3 x |x|), and a target without `trend` gets the trend part the contract asks for (x less its scalp's
    x, score TREND_SCORE, or 0 when that is 0). Anything given in full is left as it is."""
    p = {"v": 2, "seq": 1, "rev": 1, "ts": 1000.0, "expires": 1060.0, "source": "paper", "state": "live",
         "targets": {"BTC": {"x": -1.8, "px": 60000.0}, "ETH": {"x": -0.4, "px": 2000.0}},
         "scalps": [{"coin": "BTC", "x": -1.2, "tp": 59400.0, "sl": 60420.0, "id": 7}], "why": "test"}
    if "scalp" in kw:
        sc = kw.pop("scalp")
        kw["scalps"] = [sc] if sc else []
    p.update(kw)
    if isinstance(p.get("scalps"), list):
        p["scalps"] = [dict(sc, score=round(10.3 * abs(sc["x"]))) if isinstance(sc, dict) and "score" not in sc
                       and isinstance(sc.get("x"), (int, float)) else sc for sc in p["scalps"]]
    if isinstance(p.get("targets"), dict):
        sx = {sc.get("coin"): sc.get("x") for sc in p.get("scalps") or [] if isinstance(sc, dict)}
        p["targets"] = {c: dict(t, trend=(lambda x: {"x": x, "score": TREND_SCORE if x else 0})(
                            round(t["x"] - (sx.get(c) or 0.0), 10)))
                        if isinstance(t, dict) and "trend" not in t and isinstance(t.get("x"), (int, float))
                        and isinstance(sx.get(c) or 0.0, (int, float)) else t
                        for c, t in p["targets"].items()}
    return p


def payload_v1(**kw) -> dict:
    """A version 1 payload, as /v1/signal serves it for agents 0.4.x and 0.5.0."""
    p = {"v": 1, "seq": 1, "rev": 1, "ts": 1000.0, "expires": 1060.0, "source": "paper", "state": "live",
         "targets": {"BTC": {"x": -1.8, "px": 60000.0}, "ETH": {"x": -0.4, "px": 2000.0}},
         "scalp": {"coin": "BTC", "x": -1.2, "tp": 59400.0, "sl": 60420.0, "id": 7}, "why": "test"}
    p.update(kw)
    return p

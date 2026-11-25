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


def payload(**kw) -> dict:
    p = {"v": 1, "seq": 1, "rev": 1, "ts": 1000.0, "expires": 1060.0, "source": "paper", "state": "live",
         "targets": {"BTC": {"x": -1.8, "px": 60000.0}, "ETH": {"x": -0.4, "px": 2000.0}},
         "scalp": {"coin": "BTC", "x": -1.2, "tp": 59400.0, "sl": 60420.0, "id": 7}, "why": "test"}
    p.update(kw)
    return p

"""FUZE signal protocol v1: verify, check and validate envelopes (see docs/PROTOCOL.md)."""

from __future__ import annotations

import base64
import binascii
import json
import math
from pathlib import Path

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from fuze.config import read_json, write_json

# The only keys this release trusts. A new key arrives in a release, never over the network.
PINNED = {"k1": "4YwkvSXI90nvycvuDte8h9N1ULf00v+PM95Yj3+8iNU="}

COINS = ("BTC", "ETH")
STATES = ("live", "flat", "offline")
SOURCES = ("paper", "testnet", "mainnet")
MAX_PAYLOAD = 16_384  # bytes; a real payload is well under 1 KB
MAX_X = 50.0
MAX_FUTURE_S = 30.0
MAX_LIFETIME_S = 60.0  # PROTOCOL.md: a message is valid until `expires`, 60 s after `ts`; a longer life is dropped
LIFETIME_SLACK_S = 0.001  # float rounding of two unix times with milliseconds


def _b64(text) -> bytes | None:
    try:
        return base64.b64decode(text, validate=True)
    except (binascii.Error, ValueError, TypeError):
        return None


def verify(envelope, keys=PINNED) -> dict | None:
    """Check the signature over the payload TEXT with a pinned key, then parse. None if anything is wrong."""
    if not isinstance(envelope, dict):
        return None
    payload, sig, kid = envelope.get("payload"), envelope.get("sig"), envelope.get("kid")
    if not (isinstance(payload, str) and isinstance(sig, str) and isinstance(kid, str)) or kid not in keys:
        return None
    data = payload.encode("utf-8")
    raw_sig, raw_key = _b64(sig), _b64(keys[kid])
    if len(data) > MAX_PAYLOAD or raw_sig is None or len(raw_sig) != 64 or raw_key is None or len(raw_key) != 32:
        return None
    try:
        Ed25519PublicKey.from_public_bytes(raw_key).verify(raw_sig, data)
        msg = json.loads(payload, parse_constant=lambda c: None)  # NaN/Infinity become None, then fail below
    except (InvalidSignature, ValueError):
        return None
    return msg if isinstance(msg, dict) else None


def _num(v, lo=-math.inf, hi=math.inf) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v) and lo <= v <= hi


def _int(v) -> bool:
    return isinstance(v, int) and not isinstance(v, bool) and 0 <= v < 2**53


def _price(v) -> bool:
    return _num(v, 0.0, 1e9) and v > 0


def clean(msg: dict) -> dict | None:
    """Strict shape check of a verified v1 payload. Returns only the known fields, or None."""
    if not (_int(msg.get("seq")) and _int(msg.get("rev"))):
        return None
    ts, exp = msg.get("ts"), msg.get("expires")
    if not (_num(ts, 0) and _num(exp, 0) and 0 < exp - ts <= MAX_LIFETIME_S + LIFETIME_SLACK_S):
        return None
    if msg.get("source") not in SOURCES or msg.get("state") not in STATES:
        return None
    why = msg.get("why", "")
    if not isinstance(why, str) or len(why) > 2000:
        return None
    targets = msg.get("targets")
    if not isinstance(targets, dict) or any(c not in COINS for c in targets):
        return None
    out_t = {}
    for coin, t in targets.items():
        if not (isinstance(t, dict) and _num(t.get("x"), -MAX_X, MAX_X) and _price(t.get("px"))):
            return None
        out_t[coin] = {"x": float(t["x"]), "px": float(t["px"])}
    if msg["state"] == "live" and not out_t:
        return None
    scalp = msg.get("scalp")
    if scalp is not None:
        if not isinstance(scalp, dict) or scalp.get("coin") not in out_t:
            return None
        x, whole = scalp.get("x"), out_t[scalp["coin"]]["x"]
        if not (_num(x, -MAX_X, MAX_X) and x != 0 and _price(scalp.get("tp")) and _price(scalp.get("sl"))
                and _int(scalp.get("id"))):
            return None
        if x * whole <= 0 or abs(x) > abs(whole) + 1e-6:  # the scalp is part of the coin's position
            return None
        scalp = {"coin": scalp["coin"], "x": float(x), "tp": float(scalp["tp"]), "sl": float(scalp["sl"]),
                 "id": scalp["id"]}
    why = "".join(ch for ch in why if ch.isprintable())
    return {"v": 1, "seq": msg["seq"], "rev": msg["rev"], "ts": float(ts), "expires": float(exp),
            "source": msg["source"], "state": msg["state"], "targets": out_t, "scalp": scalp, "why": why}


class Guard:
    """Applies PROTOCOL.md's checks in order and remembers the last accepted time stamp on disk."""

    def __init__(self, path: Path, keys=PINNED):
        self.path, self.keys = Path(path), keys
        last = (read_json(self.path, {}) or {}).get("ts", 0.0)
        self.last_ts = float(last) if _num(last, 0) else 0.0
        self.why = ""  # why the last envelope was dropped, in plain words

    def _drop(self, why: str) -> None:
        self.why = why
        return None

    def accept(self, envelope, now: float) -> dict | None:
        msg = verify(envelope, self.keys)  # 1. pinned key, signature
        if msg is None:
            return self._drop("bad or unknown signature")
        if msg.get("v") != 1 or isinstance(msg.get("v"), bool):  # 2. version
            return self._drop("unknown protocol version")
        msg = clean(msg)  # signed but malformed is still dropped
        if msg is None:
            return self._drop("signed message with a bad shape")
        if msg["ts"] <= self.last_ts:  # 3. replay: time stamps only move forward
            return self._drop("not newer than the last accepted message (replay)")
        if not now < msg["expires"]:  # 4. time
            return self._drop("expired")
        if msg["ts"] > now + MAX_FUTURE_S:
            return self._drop("time stamp in the future")
        write_json(self.path, {"ts": msg["ts"]})
        self.last_ts, self.why = msg["ts"], ""
        return msg

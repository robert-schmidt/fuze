"""The Lighter API key, one per network. Typed by the user at a terminal (`fuze keys`), never anywhere else.

Kept in the OS keyring when the optional `keyring` package has a working backend, otherwise in a file readable by the
owner only (0600) in the FUZE folder. Set FUZE_NO_KEYRING=1 to use the file (a server without a desktop keyring).
Never printed, logged, written to status.json, returned by the MCP server or taken as a command-line argument.
The MCP server never imports this module's `load`: it only sees "set" or "missing".
"""

from __future__ import annotations

import os
import re

from fuze import config

SERVICE = "fuze-agent"
SHAPE = re.compile(r"(?:0x)?[0-9a-fA-F]{32,200}")


def _keyring():
    """The keyring module when it has a real backend, else None."""
    if os.environ.get("FUZE_NO_KEYRING"):
        return None
    try:
        import keyring
        from keyring.backends import fail
        return None if isinstance(keyring.get_keyring(), fail.Keyring) else keyring
    except Exception:  # not installed, or no usable backend
        return None


def _file(net: str):
    return config.home() / f"lighter-{net}.key"


def _where() -> dict:
    return config.read_json(config.home() / "keys.json", {}) or {}


def clean(text: str) -> str:
    """The key without spaces or 0x, or ValueError (whose text never contains the key)."""
    text = (text or "").strip()
    if not SHAPE.fullmatch(text):
        raise ValueError("that is not a Lighter API private key (expected a long hexadecimal text). Nothing was saved.")
    return text.removeprefix("0x")


def save(net: str, secret: str) -> str:
    """Store the key for `net`; returns where ("the OS keyring" or the file path)."""
    secret = clean(secret)
    home = config.ensure_home()
    where = "file"
    kr = _keyring()
    if kr:
        try:
            kr.set_password(SERVICE, f"lighter-{net}", secret)
            where = "keyring"
            _file(net).unlink(missing_ok=True)
        except Exception:
            where = "file"
    if where == "file":
        config.atomic_write(_file(net), secret)
    config.write_json(home / "keys.json", {**_where(), net: where})
    return "the OS keyring" if where == "keyring" else str(_file(net))


def load(net: str) -> str | None:
    """The key, for the agent's own use only. Never pass it to anything that prints, logs or returns it."""
    if _where().get(net) == "keyring":
        kr = _keyring()
        try:
            return kr.get_password(SERVICE, f"lighter-{net}") if kr else None
        except Exception:
            return None
    try:
        return _file(net).read_text(encoding="utf-8").strip() or None
    except OSError:
        return None


def state(net: str) -> str:
    """ "set" or "missing", without reading the key itself."""
    where = _where().get(net)
    if where == "keyring":
        return "set"
    return "set" if where == "file" and _file(net).is_file() else "missing"


def delete(net: str) -> None:
    kr = _keyring()
    if kr and _where().get(net) == "keyring":
        try:
            kr.delete_password(SERVICE, f"lighter-{net}")
        except Exception:
            pass
    _file(net).unlink(missing_ok=True)
    w = _where()
    w.pop(net, None)
    config.write_json(config.ensure_home() / "keys.json", w)

"""Local settings in ~/.fuze (or $FUZE_HOME). Nothing here is secret in v0.1."""

from __future__ import annotations

import json
import math
import os
import tempfile
from pathlib import Path
from urllib.parse import urlsplit

DEFAULTS = {
    "server": "https://fuze.trade",
    "mode": "dry",
    "dry_balance": 1000.0,
    "scale": 0.1,
    "max_x": 3.0,
    "daily_loss_frac": 0.1,
    "stale_flat_min": None,
}
RANGES = {"scale": (0.01, 1.0), "max_x": (0.1, 25.0), "daily_loss_frac": (0.01, 0.5),
          "dry_balance": (10.0, 1e9), "stale_flat_min": (1.0, 10080.0)}
LOCAL_HOSTS = ("localhost", "127.0.0.1")
DRY_ONLY = ('Only "dry" mode exists in FUZE v0.1: it follows the signal on a simulated account. '
            "Following on Lighter testnet comes later, and real money only after that.")


def home() -> Path:
    return Path(os.environ.get("FUZE_HOME") or Path.home() / ".fuze")


def ensure_home() -> Path:
    h = home()
    h.mkdir(mode=0o700, parents=True, exist_ok=True)
    os.chmod(h, 0o700)
    return h


def atomic_write(path: Path, text: str) -> None:
    """Write a file in one step (temp file + rename), readable by the owner only."""
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=".tmp-")
    try:
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(text)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise


def write_json(path: Path, data) -> None:
    atomic_write(path, json.dumps(data, indent=1, sort_keys=True))


def read_json(path: Path, default=None):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return default


def check_server(url) -> str:
    if not isinstance(url, str):
        raise ValueError("server must be text")
    u = urlsplit(url)
    local = u.hostname in LOCAL_HOSTS
    if u.scheme != "https" and not (u.scheme == "http" and local):
        raise ValueError("server must use https (plain http is allowed only for localhost)")
    if not u.hostname or u.username or u.password or u.query or u.fragment or u.path not in ("", "/"):
        raise ValueError("server must be a bare address such as https://fuze.trade")
    return url.rstrip("/")


def _number(name, value) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(f"{name} must be a number")
    lo, hi = RANGES[name]
    if not lo <= value <= hi:
        raise ValueError(f"{name} must be between {lo:g} and {hi:g}")
    return float(value)


def validate(cfg) -> dict:
    if not isinstance(cfg, dict):
        raise ValueError("config must be a JSON object")
    unknown = set(cfg) - set(DEFAULTS)
    if unknown:
        raise ValueError(f"unknown config fields: {', '.join(sorted(unknown))}")
    out = {**DEFAULTS, **cfg}
    out["server"] = check_server(out["server"])
    if out["mode"] != "dry":
        raise ValueError(DRY_ONLY)
    for name in ("dry_balance", "scale", "max_x", "daily_loss_frac"):
        out[name] = _number(name, out[name])
    if out["stale_flat_min"] is not None:
        out["stale_flat_min"] = _number("stale_flat_min", out["stale_flat_min"])
    return out


def load() -> dict:
    return validate(read_json(home() / "config.json", {}))


def save(cfg) -> dict:
    cfg = validate(cfg)
    write_json(ensure_home() / "config.json", cfg)
    return cfg

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
    "size_mode": "percent",  # "percent": a share of the balance follows the signal; "fixed": a fixed amount does
    "percent": 10.0,
    "fixed_usd": 100.0,
    "max_position_usd": None,
    "max_x": 3.0,
    "daily_loss_frac": 0.1,
    "stale_flat_min": None,
}
RANGES = {"percent": (1.0, 100.0), "fixed_usd": (10.0, 1e6), "max_position_usd": (10.0, 1e6),
          "max_x": (0.1, 25.0), "daily_loss_frac": (0.01, 0.5), "dry_balance": (10.0, 1e9),
          "stale_flat_min": (1.0, 10080.0)}
SIZE_MODES = ("percent", "fixed")
LIMITS = ("size_mode", "percent", "fixed_usd", "max_position_usd", "max_x", "daily_loss_frac", "stale_flat_min")
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
    if "scale" in cfg:  # files written before sizing modes: scale 0.1 meant 10% of the balance
        cfg = dict(cfg)
        scale = cfg.pop("scale")
        if isinstance(scale, bool) or not isinstance(scale, (int, float)):
            raise ValueError("scale must be a number")
        cfg.setdefault("percent", round(scale * 100, 6))
    unknown = set(cfg) - set(DEFAULTS)
    if unknown:
        raise ValueError(f"unknown config fields: {', '.join(sorted(unknown))}")
    out = {**DEFAULTS, **cfg}
    out["server"] = check_server(out["server"])
    if out["mode"] != "dry":
        raise ValueError(DRY_ONLY)
    if out["size_mode"] not in SIZE_MODES:
        raise ValueError('size_mode must be "percent" (a share of your balance) or "fixed" (a fixed amount)')
    for name in ("dry_balance", "percent", "fixed_usd", "max_x", "daily_loss_frac"):
        out[name] = _number(name, out[name])
    for name in ("max_position_usd", "stale_flat_min"):
        if out[name] is not None:
            out[name] = _number(name, out[name])
    return out


def load() -> dict:
    return validate(read_json(home() / "config.json", {}))


def save(cfg) -> dict:
    cfg = validate(cfg)
    write_json(ensure_home() / "config.json", cfg)
    return cfg


def current_balance(cfg) -> float:
    """The balance the agent last reported, or the simulated starting balance if it has not run yet."""
    try:
        bal = ((read_json(home() / "status.json") or {}).get("account") or {}).get("balance")
    except (ValueError, OSError, AttributeError):
        bal = None
    ok = isinstance(bal, (int, float)) and not isinstance(bal, bool) and math.isfinite(bal) and bal > 0
    return float(bal) if ok else cfg["dry_balance"]

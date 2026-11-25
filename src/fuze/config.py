"""Local settings in ~/.fuze (or $FUZE_HOME). Nothing in config.json is secret: the API key is kept apart (keys.py)."""

from __future__ import annotations

import json
import math
import os
import tempfile
from pathlib import Path
from urllib.parse import urlsplit

DEFAULTS = {
    "server": "https://fuze.trade",
    "mode": "simulation",  # "simulation" (no money), "testnet" (Lighter, test money), "mainnet" (Lighter, real money)
    "dry_balance": 1000.0,
    "size_mode": "percent",  # "percent": a share of the balance follows the signal; "fixed": a fixed amount does
    "percent": 10.0,
    "fixed_usd": 100.0,
    "max_position_usd": None,
    "max_x": 3.0,
    "daily_loss_frac": 0.1,
    "stale_flat_min": None,
    "testnet_account": None,  # Lighter account index (public: it is in the explorer's address); set with `fuze keys`
    "testnet_key_index": 4,  # the API key's index on that account; Lighter keeps 0 to 3 for its own apps
    "mainnet_account": None,
    "mainnet_key_index": 4,
}
RANGES = {"percent": (1.0, 100.0), "fixed_usd": (10.0, 1e6), "max_position_usd": (10.0, 1e6),
          "max_x": (0.1, 25.0), "daily_loss_frac": (0.01, 0.5), "dry_balance": (10.0, 1e9),
          "stale_flat_min": (1.0, 10080.0)}
SIZE_MODES = ("percent", "fixed")
LIMITS = ("size_mode", "percent", "fixed_usd", "max_position_usd", "max_x", "daily_loss_frac", "stale_flat_min")
LOCAL_HOSTS = ("localhost", "127.0.0.1")
MODES = ("simulation", "testnet", "mainnet")  # in order of how real the money is
NETS = ("testnet", "mainnet")


def home() -> Path:
    return Path(os.environ.get("FUZE_HOME") or Path.home() / ".fuze")


def no_agent_here() -> str:
    """Empty when this FUZE folder has a config.json; otherwise why nothing here can reach an agent, in plain words."""
    h = home()
    if (h / "config.json").is_file():
        return ""
    how = ("FUZE_HOME is set to it" if os.environ.get("FUZE_HOME") else
           "FUZE_HOME is not set, so the default folder is used")
    return (f"No FUZE agent is set up in {h} (there is no config.json there; {how}). An agent you run uses the folder "
            "of the terminal it was started from. If this is an AI tool's MCP server, point it at the right folder: "
            "run `fuze mcp-config` in that terminal and paste what it prints into the tool's MCP settings, then "
            "restart the tool. If FUZE is not set up yet, run `fuze init`.")


def pip_hint(extra: str) -> str:
    """How to add an optional part. FUZE is not on PyPI yet: install from the repository checkout, never by name."""
    import sys
    return (f"in your FUZE checkout run: {sys.executable} -m pip install '.[{extra}]' (FUZE is not on PyPI yet; a "
            "package named fuze-agent there today is not ours)")


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


def plain_number(v: float) -> str:
    """1000000 as 1,000,000 (never 1e+06), 0.01 as 0.01."""
    return f"{v:,.0f}" if float(v).is_integer() else f"{v:,g}"


def _number(name, value) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(f"{name} must be a number")
    lo, hi = RANGES[name]
    if not lo <= value <= hi:
        raise ValueError(f"{name} must be between {plain_number(lo)} and {plain_number(hi)}")
    return float(value)


def _whole(v) -> bool:
    return isinstance(v, int) and not isinstance(v, bool)


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
    if out["mode"] == "dry":  # the name before testnet and mainnet existed
        out["mode"] = "simulation"
    if out["mode"] not in MODES:
        raise ValueError('mode must be "simulation", "testnet" or "mainnet"')
    for net in NETS:
        acct, idx = out[f"{net}_account"], out[f"{net}_key_index"]
        if acct is not None and not (_whole(acct) and 0 <= acct < 2**48):
            raise ValueError(f"{net}_account must be a whole number (your Lighter account index)")
        if not (_whole(idx) and 4 <= idx <= 254):
            raise ValueError(f"{net}_key_index must be a whole number from 4 to 254 "
                             "(Lighter keeps 0 to 3 for its own apps)")
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

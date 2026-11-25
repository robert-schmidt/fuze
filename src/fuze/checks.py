"""`fuze check` and the MCP setup_check tool: a read-only look at the local setup."""

from __future__ import annotations

import stat
import sys
import time

from fuze import config
from fuze.protocol import PINNED


def setup_report() -> list:
    """List of {"ok": bool, "check": str, "detail": str}."""
    out = []

    def add(ok, check, detail=""):
        out.append({"ok": bool(ok), "check": check, "detail": detail})

    h = config.home()
    add(sys.version_info >= (3, 10), "Python 3.10 or newer", sys.version.split()[0])
    add(h.is_dir(), "FUZE folder exists", str(h) if h.is_dir() else "run `fuze init`")
    if h.is_dir():
        mode = stat.S_IMODE(h.stat().st_mode)
        add(mode & 0o077 == 0, "FUZE folder is private to you", oct(mode))
    cfg_path = h / "config.json"
    if cfg_path.exists():
        mode = stat.S_IMODE(cfg_path.stat().st_mode)
        add(mode & 0o077 == 0, "config.json is private to you", oct(mode))
    try:
        cfg = config.load()
        add(True, "config.json is valid", f"mode {cfg['mode']}, scale {cfg['scale']:g}, cap {cfg['max_x']:g}x, "
                                          f"daily loss stop {cfg['daily_loss_frac']:.0%}")
    except (ValueError, OSError) as e:
        add(False, "config.json is valid", str(e))
    add(set(PINNED) == {"k1"}, "Signal key pinned in the code", ", ".join(PINNED))
    s = config.read_json(h / "status.json") or {}
    age = time.time() - s.get("t", 0)
    add(age < 30, "Agent is running", f"last step {age:.0f} s ago" if s else "start it with `fuze run`")
    for flag in ("PAUSE", "FLATTEN"):
        if (h / flag).exists():
            add(True, f"{flag} is on", "undo in a terminal: `fuze " + ("resume`" if flag == "PAUSE" else "unflatten`"))
    return out

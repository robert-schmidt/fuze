"""`fuze check` and the MCP setup_check tool: a read-only look at the setup. Neither ever sends an order.

The MCP server calls setup_report() without read_account: it never loads the API key. `fuze check` adds one account
read in testnet or mainnet (with the key, in this process only).
"""

from __future__ import annotations

import stat
import sys
import time

from fuze import config, keys, modes
from fuze.protocol import PINNED
from fuze.sizing import fmt


def setup_report(read_account: bool = False) -> list:
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
        cfg = config.load() if cfg_path.exists() else None
        if cfg is None:
            raise ValueError("there is none yet: run `fuze init`")
        fixed = cfg["size_mode"] == "fixed"
        size = f"a fixed ${cfg['fixed_usd']:,.0f}" if fixed else f"{cfg['percent']:g}% of the balance"
        add(True, "config.json is valid", f"mode {cfg['mode']}, {size} follows the signal, "
                                          f"cap per position {fmt('max_position_usd', cfg['max_position_usd'])}, "
                                          f"cap {cfg['max_x']:g}x, daily loss stop {cfg['daily_loss_frac']:.0%}")
    except (ValueError, OSError) as e:
        cfg = None
        add(False, "config.json is valid", str(e))
    if cfg:
        _live(cfg, add, read_account)
    add(set(PINNED) == {"k1"}, "Signal key pinned in the code", ", ".join(PINNED))
    s = config.read_json(h / "status.json") or {}
    if s.get("note"):
        add(True, "What you follow", s["note"])
    age = time.time() - s.get("t", 0)
    add(age < 30, "Agent is running", f"last step {age:.0f} s ago" if s else "start it with `fuze run`")
    for flag in ("PAUSE", "FLATTEN"):
        if (h / flag).exists():
            add(True, f"{flag} is on", "undo in a terminal: `fuze " + ("resume`" if flag == "PAUSE" else "unflatten`"))
    return out


def _live(cfg, add, read_account: bool) -> None:
    """The live prerequisites for the configured mode, and (fuze check only) one account read. No order."""
    mode = cfg["mode"]
    add(True, "Mode", modes.NAMES[mode])
    if mode == "simulation":  # the testnet key is set and rehearsed from simulation: check it once it is stored
        if cfg["testnet_account"] is None or keys.state("testnet") != "set":
            return
        mode = "testnet"
    from fuze.venue import account_link
    problems = modes.blockers(cfg, mode)
    add(not any("SDK" in p for p in problems), "Lighter SDK installed", config.pip_hint("mcp,lighter")
        if any("SDK" in p for p in problems) else "")
    acct = cfg[f"{mode}_account"]
    add(acct is not None, f"Lighter {mode} account index set",
        account_link(mode, acct) if acct is not None else f"run `fuze keys {mode}`")
    st = keys.state(mode)
    add(st == "set", f"Lighter {mode} API key", st if st == "set" else f"missing: run `fuze keys {mode}`")
    f = config.home() / f"lighter-{mode}.key"
    if f.exists():
        m = stat.S_IMODE(f.stat().st_mode)
        add(m & 0o077 == 0, "Key file is private to you", oct(m))
    if mode == "mainnet":
        why = modes.rehearsal_problem()
        add(not why, "Testnet rehearsal passed on this machine with this version", why)
    if not read_account or problems:
        return
    try:
        from fuze.venue import open_venue
        ex = open_venue({**cfg, "mode": mode}, config.home())
        a = ex.account(fresh=True)
        add(True, f"Lighter {mode} account read (no order sent)",
            f"balance ${a['balance']:,.2f}, positions {a['positions'] or 'none'}, "
            f"protected scalp parts {len(a['brackets'])}, emergency stops {len(a.get('guards') or {})}")
    except Exception as e:
        from fuze.agent import _plain
        add(False, f"Lighter {mode} account read (no order sent)", _plain(e))

"""The `fuze` command. Raising a limit, resume and unflatten exist only here, never in the MCP server."""

from __future__ import annotations

import argparse
import json
import sys

from fuze import __version__, config
from fuze.checks import setup_report

LIMITS = ("scale", "max_x", "daily_loss_frac", "stale_flat_min")


def _flag(name: str, on: bool) -> str:
    path = config.ensure_home() / name
    if on:
        path.touch(mode=0o600, exist_ok=True)
    else:
        path.unlink(missing_ok=True)
    return f"{name} is {'on' if on else 'off'}."


def _raises(name: str, new, cur) -> bool:
    if name == "stale_flat_min":  # off (None) is the riskiest setting
        return cur is not None and (new is None or new > cur)
    return new > cur


def cmd_limits(args) -> int:
    cfg = config.load()
    asked = {k: getattr(args, k) for k in LIMITS if getattr(args, k) is not None}
    if not asked:
        print(json.dumps({k: cfg[k] for k in LIMITS}, indent=1))
        return 0
    if "stale_flat_min" in asked:
        asked["stale_flat_min"] = None if asked["stale_flat_min"] == "off" else float(asked["stale_flat_min"])
    new = config.validate({**cfg, **asked})
    up = [k for k in asked if _raises(k, new[k], cfg[k])]
    if up:
        if not sys.stdin.isatty():
            print("Raising a limit needs you at a terminal; refusing because input is not a terminal.")
            return 2
        print("You are RAISING: " + ", ".join(f"{k} {cfg[k]} -> {new[k]}" for k in up))
        print("This lets the agent take more risk with your money.")
        if input("Type RAISE to confirm: ").strip() != "RAISE":
            print("Not changed.")
            return 1
    config.save(new)
    print("Saved: " + ", ".join(f"{k} = {new[k]}" for k in asked))
    return 0


def cmd_run(args) -> int:
    if args.mode != "dry":
        print(config.DRY_ONLY)
        return 2
    import fcntl  # one agent per FUZE folder: two would trade twice

    from fuze.agent import Agent, setup_logging
    config.load()
    lock = open(config.ensure_home() / "agent.lock", "w")
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        print("Another agent is already running on this FUZE folder.")
        return 2
    setup_logging()
    print("FUZE agent (dry run: simulated account, no real money). Ctrl+C to stop.")
    try:
        Agent().run()
    except KeyboardInterrupt:
        print("Stopped. Simulated positions stay as they are.")
    return 0


def cmd_status(args) -> int:
    s = config.read_json(config.home() / "status.json")
    if not s:
        print("No status yet. Start the agent with `fuze run`.")
        return 1
    a, sig = s.get("account", {}), s.get("signal") or {}
    print(f"Mode: {s['mode']} (simulated account)")
    print(f"Balance: ${a.get('balance', 0):,.2f}   Positions: {a.get('positions')}")
    print(f"Signal: revision {sig['rev']}, {sig['state']}: {sig['why']}" if sig else "Signal: none received yet")
    print(f"Agent: {s.get('reason')}")
    print(f"Limits: {s.get('limits')}   Flags: {s.get('flags')}")
    return 0


def cmd_check(args) -> int:
    report = setup_report()
    for r in report:
        print(f"[{'ok' if r['ok'] else 'NO'}] {r['check']}" + (f": {r['detail']}" if r["detail"] else ""))
    return 0 if all(r["ok"] for r in report) else 1


def cmd_init(args) -> int:
    path = config.ensure_home() / "config.json"
    if path.exists():
        print(f"{path} already exists; leaving it as it is.")
    else:
        config.save(dict(config.DEFAULTS))
        print(f"Wrote {path} with safe defaults (dry run, simulated $1,000).")
    print("Next: `fuze run` in its own terminal, then `fuze status`.")
    return 0


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="fuze", description="Follow the FUZE signal (v0.1: dry run only).")
    p.add_argument("--version", action="version", version=__version__)
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("init", help="create ~/.fuze with safe defaults")
    run = sub.add_parser("run", help="run the agent")
    run.add_argument("--mode", default="dry", help='only "dry" exists in v0.1')
    sub.add_parser("status", help="what the agent holds and why")
    for name, text in (("pause", "hold, no new orders"), ("resume", "undo pause"),
                       ("flatten", "close everything and stay out"), ("unflatten", "undo flatten")):
        sub.add_parser(name, help=text)
    lim = sub.add_parser("limits", help="show or change limits (raising asks you to confirm)")
    lim.add_argument("--scale", type=float)
    lim.add_argument("--max-x", dest="max_x", type=float)
    lim.add_argument("--daily-loss", dest="daily_loss_frac", type=float, help="0.1 = 10%%")
    lim.add_argument("--stale-flat-min", dest="stale_flat_min", help='minutes, or "off"')
    sub.add_parser("check", help="check the local setup")
    sub.add_parser("mcp", help="start the MCP server (for AI coding tools)")
    args = p.parse_args(argv)
    try:
        if args.cmd == "mcp":
            try:
                from fuze.mcp_server import main as mcp_main
            except ImportError:
                sys.exit("The MCP server needs one extra package: pip install 'fuze-agent[mcp]'")
            mcp_main()
            return 0
        flags = {"pause": ("PAUSE", True), "resume": ("PAUSE", False),
                 "flatten": ("FLATTEN", True), "unflatten": ("FLATTEN", False)}
        if args.cmd in flags:
            print(_flag(*flags[args.cmd]))
            return 0
        return {"init": cmd_init, "run": cmd_run, "status": cmd_status, "check": cmd_check,
                "limits": cmd_limits}[args.cmd](args)
    except ValueError as e:
        print(f"Error: {e}")
        return 2

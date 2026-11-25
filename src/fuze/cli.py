"""The `fuze` command. Raising risk, resume and unflatten exist only here, never in the MCP server."""

from __future__ import annotations

import argparse
import sys

from fuze import __version__, config
from fuze.checks import setup_report
from fuze.sizing import LABELS, describe, example, fmt, raised


def _flag(name: str, on: bool) -> str:
    path = config.ensure_home() / name
    if on:
        path.touch(mode=0o600, exist_ok=True)
    else:
        path.unlink(missing_ok=True)
    return f"{name} is {'on' if on else 'off'}."


def _num(text: str) -> float:
    try:
        return float(text.replace(",", "").strip().lstrip("$").rstrip("%"))
    except ValueError:
        raise ValueError(f"{text!r} is not a number") from None


def _cap(text: str):
    return None if text.strip().lower() in ("none", "off", "no") else _num(text)


def _loss(value: float) -> float:
    if not 1 <= value <= 50:
        raise ValueError("the daily loss stop is in percent of the balance, from 1 to 50 (10 means 10%)")
    return value / 100


def _asked(args) -> dict:
    """The config fields given as flags (to `fuze init` or `fuze limits`)."""
    out = {k: getattr(args, k) for k in ("size_mode", "percent", "fixed_usd", "max_x")
           if getattr(args, k) is not None}
    if args.max_position_usd is not None:
        out["max_position_usd"] = _cap(args.max_position_usd)
    if args.daily_loss is not None:
        out["daily_loss_frac"] = _loss(args.daily_loss)
    if getattr(args, "stale_flat_min", None) is not None:
        out["stale_flat_min"] = None if args.stale_flat_min == "off" else _num(args.stale_flat_min)
    return out


def _show(cfg, bal: float) -> None:
    for line in describe(cfg, bal):
        print("  " + line)


def _confirm_raise(cur, new, up, bal: float) -> int:
    """0 when the user typed RAISE at a terminal; otherwise the exit code to return. Nothing is saved here."""
    if not sys.stdin.isatty():
        print("Raising risk needs you at a terminal; refusing because input is not a terminal. Nothing was changed.")
        return 2
    print("You are RAISING: " + "; ".join(f"{LABELS[k]} {fmt(k, cur[k])} -> {fmt(k, new[k])}" for k in up))
    print("After the change: " + example(new, bal))
    print("This lets the agent take more risk with your money.")
    if input("Type RAISE to confirm: ").strip() != "RAISE":
        print("Not changed.")
        return 1
    return 0


def cmd_limits(args) -> int:
    cfg = config.load()
    bal = config.current_balance(cfg)
    asked = _asked(args)
    if not asked:
        print(f"Sizing and limits (balance ${bal:,.2f}):")
        _show(cfg, bal)
        print(f"  Close everything after no live signal for: {fmt('stale_flat_min', cfg['stale_flat_min'])}.")
        print("Change with `fuze limits --percent 5` and the like (see `fuze limits -h`). Lowering applies at once; "
              "raising asks you to type RAISE.")
        return 0
    new = config.validate({**cfg, **asked})
    up = raised(cfg, new, bal)
    if up and (code := _confirm_raise(cfg, new, up, bal)):
        return code
    config.save(new)
    print("Saved: " + ", ".join(f"{LABELS[k]} {fmt(k, new[k])}" for k in asked))
    _show(new, bal)
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
    print(f"Flags: {s.get('flags')}")
    print("Sizing:")
    _show(config.load(), a.get("balance") or config.load()["dry_balance"])
    return 0


def cmd_check(args) -> int:
    report = setup_report()
    for r in report:
        print(f"[{'ok' if r['ok'] else 'NO'}] {r['check']}" + (f": {r['detail']}" if r["detail"] else ""))
    return 0 if all(r["ok"] for r in report) else 1


def _interview(cfg) -> dict:
    """One short question per sizing setting, on a terminal. Enter keeps the value in [brackets]."""
    print("How big should your positions be? Press Enter to keep the value in [brackets].")

    def ask(question, shown, field):
        nonlocal cfg
        while True:
            text = input(f"{question} [{shown}]: ").strip()
            if not text:
                return
            try:
                cfg = config.validate({**cfg, **field(text)})
                return
            except ValueError as e:
                print(f"  {e}")

    ask("Size by a share of your balance (percent) or by a fixed amount (fixed)?", cfg["size_mode"],
        lambda t: {"size_mode": {"p": "percent", "f": "fixed"}.get(t.lower()[:1], t)})
    if cfg["size_mode"] == "percent":
        ask("Share of your balance that follows the signal, in percent (1 to 100)", f"{cfg['percent']:g}",
            lambda t: {"percent": _num(t)})
    else:
        ask("Amount of money that follows the signal, in dollars (10 to 1,000,000)", f"{cfg['fixed_usd']:g}",
            lambda t: {"fixed_usd": _num(t)})
    cap = cfg["max_position_usd"]
    ask("Largest position on one coin, in dollars, or none", "none" if cap is None else f"{cap:g}",
        lambda t: {"max_position_usd": _cap(t)})
    ask("Most you hold across coins, as a multiple of your balance (0.1 to 25)", f"{cfg['max_x']:g}",
        lambda t: {"max_x": _num(t)})
    ask("Daily loss stop, in percent of the balance (1 to 50)", f"{cfg['daily_loss_frac'] * 100:g}",
        lambda t: {"daily_loss_frac": _loss(_num(t))})
    return cfg


def cmd_init(args) -> int:
    path = config.ensure_home() / "config.json"
    asked = _asked(args)
    if path.exists() and not args.force:
        print(f"{path} already exists; leaving it as it is. See or change your sizing with `fuze limits`, "
              "or start over with `fuze init --force`.")
        return 1 if asked else 0
    new = config.validate({**config.DEFAULTS, **asked})  # a new config always starts in mode "dry"
    ask = sys.stdin.isatty() and not args.yes
    if ask:
        new = _interview(new)
    print(f"Your sizing, on the simulated ${new['dry_balance']:,.0f} account:")
    _show(new, new["dry_balance"])
    up = []
    if path.exists():  # --force: replacing your config may not raise risk without you typing RAISE
        try:
            cur = config.load()
        except (ValueError, OSError):
            cur = config.validate({})
        up = raised(cur, new, config.current_balance(cur))
    if up:
        if code := _confirm_raise(cur, new, up, new["dry_balance"]):
            return code
    elif ask and input("Save this? [Y/n] ").strip().lower() not in ("", "y", "yes"):
        print("Not saved.")
        return 1
    config.save(new)
    print(f"Wrote {path} (dry run: simulated account, no real money). Change the sizing later with `fuze limits`.")
    print("Next: `fuze run` in its own terminal, then `fuze status`.")
    return 0


def _sizing_args(p) -> None:
    p.add_argument("--size-mode", dest="size_mode", choices=config.SIZE_MODES,
                   help="percent: a share of your balance follows the signal (default); fixed: a fixed amount does")
    p.add_argument("--percent", type=float, help="share of your balance that follows the signal, 1 to 100")
    p.add_argument("--fixed-usd", dest="fixed_usd", type=float,
                   help="dollars that follow the signal in fixed mode, 10 to 1,000,000")
    p.add_argument("--max-position-usd", dest="max_position_usd",
                   help='largest position on one coin in dollars, or "off"')
    p.add_argument("--max-x", dest="max_x", type=float, help="most you hold across coins, times your balance")
    p.add_argument("--daily-loss", dest="daily_loss", type=float, help="daily loss stop in percent, 1 to 50")


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="fuze", description="Follow the FUZE signal (v0.1: dry run only).")
    p.add_argument("--version", action="version", version=__version__)
    sub = p.add_subparsers(dest="cmd", required=True)
    init = sub.add_parser("init", help="create ~/.fuze and set how big your positions are")
    _sizing_args(init)
    init.add_argument("--yes", action="store_true", help="ask no questions; use the flags and the safe defaults")
    init.add_argument("--force", action="store_true", help="replace an existing config.json")
    run = sub.add_parser("run", help="run the agent")
    run.add_argument("--mode", default="dry", help='only "dry" exists in v0.1')
    sub.add_parser("status", help="what the agent holds and why")
    for name, text in (("pause", "hold, no new orders"), ("resume", "undo pause"),
                       ("flatten", "close everything and stay out"), ("unflatten", "undo flatten")):
        sub.add_parser(name, help=text)
    lim = sub.add_parser("limits", help="show or change your sizing and limits (raising asks you to type RAISE)")
    _sizing_args(lim)
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
    except EOFError:  # Ctrl+D at a question
        print("\nNothing was changed.")
        return 1

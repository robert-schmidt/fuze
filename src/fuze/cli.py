"""The `fuze` command. Raising risk, resume, unflatten, the mode and the keys exist only here, never in the MCP
server."""

from __future__ import annotations

import argparse
import getpass
import json
import os
import shlex
import sys
import time
from pathlib import Path

from fuze import __version__, config, keys, modes
from fuze.checks import setup_report
from fuze.sizing import LABELS, describe, example, fmt, raised


UNDO = {"PAUSE": ("resume", "The agent follows the signal again: it may open or add to positions at once."),
        "FLATTEN": ("unflatten", "The agent follows the signal again: it may open positions at once.")}


def _undo_flag(name: str) -> int:
    """resume / unflatten: like raising risk, only by you at a terminal, typed."""
    word, what = UNDO[name]
    if not (config.home() / name).exists():
        print(f"{name} is off.")
        return 0
    if not sys.stdin.isatty():
        print(f"`fuze {word}` needs you at a terminal; refusing because input is not a terminal. {name} stays on.")
        return 2
    print(what)
    if input(f"Type {word.upper()} to confirm: ").strip() != word.upper():
        print(f"Not changed: {name} stays on.")
        return 1
    print(_flag(name, False))
    return 0


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
    if "size_mode" in up:
        k = "percent" if new["size_mode"] == "percent" else "fixed_usd"
        print(f"  ({LABELS[k]} after the change: {fmt(k, new[k])})")
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
    _warn_too_small(new, bal)
    if _agent_running():
        print("The running agent resizes to this within seconds.")
    return 0


def _agent_running() -> bool:
    s = config.read_json(config.home() / "status.json") or {}
    return isinstance(s.get("t"), (int, float)) and time.time() - s["t"] < 30


def _warn_too_small(cfg, bal: float) -> None:
    """Say so when, at the current signal, these settings ask for changes the agent never makes (under its band)."""
    from fuze.follow import asked_usd, min_change
    sig = (config.read_json(config.home() / "status.json") or {}).get("signal")
    asked = {c: v for c, v in asked_usd(sig, cfg, bal).items() if abs(v) >= 0.005}
    tol = min_change(bal)
    if asked and all(abs(v) < tol for v in asked.values()):
        print("Warning: at the current signal this asks for " + ", ".join(f"{c} ${abs(v):,.0f}" for c, v in
                                                                         asked.items())
              + f", each under ${tol:,.0f}, the smallest change the agent makes (the larger of $10 and 2% of your "
              "balance). Nothing would be opened at this size.")


def _lock():
    """The agent's lock on this FUZE folder, or None when an agent holds it. Close the file to release it."""
    import fcntl

    f = open(os.open(config.ensure_home() / "agent.lock", os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600), "w")
    try:
        fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
        return f
    except OSError:
        f.close()
        return None


def _plain(e) -> str:
    from fuze.agent import _plain as plain
    return plain(e)


def _venue(cfg, mode=None):
    from fuze.venue import open_venue
    return open_venue({**cfg, "mode": mode or cfg["mode"]}, config.ensure_home())


BANNER = {"simulation": "simulated account, no real money",
          "testnet": "Lighter TESTNET, test money",
          "mainnet": "Lighter MAINNET: REAL MONEY"}


def cmd_run(args) -> int:
    cfg = config.load()
    if args.mode and args.mode != cfg["mode"]:
        print(f"`fuze run` trades in the mode set in your settings: {modes.NAMES[cfg['mode']]}. To change it, run "
              f"`fuze mode {args.mode}` in a terminal.")
        return 2
    missing = modes.blockers(cfg)
    if missing:
        print(f"Cannot start in {modes.NAMES[cfg['mode']]}:")
        for m in missing:
            print("  - " + m)
        return 2
    from fuze.agent import Agent, setup_logging
    lock = _lock()  # one agent per FUZE folder: two would trade twice
    if not lock:
        print("Another agent is already running on this FUZE folder.")
        return 2
    try:
        ex = _venue(cfg)
    except Exception as e:
        print(f"Cannot start in {modes.NAMES[cfg['mode']]}: {_plain(e)}")
        return 2
    setup_logging()
    link = ex.link()
    print(f"FUZE agent ({BANNER[cfg['mode']]})" + (f", account {link}" if link else "") + ". Ctrl+C to stop.")
    try:
        Agent(exchange=ex).run()
    except KeyboardInterrupt:
        print("Stopped. Positions stay as they are" + (
            " (on the exchange the scalp part keeps its take profit and stop loss, and the rest of each position its "
            "emergency stop)." if ex.live else ". The simulated account checks its take profit, stop loss and "
            "emergency stops only while the agent runs."))
    return 0


def _mode_lines(cfg, status=None) -> list:
    mode, status = cfg["mode"], status or {}
    out = [f"Mode: {modes.NAMES[mode]}"]
    if mode != "simulation":
        from fuze.venue import account_link
        link = account_link(mode, cfg[f"{mode}_account"])
        out.append(f"Lighter {mode} account: {link or 'not set (`fuze keys ' + mode + '`)'}; API key "
                   f"{keys.state(mode)}")
    if status.get("note"):
        out.append(status["note"])
    return out


def cmd_status(args) -> int:
    from fuze.follow import describe_compare, from_status
    s = config.read_json(config.home() / "status.json")
    if not s:
        print("No status yet. Start the agent with `fuze run`.")
        return 1
    cfg = config.load()
    a, sig = s.get("account") or {}, s.get("signal") or {}
    for line in _mode_lines(cfg, s):
        print(line)
    if s.get("mode") != cfg["mode"]:
        print(f"The agent last ran in {s.get('mode')}; restart it to trade in {cfg['mode']}.")
    age = time.time() - s["t"] if isinstance(s.get("t"), (int, float)) else None
    print("Agent: " + ("running" if age is not None and age < 30 else "NOT running (start it with `fuze run`)")
          + (f", last step {age:,.0f} s ago" if age is not None else ""))
    print(f"Balance: ${a.get('balance') or 0:,.2f}")
    rows, tol = from_status(s)
    if rows:
        print("Positions (what the signal asks for at your limits, and what you hold):")
        for line in describe_compare(rows, tol):
            print("  " + line)
    else:
        held = {c: u for c, u in (a.get("positions") or {}).items() if u}
        print("Positions: " + (", ".join(f"{c} {u:+g}" for c, u in held.items()) or "none"))
    stops = {c: g for c, g in (a.get("guards") or {}).items() if isinstance(g, dict)
             and all(isinstance(g.get(k), (int, float)) and not isinstance(g.get(k), bool) for k in ("units", "stop"))}
    if stops:
        print("Emergency stops (for the part with no take profit or stop loss of its own): "
              + ", ".join(f"{c} {g['units']:+g} at {g['stop']:,.2f}" for c, g in stops.items()))
    if sig:
        src = modes.SOURCE_NAMES.get(sig.get("source"), sig.get("source"))
        print(f"Signal: revision {sig['rev']}, {sig['state']}, from our {src} account. Why (data from the server): "
              f"{sig['why']}")
    else:
        print("Signal: none received yet")
    print(f"Last step: {s.get('reason')}")
    flags = s.get("flags") or {}
    print(f"Pause: {'ON (undo with `fuze resume`)' if flags.get('pause') else 'off'}. "
          f"Flatten: {'ON (undo with `fuze unflatten`)' if flags.get('flatten') else 'off'}.")
    print("Sizing:")
    _show(cfg, a.get("balance") or cfg["dry_balance"])
    return 0


def cmd_ui(args) -> int:
    from fuze.ui import serve
    return serve(args.port, args.open)


def cmd_check(args) -> int:
    report = setup_report(read_account=True)
    for r in report:
        print(f"[{'ok' if r['ok'] else 'NO'}] {r['check']}" + (f": {r['detail']}" if r["detail"] else ""))
    return 0 if all(r["ok"] for r in report) else 1


# --- modes and keys: terminal only --------------------------------------------------------------------------------

def _keys_prompt(cfg, net: str, account=None, key_index=None) -> dict:
    """Ask the account index, key index and the key (hidden) for `net`. Returns the config with them saved."""
    cur_a, cur_k = cfg[f"{net}_account"], cfg[f"{net}_key_index"]
    if account is None:
        text = input(f"Lighter {net} account index{f' [{cur_a}]' if cur_a is not None else ''}: ").strip()
        account = int(text) if text else cur_a
    if key_index is None:
        text = input(f"API key index on that account (4 to 254) [{cur_k}]: ").strip()
        key_index = int(text) if text else cur_k
    if account is None:
        raise ValueError("an account index is needed (docs/lighter-setup.md says where to find it)")
    new = config.validate({**cfg, f"{net}_account": account, f"{net}_key_index": key_index})
    print(f"Paste the API private key for index {key_index}. It is not shown and is never printed or logged. "
          "Never your wallet's private key or recovery phrase.")
    keep = " (Enter keeps the stored one)" if keys.state(net) == "set" else ""
    secret = getpass.getpass(f"Lighter {net} API private key{keep}: ")
    if secret.strip():
        keys.clean(secret)  # a wrong key saves nothing, the account index included
    config.save(new)
    if secret.strip():
        where = keys.save(net, secret)
        print(f"Key stored in {where}.")
    elif keys.state(net) != "set":
        print("No key given; none is stored.")
    return new


def cmd_keys(args) -> int:
    cfg = config.load()
    if not args.net:
        from fuze.venue import account_link
        for net in config.NETS:
            print(f"{net}: account {cfg[f'{net}_account'] if cfg[f'{net}_account'] is not None else 'not set'}, "
                  f"key index {cfg[f'{net}_key_index']}, API key {keys.state(net)}"
                  + (f", {account_link(net, cfg[f'{net}_account'])}" if cfg[f"{net}_account"] is not None else ""))
        print("Set with `fuze keys testnet` (or mainnet) in a terminal. The key is typed there, hidden, never as an "
              "argument and never in a chat.")
        return 0
    net = args.net
    if not sys.stdin.isatty():
        print("Keys are typed by you at a terminal; refusing because input is not a terminal. Nothing was changed.")
        return 2
    lock = _lock() if net == cfg["mode"] else None
    if net == cfg["mode"] and not lock:
        print(f"The agent is running in {net}. Stop it first, then change its {net} account or key.")
        return 2
    try:
        if args.delete:
            if net == cfg["mode"]:
                print(f"You trade in {net}: leave it first with `fuze mode simulation`, then delete its key.")
                return 2
            keys.delete(net)
            print(f"The {net} API key is deleted from this machine. It still works on Lighter until you replace it "
                  "there (docs/lighter-setup.md).")
            return 0
        if net == cfg["mode"] and args.account is not None and args.account != cfg[f"{net}_account"]:
            print(f"You trade in {net}: to follow on another account, leave it first with `fuze mode simulation` "
                  "(it checks that nothing is open), then change the account.")
            return 2
        _keys_prompt(cfg, net, args.account, args.key_index)
        print("`fuze check` reads the account with it (it sends no order).")
        return 0
    finally:
        if lock:
            lock.close()


def _held(a) -> bool:
    return bool(a["brackets"] or a.get("guards")) or any(abs(v) > 1e-12 for v in a["positions"].values())


def _close_first(cfg, cur: str, a, why="A mode change never strands a position.") -> int:
    """Something is open in `cur` and has to be closed first (a mode change never strands a position; the rehearsal
    needs an empty account). The simulated account closes it by itself; on Lighter you type CLOSE and it is closed
    with market orders now. 0 once nothing is open."""
    ex = _venue(cfg, cur)
    if cur != "simulation":
        print(f"Positions are open in {cur}: {a['positions']}. {why}\n"
              "Type CLOSE to close them now with market orders and cancel their open orders. Anything else leaves "
              "them as they are.")
        if input("Type CLOSE to close them: ").strip() != "CLOSE":
            print("Nothing was changed. You can also close them with `fuze flatten` and `fuze run`, then change "
                  "the mode.")
            return 2
    try:
        ex.flatten()
        for _ in range(10):
            a = ex.account(fresh=True)
            if not _held(a):
                break
            time.sleep(1.0)
    except Exception as e:
        print(f"Closing did not go through ({_plain(e)}). Nothing was changed; check the account: {ex.link()}")
        return 2
    if _held(a):
        print("Not everything closed" + (" (the simulated account has no price yet: run `fuze run` once first)"
                                         if cur == "simulation" else f": {a['positions']}. Check {ex.link()}")
              + ". Nothing was changed.")
        return 2
    print("Closed: your simulated positions, in the simulated account." if cur == "simulation"
          else f"Closed: nothing is open in {cur} now.")
    return 0


def switch_mode(cfg, target: str) -> int:
    """Change the mode. Terminal only, agent stopped, nothing open in the current mode, the new one ready; moving
    toward real money asks for RAISE, and mainnet also for the phrase."""
    cur = cfg["mode"]
    if target == cur:
        print(f"Already in {modes.NAMES[cur]}.")
        return 0
    if not sys.stdin.isatty():
        print("Changing the mode needs you at a terminal; refusing because input is not a terminal. "
              "Nothing was changed.")
        return 2
    lock = _lock()
    if not lock:
        print("The agent is running on this FUZE folder. Stop it first (Ctrl+C in its terminal), then change the mode.")
        return 2
    try:
        missing = modes.blockers(cfg, target)
        if missing:
            print(f"{modes.NAMES[target]} is not ready:")
            for m in missing:
                print("  - " + m)
            print("`fuze go-live` walks you through these, one step at a time.")
            return 2
        if target == "mainnet" and (why := _confirm_rehearsal(cfg)):
            print(f"{modes.NAMES[target]} stays locked: {why}. Nothing was changed.")
            return 2
        try:
            a = _venue(cfg).account(fresh=True)
        except Exception as e:
            print(f"Could not read your {cur} account to check that nothing is open there ({_plain(e)}).")
            if modes.RANK[target] > modes.RANK[cur]:
                print("Nothing was changed.")
                return 2
            from fuze.venue import account_link
            print(f"Check it yourself on {account_link(cur, cfg[f'{cur}_account'])}. If it holds no position and no "
                  "open order, type CLOSED to leave it.")
            if input("Type CLOSED to confirm: ").strip() != "CLOSED":
                print("Not changed.")
                return 1
            a = {"positions": {}, "brackets": []}
        if _held(a) and (code := _close_first(cfg, cur, a)):
            return code
        bal = config.current_balance(cfg)
        if target != "simulation":
            try:
                ex = _venue(cfg, target)
                t = ex.account(fresh=True)
            except Exception as e:
                print(f"Could not read your {target} account ({_plain(e)}). Nothing was changed.")
                return 2
            print(f"Lighter {target} account {cfg[f'{target}_account']}: balance ${t['balance']:,.2f}. {ex.link()}")
            if _held(t):
                print("That account already holds positions or orders that FUZE did not open. Give FUZE a sub-account "
                      "of its own (docs/lighter-setup.md), or close them on Lighter first. Nothing was changed.")
                return 2
            bal = t["balance"] or bal
        print("Your sizing on that balance (change it later with `fuze limits`):")
        _show(cfg, bal)
        if modes.RANK[target] > modes.RANK[cur]:
            print(f"You are moving toward real money: {modes.NAMES[cur]} -> {modes.NAMES[target]}.")
            if target == "mainnet":
                print("The rehearsal on testnet passed on this machine. On mainnet you can lose everything you put on "
                      "this account. Keep only what you can lose there.")
            if input("Type RAISE to confirm: ").strip() != "RAISE":
                print("Not changed.")
                return 1
            if target == "mainnet" and input(f"Type {modes.PHRASE} to trade real money: ").strip() != modes.PHRASE:
                print("Not changed.")
                return 1
        config.save({**cfg, "mode": target})
        for name in ("state.json", "pending.json"):  # notes about the old account mean nothing on the new one
            (config.home() / name).unlink(missing_ok=True)
        print(f"Mode: {modes.NAMES[target]}. Start the agent with `fuze run`.")
        if (config.home() / "FLATTEN").exists():
            print("FLATTEN is on: the agent opens nothing until you run `fuze unflatten`.")
        return 0
    finally:
        lock.close()


def _confirm_rehearsal(cfg) -> str:
    """Ask Lighter testnet to confirm the rehearsal record (reads only). Empty when confirmed."""
    from fuze import lighter_venue
    print("Asking Lighter testnet to confirm your rehearsal's orders (reads only, sends nothing) ...")
    try:
        client = lighter_venue.connect(cfg, "testnet")
    except Exception as e:
        return f"could not open Lighter testnet with your testnet key to confirm the rehearsal ({_plain(e)})"
    try:
        why = modes.confirm_on_testnet(cfg, client)
    finally:
        close = getattr(client, "close", None)
        if close:
            close()
    if not why:
        print("Confirmed by Lighter testnet: the rehearsal's orders were sent from your testnet account with your key.")
    return why


def cmd_mode(args) -> int:
    cfg = config.load()
    if args.target:
        return switch_mode(cfg, args.target)
    for line in _mode_lines(cfg, config.read_json(config.home() / "status.json") or {}):
        print(line)
    if cfg["mode"] != "mainnet":
        why = modes.rehearsal_problem()
        print("Testnet rehearsal: " + ("recorded as passed on this machine with this version (`fuze mode mainnet` "
                                       "asks Lighter testnet to confirm it)" if not why else why))
    print("Change with `fuze mode simulation|testnet|mainnet` in a terminal. Moving toward real money asks you to "
          f"type RAISE (and {modes.PHRASE} for mainnet); mainnet needs the testnet rehearsal first.")
    return 0


def cmd_rehearse(args) -> int:
    cfg = config.load()
    if not sys.stdin.isatty():
        print("The rehearsal needs you at a terminal; refusing because input is not a terminal.")
        return 2
    missing = [m for m in modes.blockers(cfg, "testnet")]
    if missing:
        print("Testnet is not ready:")
        for m in missing:
            print("  - " + m)
        return 2
    lock = _lock()
    if not lock:
        print("The agent is running on this FUZE folder. Stop it first, then rehearse.")
        return 2
    try:
        try:
            ex = _venue(cfg, "testnet")
            a = ex.account(fresh=True)
        except Exception as e:
            print(f"Could not read your testnet account ({_plain(e)}).")
            return 2
        print(f"Rehearsal on Lighter testnet account {cfg['testnet_account']} (balance ${a['balance']:,.2f}), "
              f"{ex.link()}:\n  open a small Bitcoin position, place the emergency stop for one half and a take profit "
              "and stop loss for the other, cancel them, close it. Each step is confirmed by reading the account. "
              "Test money only.")
        if input("Type yes to send these test orders: ").strip().lower() != "yes":
            print("Nothing was sent.")
            return 1
        rec = modes.rehearse(ex)
        config.write_json(config.ensure_home() / "rehearsal.json", rec)
        print("Rehearsal " + ("PASSED: mainnet can be chosen on this machine with this version (`fuze mode mainnet`)."
                              if rec["ok"] else "FAILED: mainnet stays locked. See docs/lighter-setup.md."))
        return 0 if rec["ok"] else 1
    finally:
        lock.close()


APP = {"testnet": "https://testnet.app.lighter.xyz", "mainnet": "https://app.lighter.xyz"}


def _lighter_account(cfg, net: str):
    """One step of `fuze go-live`: the Lighter account and API key for `net`, asked only when missing, then read
    back. Returns (config, balance), or (config, None) when Lighter does not accept them."""
    if cfg[f"{net}_account"] is None or keys.state(net) != "set":
        print(f"  1. Open {APP[net]} and connect a wallet only you control."
              + (" Open the account panel (your address, top right) and press Request Funds: the account is created "
                 "with test money." if net == "testnet" else
                 " Make a sub-account for FUZE (Sub-accounts, New Sub-Account) and transfer into it only money you "
                 "can afford to lose completely."))
        print(f"  2. Open {APP[net]}/apikeys with that account selected, press Generate API key, choose index 4, "
              "leave Maker only off" + ("" if net == "testnet" else ", and restrict the key to the BTC and ETH "
                                        "markets") + ". Your wallet signs it.")
        print("  3. The page shows the private key once, and your account index. Type both here. The key is hidden "
              "as you type, stored on this computer only, and never shown again. Never type your wallet's own key "
              "or recovery phrase anywhere.")
        cfg = _keys_prompt(cfg, net)
    try:
        ex = _venue(cfg, net)
        a = ex.account(fresh=True)
    except Exception as e:
        print(f"Lighter {net} does not accept this account index, key index and key together ({_plain(e)}). "
              f"Run `fuze keys {net}` to type them again, then `fuze go-live`.")
        return cfg, None
    print(f"Lighter {net} account {cfg[f'{net}_account']}: balance ${a['balance']:,.2f}. {ex.link()}")
    return cfg, a["balance"]


def cmd_go_live(args) -> int:
    """The guided way from simulation to real money. It only runs the same steps as `fuze keys`, `fuze rehearse` and
    `fuze mode`, in order, and skips what is already done: stop at any question and run it again to carry on."""
    cfg = config.load()
    if not sys.stdin.isatty():
        print("`fuze go-live` asks you questions and takes your keys at a terminal; refusing because input is not a "
              "terminal. Nothing was changed.")
        return 2
    if cfg["mode"] == "mainnet":
        print("You already trade real money (Lighter mainnet). `fuze status` shows what the agent holds; "
              "`fuze mode simulation` goes back to the simulated account.")
        return 0
    if _agent_running():
        print("The agent is running on this FUZE folder. Stop it first (Ctrl+C in its terminal), then run "
              "`fuze go-live` again.")
        return 2
    if not modes.sdk_installed():
        print("Trading on Lighter needs one more part, Lighter's own signing library: "
              + config.pip_hint("mcp,lighter") + "\nThen run `fuze go-live` again.")
        return 2
    print("Real money, in four steps. Steps you have done are skipped; you can stop at any question and run "
          "`fuze go-live` again.\n"
          "The signal is the same in every mode, and your keys and the rehearsal are remembered: once this is done, "
          "`fuze mode simulation` and `fuze mode mainnet` move you back and forth.\n")
    print("Step 1 of 4: an account on Lighter's test exchange (test money, free).")
    cfg, bal = _lighter_account(cfg, "testnet")
    if bal is None:
        return 2
    print("\nStep 2 of 4: the rehearsal. The agent sends its whole set of orders once on the test exchange and "
          "checks each on the account.")
    if modes.rehearsal_problem():
        held = _venue(cfg, "testnet").account(fresh=True)
        if _held(held) and (code := _close_first(cfg, "testnet", held, "The rehearsal needs an empty account.")):
            return code
        if code := cmd_rehearse(args):
            print("Real money stays locked until the rehearsal passes. Run `fuze go-live` again to retry.")
            return code
    else:
        print("Passed on this computer with this version.")
    cfg = config.load()
    if cfg["mode"] == "simulation":
        print("\nYou can follow on the test exchange for a while first and watch every order there (recommended), "
              "or carry on to real money now.")
        if input("Type testnet to follow with test money first, or mainnet to carry on: ").strip().lower() != "mainnet":
            code = switch_mode(cfg, "testnet")
            if not code:
                print("When you have watched it work, `fuze go-live` carries on with real money.")
            return code
    print("\nStep 3 of 4: your Lighter account for real money.\n"
          "You can lose everything on the account the agent trades. Use a sub-account of its own that holds only "
          "money you can afford to lose completely.")
    cfg, bal = _lighter_account(cfg, "mainnet")
    if bal is None:
        return 2
    print("\nStep 4 of 4: the switch. Your sizing is shown on that balance; you confirm by typing RAISE and "
          f"{modes.PHRASE}.")
    return switch_mode(cfg, "mainnet")


def _ask_mode(default: str) -> str:
    while True:
        text = input(f"Where should the agent trade: simulation (no money), testnet (test money) or mainnet (real "
                     f"money)? [{default}]: ").strip().lower()
        if not text:
            return default
        if text in config.MODES:
            return text
        print("  answer simulation, testnet or mainnet")


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
              "the mode with `fuze mode`, or start over with `fuze init --force`.")
        return 1 if asked or args.mode else 0
    if path.exists():
        try:
            live = config.load()["mode"]
        except (ValueError, OSError):
            live = "simulation"
        if live != "simulation":
            print(f"Your settings trade in {live}. Leave it first with `fuze mode simulation` (it checks that nothing "
                  "is open there), then `fuze init --force`.")
            return 2
    new = config.validate({**config.DEFAULTS, **asked})  # a new config is saved in simulation; see the mode below
    ask = sys.stdin.isatty() and not args.yes
    target = args.mode or (_ask_mode("simulation") if ask else "simulation")
    if ask:
        new = _interview(new)
    print(f"Your sizing, shown on a ${new['dry_balance']:,.0f} balance:")
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
    try:  # the Lighter account settings survive a --force
        keep = config.load() if path.exists() else {}
    except (ValueError, OSError):
        keep = {}
    new = config.save({**new, **{k: v for k, v in keep.items() if k.startswith(config.NETS)}})
    print(f"Wrote {path} (simulation: simulated account, no real money). Change the sizing later with "
          "`fuze limits`, the mode with `fuze mode`.")
    if target != "simulation":
        if not sys.stdin.isatty():
            print(f"Changing the mode to {target} needs you at a terminal: run `fuze mode {target}` there.")
            return 2
        net = "testnet" if target == "mainnet" else target
        if new[f"{net}_account"] is None or keys.state(net) != "set":
            print(f"Lighter {net} needs your account index and an API key (docs/lighter-setup.md).")
            new = _keys_prompt(new, net)
        if target == "mainnet" and modes.rehearsal_problem():
            print(f"Mainnet stays locked: {modes.rehearsal_problem()}. Your settings stay in simulation; "
                  "`fuze go-live` takes you there one step at a time.")
            return 2
        return switch_mode(new, target)
    print("Next: `fuze run` in its own terminal, then `fuze status`.")
    return 0


# tools whose settings take the same {"mcpServers": ...} JSON as Cursor: name -> the tool and where it keeps that JSON
SAME_JSON = {
    "gemini": "Gemini CLI: ~/.gemini/settings.json",
    "antigravity": "Antigravity (IDE and CLI): ~/.gemini/config/mcp_config.json",
    "devin": "Devin Desktop (formerly Windsurf) and Devin CLI: ~/.config/devin/mcp_config.json",
    "cline": "Cline: its MCP Servers panel, Configure, Configure MCP Servers (cline_mcp_settings.json)",
    "claude-desktop": "Claude Desktop: Settings, Developer, Edit Config (claude_desktop_config.json); then quit the app "
                      "and open it again",
    "jetbrains": "JetBrains AI Assistant: Settings | Tools | AI Assistant | Model Context Protocol (MCP). "
                 "Junie: ~/.junie/mcp/mcp.json",
    "kiro": "Kiro: ~/.kiro/settings/mcp.json",
}
TOOLS = ("claude-code", "codex", "copilot", "vscode", "cursor", "opencode", "zed", *SAME_JSON)


def fuze_command() -> list:
    """The command that starts this very fuze, as an absolute path: AI tools start MCP servers without your PATH."""
    argv0 = Path(sys.argv[0])
    if argv0.name in ("fuze", "fuze.exe"):
        found = argv0 if argv0.is_absolute() or os.sep in str(argv0) else None
        import shutil
        path = found or shutil.which(str(argv0))
        if path:
            return [os.path.abspath(path)]
    return [sys.executable, "-m", "fuze"]


def mcp_config(tool: str | None = None) -> str:
    """Ready-to-paste MCP settings: the absolute command and FUZE_HOME, which AI tools do not inherit."""
    cmd, home = fuze_command(), str(config.home().resolve())
    args, env = cmd[1:] + ["mcp"], {"FUZE_HOME": home}
    server = {"type": "stdio", "command": cmd[0], "args": args, "env": env}
    shell = " ".join(shlex.quote(x) for x in cmd + ["mcp"])
    q = shlex.quote(f"FUZE_HOME={home}")
    toml = "\n".join(["[mcp_servers.fuze]", f"command = {json.dumps(cmd[0])}", f"args = {json.dumps(args)}",
                      f"env = {{ FUZE_HOME = {json.dumps(home)} }}"])
    same = json.dumps({"mcpServers": {"fuze": server}}, indent=2)
    parts = {
        "claude-code": ("Claude Code: run this once (or put the JSON in a project's .mcp.json)",
                        f"claude mcp add fuze --scope user -e {q} -- {shell}\n\n"
                        + json.dumps({"mcpServers": {"fuze": server}}, indent=2)),
        "codex": ("Codex: run this once, or add the TOML to ~/.codex/config.toml",
                  f"codex mcp add fuze --env {q} -- {shell}\n\n{toml}"),
        "copilot": ("GitHub Copilot CLI, and Copilot in VS Code: ~/.copilot/mcp-config.json, or a workspace .mcp.json",
                    json.dumps({"mcpServers": {"fuze": {**server, "tools": ["*"]}}}, indent=2)),
        "vscode": ("VS Code with Copilot, the editor's own format: run this once, or put the second JSON in "
                   ".vscode/mcp.json in your workspace",
                   "code --add-mcp " + shlex.quote(json.dumps({"name": "fuze", **server})) + "\n\n"
                   + json.dumps({"servers": {"fuze": server}}, indent=2)),
        "cursor": ("Cursor: ~/.cursor/mcp.json (every project) or .cursor/mcp.json (one project)", same),
        "opencode": ("OpenCode: run this once (without --global: this project only)",
                     f"opencode mcp add --global --env {q} fuze -- {shell}"),
        "zed": ("Zed: in its settings file (command `zed: open settings file`)",
                json.dumps({"context_servers": {"fuze": {"command": cmd[0], "args": args, "env": env}}}, indent=2)),
        **{name: (where, same) for name, where in SAME_JSON.items()},
    }
    out = [f"# FUZE MCP server settings. Command: {shell}", f"# FUZE folder (FUZE_HOME): {home}"]
    if (why := config.no_agent_here()):
        out.append("# WARNING: " + why)
    out.append("# The server can only read and reduce risk. After adding it, restart the tool and ask for the FUZE "
               "status: it must show your mode and balance.")
    out.append("# In a settings file that already has content, add the \"fuze\" entry next to the others; do not "
               "replace the file.")
    for name in ([tool] if tool else [t for t in TOOLS if t not in SAME_JSON]):
        title, text = parts[name]
        out += ["", f"## {title}", text]
    if not tool:  # the same JSON as Cursor's, printed once: `--tool NAME` prints one of them on its own
        out += ["", "## The same JSON as Cursor's goes into (`fuze mcp-config --tool NAME` prints one):"]
        out += [f"- {name}: {where}" for name, where in SAME_JSON.items()]
    return "\n".join(out)


def cmd_mcp_config(args) -> int:
    print(mcp_config(args.tool))
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
    p = argparse.ArgumentParser(prog="fuze", description="Follow the FUZE signal: simulation, Lighter testnet or "
                                                         "Lighter mainnet.")
    p.add_argument("--version", action="version", version=__version__)
    sub = p.add_subparsers(dest="cmd", required=True)
    init = sub.add_parser("init", help=f"create {config.home()} and set how big your positions are")
    _sizing_args(init)
    init.add_argument("--yes", action="store_true", help="ask no questions; use the flags and the safe defaults")
    init.add_argument("--force", action="store_true", help="replace an existing config.json")
    init.add_argument("--mode", choices=config.MODES, help="where to trade (default simulation); testnet and "
                                                           "mainnet ask you to confirm at a terminal")
    run = sub.add_parser("run", help="run the agent in the mode set with `fuze mode`")
    run.add_argument("--mode", choices=config.MODES, help="refuse to start unless this is the mode in your settings")
    mode = sub.add_parser("mode", help="show or change the mode: simulation, testnet, mainnet (terminal only)")
    mode.add_argument("target", nargs="?", choices=config.MODES)
    kp = sub.add_parser("keys", help="set the Lighter account and API key for testnet or mainnet (typed, hidden)")
    kp.add_argument("net", nargs="?", choices=config.NETS)
    kp.add_argument("--account", type=int, help="your Lighter account index (public)")
    kp.add_argument("--key-index", dest="key_index", type=int, help="the API key's index, 4 to 254")
    kp.add_argument("--delete", action="store_true", help="delete the stored key from this machine")
    sub.add_parser("rehearse", help="the testnet rehearsal that unlocks mainnet on this machine (test orders)")
    sub.add_parser("go-live", help="from simulation to real money, one guided step at a time (terminal only): test "
                                   "account and key, rehearsal, real account and key, the switch")
    sub.add_parser("status", help="what the agent holds and why")
    for name, text in (("pause", "hold, no new orders"), ("resume", "undo pause (terminal only, type RESUME)"),
                       ("flatten", "close everything and stay out"),
                       ("unflatten", "undo flatten (terminal only, type UNFLATTEN)")):
        sub.add_parser(name, help=text)
    lim = sub.add_parser("limits", help="show or change your sizing and limits (raising asks you to type RAISE)")
    _sizing_args(lim)
    lim.add_argument("--stale-flat-min", dest="stale_flat_min", help='minutes, or "off"')
    sub.add_parser("check", help="check the local setup")
    from fuze.ui import PORT
    ui = sub.add_parser("ui", help=f"a read-only page about the agent, on this computer only (http://127.0.0.1:{PORT})")
    ui.add_argument("--port", type=int, default=PORT, help=f"port on 127.0.0.1 (default {PORT})")
    ui.add_argument("--open", action="store_true", help="open it in your browser")
    sub.add_parser("mcp", help="start the MCP server (for AI coding tools)")
    mc = sub.add_parser("mcp-config", help="print the MCP settings for Claude Code, Codex, Copilot / VS Code, Cursor and other AI tools, "
                                           "with this fuze's full path and this FUZE folder")
    mc.add_argument("--tool", choices=TOOLS, help="print only this tool's settings")
    args = p.parse_args(argv)
    try:
        if args.cmd == "mcp":
            try:
                from fuze.mcp_server import main as mcp_main
            except ImportError:
                sys.exit("The MCP server needs one extra package: " + config.pip_hint("mcp"))
            mcp_main()
            return 0
        if args.cmd in ("pause", "flatten"):
            if (why := config.no_agent_here()):
                print("Note: " + why)
            print(_flag(args.cmd.upper(), True))
            return 0
        if args.cmd in ("resume", "unflatten"):
            return _undo_flag({"resume": "PAUSE", "unflatten": "FLATTEN"}[args.cmd])
        return {"init": cmd_init, "run": cmd_run, "status": cmd_status, "check": cmd_check,
                "limits": cmd_limits, "mode": cmd_mode, "keys": cmd_keys, "rehearse": cmd_rehearse, "go-live": cmd_go_live,
                "ui": cmd_ui, "mcp-config": cmd_mcp_config}[args.cmd](args)
    except ValueError as e:
        print(f"Error: {e}")
        return 2
    except EOFError:  # Ctrl+D at a question
        print("\nNothing was changed.")
        return 1

"""The three modes, what each needs before it may run, and the testnet rehearsal that unlocks mainnet.

  simulation  a simulated account on this computer, no money (the default)
  testnet     Lighter's test exchange, test money
  mainnet     Lighter, real money: only after THIS machine passed the testnet rehearsal with THIS version of FUZE

Changing the mode is a terminal action (`fuze mode`), never an MCP tool. See cli.cmd_mode for the gates.
"""

from __future__ import annotations

import importlib.util
import math
import platform
import re
import time

from fuze import __version__, config, keys

NAMES = {"simulation": "simulation (a simulated account, no money)",
         "testnet": "Lighter testnet (test money)",
         "mainnet": "Lighter mainnet (REAL MONEY)"}
RANK = {"simulation": 0, "testnet": 1, "mainnet": 2}
SOURCE_RANK = {"paper": 0, "testnet": 1, "mainnet": 2}
SOURCE_NAMES = {"paper": "practice money (paper)", "testnet": "test money (Lighter testnet)",
                "mainnet": "real money (Lighter mainnet)"}
PHRASE = "REAL MONEY"  # typed, after RAISE, to switch to mainnet
STEPS = ("open", "guard", "protect", "cancel", "unguard", "close")
SENT = ("open", "guard", "protect", "close")  # the steps that send a transaction; Lighter testnet must show each of them
TX_WINDOW_S = 3600.0  # a rehearsal transaction must be this close to the time the record gives


def realer_note(mode: str, source: str | None) -> str:
    """Plain words when the follower risks more real money than the account it follows. Empty otherwise."""
    if source not in SOURCE_RANK or RANK.get(mode, 0) <= SOURCE_RANK[source]:
        return ""
    yours = {"testnet": "test money", "mainnet": "REAL money"}[mode]
    return (f"You follow with {yours} on Lighter {mode}, while the account you follow trades "
            f"{SOURCE_NAMES[source]}. Its results cost it {'nothing' if source == 'paper' else 'only test money'}; "
            f"yours are {yours}. x is a ratio, so the sizes still apply.")


def sdk_installed() -> bool:
    return importlib.util.find_spec("lighter") is not None


def machine() -> str:
    return platform.node() or "unknown"


def rehearsal_problem() -> str:
    """Empty if mainnet's rehearsal is done: on this machine, with this version, every step confirmed. Else why not."""
    r = config.read_json(config.home() / "rehearsal.json") or {}
    if not r:
        return "the testnet rehearsal has not been done on this machine: run `fuze rehearse` in a terminal"
    if not r.get("ok") or [s.get("step") for s in r.get("steps", []) if s.get("ok")] != list(STEPS):
        return "the last testnet rehearsal did not pass every step: run `fuze rehearse` again"
    if r.get("net") != "testnet":
        return "the rehearsal record is not from testnet"
    if r.get("machine") != machine():
        return "the rehearsal was done on another machine: run `fuze rehearse` here"
    if r.get("version") != __version__:
        return (f"the rehearsal was done with FUZE {r.get('version')}, this is {__version__}. Each version changes code "
                "that sends orders, so mainnet needs a rehearsal with the version that will trade: run `fuze rehearse` "
                "again")
    return ""


def confirm_on_testnet(cfg, client) -> str:
    """Empty when Lighter testnet itself shows the rehearsal's orders, else why not. Fails closed.

    `client` is a Lighter testnet client made with the stored testnet key (lighter_venue.connect), so making it already
    showed that Lighter accepts that key for this account and key index. Then each order the rehearsal sent (open,
    emergency stop, take profit / stop loss, close) is read back by its transaction hash: it must exist on testnet, belong to this
    account, be signed with this key index, and be from the time the record gives. Reads only; sends nothing."""
    why = rehearsal_problem()
    if why:
        return why
    r = config.read_json(config.home() / "rehearsal.json") or {}
    acct, idx = cfg["testnet_account"], cfg["testnet_key_index"]
    again = "run `fuze rehearse` again"
    if r.get("account") != acct or r.get("key_index") != idx:
        return (f"the rehearsal record is for testnet account {r.get('account')} key index {r.get('key_index')}, your "
                f"settings say account {acct} key index {idx}: {again}")
    t = r.get("t")
    if isinstance(t, bool) or not isinstance(t, (int, float)) or not math.isfinite(t):
        return f"the rehearsal record has no time: {again}"
    txs = {s.get("step"): s.get("tx") for s in r.get("steps", [])}
    for step in SENT:
        tx = txs.get(step)
        if not isinstance(tx, str) or not re.fullmatch(r"(?:0x)?[0-9a-fA-F]{16,256}", tx):
            return f"the rehearsal record has no transaction for its {step} order, so Lighter cannot confirm it: {again}"
        try:
            info = client.tx(tx)
        except RuntimeError as e:  # Lighter answered, and not with this transaction
            from fuze.agent import _plain
            return f"Lighter testnet does not confirm the rehearsal's {step} order ({_plain(e)}): {again}"
        except Exception as e:  # network, testnet down: we cannot confirm, so we do not unlock
            from fuze.agent import _plain
            return (f"could not reach Lighter testnet to confirm the rehearsal ({_plain(e)}). Mainnet stays locked "
                    "until it can be confirmed: try again later")
        if not isinstance(info, dict) or info.get("account_index") != acct or info.get("api_key_index") != idx:
            return (f"Lighter testnet shows the rehearsal's {step} order as sent by another account or API key "
                    f"than testnet account {acct} key index {idx}: {again}")
        when = info.get("queued_at") or info.get("executed_at")  # milliseconds
        if isinstance(when, bool) or not isinstance(when, (int, float)) or abs(when / 1000 - t) > TX_WINDOW_S:
            return f"Lighter testnet shows the rehearsal's {step} order at another time than the record: {again}"
    return ""


def blockers(cfg, mode: str | None = None) -> list:
    """What is missing before the agent may run in `mode` (default: the configured one). Reads no key, no network."""
    mode = mode or cfg["mode"]
    if mode == "simulation":
        return []
    out = []
    if not sdk_installed():
        out.append("the Lighter SDK is not installed: " + config.pip_hint("mcp,lighter"))
    if cfg[f"{mode}_account"] is None:
        out.append(f"no Lighter {mode} account index: run `fuze keys {mode}`")
    if keys.state(mode) != "set":
        out.append(f"no Lighter {mode} API key stored: run `fuze keys {mode}`")
    if mode == "mainnet" and (why := rehearsal_problem()):
        out.append(why)
    return out


def rehearse(ex, sleep=time.sleep, say=print, coin: str = "BTC") -> dict:
    """The testnet rehearsal, on a venue (normally Lighter testnet). Every step is confirmed by reading the account:
      open     buy twice the smallest order Lighter takes; the account shows the position
      guard    the emergency stop for one half, as far from the price as the agent sets it; the account shows it, and
               does not take it for a take profit / stop loss
      protect  a reduce-only take profit (+3%) and stop loss (-3%) for the other half, one cancels the other; the
               account shows them beside the emergency stop
               (3%: they trigger on the mark price, which on testnet's thin book can sit 1% from the last trade)
      cancel   cancel the take profit and stop loss; the account shows none, and the emergency stop still rests
      unguard  cancel the emergency stop; the account shows none
      close    a reduce-only market order for the whole position; the account shows it flat
    On a failure it cancels and closes what it opened. Returns the record for rehearsal.json."""
    steps = []
    rec = {"ok": False, "net": getattr(ex, "net", None), "account": getattr(ex, "index", None),
           "key_index": getattr(getattr(ex, "c", None), "key_index", None),
           "machine": machine(), "version": __version__, "t": time.time(), "steps": steps}

    def read():
        sleep(ex.settle_s)
        return ex.account(fresh=True)

    def step(name, ok, tx=None, detail=""):
        steps.append({"step": name, "ok": bool(ok), "tx": tx, "detail": detail})
        say(f"  [{'ok' if ok else 'NO'}] {name}: {detail}")
        return ok

    a = ex.account(fresh=True)
    if a["positions"] or a["brackets"] or a["guards"]:
        say("  The testnet account must hold no position and no take profit / stop loss to rehearse. Nothing was sent.")
        return rec
    px = ex.price(coin)
    if not px:
        say(f"  No {coin} price from the exchange. Nothing was sent.")
        return rec
    from fuze.follow import GUARD_FRAC
    units = 2 * ex.smallest(coin, px)  # one half under the pair, one under the emergency stop, as when following
    try:
        worst = ex.worst(px, units, False)
        tx = ex.market(coin, units, px, worst, False)
        held = read()["positions"].get(coin, 0.0)
        if not step("open", held > 0, tx, f"bought {units:g} {coin} near {px:,.2f}; the account shows {held:+g}" + (
                "" if held > 0 else f". Lighter took the order but nothing filled: nobody was selling at {worst:,.2f} "
                                    "or less. Its order book can be thin; try again in a few minutes")):
            return rec
        half = ex.round(coin, held / 2)
        tx = ex.guard(coin, half, px * (1 - GUARD_FRAC), px)
        a = read()
        ok = coin in a["guards"] and not a["brackets"]
        if not step("guard", ok, tx, f"emergency stop for {half:g} {coin} at {px * (1 - GUARD_FRAC):,.2f} " + (
                "shown on the account" if ok else "NOT shown on the account" if coin not in a["guards"]
                else "shown, but taken for a take profit / stop loss")):
            return rec
        tx = ex.protect(coin, half, px * 1.03, px * 0.97, 0)
        a = read()
        ok = 0 in a["brackets"] and coin in a["guards"]
        if not step("protect", ok, tx, "take profit and stop loss " + ("shown" if 0 in a["brackets"] else "NOT shown")
                    + " on the account" + ("" if coin in a["guards"] else "; the emergency stop is gone")):
            return rec
        ex.cancel(coin)
        a = read()
        ok = not a["brackets"] and coin in a["guards"]
        if not step("cancel", ok, None, "take profit and stop loss " + ("still shown" if a["brackets"] else "gone")
                    + ("; the emergency stop still rests" if coin in a["guards"] else "; the emergency stop went too")):
            return rec
        ex.unguard(coin)
        a = read()
        if not step("unguard", coin not in a["guards"], None,
                    "none left" if coin not in a["guards"] else "the emergency stop is still shown"):
            return rec
        tx = ex.market(coin, -held, px, ex.worst(px, -held, True), True)
        left = read()["positions"].get(coin, 0.0)
        step("close", abs(left) < 1e-12, tx, "flat" if abs(left) < 1e-12 else f"still holds {left:+g}")
    except Exception as e:
        from fuze.agent import _plain
        step(STEPS[len(steps)] if len(steps) < len(STEPS) else "close", False, None, _plain(e))
    finally:
        rec["ok"] = [s["step"] for s in steps if s["ok"]] == list(STEPS)
        if not rec["ok"]:
            try:
                ex.flatten()
                left = read()
                say("  Cleaned up: " + ("the account is flat." if not left["positions"] and not left["brackets"] and not left["guards"]
                                        else f"CHECK THE ACCOUNT, it still shows {left['positions']}."))
            except Exception as e:
                from fuze.agent import _plain
                say(f"  Clean-up failed ({_plain(e)}): CHECK THE ACCOUNT on the explorer.")
    return rec

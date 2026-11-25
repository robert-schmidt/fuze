"""Mode gating, keys and the testnet rehearsal. Every exchange here is the fake one."""

import asyncio
import io
import json
import logging
import sys
import types

import pytest

from conftest import payload
from fake_lighter import FakeLighter
from fuze import cli, config, keys, lighter_venue, modes
from fuze.agent import Agent
from fuze.lighter_venue import LighterVenue

KEY = "0x" + "5e" * 40  # a made-up API key; it must never show up anywhere but its own store


class Tty(io.StringIO):
    def isatty(self):
        return True


def answers(monkeypatch, *replies, secret=KEY):
    it = iter(replies)
    monkeypatch.setattr("sys.stdin", Tty())
    monkeypatch.setattr("builtins.input", lambda _: next(it))
    monkeypatch.setattr("getpass.getpass", lambda _: secret)


@pytest.fixture
def exchanges(monkeypatch):
    """A fake Lighter per network, the SDK counted as installed, and keys and account indexes set."""
    fakes = {"testnet": FakeLighter(), "mainnet": FakeLighter(balance=500.0)}
    monkeypatch.setattr(lighter_venue, "connect", lambda cfg, net: fakes[net])
    monkeypatch.setattr(modes, "sdk_installed", lambda: True)
    monkeypatch.setenv("FUZE_NO_KEYRING", "1")
    config.save({**config.DEFAULTS, "testnet_account": 77, "mainnet_account": 5})
    keys.save("testnet", KEY)
    keys.save("mainnet", KEY)
    return fakes


def rehearsed(fakes):
    ex = LighterVenue(fakes["testnet"], config.home() / "lighter-testnet.json", net="testnet", index=77)
    rec = modes.rehearse(ex, sleep=lambda s: None, say=lambda s: None)
    config.write_json(config.home() / "rehearsal.json", rec)
    return rec


# --- the rehearsal --------------------------------------------------------------------------------------------------

def test_rehearsal_confirms_every_step_by_reading_the_account(exchanges):
    rec = rehearsed(exchanges)
    assert rec["ok"] and [s["step"] for s in rec["steps"]] == list(modes.STEPS) and all(s["ok"] for s in rec["steps"])
    f = exchanges["testnet"]
    assert [s[0] for s in f.sent] == ["market", "tp_sl", "cancel", "cancel", "market"]
    assert f.sent[0][2] == 20 and f.sent[-1][5] is True  # the smallest order, closed reduce-only
    assert f.pos[1] == 0 and f.orders == {} and modes.rehearsal_problem() == ""


def test_failed_rehearsal_cleans_up_and_keeps_mainnet_locked(exchanges):
    exchanges["testnet"].pair = "hidden"
    rec = rehearsed(exchanges)
    assert not rec["ok"] and rec["steps"][-1] == {"step": "protect", "ok": False, "tx": "cd" * 32,
                                                  "detail": "take profit and stop loss NOT shown on the account"}
    assert exchanges["testnet"].pos[1] == 0  # closed again
    assert "did not pass" in modes.rehearsal_problem()


def test_rehearsal_needs_a_flat_account(exchanges):
    exchanges["testnet"].pos[0] = 0.1
    assert not rehearsed(exchanges)["ok"] and exchanges["testnet"].sent == []


@pytest.mark.parametrize("field,value,why", [("machine", "elsewhere", "another machine"),
                                             ("version", "0.0.1", "with FUZE 0.0.1"),
                                             ("net", "mainnet", "not from testnet")])
def test_rehearsal_is_for_this_machine_and_version(exchanges, field, value, why):
    rec = rehearsed(exchanges)
    config.write_json(config.home() / "rehearsal.json", {**rec, field: value})
    assert why in modes.rehearsal_problem()


def test_cli_rehearse(exchanges, monkeypatch, capsys):
    answers(monkeypatch, "yes")
    assert cli.main(["rehearse"]) == 0 and "PASSED" in capsys.readouterr().out
    monkeypatch.setattr("sys.stdin", io.StringIO("yes\n"))
    assert cli.main(["rehearse"]) == 2  # not a terminal


# --- changing the mode ----------------------------------------------------------------------------------------------

def test_testnet_needs_a_terminal_and_raise(exchanges, monkeypatch, capsys):
    monkeypatch.setattr("sys.stdin", io.StringIO("RAISE\n"))
    assert cli.main(["mode", "testnet"]) == 2 and config.load()["mode"] == "simulation"
    answers(monkeypatch, "raise")
    assert cli.main(["mode", "testnet"]) == 1 and config.load()["mode"] == "simulation"
    answers(monkeypatch, "RAISE")
    assert cli.main(["mode", "testnet"]) == 0 and config.load()["mode"] == "testnet"
    out = capsys.readouterr().out
    assert "balance $1,000.00" in out and "testnet.app.lighter.xyz/explorer/accounts/77" in out
    assert exchanges["testnet"].sent == []  # reading only


def test_mainnet_is_locked_without_the_rehearsal(exchanges, monkeypatch, capsys):
    answers(monkeypatch, "RAISE", "REAL MONEY")
    assert cli.main(["mode", "mainnet"]) == 2 and config.load()["mode"] == "simulation"
    assert "fuze rehearse" in capsys.readouterr().out
    config.save({**config.load(), "mode": "mainnet"})  # even a hand-edited config.json does not start it
    assert cli.main(["run"]) == 2 and "rehearsal" in capsys.readouterr().out


def test_mainnet_after_the_rehearsal_needs_raise_and_the_phrase(exchanges, monkeypatch, capsys):
    rehearsed(exchanges)
    answers(monkeypatch, "RAISE", "real money")
    assert cli.main(["mode", "mainnet"]) == 1 and config.load()["mode"] == "simulation"
    answers(monkeypatch, "RAISE", "REAL MONEY")
    assert cli.main(["mode", "mainnet"]) == 0 and config.load()["mode"] == "mainnet"
    assert "app.lighter.xyz/explorer/accounts/5" in capsys.readouterr().out


def test_mode_change_refused_while_positions_are_open(exchanges, monkeypatch, capsys):
    answers(monkeypatch, "RAISE")
    cli.main(["mode", "testnet"])
    exchanges["testnet"].pos[1] = -0.003
    rehearsed_ok = {"ok": True, "net": "testnet", "machine": modes.machine(), "version": cli.__version__,
                    "steps": [{"step": s, "ok": True} for s in modes.STEPS]}
    config.write_json(config.home() / "rehearsal.json", rehearsed_ok)
    answers(monkeypatch)  # no question may be asked
    assert cli.main(["mode", "simulation"]) == 2 and "Positions are open in testnet" in capsys.readouterr().out
    assert config.load()["mode"] == "testnet"
    exchanges["testnet"].pos[1] = 0.0
    assert cli.main(["mode", "simulation"]) == 0 and config.load()["mode"] == "simulation"  # safer: no RAISE


def test_mode_change_refused_when_the_new_account_is_not_empty(exchanges, monkeypatch, capsys):
    exchanges["testnet"].pos[0] = 0.5
    answers(monkeypatch, "RAISE")
    assert cli.main(["mode", "testnet"]) == 2 and "sub-account of its own" in capsys.readouterr().out


def test_mode_change_refused_while_the_agent_runs(exchanges, monkeypatch, capsys):
    lock = cli._lock()
    answers(monkeypatch, "RAISE")
    assert cli.main(["mode", "testnet"]) == 2 and "Stop it first" in capsys.readouterr().out
    lock.close()


def test_simulated_positions_block_leaving_simulation(exchanges, monkeypatch, capsys):
    from fuze.dry import DryExchange
    DryExchange(config.home(), 1000.0).market("BTC", 0.01, 60000.0)
    answers(monkeypatch, "RAISE")
    assert cli.main(["mode", "testnet"]) == 2 and "Positions are open in simulation" in capsys.readouterr().out


def test_missing_keys_block_the_mode(monkeypatch, capsys):
    monkeypatch.setattr(modes, "sdk_installed", lambda: False)
    config.save(dict(config.DEFAULTS))
    answers(monkeypatch, "RAISE")
    assert cli.main(["mode", "testnet"]) == 2
    out = capsys.readouterr().out
    assert "fuze-agent[lighter]" in out and "fuze keys testnet" in out


def test_init_asks_the_mode(exchanges, monkeypatch, capsys):
    (config.home() / "config.json").unlink()
    answers(monkeypatch, "testnet", "", "", "", "", "", "", "77", "", "RAISE")  # mode, sizing x5, save, account, index
    assert cli.main(["init"]) == 0 and config.load()["mode"] == "testnet"


def test_init_without_a_terminal_stays_in_simulation(capsys):
    assert cli.main(["init", "--yes", "--mode", "testnet"]) == 2 and config.load()["mode"] == "simulation"
    assert "fuze mode testnet" in capsys.readouterr().out


def test_check_in_a_live_mode_reads_and_sends_nothing(exchanges, monkeypatch, capsys):
    config.save({**config.load(), "mode": "testnet"})
    cli.main(["check"])
    out = capsys.readouterr().out
    assert "[ok] Lighter testnet account read (no order sent): balance $1,000.00" in out
    assert "[ok] Lighter testnet API key: set" in out and exchanges["testnet"].sent == []


def test_note_when_the_follower_is_more_real_than_the_source():
    assert "REAL money" in modes.realer_note("mainnet", "paper") and "practice money" in modes.realer_note("mainnet",
                                                                                                         "paper")
    assert "test money" in modes.realer_note("testnet", "paper")
    assert modes.realer_note("simulation", "mainnet") == "" and modes.realer_note("mainnet", "mainnet") == ""


# --- keys -----------------------------------------------------------------------------------------------------------

def test_keys_are_typed_hidden_at_a_terminal_only(monkeypatch, capsys):
    monkeypatch.setenv("FUZE_NO_KEYRING", "1")
    config.save(dict(config.DEFAULTS))
    monkeypatch.setattr("sys.stdin", io.StringIO(KEY + "\n"))
    assert cli.main(["keys", "testnet"]) == 2 and keys.state("testnet") == "missing"
    with pytest.raises(SystemExit):
        cli.main(["keys", "testnet", "--key", KEY])  # never a command-line argument
    answers(monkeypatch, "77", "")
    assert cli.main(["keys", "testnet"]) == 0
    assert keys.state("testnet") == "set" and keys.load("testnet") == KEY[2:]
    f = config.home() / "lighter-testnet.key"
    assert f.stat().st_mode & 0o777 == 0o600 and config.load()["testnet_account"] == 77
    assert KEY[2:] not in capsys.readouterr().out + json.dumps(config.load())
    answers(monkeypatch, "", "", secret="not a key")
    assert cli.main(["keys", "testnet"]) == 2 and keys.load("testnet") == KEY[2:]  # a bad key changes nothing


def test_os_keyring_is_used_when_available(monkeypatch):
    store = {}
    fail = types.ModuleType("keyring.backends.fail")
    fail.Keyring = type("Keyring", (), {})
    kr = types.ModuleType("keyring")
    kr.get_keyring = lambda: object()
    kr.set_password = lambda s, u, p: store.__setitem__((s, u), p)
    kr.get_password = lambda s, u: store.get((s, u))
    kr.delete_password = lambda s, u: store.pop((s, u))
    monkeypatch.setitem(sys.modules, "keyring", kr)
    monkeypatch.setitem(sys.modules, "keyring.backends", types.ModuleType("keyring.backends"))
    monkeypatch.setitem(sys.modules, "keyring.backends.fail", fail)
    monkeypatch.delenv("FUZE_NO_KEYRING", raising=False)
    assert keys.save("mainnet", KEY) == "the OS keyring"
    assert store == {("fuze-agent", "lighter-mainnet"): KEY[2:]}
    assert not (config.home() / "lighter-mainnet.key").exists()
    assert keys.state("mainnet") == "set" and keys.load("mainnet") == KEY[2:]
    keys.delete("mainnet")
    assert store == {} and keys.state("mainnet") == "missing"


def test_no_keyring_backend_falls_back_to_a_private_file(monkeypatch):
    fail = types.ModuleType("keyring.backends.fail")
    fail.Keyring = type("Keyring", (), {})
    kr = types.ModuleType("keyring")
    kr.get_keyring = lambda: fail.Keyring()
    monkeypatch.setitem(sys.modules, "keyring", kr)
    monkeypatch.setitem(sys.modules, "keyring.backends", types.ModuleType("keyring.backends"))
    monkeypatch.setitem(sys.modules, "keyring.backends.fail", fail)
    monkeypatch.delenv("FUZE_NO_KEYRING", raising=False)
    assert keys.save("testnet", KEY).endswith("lighter-testnet.key")


def test_sdk_errors_never_quote_the_key(monkeypatch):
    """LighterClient with a stand-in SDK whose errors contain the key."""
    sdk = types.ModuleType("lighter")
    sc = types.ModuleType("lighter.signer_client")
    sc.CreateOrderTxReq = object

    class Refuses:
        def __init__(self, **kw):
            raise ValueError("bad key " + kw["api_private_keys"][4])

    class Mismatch:
        def __init__(self, **kw):
            self.kw = kw

        def check_client(self):
            return "key " + self.kw["api_private_keys"][4] + " does not match"

        async def close(self):
            pass

    monkeypatch.setitem(sys.modules, "lighter", sdk)
    monkeypatch.setitem(sys.modules, "lighter.signer_client", sc)
    for cls in (Refuses, Mismatch):
        sdk.SignerClient = cls
        with pytest.raises(RuntimeError) as e:
            lighter_venue.LighterClient("testnet", 77, 4, KEY)
        assert KEY[2:] not in str(e.value) and "5e5e" not in str(e.value)


def test_chain_id_is_explicit(monkeypatch):
    sdk = types.ModuleType("lighter")
    sc = types.ModuleType("lighter.signer_client")
    sc.CreateOrderTxReq = object
    seen = {}

    class Client:
        def __init__(self, **kw):
            seen.update(kw)

        def check_client(self):
            return None

    sdk.SignerClient = Client
    monkeypatch.setitem(sys.modules, "lighter", sdk)
    monkeypatch.setitem(sys.modules, "lighter.signer_client", sc)
    lighter_venue.LighterClient("testnet", 77, 4, KEY)
    assert (seen["url"], seen["chain_id"]) == ("https://api.testnet.lighter.xyz", 300)
    lighter_venue.LighterClient("mainnet", 5, 4, KEY)
    assert (seen["url"], seen["chain_id"]) == ("https://mainnet.zklighter.elliot.ai", 304)


def test_the_key_never_reaches_logs_status_or_any_mcp_tool(exchanges, signer, caplog, monkeypatch, capsys):
    from fuze.mcp_server import build

    caplog.set_level(logging.DEBUG)
    config.save({**config.load(), "mode": "testnet"})
    clock = lambda: 1010.0  # noqa: E731
    a = Agent(config.load(), home=config.home(), keys=signer.keys, clock=clock, sleep=lambda s: None,
              exchange=LighterVenue(exchanges["testnet"], config.home() / "lighter-testnet.json", clock, "testnet", 77))
    exchanges["testnet"].fill = "half"
    a.handle(json.dumps(signer.envelope(payload(ts=1005.0, expires=1065.0))))
    a.handle(json.dumps(signer.envelope({"bad": KEY})))
    cli.main(["status"])
    cli.main(["check"])
    cli.main(["keys"])
    cli.main(["mode"])
    app = build()
    outputs = []
    for name, args in [("status", {}), ("signal", {}), ("trades", {"n": 50}), ("setup_check", {}),
                       *[("docs", {"topic": t}) for t in ("modes", "setup", "safety", "status")]]:
        res = asyncio.run(app.call_tool(name, args))
        outputs.append("".join(c.text for c in res.content))
    files = "".join(p.read_text(errors="ignore") for p in config.home().iterdir()
                    if p.is_file() and p.name != "lighter-testnet.key" and p.name != "lighter-mainnet.key")
    seen = caplog.text + capsys.readouterr().out + "".join(outputs) + files
    assert KEY[2:] not in seen and KEY[2:12] not in seen
    assert json.loads(outputs[0])["api_key"] == {"testnet": "set", "mainnet": "set"}  # "set", and nothing more


def test_no_mcp_tool_takes_a_key_or_changes_the_mode():
    from fuze.mcp_server import build

    tools = asyncio.run(build().list_tools())
    for t in tools:
        props = set(t.input_schema.get("properties", {}))
        assert not {"key", "api_key", "secret", "mode", "account", "private_key"} & props
        assert "mode" not in t.name and "key" not in t.name

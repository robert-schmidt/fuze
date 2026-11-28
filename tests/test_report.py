"""What the agent reports: the wire format, the key, the handle, the result index, the queue, the share commands, and
that nothing in reporting can raise into the trading loop or hold it up. No network: the sender is replaced."""

import base64
import hashlib
import json
import stat
import threading
import time

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from conftest import TEST_KEYS, payload
from fuze import cli, config, report
from fuze.agent import Agent
from fuze.report import Equity, Reporter, handle

BASE = {"v", "seq", "ts", "kind", "ver", "mode", "public"}
CONTRACT = {"hello": BASE | {"settings", "handle"}, "beat": BASE | {"equity", "x", "state"},
            "trade": BASE | {"coin", "side", "why", "part", "risk", "x", "px", "ref", "rev", "late", "result"},
            "prove": BASE | {"wallet"}, "bye": BASE}
SETTINGS = {"size_mode", "percent", "max_x", "daily_loss_frac", "ceiling", "cap", "risk_allowed", "coins"}


class Wire:
    """Stands in for the server: keeps every body, answers like fellow.py (409 until the agent said hello)."""

    def __init__(self, fail=None):
        self.bodies, self.known, self.fail = [], set(), fail

    def __call__(self, body: bytes):
        if self.fail:
            self.fail()
        env = json.loads(body)
        self.bodies.append(env)
        p = json.loads(env["payload"])
        if p["kind"] == "hello":
            self.known.add(env["key"])
        elif env["key"] not in self.known:
            return 409, {"error": "unknown agent: send hello first"}
        aid = hashlib.sha256(base64.b64decode(env["key"])).hexdigest()[:16]
        ans = {"ok": True, "id": aid}
        if p["kind"] == "hello" and p.get("handle"):
            h = handle(p["handle"])
            ans["handle"] = {**h, "verified": h["kind"] == "github"}
        if p["kind"] == "prove":
            ans["wallet"] = True
        return 200, ans

    def payloads(self):
        return [json.loads(e["payload"]) for e in self.bodies]


def cfg(**kw):
    return config.validate({"max_position_usd": 500.0, **kw})


def reporter(wire, clock=lambda: 1_800_000_000.0, **kw):
    return Reporter(cfg(**kw), home=config.ensure_home(), clock=clock, send=wire, start=False)


# --- the wire format -----------------------------------------------------------------------------------------------

def test_envelopes_verify_and_carry_only_fields_from_the_contract(fuze_home):
    wire = Wire()
    r = reporter(wire, public=True, handle="https://github.com/Octo")
    r.hello(cfg(public=True, handle="github.com/Octo"))
    r.beat(1234.5, {"BTC": -0.003}, {"BTC": 60000.0}, "following")
    r.trade("BTC", "sell", "open", 0.18, 59994.0, ref=60000.0, rev=3, late=0.4, part=None, result=None,
            snap=(1234.5, {"BTC": -0.003}, {"BTC": 60000.0}))
    r.trade("BTC", "buy", "tp", 0.12, 59400.0, part="scalp", result=0.36, risk=12)
    r.trade("ETH", "buy", "close", 0.1, 2000.0, part="trend", risk=101)  # not a score: left out
    r.bye()
    r._drain()
    assert [p["kind"] for p in wire.payloads()] == ["hello", "beat", "trade", "trade", "trade", "bye"]
    for env in wire.bodies:
        raw = base64.b64decode(env["key"])
        Ed25519PublicKey.from_public_bytes(raw).verify(base64.b64decode(env["sig"]), env["payload"].encode())
        assert hashlib.sha256(raw).hexdigest()[:16] == r.id
        p = json.loads(env["payload"])
        assert set(p) <= CONTRACT[p["kind"]], p
        assert p["v"] == 1 and p["ver"] == "0.6.0" and p["mode"] == "simulation" and p["public"] is True
        assert env["payload"] == json.dumps(p, separators=(",", ":")) and len(json.dumps(env)) <= report.MAX_BODY
        assert "1234" not in env["payload"] and "500" not in env["payload"]  # no balance, no dollar cap
    hello, beat, trade = wire.payloads()[:3]
    st = hello["settings"]
    assert set(st) <= SETTINGS and st["cap"] is True and st["ceiling"] is False
    assert st["risk_allowed"] == 60 and st["coins"] == ["BTC", "ETH", "HYPE", "LIT"]
    tp, close = wire.payloads()[3:5]
    assert (tp["part"], tp["risk"]) == ("scalp", 12) and close["part"] == "trend" and "risk" not in close
    assert hello["handle"] == "https://github.com/Octo"
    assert beat["equity"] == 1.0 and beat["state"] == "following"
    assert beat["x"] == {"BTC": round(-0.003 * 60000 / 1234.5, 4)}
    assert [trade[k] for k in ("coin", "side", "why", "x", "ref", "rev")] == ["BTC", "sell", "open", 0.18, 60000.0, 3]
    seqs = [p["seq"] for p in wire.payloads()]
    assert seqs == sorted(set(seqs))


def test_private_sends_no_handle_and_fixed_mode_no_amount(fuze_home):
    wire = Wire()
    r = reporter(wire, handle="https://x.com/someone", size_mode="fixed", fixed_usd=777.0)
    r.hello(cfg(handle="https://x.com/someone", size_mode="fixed", fixed_usd=777.0))
    r._drain()
    p = wire.payloads()[0]
    assert p["public"] is False and "handle" not in p and "percent" not in p["settings"] and "777" not in json.dumps(p)


def test_seq_only_goes_up_across_restarts(fuze_home):
    wire = Wire()
    reporter(wire, clock=lambda: 1_800_000_000.0).send_hello()
    reporter(wire, clock=lambda: 1_700_000_000.0).send_hello()  # a restart with the clock set back
    a, b = (p["seq"] for p in wire.payloads())
    assert a == 1_800_000_000_000 and b == a + 1


def test_the_409_answer_sends_hello_then_the_report_again(fuze_home):
    wire = Wire()
    r = reporter(wire)
    r.trade("ETH", "sell", "open", 0.04, 2000.0)
    r._drain()
    assert [p["kind"] for p in wire.payloads()] == ["trade", "hello", "trade"] and not r.q


# --- the agent's key -----------------------------------------------------------------------------------------------

def test_the_key_file_is_private_and_never_printed(fuze_home, capsys):
    r = reporter(Wire())
    path = fuze_home / "agent.key"
    assert stat.S_IMODE(path.stat().st_mode) == 0o600 and len(r.id) == 16
    secret = path.read_text()
    from cryptography.hazmat.primitives import serialization
    raw = serialization.load_pem_private_key(secret.encode(), None).private_bytes_raw()
    assert cli.main(["share"]) == 0
    out = capsys.readouterr().out
    assert r.id in out and "private" in out
    body = secret.split("-----")[2].strip()
    for shown in (body, raw.hex(), base64.b64encode(raw).decode()):
        assert shown not in out
    assert reporter(Wire()).id == r.id  # the same identity after a restart


def test_a_malformed_key_file_is_said_and_never_replaced(fuze_home, capsys):
    config.ensure_home()
    (fuze_home / "agent.key").write_text("not a key")
    wire = Wire()
    r = reporter(wire)
    r.hello(cfg())
    r._drain()
    assert "not a key FUZE made" in r.problem and wire.bodies == []
    assert (fuze_home / "agent.key").read_text() == "not a key"
    assert cli.main(["share"]) == 1 and "Reports are not sent" in capsys.readouterr().out


# --- the handle ----------------------------------------------------------------------------------------------------

@pytest.mark.parametrize("text,want", [
    ("https://x.com/fuze_trade", ("x", "fuze_trade", "https://x.com/fuze_trade")),
    ("twitter.com/@Abc/", ("x", "Abc", "https://x.com/Abc")),
    ("@name", None),
    ("x.com/@name", ("x", "name", "https://x.com/name")),
    ("https://mobile.twitter.com/someone?ref=1", ("x", "someone", "https://x.com/someone")),
    ("https://github.com/robert-schmidt?tab=repos", ("github", "robert-schmidt", "https://github.com/robert-schmidt")),
    ("HTTPS://WWW.GITHUB.COM/a", ("github", "a", "https://github.com/a")),
    ("https://x.com/home", None), ("https://github.com/settings", None), ("https://github.com/a--b", None),
    ("https://github.com/-a", None), ("https://x.com/" + "a" * 16, None), ("https://x.com/a/status/1", None),
    ("https://evil.example/x.com/a", None), ("https://gitlab.com/a", None), ("javascript:alert(1)", None),
    ("x.com/a b", None), (7, None), ("", None),
])
def test_handle_table(text, want):
    h = handle(text)
    assert (h and (h["kind"], h["name"], h["url"])) == want


def test_config_keeps_the_rebuilt_handle_and_refuses_others(fuze_home):
    assert config.validate({"handle": "twitter.com/@Abc"})["handle"] == "https://x.com/Abc"
    with pytest.raises(ValueError, match="X or a GitHub profile"):
        config.validate({"handle": "https://evil.example/a"})
    with pytest.raises(ValueError, match="public"):
        config.validate({"public": "yes"})
    assert "public" not in config.LIMITS and "handle" not in config.LIMITS


# --- the result index ----------------------------------------------------------------------------------------------

def test_equity_leaves_out_deposits_and_withdrawals(fuze_home):
    path = config.ensure_home() / "equity.json"
    e = Equity(path)
    held = {"BTC": 0.01}
    assert e.step(1000.0, held, {"BTC": 60000.0}) == 1.0
    assert e.step(1010.0, held, {"BTC": 61000.0}) == pytest.approx(1.01)  # a winning step: +$10 on $1,000
    assert e.step(1510.0, held, {"BTC": 61000.0}) == pytest.approx(1.01)  # a deposit of $500: no return
    assert e.step(1500.0, held, {"BTC": 60000.0}) == pytest.approx(1.01 * 1500 / 1510)  # a losing step
    after_loss = e.index
    assert e.step(1000.0, held, {"BTC": 60000.0}) == pytest.approx(after_loss)  # a withdrawal of $500
    assert e.step(997.0, held, {"BTC": 60000.0}) == pytest.approx(after_loss * 0.997)  # fees and funding count
    assert Equity(path).index == pytest.approx(after_loss * 0.997)  # a restart continues it
    assert e.step(1200.0, {}, {}, mode="testnet") == pytest.approx(after_loss * 0.997)  # another account: a new base


# --- the queue: bounded, trades kept longest, nothing raises -------------------------------------------------------

def test_the_queue_drops_the_oldest_beat_first_and_keeps_trades(fuze_home):
    r = reporter(Wire())
    for i in range(10):
        r.trade("BTC", "sell", "open", 0.1, 60000.0 + i)
    for i in range(500):
        r.beat(1000.0, {}, {}, "following")
    assert len(r.q) == report.QUEUE and sum(x["kind"] == "trade" for x in r.q) == 10
    for i in range(300):
        r.trade("ETH", "buy", "add", 0.1, 2000.0)
    assert len(r.q) == report.QUEUE and all(x["kind"] == "trade" for x in r.q)


def test_a_failed_trade_is_tried_again_at_most_20_times_and_a_beat_once(fuze_home):
    def down():
        raise OSError("no route")

    wire = Wire(fail=down)
    r = reporter(wire)
    r.beat(1000.0, {}, {}, "flat")
    r._drain()
    assert not r.q  # a beat is not tried again
    r.trade("BTC", "sell", "open", 0.1, 60000.0)
    for _ in range(report.TRADE_TRIES - 1):
        r._drain()
    assert len(r.q) == 1 and r.q[0]["tries"] == report.TRADE_TRIES - 1
    r._drain()
    assert not r.q


def test_reporter_calls_never_raise(fuze_home):
    r = reporter(Wire())
    r.trade(None, "up", "why", "big", None)
    r.beat("lots", None, None, None)
    r.hello(None)
    r.trade("BTC", "sell", "open", float("nan"), 60000.0)
    assert r.q == []


def signal_run(rep, signer, steps=3):
    """A simulated agent following a few signals; returns it."""
    config.save(dict(config.DEFAULTS))
    now = [1010.0]
    a = Agent(home=config.ensure_home(), keys=signer.keys, clock=lambda: now[0], reporter=rep)
    for seq in range(1, steps + 1):
        now[0] = 1005.0 + 5 * seq
        a.handle(json.dumps(signer.envelope(payload(seq=seq, ts=now[0], expires=now[0] + 60))))
    return a


def test_a_sender_that_always_raises_changes_nothing_in_trading(fuze_home, signer):
    def boom(body):
        raise RuntimeError("the server exploded")

    rep = Reporter(config.validate({}), home=config.ensure_home(), send=boom)
    a = signal_run(rep, signer)
    assert a.acct["positions"]["BTC"] == pytest.approx(-0.003) and a.acct["brackets"] == {"BTC": 7}
    time.sleep(0.2)
    assert rep.thread.is_alive()


def test_a_sender_that_hangs_never_holds_up_trading(fuze_home, signer):
    release = threading.Event()
    rep = Reporter(config.validate({}), home=config.ensure_home(), send=lambda body: release.wait() and (200, {}))
    try:
        t0 = time.monotonic()
        a = signal_run(rep, signer)
        for _ in range(500):
            a._beat(1020.0, {})
        assert time.monotonic() - t0 < 5
        assert a.acct["positions"]["BTC"] == pytest.approx(-0.003) and len(rep.q) <= report.QUEUE
        assert any(x["kind"] == "trade" for x in rep.q)
    finally:
        release.set()


# --- the agent's calls ---------------------------------------------------------------------------------------------

class Recorder:
    def __init__(self):
        self.calls = []

    def __getattr__(self, name):
        return lambda *a, **kw: self.calls.append((name, a, kw))

    def of(self, name):
        return [(a, kw) for n, a, kw in self.calls if n == name]


def test_a_full_run_reports_hello_trades_a_beat_and_bye(fuze_home):
    from test_agent import Server
    server, rec = Server(), Recorder()
    agent = Agent(config.validate({"server": server.url}), home=config.ensure_home(), keys=TEST_KEYS,
                  clock=lambda: 1010.0, reporter=rec)
    stop = threading.Event()
    t = threading.Thread(target=agent.run, args=(stop,), daemon=True)
    t.start()
    deadline = time.time() + 10
    while time.time() < deadline and len(rec.of("trade")) < 3:
        time.sleep(0.05)
    stop.set()
    t.join(5)
    server.httpd.shutdown()
    names = [n for n, _, _ in rec.calls]
    assert names[0] == "hello" and names[-1] == "bye" and names.count("hello") == 1 and "beat" in names
    trades = [(a, kw) for a, kw in rec.of("trade")]
    assert [(a[0], a[1], a[2]) for a, _ in trades] == [("BTC", "sell", "open"), ("ETH", "sell", "open"),
                                                       ("BTC", "buy", "reduce")]  # revision 2 ends the short-term trade
    (btc, kw), (eth, kw2), (close, kw3) = trades
    assert btc[3] == pytest.approx(0.18, rel=1e-3) and btc[4] == pytest.approx(60000 * (1 - 0.0001))  # the fill price
    assert kw["ref"] == 60000.0 and kw["rev"] == 1 and kw["late"] == 0.0 and kw["result"] is None
    assert eth[3] == pytest.approx(0.04, rel=1e-3) and kw2["ref"] == 2000.0
    assert (kw2["part"], kw2["risk"]) == ("trend", 6)  # Ether has only its trend part
    # a close's fill price is not known: the result is worked out at the reference price, from the entry
    assert kw3["rev"] == 2 and kw3["result"] == pytest.approx(-0.002 * (60000 - 59994) / 1000 * 100, rel=1e-2)
    assert (kw3["part"], kw3["risk"]) == ("scalp", 12)  # the part that explains it, and the score it had
    assert kw.get("part") is None and kw.get("risk") is None  # opening both parts at once: no single part explains it
    balance, units, prices = kw3["snap"]
    assert units == {"BTC": pytest.approx(-0.001, rel=1e-3), "ETH": pytest.approx(-0.02)} and prices["ETH"] == 2000.0
    beat = rec.of("beat")[0][0]
    assert beat[3] == "no_signal"  # the first step comes from the tampered message, which is dropped


def test_a_stop_loss_found_filled_is_reported(fuze_home, signer):
    """The scalp's stop loss fills on the (simulated) exchange between two steps: a trade with why sl, part scalp."""
    config.save(dict(config.DEFAULTS))
    rec, now = Recorder(), [1010.0]
    a = Agent(home=config.ensure_home(), keys=signer.keys, clock=lambda: now[0], reporter=rec)

    def step(seq, px):
        now[0] = 1005.0 + 5 * seq
        a.handle(json.dumps(signer.envelope(payload(
            seq=seq, ts=now[0], expires=now[0] + 60,
            targets={"BTC": {"x": -1.8, "px": px}, "ETH": {"x": -0.4, "px": 2000.0}}))))

    step(1, 60000.0)
    assert rec.of("beat")[0][0][3] == "following"
    step(2, 60500.0)  # through the stop loss at 60,420
    found = [(args, kw) for args, kw in rec.of("trade") if args[2] == "sl"]
    assert len(found) == 1
    args, kw = found[0]
    assert args[:2] == ("BTC", "buy") and args[4] == 60420.0 and kw["part"] == "scalp"
    assert args[3] == pytest.approx(0.002 * 60420 / 1000, rel=1e-2)


def test_an_emergency_stop_found_filled_is_reported(fuze_home, signer):
    from fake_lighter import FakeLighter
    from test_lighter import Clock, agent, send
    fake, c, rec = FakeLighter(), Clock(), Recorder()
    a = agent(fake, signer, c)
    a.reporter = rec
    send(a, signer, c)
    fake.stop_out(1, "guard")
    c.t += 6
    send(a, signer, c, seq=2)
    args, kw = next((args, kw) for args, kw in rec.of("trade") if args[2] == "stop")
    assert args[:2] == ("BTC", "buy") and args[4] == 72000.0 and kw["part"] == "trend"
    assert args[3] == pytest.approx(0.001 * 72000 / 1000, rel=1e-2)


# --- the share commands --------------------------------------------------------------------------------------------

@pytest.fixture
def wire(monkeypatch):
    w = Wire()
    monkeypatch.setattr(Reporter, "_http", lambda self, body: w(body))
    return w


def test_share_shows_what_is_sent(fuze_home, capsys):
    cli.main(["init"])
    capsys.readouterr()
    assert cli.main(["share"]) == 0
    out = capsys.readouterr().out
    for line in report.SENT:
        assert line in out
    assert report.NEVER in out and "src/fuze/report.py" in out and "private" in out and "/fellowship/" not in out


def test_share_public_and_private_need_a_terminal(fuze_home, monkeypatch, wire, capsys):
    import io
    cli.main(["init"])
    monkeypatch.setattr("sys.stdin", io.StringIO("https://x.com/a\n"))
    assert cli.main(["share", "public"]) == 2 and cli.main(["share", "private"]) == 2
    assert not config.load()["public"] and wire.bodies == []


def test_share_public_asks_the_link_sends_hello_and_private_undoes_it(fuze_home, monkeypatch, wire, capsys):
    from test_cli import answers
    cli.main(["init"])
    answers(monkeypatch, "https://evil.example/a", "x.com/@Fuze_Fan")
    assert cli.main(["share", "public"]) == 0
    c = config.load()
    assert c["public"] is True and c["handle"] == "https://x.com/Fuze_Fan"
    out = capsys.readouterr().out
    aid = report.agent_id(report.load_key(fuze_home))
    assert "not an X or GitHub profile link" in out and f"https://fuze.trade/fellowship/{aid}" in out
    assert "shown as you typed it" in out
    p = wire.payloads()[-1]
    assert p["kind"] == "hello" and p["public"] is True and p["handle"] == "https://x.com/Fuze_Fan"
    assert cli.main(["share"]) == 0 and "PUBLIC" in capsys.readouterr().out
    answers(monkeypatch)
    assert cli.main(["share", "private"]) == 0
    c = config.load()
    assert c["public"] is False and c["handle"] is None and wire.payloads()[-1]["public"] is False
    answers(monkeypatch)
    assert cli.main(["share", "public", "--handle", "https://evil.example/a"]) == 2 and not config.load()["public"]


def test_share_prove_github_and_lighter(fuze_home, monkeypatch, wire, capsys):
    from test_cli import answers
    from fuze import lighter_venue

    class Signer:
        def create_auth_token_with_expiry(self, life, api_key_index=None):
            assert life == 60 and api_key_index == 4
            return "170:77:4:" + "ab12" * 8, None

    class Client:
        c, key_index, closed = Signer(), 4, False

        def close(self):
            Client.closed = True

    monkeypatch.setattr(lighter_venue, "connect", lambda cfg, net: Client())
    config.save({**config.DEFAULTS, "mode": "testnet", "testnet_account": 77, "public": True,
                 "handle": "https://github.com/octo"})
    answers(monkeypatch, "", "YES")
    assert cli.main(["share", "prove"]) == 0
    out = capsys.readouterr().out
    aid = report.agent_id(report.load_key(fuze_home))
    assert f"fuze-{aid}" in out and "GitHub confirmed it" in out and "account 77 is now shown" in out
    assert "read-only" in out and "never stores it" in out and Client.closed
    p = wire.payloads()[-1]
    assert p["kind"] == "prove" and p["wallet"] == {"net": "testnet", "account": 77, "token": "170:77:4:" + "ab12" * 8}
    assert "ab12ab12" not in out and not any("ab12ab12" in f.read_text(errors="ignore")
                                             for f in fuze_home.iterdir() if f.is_file())
    answers(monkeypatch, "", "no")
    assert cli.main(["share", "prove"]) == 1 and "Nothing was sent" in capsys.readouterr().out
    config.save({**config.load(), "public": False, "handle": None})
    answers(monkeypatch)
    assert cli.main(["share", "prove"]) == 2 and "fuze share public" in capsys.readouterr().out


def test_init_asks_public_or_private_and_says_what_is_sent(fuze_home, monkeypatch, capsys):
    from test_cli import answers
    answers(monkeypatch, "", "", "", "", "", "", "", "", "yes", "github.com/octo", "")
    assert cli.main(["init"]) == 0
    c = config.load()
    assert c["public"] is True and c["handle"] == "https://github.com/octo"
    assert report.DISCLOSURE in capsys.readouterr().out
    assert cli.main(["init", "--force", "--yes"]) == 0 and config.load()["public"] is True  # not asked: kept
    assert report.DISCLOSURE in capsys.readouterr().out


def test_status_and_mcp_say_public_or_private(fuze_home, capsys):
    import asyncio
    from fuze.mcp_server import build
    config.save(dict(config.DEFAULTS))
    config.write_json(fuze_home / "status.json", {"t": 0, "mode": "simulation", "reason": "r",
                                                  "account": {"balance": 1000.0, "positions": {}, "brackets": {}}})
    assert cli.main(["status"]) == 0
    assert "reports its trades and results" in capsys.readouterr().out
    app = build()
    names = {t.name for t in asyncio.run(app.list_tools())}
    assert not any("share" in n or "public" in n for n in names)
    out = asyncio.run(app.call_tool("status", {}))
    text = json.dumps(out, default=str)
    assert '"sharing": "private"' in text.replace("\\", "")

"""`fuze ui`: what the page shows, and the guards around a process that sits next to the API key."""

import asyncio
import http.client
import json
import re
import socket
import subprocess
import sys
import threading
import time
from importlib import resources

import pytest
from ui_fixture import SECRET, mainnet_home

from fuze import config, ui


@pytest.fixture
def page():
    httpd = ui.make_server(0)  # any free port, still 127.0.0.1 only
    threading.Thread(target=httpd.serve_forever, args=(0.05,), daemon=True).start()
    yield httpd
    httpd.shutdown()
    httpd.server_close()


def get(httpd, path="/", host=None, method="GET"):
    port = httpd.server_address[1]
    c = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
    c.putrequest(method, path, skip_host=True)
    c.putheader("Host", host if host is not None else f"127.0.0.1:{port}")
    c.endheaders()
    r = c.getresponse()
    body = r.read()
    c.close()
    return r, body


def dead_pid() -> int:
    p = subprocess.Popen([sys.executable, "-c", "pass"])
    p.wait()
    return p.pid


# --- what it shows -----------------------------------------------------------------------------------------------

def test_mainnet_running_snapshot(fuze_home):
    mainnet_home()
    d = ui.snapshot()
    assert d["agent"]["state"] == "running" and d["agent"]["running"]
    assert d["mode"] == {**d["mode"], "name": "mainnet", "trading": "mainnet", "real_money": True, "mismatch": False}
    assert d["mode"]["explorer"] == "https://app.lighter.xyz/explorer/accounts/281474"
    assert d["account"]["balance"] == 2431.8 and d["account"]["today"] == pytest.approx(-28.2)
    btc, eth = d["positions"]
    assert (btc["side"], eth["side"]) == ("short", "long")
    assert btc["usd"] == pytest.approx(0.0035 * 58520) and btc["result"] == pytest.approx(-0.0035 * (58520 - 58911))
    short, hype = d["shorts"]  # one per coin: the BTC part held, the HYPE trade only in the signal
    assert short["protected"] and short["tp"] == 58029.0 and short["held"] and short["coin"] == "BTC"
    assert hype["coin"] == "HYPE" and not hype["held"] and hype["score"] == 1
    assert d["signal"]["scalps"][1]["name"] == "HYPE" and d["signal"]["targets"][0]["trend_score"] == 14
    assert d["limits"]["risk_allowed"] == 60 and d["limits"]["values"]["coins"] == "BTC, ETH, HYPE, LIT"
    assert "REAL money" in d["signal"]["note"] and d["signal"]["fresh"] and d["signal"]["origin"] == "agent"
    assert d["keys"]["mainnet"]["key"] == "set" and d["rehearsal"] == "passed"
    assert d["limits"]["daily"]["used"] == pytest.approx(28.2 / 123)
    assert any("5% of your balance" in line for line in d["limits"]["lines"])
    links = [t["link"] for t in d["trades"]]
    assert links[0] is None and links[1].startswith("https://app.lighter.xyz/explorer/logs/")  # evil link dropped


def test_the_page_shows_what_the_signal_asks_for_next_to_what_is_held(fuze_home):
    mainnet_home()
    st = config.read_json(fuze_home / "status.json")
    st.update(wanted={"BTC": -0.0035, "ETH": 0.0}, min_change_usd=48.6)
    config.write_json(fuze_home / "status.json", st)
    d = ui.snapshot()
    btc = next(r for r in d["asked"]["rows"] if r["coin"] == "BTC")
    assert btc["asked_usd"] == btc["held_usd"] and not btc["under_min_change"]
    assert any(line.startswith("BTC: the signal asks for short $") for line in d["asked"]["lines"])
    assert d["asked"]["min_change"] == 48.6


def test_states_without_a_running_agent(fuze_home):
    config.save(dict(config.DEFAULTS))
    assert ui.snapshot()["agent"]["state"] == "never"
    mainnet_home(pid=dead_pid())
    d = ui.snapshot()
    assert d["agent"]["state"] == "stopped" and d["shorts"][0]["held"]
    mainnet_home()
    (fuze_home / "PAUSE").touch()
    assert ui.snapshot()["agent"]["state"] == "paused"
    (fuze_home / "FLATTEN").touch()
    assert ui.snapshot()["agent"]["state"] == "flatten"
    assert ui.snapshot(now=time.time() + 60)["agent"]["state"] == "stopped"  # no step for a minute


def test_the_page_reads_the_signal_when_the_agent_is_not_running(fuze_home):
    config.save(dict(config.DEFAULTS))
    seen = []
    msg = {"v": 1, "seq": 9, "rev": 3, "ts": time.time() - 1, "expires": time.time() + 59, "source": "mainnet",
           "state": "live", "targets": {"BTC": {"x": 1.0, "px": 60000.0}}, "scalp": None, "why": "x"}
    peeker = ui.Peeker(lambda server: seen.append(server) or msg)
    d = ui.snapshot(peeker=peeker)
    assert d["signal"]["origin"] == "page" and d["signal"]["rev"] == 3 and seen == ["https://fuze.trade"]
    ui.snapshot(peeker=peeker)
    assert len(seen) == 1  # at most every PEEK_S seconds
    assert not (fuze_home / "guard.json").exists()  # the agent's replay guard is not touched


def test_no_key_and_no_key_file_in_the_json(fuze_home, page):
    mainnet_home(key_file=True)
    assert (fuze_home / "lighter-mainnet.key").read_text() == SECRET
    r, body = get(page, "/api/status")
    text = body.decode()
    assert r.status == 200 and json.loads(text)["keys"]["mainnet"]["key"] == "set"
    assert SECRET not in text and ".key" not in text and "lighter-mainnet" not in text


# --- the server's guards -----------------------------------------------------------------------------------------

def test_binds_loopback_only_and_serves_the_fixed_files(page):
    assert page.server_address[0] == "127.0.0.1"
    for path, (_, ctype) in ui.FILES.items():
        r, body = get(page, path)
        assert r.status == 200 and r.getheader("Content-Type") == ctype and body
        assert r.getheader("Content-Security-Policy").startswith(
            "default-src 'none'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; "
            "font-src 'self'")
        assert r.getheader("X-Content-Type-Options") == "nosniff" and r.getheader("Server") == "fuze"
        assert "frame-ancestors 'none'" in r.getheader("Content-Security-Policy")  # no other page may frame it
        assert r.getheader("X-Frame-Options") == "DENY"
    r, _ = get(page, "/nothing-here")
    assert r.status == 404 and r.getheader("X-Frame-Options") == "DENY"


@pytest.mark.parametrize("host", ["evil.example", "evil.example:{port}", "127.0.0.1", "127.0.0.1:1",
                                  "localhost.evil.example:{port}", ""])
def test_wrong_host_is_refused(page, host):  # DNS rebinding: another site's name pointed at 127.0.0.1
    r, body = get(page, "/api/status", host=host.format(port=page.server_address[1]))
    assert r.status == 421 and b"balance" not in body


def test_localhost_name_is_accepted(page):
    assert get(page, "/api/ping", host=f"localhost:{page.server_address[1]}")[0].status == 200


@pytest.mark.parametrize("method", ["POST", "PUT", "DELETE", "PATCH", "OPTIONS", "HEAD"])
def test_get_only(page, method):
    r, _ = get(page, "/api/status", method=method)
    assert r.status == 405 and r.getheader("Allow") == "GET"


@pytest.mark.parametrize("path", ["/../../etc/passwd", "/static/index.html", "/%2e%2e/config.json", "/config.json",
                                  "/status.json", "/index.html/..", "//etc/passwd", "/api/status/../../x"])
def test_nothing_outside_the_fixed_list(page, path):
    assert get(page, path)[0].status == 404


def test_query_string_is_ignored(page):
    r, body = get(page, "/app.js?file=../../config.json")
    assert r.status == 200 and body == (resources.files("fuze") / "static" / "app.js").read_bytes()


def test_static_files_have_no_inline_code_and_load_nothing_from_elsewhere():
    root = resources.files("fuze") / "static"
    html, css, js = ((root / n).read_text() for n in ("index.html", "app.css", "app.js"))
    assert re.findall(r"<script[^>]*>", html) == ['<script src="/app.js" defer>']
    assert "<style" not in html and " style=" not in html and not re.search(r"\son[a-z]+=", html)
    assert all(u.startswith("/") for u in re.findall(r'(?:src|href)="([^"]*)"', html)
               if not u.startswith(("https://fuze.trade", "https://docs.fuze.trade", "#")))
    assert re.findall(r'<link[^>]*href="([^"]*)"', html) == ["/favicon.svg", "/app.css", "/archivo.woff2"]
    assert "http" not in css and "@import" not in css
    assert re.findall(r"fetch\(([^,)]*)", js) == ['"/api/status"']
    assert "innerHTML" not in js and "eval(" not in js and "localStorage" not in js
    assert set(ui.FILES.values()) <= {(n, t) for n, t in ui.FILES.values() if (root / n).is_file()}
    assert (root / "archivo-OFL.txt").read_text().count("SIL Open Font License") >= 2


# --- starting it -------------------------------------------------------------------------------------------------

def test_port_taken_says_so(fuze_home, capsys):
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    s.listen()
    port = s.getsockname()[1]
    try:
        assert ui.serve(port) == 2
    finally:
        s.close()
    assert f"Port {port} on 127.0.0.1 is taken" in capsys.readouterr().out


def test_port_out_of_range(capsys):
    from fuze.cli import main
    assert main(["ui", "--port", "80"]) == 2
    assert "1024 to 65535" in capsys.readouterr().out


def test_no_option_to_bind_elsewhere():
    from fuze.cli import main
    with pytest.raises(SystemExit):
        main(["ui", "--host", "0.0.0.0"])


def test_mcp_ui_tool_reports_address_and_state(fuze_home, page, monkeypatch):
    from fuze.mcp_server import build

    def call():
        res = asyncio.run(build().call_tool("ui", {}))
        return json.loads(res.content[0].text)

    config.ensure_home()
    config.write_json(fuze_home / "ui.json", {"port": 1})  # out of range: the default address
    real = ui.probe
    monkeypatch.setattr(ui, "probe", lambda port: False)  # whatever runs on this machine's 3893
    d = call()
    assert d["address"] == "http://127.0.0.1:3893" and not d["running"] and "fuze ui --open" in d["say"]
    monkeypatch.setattr(ui, "probe", real)
    port = page.server_address[1]
    config.write_json(fuze_home / "ui.json", {"port": port, "pid": 1})
    d = call()
    assert d["running"] and d["address"] == f"http://127.0.0.1:{port}"


def test_agent_writes_what_the_page_needs(fuze_home):
    from test_agent import Server, run_agent

    st = run_agent(fuze_home, Server(stream=False), lambda s: (s.get("signal") or {}).get("seq") == 1)
    assert st["started"] and st["book"]["BTC"]["entry"] > 0 and st["book"]["BTC"]["mark"] > 0
    assert st["protected"]["BTC"]["id"] == 7 and st["day"]
    assert st["limits"]["risk_allowed"] == 60 and st["limits"]["coins"] == ["BTC", "ETH", "HYPE", "LIT"]


def test_a_status_written_by_0_5_0_still_shows_its_pair(fuze_home):
    mainnet_home()
    st = config.read_json(fuze_home / "status.json")
    st["protected"], st["account"]["brackets"] = st["protected"]["BTC"], [796]  # 0.5.0's form
    config.write_json(fuze_home / "status.json", st)
    d = ui.snapshot()
    assert d["shorts"][0]["coin"] == "BTC" and d["shorts"][0]["held"] and d["shorts"][0]["protected"]

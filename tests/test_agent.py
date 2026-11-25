import json
import logging
import threading
import time
import urllib.error
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from conftest import TEST_KEYS, VECTORS
from fuze import config
from fuze.agent import Agent, ScrubHex, opener


def test_hex_scrubbing_filter():
    rec = logging.LogRecord("fuze", logging.INFO, __file__, 1, "key %s and 0x%s ok", ("ab" * 32, "1f" * 20), None)
    ScrubHex().filter(rec)
    msg = rec.getMessage()
    assert "abab" not in msg and "1f1f" not in msg and msg.count("[hex removed]") == 2 and msg.endswith("ok")
    rec = logging.LogRecord("fuze", logging.INFO, __file__, 1, "seq 42 price 60000.5 deadbeef", None, None)
    ScrubHex().filter(rec)
    assert rec.getMessage() == "seq 42 price 60000.5 deadbeef"  # short hex and numbers stay


class Server:
    """A local FUZE server serving the published test vectors."""

    def __init__(self, stream=True, redirect=False):
        events = [VECTORS["tampered"]] + VECTORS["valid"]

        class H(BaseHTTPRequestHandler):
            def log_message(self, *a):
                pass

            def do_GET(self):
                if redirect:
                    self.send_response(302)
                    self.send_header("Location", "http://example.com/")
                    self.end_headers()
                elif self.path == "/v1/stream" and stream:
                    self.send_response(200)
                    self.send_header("Content-Type", "text/event-stream")
                    self.end_headers()
                    for i, e in enumerate(events):
                        self.wfile.write(f"id: {i}\ndata: {json.dumps(e)}\n\n".encode())
                elif self.path == "/v1/signal":
                    body = json.dumps(VECTORS["valid"][0]).encode()
                    self.send_response(200)
                    self.end_headers()
                    self.wfile.write(body)
                else:
                    self.send_error(404)

        self.httpd = ThreadingHTTPServer(("127.0.0.1", 0), H)
        self.url = f"http://127.0.0.1:{self.httpd.server_address[1]}"
        threading.Thread(target=self.httpd.serve_forever, daemon=True).start()


def run_agent(fuze_home, server, until):
    cfg = config.validate({"server": server.url})
    agent = Agent(cfg, home=config.ensure_home(), keys=TEST_KEYS, clock=lambda: 1010.0)
    stop = threading.Event()
    t = threading.Thread(target=agent.run, args=(stop,), daemon=True)
    t.start()
    deadline = time.time() + 10
    while time.time() < deadline and not until(config.read_json(fuze_home / "status.json") or {}):
        time.sleep(0.05)
    stop.set()
    t.join(5)
    server.httpd.shutdown()
    return config.read_json(fuze_home / "status.json")


def test_end_to_end_stream(fuze_home):
    st = run_agent(fuze_home, Server(), lambda s: (s.get("signal") or {}).get("seq") == 3)
    assert st["signal"]["rev"] == 2 and st["mode"] == "dry"
    acct = st["account"]
    assert acct["positions"] == {"ETH": pytest.approx(-0.4 * 0.1 * 1000 / 2000)} and acct["brackets"] == []
    trades = [json.loads(x) for x in (fuze_home / "trades.jsonl").read_text().splitlines()]
    assert [(t["coin"], t["units"]) for t in trades] == [
        ("BTC", pytest.approx(-0.003)), ("ETH", pytest.approx(-0.02)), ("BTC", pytest.approx(0.003))]
    assert config.read_json(fuze_home / "guard.json") == {"ts": st["signal"]["ts"]}


def test_end_to_end_polling_fallback(fuze_home):
    st = run_agent(fuze_home, Server(stream=False), lambda s: (s.get("signal") or {}).get("seq") == 1)
    assert st["account"]["positions"]["BTC"] == pytest.approx(-0.003)
    assert st["account"]["brackets"] == [7]


def test_redirects_are_not_followed():
    s = Server(redirect=True)
    with pytest.raises(urllib.error.HTTPError):
        opener().open(s.url + "/v1/signal", timeout=5)
    s.httpd.shutdown()


def test_tls_certificate_is_checked(tmp_path):
    import datetime
    import ssl

    from cryptography import x509
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import ec
    from cryptography.x509.oid import NameOID

    key = ec.generate_private_key(ec.SECP256R1())
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "localhost")])
    now = datetime.datetime.now(datetime.timezone.utc)
    cert = (x509.CertificateBuilder().subject_name(name).issuer_name(name).public_key(key.public_key())
            .serial_number(1).not_valid_before(now).not_valid_after(now + datetime.timedelta(days=1))
            .add_extension(x509.SubjectAlternativeName([x509.DNSName("localhost")]), False).sign(key, hashes.SHA256()))
    (tmp_path / "c.pem").write_bytes(cert.public_bytes(serialization.Encoding.PEM))
    (tmp_path / "k.pem").write_bytes(key.private_bytes(serialization.Encoding.PEM,
                                                       serialization.PrivateFormat.PKCS8,
                                                       serialization.NoEncryption()))
    s = Server()
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    ctx.load_cert_chain(tmp_path / "c.pem", tmp_path / "k.pem")
    s.httpd.socket = ctx.wrap_socket(s.httpd.socket, server_side=True)
    with pytest.raises(urllib.error.URLError, match="CERTIFICATE_VERIFY_FAILED"):
        opener().open(f"https://localhost:{s.httpd.server_address[1]}/v1/signal", timeout=5)
    s.httpd.shutdown()

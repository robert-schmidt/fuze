"""`fuze ui`: a read-only page about the agent, on this computer only (default http://127.0.0.1:3893).

The page polls /api/status every few seconds. It works with or without `fuze run`: it reads the files the agent writes
in the FUZE folder (status.json, trades.jsonl, the PAUSE / FLATTEN flags) and config.json, and when the agent is not
running it reads the public signal itself to say what the signal is now (checked against the pinned key; nothing is
written, the agent's replay guard is not touched).

This process sits next to the API key, so:
  - it binds 127.0.0.1 only; there is no option to bind anything else;
  - it answers only requests whose Host header is 127.0.0.1:<port> or localhost:<port> (DNS rebinding);
  - GET only; a fixed list of paths, the static files are read once from the package at start; the query string is
    ignored, nothing in a request reaches the filesystem;
  - every answer carries a strict Content-Security-Policy; the page has no inline script or style and loads nothing
    from anywhere else (no fonts, analytics or CDNs);
  - the JSON is built field by field: modes, numbers, plain-words text, public explorer links, and the API key state
    as "set" or "missing" (keys.state). This module never reads a key and never names a key file;
  - nothing here trades or changes a setting: the page shows the command to type instead.
"""

from __future__ import annotations

import errno
import http.client
import json
import math
import os
import time
import urllib.request
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from importlib import resources
from urllib.parse import urlsplit

from fuze import __version__, config, keys, modes
from fuze.checks import setup_report
from fuze.protocol import COINS, PINNED, clean, verify
from fuze.sizing import LABELS, describe, fmt
from fuze.venue import EXPLORER, account_link

HOST = "127.0.0.1"  # never anything else: this page is for the person at this computer
PORT = 3893  # F-U-Z-E on a phone keypad
SITE, DOCS = "https://fuze.trade", "https://docs.fuze.trade"
RUNNING_S = 30.0  # the agent steps at least every few seconds; a status older than this means it is not running
PEEK_S = 10.0  # when the agent is not running: read the public signal at most this often
CSP = ("default-src 'none'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; "
       "font-src 'self'; base-uri 'none'; form-action 'none'; frame-ancestors 'none'")
FILES = {  # path -> (file in fuze/static, content type). Nothing else is ever served.
    "/": ("index.html", "text/html; charset=utf-8"),
    "/app.css": ("app.css", "text/css; charset=utf-8"),
    "/app.js": ("app.js", "text/javascript; charset=utf-8"),
    "/archivo.woff2": ("archivo.woff2", "font/woff2"),
    "/favicon.svg": ("favicon.svg", "image/svg+xml"),
}
NAMES = {"BTC": "Bitcoin", "ETH": "Ether"}


# --- reading the FUZE folder, tolerant of anything missing or odd ------------------------------------------------

def _num(v):
    return float(v) if isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v) else None


def _text(v, limit: int = 600) -> str:
    return "".join(ch for ch in v if ch.isprintable())[:limit] if isinstance(v, str) else ""


def _read(path) -> dict:
    try:
        d = config.read_json(path)
    except (ValueError, OSError):
        return {}
    return d if isinstance(d, dict) else {}


def _alive(pid) -> bool | None:
    if isinstance(pid, bool) or not isinstance(pid, int) or pid <= 0:
        return None
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except OSError:  # exists, owned by someone else
        return True
    return True


def _since(path):
    try:
        return path.stat().st_mtime
    except OSError:
        return None


def _link(url):
    """Only an https link to Lighter's own explorer pages is passed to the page."""
    ok = isinstance(url, str) and any(url.startswith(e + "/") for e in EXPLORER.values())
    return url if ok and len(url) < 400 and url.isprintable() and " " not in url else None


def _utc_day(t: float) -> str:
    return datetime.fromtimestamp(t, timezone.utc).date().isoformat()


def _tail(path, n: int = 20) -> list:
    """The last n lines of trades.jsonl, newest first, as plain fields (reads at most the last 64 KB)."""
    try:
        with open(path, "rb") as f:
            f.seek(0, os.SEEK_END)
            size = f.tell()
            f.seek(max(0, size - 65536))
            data = f.read()
    except OSError:
        return []
    lines = data.decode("utf-8", "replace").splitlines()[1 if size > 65536 else 0:]
    out = []
    for line in reversed(lines):
        try:
            r = json.loads(line)
        except ValueError:
            continue
        if not isinstance(r, dict) or r.get("coin") not in COINS:
            continue
        out.append({"t": _num(r.get("t")), "coin": r["coin"], "units": _num(r.get("units")),
                    "asked": _num(r.get("asked")), "px": _num(r.get("px")), "worst": _num(r.get("worst")),
                    "pnl": _num(r.get("pnl")), "kind": _text(r.get("kind"), 40), "result": _text(r.get("result"), 40),
                    "mode": r.get("mode") if r.get("mode") in config.MODES else None, "link": _link(r.get("link"))})
        if len(out) >= n:
            break
    return out


def _signal(sig) -> dict | None:
    """The fields of a verified, cleaned signal that the page shows."""
    if not isinstance(sig, dict):
        return None
    sc = sig.get("scalp") if isinstance(sig.get("scalp"), dict) else None
    targets = sig.get("targets") if isinstance(sig.get("targets"), dict) else {}
    return {"state": sig.get("state") if sig.get("state") in ("live", "flat", "offline") else None,
            "rev": sig.get("rev") if isinstance(sig.get("rev"), int) else None,
            "seq": sig.get("seq") if isinstance(sig.get("seq"), int) else None,
            "ts": _num(sig.get("ts")), "expires": _num(sig.get("expires")),
            "source": sig.get("source") if sig.get("source") in modes.SOURCE_RANK else None,
            "why": _text(sig.get("why"), 600),
            "targets": [{"coin": c, "name": NAMES[c], "x": _num(t.get("x")), "px": _num(t.get("px"))}
                        for c, t in targets.items() if c in COINS and isinstance(t, dict)],
            "scalp": {"coin": sc["coin"], "x": _num(sc.get("x")), "tp": _num(sc.get("tp")), "sl": _num(sc.get("sl")),
                      "id": sc.get("id") if isinstance(sc.get("id"), int) else None}
            if sc and sc.get("coin") in COINS else None}


def peek(server: str, timeout: float = 4.0) -> dict | None:
    """The public signal now, verified against the pinned key, or None. Writes nothing (the agent's replay guard is
    the agent's own)."""
    from fuze.agent import MAX_LINE, opener

    req = urllib.request.Request(server + "/v1/signal", headers={"User-Agent": f"fuze-agent/{__version__} (ui)"})
    try:
        with opener().open(req, timeout=timeout) as r:
            body = r.read(MAX_LINE + 1)
        if len(body) > MAX_LINE:
            return None
        msg = verify(json.loads(body), PINNED)
    except Exception:
        return None
    if not msg or msg.get("v") != 1 or isinstance(msg.get("v"), bool):
        return None
    return clean(msg)


class Peeker:
    """peek(), at most every PEEK_S seconds, remembered between polls of the page."""

    def __init__(self, fetch=peek):
        self.fetch, self.t, self.msg, self.at = fetch, 0.0, None, None

    def get(self, server: str, now: float):
        if self.fetch and now - self.t >= PEEK_S:
            self.t = now
            msg = self.fetch(server)
            if msg:
                self.msg, self.at = msg, now
        return self.msg, self.at


def snapshot(now: float | None = None, peeker: Peeker | None = None) -> dict:
    """Everything the page shows, as plain JSON. Never a key, never a key file's name."""
    now = time.time() if now is None else now
    h = config.home()
    s = _read(h / "status.json")
    try:
        cfg, cfg_error = config.load(), ""
    except (ValueError, OSError) as e:
        cfg, cfg_error = config.validate({}), _text(str(e), 300)
    mode = cfg["mode"]

    # the agent
    t = _num(s.get("t"))
    age = now - t if t else None
    alive = _alive(s.get("pid"))
    running = age is not None and age < RUNNING_S and alive is not False
    pause, flatten = h / "PAUSE", h / "FLATTEN"
    flags = {"pause": pause.exists(), "flatten": flatten.exists(),
             "daily_stop": s.get("stopped_day") == _utc_day(now)}
    if not s:
        state, since = "never", None
    elif not running:
        state, since = "stopped", t
    elif flags["flatten"]:
        state, since = "flatten", _since(flatten)
    elif flags["daily_stop"]:
        state, since = "daily_stop", None
    elif flags["pause"]:
        state, since = "paused", _since(pause)
    else:
        state, since = "running", _num(s.get("started"))
    agent_mode = s.get("mode") if s.get("mode") in config.MODES else None
    trading = agent_mode if running and agent_mode else mode

    # the account the agent last read
    a = s.get("account") if isinstance(s.get("account"), dict) else {}
    bal = _num(a.get("balance"))
    held = a.get("positions") if isinstance(a.get("positions"), dict) else {}
    brackets = [b for b in a.get("brackets") or [] if isinstance(b, int)] if isinstance(a.get("brackets"), list) else []
    book = s.get("book") if isinstance(s.get("book"), dict) else {}
    sig = _signal(s.get("signal"))
    received = _num(s.get("received_at"))
    sig_px = {x["coin"]: x["px"] for x in (sig or {}).get("targets", [])}
    positions = []
    for c in COINS:
        units = _num(held.get(c))
        if not units:
            continue
        b = book.get(c) if isinstance(book.get(c), dict) else {}
        entry, mark = _num(b.get("entry")) or None, _num(b.get("mark")) or sig_px.get(c)
        result = units * (mark - entry) if entry and mark else None
        positions.append({"coin": c, "name": NAMES[c], "side": "short" if units < 0 else "long", "units": units,
                          "usd": abs(units) * mark if mark else None, "entry": entry, "mark": mark,
                          "result": result, "result_pct": result / (abs(units) * entry) * 100 if result is not None
                          else None})
    exposure = sum(p["usd"] or 0 for p in positions)
    from fuze.follow import describe_compare, from_status
    rows, tol = from_status(s) if running else ([], None)
    asked = {"rows": rows, "lines": [_text(x, 400) for x in describe_compare(rows, tol)],
             "min_change": _num(tol) or None}
    day_start = _num(s.get("day_start"))
    today_known = bool(bal and day_start and s.get("day") == _utc_day(now))
    frac = cfg["daily_loss_frac"]
    daily = None
    if today_known:
        allowed, lost = day_start * frac, max(0.0, day_start - bal)
        daily = {"day_start": day_start, "floor": day_start * (1 - frac), "allowed": allowed, "lost": lost,
                 "used": min(1.0, lost / allowed) if allowed else None}

    # the short-term part: what the agent placed (memory "prot"), else what the signal has
    prot = s.get("protected") if isinstance(s.get("protected"), dict) else None
    short = None
    if prot and prot.get("coin") in COINS and _num(prot.get("units")):
        c = prot["coin"]
        mark = _num((book.get(c) or {}).get("mark") if isinstance(book.get(c), dict) else None) or sig_px.get(c)
        short = {"coin": c, "name": NAMES[c], "side": "short" if prot["units"] < 0 else "long",
                 "units": _num(prot["units"]), "usd": abs(prot["units"]) * mark if mark else None,
                 "tp": _num(prot.get("tp")), "sl": _num(prot.get("sl")), "mark": mark,
                 "protected": prot.get("id") in brackets, "held": True}
    elif sig and sig["scalp"] and running:
        sc = sig["scalp"]
        short = {"coin": sc["coin"], "name": NAMES[sc["coin"]], "side": "short" if (sc["x"] or 0) < 0 else "long",
                 "units": None, "usd": None, "tp": sc["tp"], "sl": sc["sl"], "mark": sig_px.get(sc["coin"]),
                 "protected": False, "held": False}

    # the signal: the agent's last verified one, or (agent not running) the public one read by this page
    origin = "agent"
    if not running and peeker:
        msg, at = peeker.get(cfg["server"], now)
        if msg and (not sig or (msg.get("ts") or 0) > (sig["ts"] or 0)):
            sig, received, origin = _signal(msg), at, "page"
    if sig:
        sig.update(origin=origin, received_at=received, age=now - sig["ts"] if sig["ts"] else None,
                   fresh=bool(sig["expires"] and now < sig["expires"] and received and now - received <= 60),
                   source_words=modes.SOURCE_NAMES.get(sig["source"], ""),
                   note=modes.realer_note(trading, sig["source"]) if sig["source"] else "")

    nets = {net: {"key": keys.state(net), "account": cfg[f"{net}_account"],
                  "link": _link(account_link(net, cfg[f"{net}_account"]))} for net in config.NETS}
    sizing_bal = bal if bal and bal > 0 else cfg["dry_balance"]
    try:
        checks = [{"ok": bool(r["ok"]), "check": _text(r["check"], 120), "detail": _text(r["detail"], 300)}
                  for r in setup_report()]
    except Exception as e:  # a check that breaks must not take the page down
        checks = [{"ok": False, "check": "Setup check", "detail": _text(f"could not run: {type(e).__name__}")}]
    rehearsal = modes.rehearsal_problem()
    return {
        "now": now, "version": __version__, "links": {"site": SITE, "docs": DOCS}, "server": cfg["server"],
        "agent": {"state": state, "running": running, "since": since, "last_step": t, "age": age,
                  "reason": _text(s.get("reason"), 600), "mode": agent_mode,
                  "version": _text(s.get("version"), 20), "last_drop": _text(s.get("last_drop"), 200)},
        "flags": {**flags, "pause_since": _since(pause), "flatten_since": _since(flatten)},
        "mode": {"name": mode, "trading": trading, "real_money": "mainnet" in (mode, trading),
                 "mismatch": bool(running and agent_mode and agent_mode != mode),
                 "explorer": _link(s.get("account_link")) if running else nets.get(mode, {}).get("link")},
        "account": {"balance": bal, "simulated_start": cfg["dry_balance"] if mode == "simulation" else None,
                    "today_known": today_known, "today": bal - day_start if today_known else None,
                    "today_pct": (bal - day_start) / day_start * 100 if today_known else None,
                    "exposure": exposure, "exposure_x": exposure / bal if bal else None},
        "positions": positions, "asked": asked, "short": short, "signal": sig,
        "limits": {"lines": describe(cfg, sizing_bal), "balance": sizing_bal, "size_mode": cfg["size_mode"],
                   "percent": cfg["percent"], "fixed_usd": cfg["fixed_usd"],
                   "values": {k: fmt(k, cfg[k]) for k in LABELS}, "labels": dict(LABELS), "daily": daily,
                   "daily_frac": frac},
        "trades": _tail(h / "trades.jsonl"), "checks": checks, "keys": nets,
        "rehearsal": "passed" if not rehearsal else rehearsal, "config_error": cfg_error,
    }


# --- the HTTP server --------------------------------------------------------------------------------------------

def _static() -> dict:
    root = resources.files("fuze") / "static"
    return {path: (root.joinpath(name).read_bytes(), ctype) for path, (name, ctype) in FILES.items()}


class Handler(BaseHTTPRequestHandler):
    server_version, sys_version = "fuze", ""
    timeout = 10  # a client that sends nothing does not hold a thread for long

    def version_string(self) -> str:  # no Python version in the Server header
        return "fuze"

    def log_message(self, *args) -> None:  # quiet: one line per poll would bury the terminal
        pass

    def _send(self, code: int, body: bytes, ctype: str, extra=None) -> None:
        self.send_response(code)
        for k, v in {"Content-Type": ctype, "Content-Length": str(len(body)), "Content-Security-Policy": CSP,
                     "X-Content-Type-Options": "nosniff", "Referrer-Policy": "no-referrer",
                     "Cross-Origin-Resource-Policy": "same-origin", "Cross-Origin-Opener-Policy": "same-origin",
                     "X-Frame-Options": "DENY", "Cache-Control": "no-store", **(extra or {})}.items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(body)

    def _plain(self, code: int, text: str, extra=None) -> None:
        self._send(code, (text + "\n").encode(), "text/plain; charset=utf-8", extra)

    def _host_ok(self) -> bool:
        hosts = self.headers.get_all("Host") or []
        port = self.server.server_address[1]
        return len(hosts) == 1 and hosts[0].strip().lower() in (f"127.0.0.1:{port}", f"localhost:{port}")

    def do_GET(self) -> None:
        if not self._host_ok():  # a page on another site that points its own name at 127.0.0.1 gets nothing
            return self._plain(421, "This page answers only at http://127.0.0.1 or http://localhost with its port.")
        path = urlsplit(self.path).path  # the query string is ignored
        if path == "/api/status":
            body = json.dumps(snapshot(peeker=self.server.peeker), allow_nan=False).encode()
            return self._send(200, body, "application/json")
        if path == "/api/ping":
            return self._send(200, json.dumps({"fuze": "ui", "version": __version__}).encode(), "application/json")
        if path in self.server.files:
            body, ctype = self.server.files[path]
            return self._send(200, body, ctype)
        return self._plain(404, "Not found.")

    def _refuse(self) -> None:
        self._plain(405, "This page is read-only: GET only.", {"Allow": "GET"})

    do_HEAD = do_POST = do_PUT = do_DELETE = do_PATCH = do_OPTIONS = do_CONNECT = do_TRACE = _refuse


def make_server(port: int = PORT, peeker: Peeker | None = None) -> ThreadingHTTPServer:
    httpd = ThreadingHTTPServer((HOST, port), Handler)
    httpd.daemon_threads = True
    httpd.files, httpd.peeker = _static(), peeker
    return httpd


def probe(port: int, timeout: float = 1.0) -> bool:
    """True when a FUZE page answers on 127.0.0.1:port."""
    try:
        c = http.client.HTTPConnection(HOST, port, timeout=timeout)
        c.request("GET", "/api/ping", headers={"Host": f"{HOST}:{port}"})
        r = c.getresponse()
        ok = r.status == 200 and json.loads(r.read(4096)).get("fuze") == "ui"
        c.close()
        return ok
    except (OSError, ValueError, http.client.HTTPException, AttributeError):
        return False


def where() -> dict:
    """For the MCP server: the page's address and whether it answers. Read only."""
    info = _read(config.home() / "ui.json")
    port = info.get("port")
    port = port if isinstance(port, int) and not isinstance(port, bool) and 1024 <= port <= 65535 else PORT
    url = f"http://{HOST}:{port}"
    up = probe(port)
    return {"address": url, "running": up,
            "say": (f"The FUZE page is open at {url} (only on this computer, read-only)." if up else
                    f"The FUZE page is not running. Start it in a terminal with `fuze ui --open`; it will be at "
                    f"{url}."),
            "read_only": "The page shows status, balance, positions, the signal, limits and setup; it cannot trade or "
                         "change settings."}


def _say(text: str) -> None:
    print(text, flush=True)


def serve(port: int = PORT, open_browser: bool = False, say=_say) -> int:
    if not 1024 <= port <= 65535:
        say("The port must be a whole number from 1024 to 65535.")
        return 2
    try:
        httpd = make_server(port, Peeker())
    except OSError as e:
        if e.errno != errno.EADDRINUSE:
            raise
        url = f"http://{HOST}:{port}"
        if probe(port):
            say(f"A FUZE page is already running at {url}. Open that, or stop it first.")
        else:
            say(f"Port {port} on {HOST} is taken by another program. Choose another: `fuze ui --port {port + 1}`.")
        return 2
    url = f"http://{HOST}:{port}"
    marker = config.ensure_home() / "ui.json"
    config.write_json(marker, {"port": port, "pid": os.getpid(), "t": time.time()})
    say(f"FUZE page: {url}  (only on this computer, read-only; it never trades). Ctrl+C to stop.")
    if open_browser:
        import webbrowser
        webbrowser.open(url)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        say("Stopped the FUZE page.")
    finally:
        httpd.server_close()
        if _read(marker).get("pid") == os.getpid():
            marker.unlink(missing_ok=True)
    return 0

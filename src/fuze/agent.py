"""The agent loop: read the signal, check it, decide, trade on the (simulated) exchange, write status.json."""

from __future__ import annotations

import http.client
import json
import logging
import os
import re
import ssl
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path

from fuze import __version__
from fuze.config import ensure_home, load, read_json, write_json
from fuze.dry import DryExchange
from fuze.follow import decide
from fuze.protocol import COINS, PINNED, Guard

log = logging.getLogger("fuze")
MAX_LINE = 65_536
POLL_S = 2.0
HEX = re.compile(r"(?:0x)?[0-9a-fA-F]{32,}")


class ScrubHex(logging.Filter):
    """Replaces long hex strings (what private keys and signatures look like) in every log line."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.msg, record.args = HEX.sub("[hex removed]", record.getMessage()), None
        return True


def setup_logging(level=logging.INFO) -> None:
    handler = logging.StreamHandler()
    handler.addFilter(ScrubHex())
    handler.setFormatter(logging.Formatter("%(asctime)s %(message)s"))
    log.addHandler(handler)
    log.setLevel(level)


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):  # a redirect could downgrade to http or leave our server
        return None


def opener() -> urllib.request.OpenerDirector:
    ctx = ssl.create_default_context()  # certificate and host name checks always on
    return urllib.request.build_opener(_NoRedirect, urllib.request.HTTPSHandler(context=ctx))


NET_ERRORS = (OSError, urllib.error.URLError, http.client.HTTPException, ValueError)


class Agent:
    def __init__(self, cfg=None, home: Path | None = None, keys=PINNED, clock=time.time, exchange=None):
        self.home = Path(home) if home else ensure_home()
        self.fixed_cfg, self.cfg = cfg is not None, cfg or load()
        self.server, self.clock = self.cfg["server"], clock
        self.guard = Guard(self.home / "guard.json", keys)
        self.ex = exchange or DryExchange(self.home, self.cfg["dry_balance"], clock)
        self.memory = read_json(self.home / "state.json", {}) or {}
        self.memory["rev"] = None  # act on the first signal after a start
        self.signal = self.received_at = self.last_error = self.last_reason = None
        self.http = opener()
        self.headers = {"User-Agent": f"fuze-agent/{__version__}"}

    # --- network -----------------------------------------------------------------------------
    def stream(self, stop: threading.Event):
        """Yield each `data:` event of /v1/stream as text."""
        req = urllib.request.Request(self.server + "/v1/stream", headers={**self.headers,
                                                                          "Accept": "text/event-stream"})
        with self.http.open(req, timeout=20) as r:
            data = []
            while not stop.is_set():
                raw = r.readline(MAX_LINE + 1)
                if not raw:
                    return
                if len(raw) > MAX_LINE or sum(map(len, data)) > MAX_LINE:
                    raise ValueError("stream line too long")
                line = raw.decode("utf-8").rstrip("\r\n")
                if line.startswith("data:"):
                    data.append(line[5:].removeprefix(" "))
                elif not line and data:
                    yield "\n".join(data)
                    data = []

    def poll(self) -> None:
        req = urllib.request.Request(self.server + "/v1/signal", headers=self.headers)
        try:
            with self.http.open(req, timeout=10) as r:
                body = r.read(MAX_LINE + 1)
            if len(body) > MAX_LINE:
                raise ValueError("response too large")
            self.handle(body.decode("utf-8"))
        except NET_ERRORS as e:
            if str(e) != self.last_error:  # say it once, not every 2 seconds
                log.warning("Could not read the signal: %s", e)
                self.last_error = str(e)
            self.tick()

    def run(self, stop: threading.Event | None = None) -> None:
        stop = stop or threading.Event()
        failures = 0
        while not stop.is_set():
            try:
                for text in self.stream(stop):
                    failures = 0
                    self.handle(text)
            except NET_ERRORS as e:
                log.warning("Stream unavailable (%s); polling every %g seconds.", e, POLL_S)
            failures += 1
            until = time.monotonic() + min(60, 2 ** failures)
            while not stop.is_set() and time.monotonic() < until:
                self.poll()
                stop.wait(POLL_S)

    # --- one step ------------------------------------------------------------------------------
    def handle(self, text: str) -> None:
        try:
            env = json.loads(text)
        except ValueError:
            env = None
        msg = self.guard.accept(env, self.clock())
        if msg:
            self.signal, self.received_at, self.last_error = msg, self.clock(), None
            self.ex.mark({c: t["px"] for c, t in msg["targets"].items()})
        else:
            log.info("Dropped a message: %s.", self.guard.why)
        self.tick()

    def tick(self) -> None:
        now = self.clock()
        if not self.fixed_cfg:
            try:
                self.cfg = {**load(), "server": self.server}  # lowered limits apply at once
            except (ValueError, OSError) as e:
                log.error("config.json is not valid (%s); keeping the last good limits.", e)
        flags = {"pause": (self.home / "PAUSE").exists(), "flatten": (self.home / "FLATTEN").exists()}
        acct = self.ex.account()
        d = decide(self.signal, self.received_at, now, acct, self.cfg, flags, self.memory)
        self.memory = d.memory
        if d.act:
            self.apply(d, acct)
        if d.reason != self.last_reason:
            log.info("%s", d.reason)
            self.last_reason = d.reason
        write_json(self.home / "state.json", self.memory)
        write_json(self.home / "status.json", {
            "t": now, "pid": os.getpid(), "version": __version__, "mode": self.cfg["mode"], "server": self.server,
            "reason": d.reason, "flags": flags, "account": self.ex.account(), "signal": self.signal,
            "received_at": self.received_at, "last_drop": self.guard.why,
            "limits": {k: self.cfg[k] for k in ("scale", "max_x", "daily_loss_frac", "stale_flat_min")},
            "day_start": self.memory.get("day_start"), "stopped_day": self.memory.get("stopped_day")})

    def apply(self, d, acct) -> None:
        try:
            for coin in COINS:
                self.ex.cancel(coin)
            for coin, units in d.targets.items():
                delta = units - acct["positions"].get(coin, 0.0)
                if abs(delta) > 1e-12:
                    self.ex.market(coin, delta, d.px.get(coin))
            if d.bracket:
                b = d.bracket
                self.ex.protect(b["coin"], b["units"], b["tp"], b["sl"], b["id"])
        except Exception as e:  # the next tick sees the mismatch and resyncs
            log.error("Order step failed: %s", e)

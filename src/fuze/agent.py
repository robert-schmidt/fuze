"""The agent loop: read the signal, check it, decide, trade on the venue (simulated or Lighter), write status.json.

One code path for every mode. The order step follows these rules on every venue:
  - the account read decides: after every order the account is read back before anything else is done;
  - an order that did not fill (or filled in part) is never followed by a blind second one: the step stops, and the
    next try comes after MISS_WAIT_S, sized from a new account read;
  - an order in flight is written to pending.json before it is sent, so a restart reads the account first and never
    sends it again;
  - reductions are reduce-only and every market order has a worst price (venue.SLIP_ADD / SLIP_REDUCE);
  - the scalp part rests under its own take profit and stop loss on the venue, sized to that part, re-placed when its
    size or levels change and cancelled when it closes; if the venue does not show them after placing, the scalp part
    is closed.
"""

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
from fuze.config import LIMITS, ensure_home, load, read_json, write_json
from fuze.follow import decide
from fuze.protocol import COINS, PINNED, Guard
from fuze.venue import open_venue, tx_link, worst_price

log = logging.getLogger("fuze")
MAX_LINE = 65_536
POLL_S = 2.0
MISS_WAIT_S = 60.0  # after an order that did not fill in full: wait this long before the next try
INFLIGHT_WAIT_S = 10.0  # an order found in pending.json at a start: read the account only this long after it was sent
READS = 3  # read-backs after an order, settle_s apart, before calling it not (fully) filled
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
    def __init__(self, cfg=None, home: Path | None = None, keys=PINNED, clock=time.time, exchange=None,
                 sleep=time.sleep):
        self.home = Path(home) if home else ensure_home()
        self.fixed_cfg, self.cfg = cfg is not None, cfg or load()
        self.server, self.clock, self.sleep, self.mode = self.cfg["server"], clock, sleep, self.cfg["mode"]
        self.guard = Guard(self.home / "guard.json", keys)
        self.ex = exchange or open_venue(self.cfg, self.home, clock)
        self.memory = read_json(self.home / "state.json", {}) or {}
        if self.memory.get("mode", "simulation") != self.mode:  # notes about another account mean nothing here
            self.memory = {}
        self.memory.update(rev=None, mode=self.mode)  # act on the first signal after a start
        self.pending = read_json(self.home / "pending.json")  # an order sent just before the agent stopped
        self.signal = self.received_at = self.last_error = self.last_reason = None
        self.acct, self.notes = None, []
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

    def say(self, reason: str) -> None:
        if reason != self.last_reason:
            log.info("%s", reason)
            self.last_reason = reason

    def tick(self) -> None:
        now = self.clock()
        if not self.fixed_cfg:
            try:
                self.cfg = {**load(), "server": self.server, "mode": self.mode}  # lowered limits apply at once
            except (ValueError, OSError) as e:
                log.error("config.json is not valid (%s); keeping the last good limits.", e)
        flags = {"pause": (self.home / "PAUSE").exists(), "flatten": (self.home / "FLATTEN").exists()}
        reason = self.step(now, flags)
        self.say(reason)
        write_json(self.home / "state.json", self.memory)
        src = (self.signal or {}).get("source")
        from fuze.modes import realer_note
        write_json(self.home / "status.json", {
            "t": now, "pid": os.getpid(), "version": __version__, "mode": self.mode, "server": self.server,
            "account_link": self.ex.link(), "note": realer_note(self.mode, src) if src else "",
            "reason": reason, "flags": flags, "account": self.acct, "signal": self.signal,
            "received_at": self.received_at, "last_drop": self.guard.why, "pending": self.pending,
            "limits": {k: self.cfg[k] for k in LIMITS},
            "day_start": self.memory.get("day_start"), "stopped_day": self.memory.get("stopped_day")})

    def step(self, now: float, flags: dict) -> str:
        """Read the account, settle an order left in flight, decide, trade. Returns the reason in plain words."""
        try:
            if self.pending and now - self.pending["t"] < INFLIGHT_WAIT_S:
                return ("An order sent just before the agent stopped may still be settling: waiting, then reading "
                        "the account.")
            self.acct = self.ex.account(fresh=bool(self.pending))
            if self.pending:
                self.settle(self.acct, now)
        except Exception as e:
            return f"Could not read the account ({_plain(e)}): no orders until it can be read."
        if now < self.memory.get("retry_at", 0):
            return (f"An order did not fill in full; the next try is in {self.memory['retry_at'] - now:.0f} s, "
                    "sized from a new account read.")
        cfg = self.cfg
        d = decide(self.signal, self.received_at, now, self.acct, cfg, flags, self.memory)
        self.memory, self.notes = d.memory, []
        if d.act:
            try:
                self.apply(d, now)
            except Exception as e:  # the next step reads the account and starts from what it shows
                log.error("Order step stopped: %s", _plain(e))
                self.notes.append(f"The order step stopped ({_plain(e)}); the next step starts from the account.")
            try:
                self.acct = self.ex.account(fresh=True)
            except Exception as e:
                self.notes.append(f"Could not read the account after the orders ({_plain(e)}).")
        return " ".join([d.reason] + self.notes)

    # --- orders: the same path for the simulated account and Lighter ---------------------------
    def read_back(self, coin: str, before: float, units: float) -> dict:
        """Read the account after an order, up to READS times, until the position moved by the full amount."""
        for i in range(READS):
            self.sleep(self.ex.settle_s)
            acct = self.ex.account(fresh=True)
            got = acct["positions"].get(coin, 0.0) - before
            if abs(got - units) <= max(1e-9, 0.001 * abs(units)) or not self.ex.live:
                break
        self.acct = acct
        return acct

    def settle(self, acct: dict, now: float) -> bool:
        """What the account shows about the order in pending.json. True if it filled in full."""
        p, self.pending = self.pending, None
        (self.home / "pending.json").unlink(missing_ok=True)
        got = acct["positions"].get(p["coin"], 0.0) - p["before"]
        full = abs(got - p["units"]) <= max(1e-9, 0.001 * abs(p["units"]))
        what = "filled" if full else "filled in part" if got * p["units"] > 0 else "did not fill"
        if self.ex.live:
            with open(self.home / "trades.jsonl", "a", encoding="utf-8") as f:
                f.write(json.dumps({"t": now, "mode": self.mode, "coin": p["coin"], "asked": p["units"],
                                    "units": round(got, 12), "worst": p["worst"], "reduce_only": p["reduce_only"],
                                    "kind": "market", "result": what, "tx": p.get("tx"),
                                    "link": tx_link(self.mode, p.get("tx"))}) + "\n")
        if not full:
            self.memory["retry_at"] = now + MISS_WAIT_S
            self.notes.append(f"The {p['coin']} order {what} (asked {p['units']:+.6f}, the account shows "
                              f"{got:+.6f}); no further orders now, the next try in {MISS_WAIT_S:g} s.")
            log.warning("%s order for %+.6f %s; the account shows %+.6f. Next try in %g s, from a new account read.",
                        p["coin"], p["units"], what, got, MISS_WAIT_S)
        return full

    def send(self, coin: str, units: float, ref: float, reduce_only: bool) -> bool:
        """One market order, read back. True if it filled in full."""
        held = self.acct["positions"].get(coin, 0.0)
        worst = worst_price(ref, units, reduce_only)
        self.pending = {"t": self.clock(), "coin": coin, "units": units, "before": held, "worst": worst,
                        "reduce_only": reduce_only}
        write_json(self.home / "pending.json", self.pending)  # before sending: a restart must not send it again
        try:
            self.pending["tx"] = self.ex.market(coin, units, ref, worst, reduce_only)
            write_json(self.home / "pending.json", self.pending)
        except Exception as e:  # it may still have reached the exchange: the account read decides
            log.error("%s order: %s (the account read decides whether it went through)", coin, _plain(e))
        return self.settle(self.read_back(coin, held, units), self.clock())

    def trade(self, coin: str, want: float, ref) -> bool:
        """Bring one coin to `want` units. False when an order did not fill in full (the step stops there)."""
        held = self.acct["positions"].get(coin, 0.0)
        if abs(want - held) < 1e-12:
            return True
        if not ref:
            self.notes.append(f"No {coin} price to set a worst price with: that order waits.")
            return True
        legs = [(-held, True), (want, False)] if held and want and held * want < 0 else \
            [(want - held, abs(want) < abs(held) and held * want >= 0)]  # a flip: close first, then open
        for units, reduce in legs:
            units = -held if reduce and abs(want) < 1e-12 or reduce and abs(units) > abs(held) else units
            units = self.ex.round(coin, units)
            if not self.ex.tradable(coin, units, ref):
                self.notes.append(f"The {coin} change of {units:+.6f} is under the exchange's smallest order: skipped.")
                return True
            if not self.send(coin, units, ref, reduce):
                return False
            held = self.acct["positions"].get(coin, 0.0)
        return True

    def apply(self, d, now: float) -> None:
        m, ex, want = self.memory, self.ex, dict(d.targets)
        br = dict(d.bracket) if d.bracket else None
        if br:
            c = br["coin"]
            br["units"] = ex.round(c, br["units"])
            if not ex.tradable(c, br["units"], d.px.get(c)):  # too small to rest under its own stop loss: not opened
                if abs(want[c] - self.acct["positions"].get(c, 0.0)) > 1e-12:
                    want[c] -= d.bracket["units"]
                    m["set"] = {**m.get("set", {}), c: want[c]}
                m["scalp"], br = None, None
                self.notes.append("The scalp part is not opened: it is under the exchange's smallest order, so it "
                                  "could not rest under its own stop loss.")
        placed = m.get("prot")
        closing = all(abs(v) < 1e-12 for v in want.values())
        for c in COINS:  # a pair that changes or ends is cancelled before any order on its coin
            if closing or (placed and placed["coin"] == c and (not br or _pair(br) != _pair(placed))):
                ex.cancel(c)
                if placed and placed["coin"] == c:
                    m["prot"] = placed = None
        first = br["coin"] if br else None
        for c in sorted(COINS, key=lambda c: c != first):  # the scalp's coin first: it is the urgent part
            ref = d.px.get(c) or ex.price(c)
            if not self.trade(c, want[c], ref):
                break  # not filled in full: no further orders now; protect what is held, then stop
        if br:
            self.protect(br, d.px.get(br["coin"]) or ex.price(br["coin"]))

    def protect(self, br: dict, ref) -> None:
        m, ex, c = self.memory, self.ex, br["coin"]
        held = self.acct["positions"].get(c, 0.0)
        units = ex.round(c, min(abs(br["units"]), abs(held)) * (1 if br["units"] > 0 else -1)) \
            if held * br["units"] > 0 else 0.0
        if not units:
            return
        want = {**br, "units": units}
        placed = m.get("prot")
        if placed and _pair(placed) == _pair(want) and placed["id"] in self.acct["brackets"]:
            return
        ex.cancel(c)  # whatever rests on this coin; the pair is placed fresh
        try:
            ex.protect(c, units, br["tp"], br["sl"], br["id"])
        except Exception as e:
            log.error("Take profit / stop loss for %s: %s", c, _plain(e))
        self.sleep(ex.settle_s)
        self.acct = ex.account(fresh=True)
        if br["id"] in self.acct["brackets"]:
            m["prot"] = want
            log.info("Protected the scalp part %+.6f %s: take profit %g, stop loss %g.", units, c, br["tp"], br["sl"])
            return
        # the exchange does not show them: the scalp part may not stay open unprotected
        log.error("The take profit / stop loss for the %s scalp part are not on the exchange: closing that part.", c)
        self.notes.append("The scalp part's take profit and stop loss could not be placed, so that part was closed.")
        ex.cancel(c)
        m.update(prot=None, scalp=None, scalp_done=br["id"])
        if self.send(c, -units, ref, True):
            m["set"] = {**m.get("set", {}), c: self.acct["positions"].get(c, 0.0)}


def _pair(p: dict) -> tuple:
    return p["coin"], round(p["units"], 10), p["tp"], p["sl"], p["id"]


def _plain(e: Exception) -> str:
    """An error in a few words, with anything that looks like a key or signature removed."""
    return HEX.sub("[hex removed]", str(e) or type(e).__name__)[:200]

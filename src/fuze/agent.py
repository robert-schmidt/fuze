"""The agent loop: read the signal, check it, decide, trade on the venue (simulated or Lighter), write status.json.

One code path for every mode. The order step follows these rules on every venue:
  - the account read decides: after every order the account is read back before anything else is done;
  - an order that did not fill (or filled in part) is never followed by a blind second one: the step stops, and the
    next try comes after MISS_WAIT_S, sized from a new account read;
  - an order in flight is written to pending.json before it is sent, so a restart reads the account first and never
    sends it again;
  - reductions are reduce-only and every market order has a worst price (venue.SLIP_ADD / SLIP_REDUCE);
  - each coin's scalp part rests under its own take profit and stop loss on the venue (one pair per coin), sized to
    that part, never larger than the position nor on the other side of it, re-placed when its size or levels change and
    cancelled when it closes; if the venue does not show them after placing, that scalp part is closed;
  - the rest of each position (the trend part, which has no take profit or stop loss) rests under an emergency stop
    on the venue, far from the price (follow.guard_plan): it is moved with the price while a live signal is followed
    and stays where it is when the agent is off or the signal is gone, so a position nobody is watching has an order
    behind it.
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
from fuze.follow import GUARD_FRAC, STALE_S, decide, guard_plan, migrate, min_change, utc_day
from fuze.protocol import COINS, NAMES, PATHS, PINNED, Guard
from fuze.sizing import counted
from fuze.venue import open_venue, tx_link

log = logging.getLogger("fuze")
MAX_LINE = 65_536
POLL_S = 2.0
MISS_WAIT_S = 60.0  # after an order that did not fill in full: wait this long before the next try
INFLIGHT_WAIT_S = 10.0  # an order found in pending.json at a start: read the account only this long after it was sent
READS = 3  # read-backs after an order, settle_s apart, before calling it not (fully) filled
HEX = re.compile(r"(?:0x)?[0-9a-fA-F]{32,}")
BEAT_S = 300.0  # a beat report (result, positions as multiples of the balance, state) this often


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
    log.propagate = False  # Lighter's SDK sets up the root logger: without this every line prints twice, once unscrubbed


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):  # a redirect could downgrade to http or leave our server
        return None


def opener() -> urllib.request.OpenerDirector:
    ctx = ssl.create_default_context()  # certificate and host name checks always on
    return urllib.request.build_opener(_NoRedirect, urllib.request.HTTPSHandler(context=ctx))


NET_ERRORS = (OSError, urllib.error.URLError, http.client.HTTPException, ValueError)


class Agent:
    def __init__(self, cfg=None, home: Path | None = None, keys=PINNED, clock=time.time, exchange=None,
                 sleep=time.sleep, reporter=None):
        self.home = Path(home) if home else ensure_home()
        self.fixed_cfg, self.cfg = cfg is not None, cfg or load()
        self.server, self.clock, self.sleep, self.mode = self.cfg["server"], clock, sleep, self.cfg["mode"]
        self.guard = Guard(self.home / "guard.json", keys)
        self.ex = exchange or open_venue(self.cfg, self.home, clock)
        self.memory = migrate(read_json(self.home / "state.json", {}) or {})  # 0.5.0's one pair -> one per coin
        if self.memory.get("mode", "simulation") != self.mode:  # notes about another account mean nothing here
            self.memory = {}
        self.memory.update(rev=None, mode=self.mode)  # act on the first signal after a start
        self.pending = read_json(self.home / "pending.json")  # an order sent just before the agent stopped
        self.signal = self.received_at = self.last_error = self.last_reason = None
        self.acct, self.notes = None, []
        self.started = clock()  # for `fuze ui`: running since
        self.http = opener()
        self.headers = {"User-Agent": f"fuze-agent/{__version__}"}
        # reporting (report.Reporter, or None): it only queues, and every call to it is wrapped in _report
        self.reporter, self.said, self.beat_at, self.read_ok = reporter, None, None, False
        self.rev_seen, self.order, self.sig_px, self.flags, self.parts = (None, None), None, {}, {}, {}

    # --- network -----------------------------------------------------------------------------
    def stream(self, stop: threading.Event):
        """Yield each `data:` event of /v2/stream as text."""
        req = urllib.request.Request(self.server + PATHS[1], headers={**self.headers, "Accept": "text/event-stream"})
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
        req = urllib.request.Request(self.server + PATHS[0], headers=self.headers)
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
        try:
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
        except KeyboardInterrupt:  # Ctrl+C: a clean stop
            self._report("bye")
            raise
        self._report("bye")

    # --- one step ------------------------------------------------------------------------------
    def handle(self, text: str) -> None:
        try:
            env = json.loads(text)
        except ValueError:
            env = None
        msg = self.guard.accept(env, self.clock())
        if msg:
            self.signal, self.received_at, self.last_error = msg, self.clock(), None
            if msg.get("rev") != self.rev_seen[0]:  # for the trade report: how late an order came after its revision
                self.rev_seen = (msg.get("rev"), self.received_at)
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
                # changed limits (lowered, or raised by the user at a terminal) reach decide() on this step, which
                # resizes the held position to them; see follow.decide
                self.cfg = {**load(), "server": self.server, "mode": self.mode}
            except (ValueError, OSError) as e:
                log.error("config.json is not valid (%s); keeping the last good limits.", e)
        flags = {"pause": (self.home / "PAUSE").exists(), "flatten": (self.home / "FLATTEN").exists()}
        self.flags = flags
        said = (self.mode, *(self.cfg.get(k) for k in LIMITS), self.cfg.get("public"), self.cfg.get("handle"))
        if said != self.said:  # at start, and when a setting or the sharing changes
            self.said = said
            self._report("hello", self.cfg)
        reason = self.step(now, flags)
        self.say(reason)
        if self.read_ok and (self.beat_at is None or now - self.beat_at >= BEAT_S):
            self.beat_at = now
            self._beat(now, flags)
        write_json(self.home / "state.json", self.memory)
        src = (self.signal or {}).get("source")
        from fuze.modes import realer_note
        write_json(self.home / "status.json", {
            "t": now, "pid": os.getpid(), "version": __version__, "mode": self.mode, "server": self.server,
            "account_link": self.ex.link(), "note": realer_note(self.mode, src) if src else "",
            "reason": reason, "flags": flags, "account": self.acct, "signal": self.signal,
            "received_at": self.received_at, "last_drop": self.guard.why, "pending": self.pending,
            "limits": {k: self.cfg[k] for k in LIMITS}, "started": self.started, "book": self.book(),
            "protected": self.memory.get("prots") or {}, "day": self.memory.get("day"),
            "day_start": self.memory.get("day_start"), "stopped_day": self.memory.get("stopped_day"),
            "wanted": self.memory.get("wanted"), "min_change_usd": self.memory.get("min_change")})

    def book(self) -> dict:
        """Entry and mark price per held coin, for `fuze ui`. Never stops a step."""
        try:
            return self.ex.book() or {}
        except Exception:
            return {}

    def step(self, now: float, flags: dict) -> str:
        """Read the account, settle an order left in flight, decide, trade. Returns the reason in plain words."""
        self.read_ok, prev = False, self.acct
        try:
            if self.pending and now - self.pending["t"] < INFLIGHT_WAIT_S:
                return ("An order sent just before the agent stopped may still be settling: waiting, then reading "
                        "the account.")
            self.acct = self.ex.account(fresh=bool(self.pending))
            if self.pending:
                self.settle(self.acct, now)
            elif prev:
                self._found_fills(prev)
        except Exception as e:
            return f"Could not read the account ({_plain(e)}): no orders until it can be read."
        self.read_ok = True
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
        try:
            self.keep_guards(now, flags)
        except Exception as e:  # the next step tries again
            log.error("Emergency stop: %s", _plain(e))
            self.memory["guard_retry"] = now + MISS_WAIT_S
            self.notes.append(f"The emergency stop could not be set ({_plain(e)}); the next try is in "
                              f"{MISS_WAIT_S:g} s.")
        return " ".join([d.reason] + self.notes)

    def keep_guards(self, now: float, flags: dict) -> None:
        """The emergency stop of every coin (follow.guard_plan): placed, resized, moved with the price or removed."""
        m, ex, acct = self.memory, self.ex, self.acct
        if now < m.get("guard_retry", 0) or self.pending:
            return
        resting, mine = acct.get("guards") or {}, dict(m.get("guards") or {})

        def gone(c):  # we placed it and the exchange no longer shows it
            g = mine.pop(c)
            log.warning("The %s emergency stop at %g is no longer on the exchange: it filled, expired or was "
                        "cancelled there. With a live signal the position is brought back to what it asks for.",
                        c, g["stop"])
            self.notes.append(f"The {c} emergency stop at {g['stop']:,.2f} is no longer on the exchange (it filled, "
                              "expired or was cancelled there).")

        for c in [c for c in mine if c not in resting]:
            gone(c)
        following = m.get("live_at") == now and not flags.get("pause") and not flags.get("flatten")
        prots, shown, placed = m.get("prots") or {}, acct.get("brackets") or {}, {}
        for c in COINS:
            px, held = ex.price(c), acct["positions"].get(c, 0.0)
            if not px:
                continue
            p = prots.get(c)  # the coin's own pair covers its scalp part only while the exchange shows it
            covered = p["units"] if p and shown.get(c) == p["id"] else 0.0
            what, g = guard_plan(held, covered, px, resting.get(c), now, following,
                                 min_change(counted(self.cfg, acct["balance"])) / px)
            if what == "place":
                g["units"] = ex.round(c, g["units"])
                if not ex.tradable(c, g["units"], px):  # under the exchange's smallest order: nothing can rest
                    what = "remove" if c in resting else "none"
            if what == "remove":
                if not ex.unguard(c) and c in mine:  # nothing left to close, and the stop went by itself: it filled
                    gone(c)
                mine.pop(c, None)
            elif what == "place":
                ex.guard(c, g["units"], g["stop"], g["ref"])
                placed[c] = g
        m["guards"] = mine
        if not placed:
            return
        self.sleep(ex.settle_s)
        self.acct = ex.account(fresh=True)
        for c, g in placed.items():
            shown = (self.acct.get("guards") or {}).get(c)
            if shown:
                m["guards"][c] = shown
                log.info("Emergency stop for %+.6f %s at %g, %.0f%% from the price: it rests on the exchange for the "
                         "part of the position with no take profit or stop loss of its own.", g["units"], c,
                         shown["stop"], GUARD_FRAC * 100)
            else:
                m["guard_retry"] = now + MISS_WAIT_S
                log.error("The %s emergency stop is not on the exchange after placing it; the next try is in %g s.",
                          c, MISS_WAIT_S)
                self.notes.append(f"The {c} emergency stop is not on the exchange after placing it; the next try is "
                                  f"in {MISS_WAIT_S:g} s.")

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
        if abs(got) > 1e-12:
            self._report_fill(p, got)
        what = "filled" if full else "filled in part" if got * p["units"] > 0 else "did not fill"
        if self.ex.live:
            with open(os.open(self.home / "trades.jsonl", os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o600), "a", encoding="utf-8") as f:
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

    def send(self, coin: str, units: float, ref: float, reduce_only: bool, part=None, risk=None) -> bool:
        """One market order, read back. True if it filled in full. part / risk: the part of the signal that explains
        it and that part's score, for the trade report only."""
        held = self.acct["positions"].get(coin, 0.0)
        worst = self.ex.worst(ref, units, reduce_only)
        self.pending = {"t": self.clock(), "coin": coin, "units": units, "before": held, "worst": worst,
                        "reduce_only": reduce_only, "ref": ref}
        self.order = {"t": self.pending["t"], "book": self.book(), "balance": self.acct.get("balance"), "part": part,
                      "risk": risk}
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
            part, risk = self.parts.get(coin) or (None, None)
            if not self.send(coin, units, ref, reduce, part=part, risk=risk):
                return False
            held = self.acct["positions"].get(coin, 0.0)
        return True

    def apply(self, d, now: float) -> None:
        """Coin by coin, the coins with a short-term part first (the urgent part): cancel the coin's take profit / stop
        loss when it changes or ends, trade the coin, then place its pair. So a pair is always cancelled before any
        order on its coin, and a new short-term part waits for its pair only as long as its own trade takes. An order
        that does not fill in full ends the step there: what is held of that coin is protected, and the coins not
        reached keep what rests on them until the next try, sized from a new account read."""
        m, ex, want = self.memory, self.ex, dict(d.targets)
        self.sig_px, self.parts = dict(d.px), dict(d.parts or {})
        brackets = {}
        for c, b in (d.brackets or {}).items():
            b = {**b, "units": ex.round(c, b["units"])}
            if ex.tradable(c, b["units"], d.px.get(c)):
                brackets[c] = b
                continue
            if abs(want[c] - self.acct["positions"].get(c, 0.0)) > 1e-12:  # too small to rest under its own stop loss
                want[c] -= d.brackets[c]["units"]
                m["set"] = {**m.get("set", {}), c: want[c]}
            self.notes.append(f"The {NAMES[c]} short-term trade is not opened: it is under the exchange's smallest "
                              "order, so it could not rest under its own stop loss.")
        prots = m.setdefault("prots", {})
        for c in sorted(COINS, key=lambda c: c not in brackets):
            placed, br, held = prots.get(c), brackets.get(c), self.acct["positions"].get(c, 0.0)
            if (placed and (not br or _pair(br) != _pair(placed))) or (abs(want[c]) < 1e-12 and abs(held) > 1e-12):
                ex.cancel(c)  # whatever pair rests on this coin, before any order on it
                prots.pop(c, None)
            ref = d.px.get(c) or ex.price(c)
            filled = self.trade(c, want[c], ref)
            if br:
                self.protect(br, ref)
            if not filled:
                break  # not filled in full: no further orders now

    def protect(self, br: dict, ref) -> None:
        """Rest the coin's take profit and stop loss for its scalp part: at most what is held, only on the side held.
        If the exchange does not show them after placing, the scalp part is closed: it may not stay open unprotected."""
        m, ex, c = self.memory, self.ex, br["coin"]
        held = self.acct["positions"].get(c, 0.0)
        units = ex.round(c, min(abs(br["units"]), abs(held)) * (1 if br["units"] > 0 else -1)) \
            if held * br["units"] > 0 else 0.0
        if not units:
            return
        want, prots = {**br, "units": units}, m.setdefault("prots", {})
        placed = prots.get(c)
        if placed and _pair(placed) == _pair(want) and (self.acct.get("brackets") or {}).get(c) == placed["id"]:
            return
        ex.cancel(c)  # whatever rests on this coin; the pair is placed fresh
        prots.pop(c, None)
        try:
            ex.protect(c, units, br["tp"], br["sl"], br["id"])
        except Exception as e:
            log.error("Take profit / stop loss for %s: %s", c, _plain(e))
        self.sleep(ex.settle_s)
        self.acct = ex.account(fresh=True)
        if (self.acct.get("brackets") or {}).get(c) == br["id"]:
            prots[c] = want
            log.info("Protected the %s scalp part %+.6f: take profit %g, stop loss %g.", c, units, br["tp"], br["sl"])
            return
        log.error("The take profit / stop loss for the %s scalp part are not on the exchange: closing that part.", c)
        self.notes.append(f"The {NAMES[c]} short-term part's take profit and stop loss could not be placed, so that "
                          "part was closed.")
        ex.cancel(c)
        m["done"] = {**(m.get("done") or {}), c: br["id"]}
        if self.send(c, -units, ref, True, part="scalp", risk=br.get("score")):
            m["set"] = {**m.get("set", {}), c: self.acct["positions"].get(c, 0.0)}

    # --- reporting (report.py): every call is wrapped; nothing here may stop, delay or change a step ----------------
    def _report(self, what: str, *args, **kw) -> None:
        if self.reporter is None:
            return
        try:
            getattr(self.reporter, what)(*args, **kw)
        except Exception as e:
            log.debug("Report not queued: %s", type(e).__name__)

    def _prices(self) -> dict:
        """Prices for the reports, without a request: the exchange's mark from the last account read, else the
        signal's."""
        px = {c: t["px"] for c, t in ((self.signal or {}).get("targets") or {}).items()}
        for c, b in self.book().items():
            if isinstance(b, dict) and isinstance(b.get("mark"), (int, float)) and b["mark"] > 0:
                px[c] = b["mark"]
        return px

    def _snap(self) -> tuple:
        a = self.acct or {}
        return a.get("balance"), dict(a.get("positions") or {}), self._prices()

    def _beat(self, now: float, flags: dict) -> None:
        if self.reporter is None:
            return
        try:
            sig = self.signal
            fresh = bool(sig and self.received_at is not None and now < sig["expires"]
                         and now - self.received_at <= STALE_S and sig["state"] != "offline")
            state = ("flat" if flags.get("flatten") else "daily_stop" if self.memory.get("stopped_day") == utc_day(now)
                     else "paused" if flags.get("pause") else "no_signal" if not fresh
                     else "flat" if sig["state"] == "flat" else "following")
            self._report("beat", *self._snap(), state)
        except Exception as e:
            log.debug("Report not queued: %s", type(e).__name__)

    def _report_fill(self, p: dict, got: float) -> None:
        """One order of ours that filled (in full or in part): why, its size as a multiple of the balance, its price."""
        if self.reporter is None:
            return
        try:
            c, before = p["coin"], p["before"]
            after = before + got
            ctx = self.order if self.order and self.order.get("t") == p["t"] else {}
            why = ("open" if abs(before) < 1e-12 else "add" if before * got > 0 else
                   ("flatten" if self.flags.get("flatten") else "close") if abs(after) <= 1e-9 * max(1.0, abs(before))
                   else "reduce")
            b0, b1 = (ctx.get("book") or {}).get(c) or {}, self.book().get(c) or {}
            ref = p.get("ref") or b1.get("mark")
            px, filled = ref, False  # filled: px is the real fill; else it is the price the order was sent at
            e0 = b0.get("entry") if before else 0.0
            if why in ("open", "add") and ref and b1.get("entry") and e0 is not None:  # the fill, from the new entry
                fill = (b1["entry"] * after - e0 * before) / got
                if abs(fill / ref - 1) < 0.1:
                    px, filled = fill, True
            bal = ctx.get("balance") or (self.acct or {}).get("balance")
            if not px or not bal or bal <= 0:
                return
            result = -got * (px - e0) / bal * 100 if why in ("reduce", "close", "flatten") and e0 else None
            rev = (self.signal or {}).get("rev") if ctx else None
            late = p["t"] - self.rev_seen[1] if rev is not None and rev == self.rev_seen[0] else None
            self._report("trade", c, "buy" if got > 0 else "sell", why, abs(got) * px / bal, px,
                         # no real fill price: no ref, so the server measures no distance from the signal's price
                         ref=self.sig_px.get(c) if ctx and filled else None, rev=rev, late=late, part=ctx.get("part"),
                         risk=ctx.get("risk"), result=result, snap=self._snap())
        except Exception as e:
            log.debug("Report not queued: %s", type(e).__name__)

    def _found_fills(self, prev: dict) -> None:
        """A take profit, stop loss or emergency stop that filled on the exchange since the last step: the order was
        resting at the last read, is gone now, and the position shrank by about its size. One that was cancelled on the
        exchange (the position did not move) is no trade."""
        if self.reporter is None:
            return
        try:
            m, acct, px = self.memory, self.acct, self._prices()
            bal, h0, h1 = prev.get("balance"), prev.get("positions") or {}, acct.get("positions") or {}
            found = []
            was, shown = prev.get("brackets") or {}, acct.get("brackets") or {}
            for c, pr in (m.get("prots") or {}).items():
                if was.get(c) == pr["id"] and shown.get(c) != pr["id"]:
                    u, now = pr["units"], px.get(c)
                    long = u > 0
                    why = "close" if not now else ("tp" if (now >= pr["tp"] if long else now <= pr["tp"]) else
                                                   "sl" if (now <= pr["sl"] if long else now >= pr["sl"]) else "close")
                    found.append((c, u, {"tp": pr["tp"], "sl": pr["sl"]}.get(why, now), why, "scalp", pr.get("score")))
            for c, g in (m.get("guards") or {}).items():
                if c in (prev.get("guards") or {}) and c not in (acct.get("guards") or {}):
                    trend = ((m.get("parts") or {}).get(c) or {}).get("trend") or [0.0, None]
                    found.append((c, g["units"], g["stop"], "stop", "trend", trend[1] if trend[0] else None))
            for c, u, at, why, part, risk in found:
                moved = (h0.get(c, 0.0) - h1.get(c, 0.0)) * (1 if u > 0 else -1)  # how much the position shrank
                if at and bal and bal > 0 and moved >= 0.5 * abs(u):
                    self._report("trade", c, "sell" if u > 0 else "buy", why, min(abs(u), moved) * at / bal, at,
                                 part=part, risk=risk, snap=self._snap())
        except Exception as e:
            log.debug("Report not queued: %s", type(e).__name__)


def _pair(p: dict) -> tuple:
    return p["coin"], round(p["units"], 10), p["tp"], p["sl"], p["id"]


def _plain(e: Exception) -> str:
    """An error in a few words, with anything that looks like a key or signature removed."""
    return HEX.sub("[hex removed]", str(e) or type(e).__name__)[:200]

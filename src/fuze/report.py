"""What the agent reports to the FUZE server: its trades and results, signed with a key of its own.

Every agent reports (there is no off switch, and `fuze share` shows exactly what is sent). The user chooses private
(the default: only FUZE sees the reports) or public (the agent is listed in the FUZE Fellowship on the site with a
handle). Nothing here can reach the trading loop: the agent hands a report to a queue and goes on; a thread of its own
sends it, and every error there is swallowed. The server's answer is never read by the trading code.

What a report may carry is a fixed list (the server keeps nothing else): sizes as multiples of the agent's own
balance, results in percent, prices, the signal's revision, the settings in words. Never a dollar amount, a coin
amount, a balance, a key, or anything about the computer.

  POST {server}/v1/agents/report   {"key": public key, "payload": compact JSON text, "sig": Ed25519 over the payload}
"""

from __future__ import annotations

import base64
import hashlib
import json
import logging
import math
import os
import re
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from fuze import __version__
from fuze.config import read_json, write_json

log = logging.getLogger("fuze")
PATH = "/v1/agents/report"
KEY_FILE, SEQ_FILE, EQUITY_FILE = "agent.key", "report.json", "equity.json"
MAX_BODY = 8192  # the server takes a report of at most this many bytes
MAX_ANSWER = 16_384  # an answer is a few hundred bytes; read no more than this
TIMEOUT_S = 5.0
QUEUE = 200  # reports waiting at most; the oldest beat goes first, trades last
TRADE_TRIES = 20  # a trade report is tried this many times before it is dropped
BEAT_S = 300.0  # the agent sends a beat this often
KEEP_TS_S = 540.0  # a report sent late keeps its own time while it is this young (the server takes 10 minutes)
FLOW_USD, FLOW_FRAC = 5.0, 0.02  # a balance change this far from what the prices explain is a deposit or withdrawal
PAGE = "https://fuze.trade/fellowship/"
STATES = ("following", "paused", "flat", "daily_stop", "no_signal")
WHY = ("open", "add", "reduce", "close", "tp", "sl", "stop", "flatten")

# What `fuze share` and the docs (docs/agent/sharing.md) say; the same lists as the code below sends.
SENT = [
    "Every report: the agent's id (from a key it made on this computer), the time, a counter, the kind of report, the "
    "FUZE version, the mode (simulation, testnet or mainnet), and whether you chose public.",
    "At start and when a setting changes: the sizing in words (a share of the balance or a fixed amount, the share in "
    "percent), the exposure cap as a multiple of the balance, the daily loss stop in percent, the risk allowed, the "
    "coins followed, and yes or no for a balance ceiling and for a cap per position (never their amounts).",
    "Every 5 minutes: the result since the start as a multiple (1.02 is 2% up, with deposits and withdrawals left "
    "out), each position as a multiple of the balance, and what the agent is doing (following, paused, flat, stopped "
    "for the day, no signal).",
    "After each order that filled, and when a take profit, stop loss or emergency stop filled: the coin, buy or sell, "
    "why (open, add, reduce, close, take profit, stop loss, emergency stop, flatten), its size as a multiple of the "
    "balance, the price, the signal's price and revision, the seconds between the signal and the order, the part of "
    "the signal it follows (trend or short-term) and that part's risk score when one part explains it, and on a "
    "closing trade its result in percent of the balance.",
    "When the agent stops: that it stopped.",
]
PUBLIC_ADDS = ("Public adds your handle (an X or GitHub profile link) to the hello report. The site then lists the "
               "agent in the FUZE Fellowship: its handle, mode, settings, how long it has been running, its result in "
               "percent and its trades. On testnet or mainnet, after `fuze share prove`, also its Lighter account "
               "number.")
NEVER = ("Never sent: a dollar amount, a number of coins, your balance, any key, or anything about this computer. The "
         "Lighter account number is sent only by `fuze share prove`, and shown only while the agent is public. Like "
         "any web request, a report reaches the server from your internet address: the server keeps it in memory only, "
         "to limit how many new agents one address makes, and never writes it to disk.")
DISCLOSURE = ("This agent reports its trades and results to the FUZE server. Sizes are sent as multiples of your "
              "balance and results in percent: no dollar amount, no balance and no key. Private (the default): only "
              "FUZE sees them. Public: the agent is listed in the FUZE Fellowship on fuze.trade with your X or GitHub "
              "link. `fuze share` shows exactly what is sent, and changes it.")


# --- the agent's own key ---------------------------------------------------------------------------------------------

class KeyProblem(Exception):
    """agent.key is there but cannot be used. The message says so in plain words; it never quotes the file."""


def key_path(home: Path) -> Path:
    return Path(home) / KEY_FILE


def load_key(home: Path, make: bool = True) -> Ed25519PrivateKey:
    """The agent's signing key from agent.key; made on first use (0600). A file that is there but unreadable or
    malformed raises KeyProblem: making a new one over it silently would give the agent a new identity."""
    path = key_path(home)
    try:
        data = path.read_bytes()
    except FileNotFoundError:
        if not make:
            raise KeyProblem(f"there is no {KEY_FILE} in {home} yet") from None
        sk = Ed25519PrivateKey.generate()
        pem = sk.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
                               serialization.NoEncryption())
        Path(home).mkdir(mode=0o700, parents=True, exist_ok=True)
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)  # never over a file another process just made
        with os.fdopen(fd, "wb") as f:
            f.write(pem)
        return sk
    except OSError as e:
        raise KeyProblem(f"{path} cannot be read ({type(e).__name__}). Reports are not sent until it can. Fix its "
                         "permissions, or move it away to let FUZE make a new one (the agent then gets a new id).") \
            from None
    try:
        sk = serialization.load_pem_private_key(data, password=None)
    except Exception:
        sk = None
    if not isinstance(sk, Ed25519PrivateKey):
        raise KeyProblem(f"{path} is not a key FUZE made. Reports are not sent until it is fixed. Move it away to let "
                         "FUZE make a new one (the agent then gets a new id).")
    return sk


def public_raw(sk: Ed25519PrivateKey) -> bytes:
    return sk.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)


def agent_id(sk: Ed25519PrivateKey) -> str:
    """The first 16 hex characters of the SHA-256 of the raw public key: the same id the server gives the agent."""
    return hashlib.sha256(public_raw(sk)).hexdigest()[:16]


def envelope(sk: Ed25519PrivateKey, payload: dict) -> dict:
    """What goes on the wire: the payload as compact JSON text, signed over its exact bytes."""
    text = json.dumps(payload, separators=(",", ":"))
    return {"key": base64.b64encode(public_raw(sk)).decode(), "payload": text,
            "sig": base64.b64encode(sk.sign(text.encode())).decode()}


# --- the handle: the same rules as the server's ---------------------------------------------------------------------

X_NOT = {"home", "i", "search", "explore", "settings", "intent", "share", "hashtag", "notifications", "messages",
         "login", "signup", "compose", "tos", "privacy"}
GH_NOT = {"orgs", "settings", "features", "topics", "sponsors", "about", "pricing", "login", "join", "marketplace",
          "explore", "apps", "enterprise", "collections", "trending", "notifications", "new", "organizations", "search",
          "site", "security", "contact", "readme", "issues", "pulls"}


def handle(text):
    """An X or a GitHub profile link as the user typed it -> {"kind", "name", "url"} with the address rebuilt here, or
    None. The server applies the same rules (the two repositories share no code), so what passes here passes there."""
    if not isinstance(text, str) or len(text) > 100:
        return None
    m = re.fullmatch(r"(?:https?://)?(?:www\.|mobile\.)?(x\.com|twitter\.com|github\.com)/@?([A-Za-z0-9_-]+)/?"
                     r"(?:[?#].*)?", text.strip(), re.I)
    if not m:
        return None
    host, name = m.group(1).lower(), m.group(2)
    if host == "github.com":
        ok = re.fullmatch(r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,37}[A-Za-z0-9])?", name) and "--" not in name \
            and name.lower() not in GH_NOT
        return {"kind": "github", "name": name, "url": "https://github.com/" + name} if ok else None
    ok = re.fullmatch(r"[A-Za-z0-9_]{1,15}", name) and name.lower() not in X_NOT
    return {"kind": "x", "name": name, "url": "https://x.com/" + name} if ok else None


def settings_of(cfg) -> dict:
    """The settings a hello carries: the sizing in words and yes or no for the dollar caps, never their amounts."""
    s = {"size_mode": cfg["size_mode"], "max_x": cfg["max_x"], "daily_loss_frac": cfg["daily_loss_frac"],
         "ceiling": cfg.get("max_balance_usd") is not None, "cap": cfg.get("max_position_usd") is not None}
    if cfg["size_mode"] == "percent":  # in fixed mode the share is not in use; the fixed amount is dollars: never sent
        s["percent"] = cfg["percent"]
    for k in ("risk_allowed", "coins"):  # in every config since 0.6.0 (config.validate adds the defaults)
        if k in cfg:
            s[k] = list(cfg[k]) if k == "coins" else cfg[k]
    return s


def status_line(cfg) -> str:
    """One line for `fuze run` and `fuze status`."""
    how = ("public: listed in the FUZE Fellowship" + (f" as {cfg['handle']}" if cfg.get("handle") else "")
           if cfg.get("public") else "private: only FUZE sees them")
    return (f"Reporting: this agent reports its trades and results to {cfg['server']} ({how}). `fuze share` shows "
            "what is sent.")


# --- the result: a return index that deposits and withdrawals do not move ------------------------------------------

def _num(v) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v)


class Equity:
    """A return index that starts at 1.0. Each step, the change the prices explain is the units held at the last step
    times the price change; a balance change further than max($5, 2%) from that is a deposit or withdrawal and is left
    out, anything closer counts in full (fees, funding, slippage). Kept on disk so a restart continues it."""

    def __init__(self, path: Path):
        self.path = Path(path)
        try:
            s = read_json(self.path, {}) or {}
        except (ValueError, OSError):
            s = {}
        self.s = s if isinstance(s, dict) and _num(s.get("index")) else {}

    @property
    def index(self) -> float:
        return float(self.s.get("index", 1.0))

    def step(self, balance, units: dict, prices: dict, mode: str = "") -> float:
        if not _num(balance) or balance < 0:
            return self.index
        s, idx = self.s, self.index
        prev, then = s.get("balance"), s.get("px") or {}
        if _num(prev) and prev > 0 and s.get("mode", mode) == mode:
            explained = sum(u * (prices[c] - then[c]) for c, u in (s.get("units") or {}).items()
                            if _num(u) and _num(prices.get(c)) and _num(then.get(c)))
            change = balance - prev
            flow = change - explained
            counted = explained if abs(flow) > max(FLOW_USD, FLOW_FRAC * prev) else change
            idx = max(0.0, idx * (prev + counted) / prev)
        self.s = {"index": idx, "balance": balance, "mode": mode,
                  "units": {c: u for c, u in units.items() if _num(u) and u},
                  "px": {c: p for c, p in prices.items() if _num(p) and p > 0}}
        try:
            write_json(self.path, self.s)
        except OSError as e:
            log.debug("Could not keep the result index: %s", type(e).__name__)
        return idx


# --- the reporter ---------------------------------------------------------------------------------------------------

class Reporter:
    """Reports in a queue, sent by a daemon thread of its own. hello(), beat(), trade() and bye() only put a report in
    the queue and return; none of them raises. A report that fails is dropped, except a trade, which is tried again on
    the next send, up to TRADE_TRIES times. `send` (tests) replaces the HTTP call: (body bytes) -> (status, answer)."""

    def __init__(self, cfg, home: Path | None = None, clock=time.time, send=None, start: bool = True):
        from fuze.config import home as fuze_home
        self.home = Path(home) if home else fuze_home()
        self.clock, self.post = clock, send or self._http
        self.server, self.mode = cfg["server"], cfg["mode"]
        self.public, self.handle = bool(cfg.get("public")), cfg.get("handle")
        self.settings = settings_of(cfg)
        self.q, self.lock, self.seq_lock, self.wake = [], threading.Lock(), threading.Lock(), threading.Event()
        self.problem, self.key, self.id = "", None, None
        try:
            self.key = load_key(self.home)
            self.id = agent_id(self.key)
        except KeyProblem as e:
            self.problem = str(e)
            log.warning("Reports are not sent: %s", e)
        except Exception as e:  # a full disk, a read-only folder: reporting is off, trading goes on
            self.problem = f"the agent's key could not be made ({type(e).__name__})"
            log.warning("Reports are not sent: %s.", self.problem)
        self.equity = Equity(self.home / EQUITY_FILE)
        self.busy = False
        self.thread = None
        if start and self.key:
            self.thread = threading.Thread(target=self._loop, name="fuze-report", daemon=True)
            self.thread.start()

    # --- what the agent calls: queue only, never raise --------------------------------------------------------------
    def hello(self, cfg) -> None:
        try:
            self.mode, self.public, self.handle = cfg["mode"], bool(cfg.get("public")), cfg.get("handle")
            self.settings = settings_of(cfg)
            self._put({"kind": "hello"})
        except Exception as e:
            log.debug("Report not queued: %s", type(e).__name__)

    def beat(self, balance, units: dict, prices: dict, state: str) -> None:
        """balance and units stay on this computer: they move the result index here, and only the index and each
        position as a multiple of the balance are sent."""
        try:
            x = {}
            if _num(balance) and balance > 0:
                for c, u in units.items():
                    if _num(u) and _num(prices.get(c)):
                        x[c] = round(max(-50.0, min(50.0, u * prices[c] / balance)), 4)
            self._put({"kind": "beat", "x": x, "state": state if state in STATES else "following",
                       "snap": (balance, dict(units), dict(prices))})
        except Exception as e:
            log.debug("Report not queued: %s", type(e).__name__)

    def trade(self, coin: str, side: str, why: str, x, px, ref=None, rev=None, late=None, part=None, result=None,
              snap=None, risk=None) -> None:
        """One trade. x: its value as a multiple of the balance; result: on a closing trade, percent of the balance;
        part and risk: the part of the signal that explains the order and its risk score, when one part does."""
        try:
            if side not in ("buy", "sell") or why not in WHY or not (_num(x) and x > 0) or not (_num(px) and px > 0):
                return
            t = {"coin": coin, "side": side, "why": why, "x": round(min(float(x), 50.0), 4), "px": float(px)}
            for k, v, ok in (("ref", ref, _num(ref) and ref > 0), ("rev", rev, isinstance(rev, int) and rev >= 0),
                             ("late", late, _num(late) and late >= 0), ("part", part, part in ("trend", "scalp")),
                             ("result", result, _num(result)),
                             ("risk", risk, isinstance(risk, int) and not isinstance(risk, bool) and 0 <= risk <= 100)):
                if ok:
                    t[k] = round(max(-100.0, min(1000.0, v)), 4) if k == "result" else \
                        round(min(v, 86400.0), 3) if k == "late" else v
            self._put({"kind": "trade", "trade": t, "snap": snap, "tries": 0})
        except Exception as e:
            log.debug("Report not queued: %s", type(e).__name__)

    def bye(self) -> None:
        try:
            self._put({"kind": "bye"})
        except Exception as e:
            log.debug("Report not queued: %s", type(e).__name__)

    def close(self, wait_s: float = 3.0) -> None:
        """At a clean stop: give the queue (the bye) a few seconds to go out. Trading has stopped by then."""
        end = time.monotonic() + wait_s
        while self.thread and time.monotonic() < end and (self.q or self.busy):
            self.wake.set()
            time.sleep(0.05)

    # --- what the share commands call: sent at once, the answer returned ------------------------------------------
    def send_hello(self) -> tuple:
        """(status, answer) from the server; status 0 when it could not be reached."""
        return self._now({"kind": "hello"})

    def prove(self, client, net: str, account: int) -> tuple:
        """Prove the Lighter account with a read-only token that lasts a minute, asked for here and sent once. It is
        never logged, never written to disk and never kept after this call."""
        token, err = client.c.create_auth_token_with_expiry(60, api_key_index=client.key_index)
        if err or not token:
            return 0, {"error": "Lighter's library could not make the read-only token"}
        return self._now({"kind": "prove", "wallet": {"net": net, "account": int(account), "token": token}})

    # --- inside ---------------------------------------------------------------------------------------------------
    def _put(self, item: dict) -> None:
        if not self.key:
            return
        item["t"] = self.clock()
        with self.lock:
            self.q.append(item)
            while len(self.q) > QUEUE:  # the oldest beat first, trades last
                for kind in ("beat", "hello", "bye", "trade"):
                    i = next((i for i, r in enumerate(self.q) if r["kind"] == kind), None)
                    if i is not None:
                        del self.q[i]
                        break
        self.wake.set()

    def _loop(self) -> None:
        while True:
            self.wake.wait()  # a new report wakes it: a trade that failed is tried again with the next send
            self.wake.clear()
            try:
                self._drain()
            except Exception as e:  # never let the thread die: the next report wakes it again
                log.debug("Report thread: %s", type(e).__name__)

    def _drain(self) -> None:
        """Send what waits, oldest first. The first failure ends the round: the server is likely unreachable, and a
        trade waits at the front for the next send."""
        while True:
            with self.lock:
                if not self.q:
                    return
                item = self.q[0]
                self.busy = True
            try:
                ok = self._deliver(item)
            except Exception as e:
                log.debug("Report not sent: %s", type(e).__name__)
                ok = None
            finally:
                self.busy = False
            with self.lock:
                if item["kind"] == "trade" and ok is False:
                    item["tries"] += 1
                    if item["tries"] < TRADE_TRIES:
                        return
                if self.q and self.q[0] is item:
                    self.q.pop(0)
                elif item in self.q:
                    self.q.remove(item)
            if ok is False:
                return

    def _deliver(self, item: dict):
        """True: taken. False: worth trying again (no answer, the server busy). None: refused, never tried again."""
        if item.get("snap") and "equity" not in item:  # moves the result index once, also if the send is retried
            bal, units, prices = item.pop("snap")
            item["equity"] = self.equity.step(bal, units, prices, self.mode)
        st, ans = self._send(item)
        if st == 409 and "send hello first" in str(ans.get("error")):
            st2, _ = self._send({"kind": "hello", "t": self.clock()})
            if st2 == 200:
                st, ans = self._send(item)
        if st == 200:
            return True
        log.debug("Report not taken (%s): %s", st or "no answer", str(ans.get("error"))[:200])
        again = st in (0, 429) or st >= 500 or (st == 409 and "already taken" in str(ans.get("error")))
        return False if again else None  # 409 "already taken": `fuze share` used the same counter just then

    def _now(self, item: dict) -> tuple:
        if not self.key:
            return 0, {"error": self.problem}
        item["t"] = self.clock()
        st, ans = self._send(item)
        if st == 409 and "send hello first" in str(ans.get("error")):
            if self._send({"kind": "hello", "t": self.clock()})[0] == 200:
                st, ans = self._send(item)
        return st, ans

    def _payload(self, item: dict) -> dict:
        now = self.clock()
        seq = self._seq(now)
        t = item.get("t", now)
        p = {"v": 1, "seq": seq, "ts": round(t if 0 <= now - t < KEEP_TS_S else now, 3), "kind": item["kind"],
             "ver": __version__, "mode": self.mode, "public": self.public}
        kind = item["kind"]
        if kind == "hello":
            p["settings"] = dict(self.settings)
            if self.public and self.handle:
                p["handle"] = self.handle
        elif kind == "beat":
            p.update(equity=round(max(0.0, min(1000.0, item.get("equity", self.equity.index))), 6), x=item["x"],
                     state=item["state"])
        elif kind == "trade":
            p.update(item["trade"])
        elif kind == "prove":
            p["wallet"] = item["wallet"]
        return p

    def _seq(self, now: float) -> int:
        """Milliseconds since 1970, never less than the last one sent + 1, kept on disk so a restart goes on from it."""
        path = self.home / SEQ_FILE
        with self.seq_lock:  # not the queue's lock: the agent's _put never waits on this file
            try:
                last = (read_json(path, {}) or {}).get("seq", 0)
            except (ValueError, OSError, AttributeError):
                last = 0
            seq = max(int(now * 1000), (last if isinstance(last, int) else 0) + 1)
            try:
                write_json(path, {"seq": seq})
            except OSError:
                pass
        return seq

    def _send(self, item: dict) -> tuple:
        try:
            body = json.dumps(envelope(self.key, self._payload(item))).encode()
            if len(body) > MAX_BODY:
                return 413, {"error": "the report is larger than the server takes"}
            st, ans = self.post(body)
            return int(st), ans if isinstance(ans, dict) else {}
        except Exception as e:
            log.debug("Report not sent: %s", type(e).__name__)
            return 0, {"error": f"could not reach {self.server} ({type(e).__name__})"}

    def _http(self, body: bytes) -> tuple:
        from fuze.agent import opener  # https with certificate checks, redirects refused
        req = urllib.request.Request(self.server + PATH, data=body, method="POST",
                                     headers={"Content-Type": "application/json",
                                              "User-Agent": f"fuze-agent/{__version__}"})
        try:
            with opener().open(req, timeout=TIMEOUT_S) as r:
                st, raw = r.status, r.read(MAX_ANSWER + 1)
        except urllib.error.HTTPError as e:
            st, raw = e.code, e.read(MAX_ANSWER + 1)
        if len(raw) > MAX_ANSWER:
            raise ValueError("the answer is too large")
        try:
            ans = json.loads(raw or b"{}")
        except ValueError:
            ans = {}
        return st, ans

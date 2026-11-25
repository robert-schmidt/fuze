"""Lighter (lighter.xyz), modes "testnet" and "mainnet". UNVERIFIED AGAINST THE REAL EXCHANGE: no order has been sent by
this code yet. The testnet rehearsal (`fuze rehearse`) is the first time it meets Lighter.

Two layers:
  LighterClient  the raw calls, in the exchange's integer units. Reads use Lighter's REST API over the standard library;
                 orders are signed on this machine by the official SDK (package lighter-sdk, module `lighter`), which is
                 imported only here, so simulation needs nothing extra. The API key never leaves this object.
  LighterVenue   the venue interface (venue.py): units and prices rounded to the decimals Lighter publishes for each
                 market, its smallest order, reduce-only closes, the protective pair and its record on disk.
Tests replace LighterClient with a fake; nothing in the tests talks to Lighter.
"""

from __future__ import annotations

import asyncio
import json
import math
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from fuze import keys
from fuze.config import read_json, write_json
from fuze.protocol import COINS
from fuze.venue import CHAIN_ID, HOSTS, SLIP_ADD, SLIP_REDUCE, Venue, account_link

READ_EVERY_S = 5.0  # a standard Lighter account gets about 60 requests a minute, orders included
TOKEN_S = 480.0  # the read token for open orders lasts 10 minutes; renew after 8
MAX_BODY = 4_000_000


class LighterClient:
    """Raw Lighter calls. Every error raised here is in plain words and never contains the key."""

    def __init__(self, net: str, account: int, key_index: int, key: str, opener=None):
        try:
            import lighter
            from lighter.signer_client import CreateOrderTxReq
        except ImportError:
            from fuze.config import pip_hint
            raise RuntimeError("trading on Lighter needs its SDK: " + pip_hint("mcp,lighter")) from None
        from fuze.agent import opener as tls_opener

        self.url, self.account_index, self.key_index = HOSTS[net], account, key_index
        self.http, self.Req = opener or tls_opener(), CreateOrderTxReq
        self.loop, self.token, self.token_t = asyncio.new_event_loop(), None, 0.0

        async def make():  # the SDK's HTTP session wants a running event loop
            return lighter.SignerClient(url=self.url, account_index=account, api_private_keys={key_index: key},
                                        chain_id=CHAIN_ID[net])
        try:
            self.c = self.loop.run_until_complete(make())
            err = self.c.check_client()
        except Exception as e:  # never the text: it could quote the key
            self._close_partial(e)
            raise RuntimeError(f"the Lighter SDK could not use the stored {net} API key ({type(e).__name__}). A Lighter "
                               f"API private key is 80 hexadecimal characters; enter it again with `fuze keys {net}`, "
                               "or register a new key on Lighter (docs/lighter-setup.md).") from None
        if err:
            self.close()
            raise RuntimeError(f"Lighter does not accept this API key for account {account} at key index {key_index}. "
                               f"Check both with `fuze keys {net}`.")

    def close(self) -> None:
        try:
            self.loop.run_until_complete(self.c.close())
        except Exception:
            pass

    def _close_partial(self, e: Exception) -> None:
        """The SDK opens its HTTP session before it checks the key; when its constructor fails, close that session
        (found on the failed constructor's frame) so no "unclosed client session" warning is left behind."""
        tb = e.__traceback__
        while tb:
            obj = tb.tb_frame.f_locals.get("self")
            api = getattr(obj, "api_client", None)
            if api is not None and hasattr(api, "close"):
                try:
                    self.loop.run_until_complete(api.close())
                except Exception:
                    pass
                return
            tb = tb.tb_next

    def tx(self, tx_hash: str) -> dict:
        """One transaction as Lighter shows it (public: no key, no order), or RuntimeError in plain words."""
        try:
            r = self.get("tx", by="hash", value=tx_hash)
        except urllib.error.HTTPError as e:
            try:
                msg = json.loads(e.read(4096)).get("message") or f"HTTP {e.code}"
            except Exception:
                msg = f"HTTP {e.code}"
            raise RuntimeError(f"Lighter answered: {str(msg)[:120]}") from None
        if r.get("code") != 200:
            raise RuntimeError(f"Lighter answered: {str(r.get('message') or r.get('code'))[:120]}")
        return r

    def get(self, path: str, headers=None, **params) -> dict:
        url = f"{self.url}/api/v1/{path}?" + urllib.parse.urlencode(params)
        req = urllib.request.Request(url, headers={"Accept": "application/json", **(headers or {})})
        with self.http.open(req, timeout=10) as r:
            body = r.read(MAX_BODY + 1)
        if len(body) > MAX_BODY:
            raise ValueError("Lighter's answer is too large")
        return json.loads(body)

    def markets(self) -> list:
        return self.get("orderBookDetails").get("order_book_details") or []

    def account(self) -> dict:
        accounts = self.get("account", by="index", value=self.account_index).get("accounts") or []
        if not accounts:
            raise RuntimeError(f"Lighter has no account {self.account_index}")
        return accounts[0]

    def active_orders(self, market_id: int) -> list:
        if not self.token or time.time() - self.token_t > TOKEN_S:
            token, err = self.c.create_auth_token_with_expiry(api_key_index=self.key_index)
            if err or not token:
                raise RuntimeError("could not make a read token for open orders")
            self.token, self.token_t = token, time.time()
        r = self.get("accountActiveOrders", headers={"authorization": self.token},
                     account_index=self.account_index, market_id=market_id)
        return r.get("orders") or []

    def _send(self, coro, what: str):
        """Sign and send one transaction. A 200 means accepted, not filled: the account read decides."""
        _, resp, err = self.loop.run_until_complete(asyncio.wait_for(coro, 15))
        if err or resp is None or getattr(resp, "code", None) != 200:
            raise RuntimeError(f"{what} refused by Lighter: {str(err or getattr(resp, 'message', resp))[:160]}")
        return getattr(resp, "tx_hash", None)

    def market_order(self, market_id, client_index, base, price, is_ask, reduce_only):
        return self._send(self.c.create_market_order(market_index=market_id, client_order_index=client_index,
                                                     base_amount=base, avg_execution_price=price, is_ask=is_ask,
                                                     reduce_only=reduce_only), "market order")

    def tp_sl(self, market_id, base, is_ask, tp_trigger, tp_price, sl_trigger, sl_price):
        """A take profit and a stop loss, reduce-only, of this size, one cancels the other."""
        c = self.c

        def req(kind, trigger, price):
            return self.Req(MarketIndex=market_id, ClientOrderIndex=0, BaseAmount=base, Price=price, IsAsk=int(is_ask),
                            Type=kind, TimeInForce=c.ORDER_TIME_IN_FORCE_GOOD_TILL_TIME, ReduceOnly=1,
                            TriggerPrice=trigger, OrderExpiry=c.DEFAULT_28_DAY_ORDER_EXPIRY)
        return self._send(c.create_grouped_orders(grouping_type=c.GROUPING_TYPE_ONE_CANCELS_THE_OTHER, orders=[
            req(c.ORDER_TYPE_TAKE_PROFIT_LIMIT, tp_trigger, tp_price),
            req(c.ORDER_TYPE_STOP_LOSS_LIMIT, sl_trigger, sl_price)]), "take profit and stop loss")

    def cancel_order(self, market_id, order_index):
        return self._send(self.c.cancel_order(market_index=market_id, order_index=order_index), "cancel")


def connect(cfg, net: str) -> LighterClient:
    """A client for `net` with the stored key. Raises RuntimeError in plain words when something is missing."""
    acct = cfg[f"{net}_account"]
    if acct is None:
        raise RuntimeError(f"no Lighter {net} account index is set: run `fuze keys {net}` in a terminal")
    key = keys.load(net)
    if not key:
        raise RuntimeError(f"no Lighter {net} API key is stored: run `fuze keys {net}` in a terminal")
    try:
        key = keys.clean(key)  # a key stored by an older version may have the wrong length: say so before the SDK
    except ValueError:
        raise RuntimeError(f"the stored {net} API key is not a Lighter API private key (those are 80 hexadecimal "
                           f"characters): enter it again with `fuze keys {net}` in a terminal") from None
    return LighterClient(net, acct, cfg[f"{net}_key_index"], key)


def _num(v, default=0.0) -> float:
    try:
        x = float(v)
    except (TypeError, ValueError):
        return default
    return x if math.isfinite(x) else default


class LighterVenue(Venue):
    live, settle_s = True, 1.5  # a standard Lighter account's market order waits about 300 ms

    def __init__(self, client, store: Path, clock=time.time, net="testnet", index=None):
        self.c, self.path, self.clock, self.net, self.index = client, Path(store), clock, net, index
        self.pairs = read_json(self.path, {}) or {}  # coin -> the protective pair we placed {"id", "units", "tp", "sl"}
        self.m, self.m_t, self.cache, self.cache_t, self.seen = {}, 0.0, None, 0.0, {}
        self._markets()
        self.client_index = int(clock() * 1000)  # unique per order, also across restarts

    # --- reading ------------------------------------------------------------------------------------------------
    def _markets(self) -> None:
        m = {}
        for d in self.c.markets():
            if d.get("symbol") in COINS:
                m[d["symbol"]] = {"id": int(d["market_id"]), "sd": int(d["size_decimals"]),
                                  "pd": int(d["price_decimals"]), "min_base": _num(d.get("min_base_amount")),
                                  "min_quote": _num(d.get("min_quote_amount")),
                                  "px": _num(d.get("last_trade_price")) or _num(d.get("mark_price")) or None}
        missing = set(COINS) - set(m)
        if missing:
            raise RuntimeError(f"Lighter's market list has no {', '.join(sorted(missing))} market")
        self.m, self.m_t = m, self.clock()

    def price(self, coin: str) -> float | None:
        if self.clock() - self.m_t > READ_EVERY_S:
            self._markets()
        return self.m[coin]["px"]

    def _ours(self, coin: str) -> list:
        """Our take profit / stop loss orders resting on this coin: reduce-only with a trigger price."""
        return [o for o in self.c.active_orders(self.m[coin]["id"])
                if o.get("reduce_only") and _num(o.get("trigger_price")) > 0]

    def account(self, fresh: bool = False) -> dict:
        now = self.clock()
        if self.cache and not fresh and now - self.cache_t < READ_EVERY_S:
            return self.cache
        a = self.c.account()
        ids = {v["id"]: c for c, v in self.m.items()}
        pos, self.seen = {}, {}
        for p in a.get("positions") or []:
            coin = ids.get(p.get("market_id"))
            units = _num(p.get("position")) * (-1 if int(p.get("sign") or 1) < 0 else 1)
            if coin and units:
                pos[coin] = units
                value = _num(p.get("position_value"))  # display only: fields as Lighter's docs name them
                self.seen[coin] = {"entry": _num(p.get("avg_entry_price")) or None,
                                   "mark": value / abs(units) if value > 0 else self.m[coin]["px"]}
        brackets = []
        for coin in list(self.pairs):
            if self._ours(coin):
                brackets.append(self.pairs[coin]["id"])
            else:  # gone: one of the pair filled (the other is cancelled with it), or it was cancelled
                self.pairs.pop(coin)
                write_json(self.path, self.pairs)
        self.cache, self.cache_t = {"balance": _num(a.get("total_asset_value")), "positions": pos,
                                    "brackets": brackets}, now
        return self.cache

    def link(self):
        return account_link(self.net, self.index)

    def book(self) -> dict:
        return dict(self.seen)

    # --- sizes --------------------------------------------------------------------------------------------------
    def _base(self, coin: str, units: float) -> int:
        """Units in Lighter's integer size units, rounded toward zero (1e-6: 0.59999999 is 0.6)."""
        return int(math.floor(abs(units) * 10 ** self.m[coin]["sd"] + 1e-6))

    def _px(self, coin: str, px: float) -> int:
        return int(round(px * 10 ** self.m[coin]["pd"]))

    def round(self, coin: str, units: float) -> float:
        return math.copysign(self._base(coin, units) / 10 ** self.m[coin]["sd"], units)

    def tradable(self, coin: str, units: float, px) -> bool:
        m, units = self.m[coin], abs(self.round(coin, units))
        return units > 0 and units >= m["min_base"] - 1e-12 and units * (px or m["px"] or 0) >= m["min_quote"] - 1e-9

    def smallest(self, coin: str, px: float) -> float:
        """The smallest order Lighter takes on this coin at this price, in units."""
        m = self.m[coin]
        step = 10 ** -m["sd"]
        return math.ceil(max(m["min_base"], m["min_quote"] * 1.05 / px) / step - 1e-9) * step

    # --- orders -------------------------------------------------------------------------------------------------
    def market(self, coin: str, units: float, ref_px, worst=None, reduce_only: bool = False):
        base = self._base(coin, units)
        if base <= 0:
            raise ValueError(f"{coin} order of {units} is smaller than Lighter's size step")
        if worst is None:
            from fuze.venue import worst_price
            worst = worst_price(ref_px or self.price(coin), units, reduce_only)
        self.client_index += 1
        self.cache = None
        return self.c.market_order(self.m[coin]["id"], self.client_index, base, self._px(coin, worst),
                                   units < 0, bool(reduce_only))

    def protect(self, coin: str, units: float, tp: float, sl: float, id) -> str | None:
        base = self._base(coin, units)
        if base <= 0:
            raise ValueError(f"{coin} take profit / stop loss of {units} is smaller than Lighter's size step")
        away = -1 if units > 0 else 1  # a long is closed by selling: its limit prices sit under the triggers
        self.pairs[coin] = {"id": id, "units": units, "tp": tp, "sl": sl}
        write_json(self.path, self.pairs)  # first: a pair that was sent but not recorded would be left behind
        self.cache = None
        return self.c.tp_sl(self.m[coin]["id"], base, units > 0, self._px(coin, tp),
                            self._px(coin, tp * (1 + away * SLIP_ADD)), self._px(coin, sl),
                            self._px(coin, sl * (1 + away * SLIP_REDUCE)))

    def cancel(self, coin: str) -> None:
        for o in self._ours(coin):
            self.c.cancel_order(self.m[coin]["id"], int(o["order_index"]))
        if self.pairs.pop(coin, None) is not None:
            write_json(self.path, self.pairs)
        self.cache = None

    def mark(self, prices: dict) -> None:
        pass

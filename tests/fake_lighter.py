"""A fake Lighter client: the raw calls of fuze.lighter_venue.LighterClient, in Lighter's integer units, no network.

Market ids, decimals and minimums as Lighter's orderBookDetails showed them (ETH 0, BTC 1). Knobs:
  fill   "full", "half", "none", or "lost" (fills, but the answer never comes back: the call raises)
  pair   "ok", "hidden" (accepted but never shown on the account), "refused" (raises)
  stop   the same three, for the emergency stop
  down   True: reading a transaction back fails as if testnet could not be reached
Every transaction it returns a hash for is kept in `txs`, as Lighter's /api/v1/tx shows it, for tx().
"""

import time

COINS = {0: "ETH", 1: "BTC"}
DEC = {0: (4, 2), 1: (5, 1)}  # market id -> (size decimals, price decimals)


class FakeLighter:
    def __init__(self, balance=1000.0, account=77, key_index=4):
        self.px = {"BTC": 60000.0, "ETH": 2000.0}
        self.bal, self.pos, self.orders, self.sent = balance, {0: 0.0, 1: 0.0}, {}, []
        self.fill, self.pair, self.stop, self.next = "full", "ok", "ok", 100
        self.account_index, self.key_index, self.txs, self.down = account, key_index, {}, False

    def _tx(self, h):
        self.txs[h] = {"code": 200, "hash": h, "account_index": self.account_index, "api_key_index": self.key_index,
                       "queued_at": int(time.time() * 1000), "executed_at": int(time.time() * 1000)}
        return h

    def tx(self, h):
        if self.down:
            raise OSError("testnet is not answering")
        if h not in self.txs:
            raise RuntimeError("Lighter answered: transaction not found")
        return self.txs[h]

    def markets(self):
        return [{"symbol": "ETH", "market_id": 0, "size_decimals": 4, "price_decimals": 2,
                 "min_base_amount": "0.0050", "min_quote_amount": "10.000000", "last_trade_price": self.px["ETH"]},
                {"symbol": "BTC", "market_id": 1, "size_decimals": 5, "price_decimals": 1,
                 "min_base_amount": "0.00020", "min_quote_amount": "10.000000", "last_trade_price": self.px["BTC"]},
                {"symbol": "SOL", "market_id": 2, "size_decimals": 3, "price_decimals": 3,
                 "min_base_amount": "0.050", "min_quote_amount": "10.000000", "last_trade_price": 150.0}]

    def account(self):
        return {"total_asset_value": f"{self.bal:.6f}",
                "positions": [{"market_id": m, "position": f"{abs(u):.8f}", "sign": -1 if u < 0 else 1}
                              for m, u in self.pos.items()]}

    def active_orders(self, market_id):
        return [o for o in self.orders.values() if o["market_index"] == market_id]

    def market_order(self, market_id, client_index, base, price, is_ask, reduce_only):
        self.sent.append(("market", market_id, base, price, is_ask, reduce_only))
        sd, pd = DEC[market_id]
        units, held = base / 10 ** sd * (-1 if is_ask else 1), self.pos[market_id]
        if reduce_only:
            assert held * units < 0, "reduce-only order that would open or add"
            units = max(-abs(held), min(abs(held), units))
        mid = self.px[COINS[market_id]]
        if (mid < price / 10 ** pd) if is_ask else (mid > price / 10 ** pd):
            return self._tx("ee" * 32)  # past the worst price: nothing fills
        part = {"full": 1.0, "half": 0.5, "none": 0.0, "lost": 1.0}[self.fill]
        self.pos[market_id] = round(held + units * part, 10)
        if self.fill == "lost":
            raise TimeoutError("no answer from Lighter")
        return self._tx("ab" * 32 if not reduce_only else "ba" * 32)

    def tp_sl(self, market_id, base, is_ask, tp_trigger, tp_price, sl_trigger, sl_price):
        self.sent.append(("tp_sl", market_id, base, is_ask, tp_trigger, tp_price, sl_trigger, sl_price))
        if self.pair == "refused":
            raise RuntimeError("take profit and stop loss refused by Lighter: invalid order")
        if self.pair == "ok":
            pd = DEC[market_id][1]
            for kind, trig in (("take-profit-limit", tp_trigger), ("stop-loss-limit", sl_trigger)):
                self.next += 1
                self.orders[self.next] = {"order_index": self.next, "market_index": market_id, "reduce_only": True,
                                          "trigger_price": f"{trig / 10 ** pd}", "is_ask": is_ask, "base": base,
                                          "type": kind, "client_order_index": 0}
        return self._tx("cd" * 32)

    def stop_order(self, market_id, client_index, base, is_ask, trigger, price):
        self.sent.append(("stop", market_id, base, is_ask, trigger, price))
        if self.stop == "refused":
            raise RuntimeError("emergency stop refused by Lighter: invalid order")
        if self.stop == "ok":
            self.next += 1
            self.orders[self.next] = {"order_index": self.next, "market_index": market_id, "reduce_only": True,
                                      "trigger_price": f"{trigger / 10 ** DEC[market_id][1]}", "is_ask": is_ask,
                                      "base": base, "type": "stop-loss", "client_order_index": client_index}
        return self._tx("5a" * 32)

    def cancel_order(self, market_id, order_index):
        self.sent.append(("cancel", market_id, order_index))
        self.orders.pop(order_index)
        return self._tx("ef" * 32)

    def stops_sent(self):
        return [s for s in self.sent if s[0] == "stop"]

    def stop_out(self, market_id, kind="pair"):
        """The exchange's stop loss fills: the position shrinks by the pair's size and both orders go. kind "guard":
        the emergency stop fills instead."""
        mine = [o for o in self.active_orders(market_id) if (o["type"] == "stop-loss") == (kind == "guard")]
        sd = DEC[market_id][0]
        self.pos[market_id] = round(self.pos[market_id] + mine[0]["base"] / 10 ** sd * (-1 if mine[0]["is_ask"] else 1),
                                    10)
        for o in mine:
            self.orders.pop(o["order_index"])

    def markets_sent(self):
        return [s for s in self.sent if s[0] == "market"]

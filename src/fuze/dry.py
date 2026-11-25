"""The simulated account (mode "simulation"). No money, no keys, no network. The interface is in venue.py.

Fills market orders at the signal's price plus SLIPPAGE, and checks its take profit / stop loss pairs on every price
it is shown (mark).
"""

from __future__ import annotations

import json
import time
from pathlib import Path

from fuze.config import read_json, write_json
from fuze.venue import Venue

SLIPPAGE = 0.0001  # 0.01% worse than the reference price on every market fill
FEE = 0.0


class DryExchange(Venue):
    def __init__(self, home: Path, start_balance: float, clock=time.time):
        self.path, self.log, self.clock = Path(home) / "dry.json", Path(home) / "trades.jsonl", clock
        self.s = read_json(self.path) or {"cash": start_balance, "pos": {}, "marks": {}, "brackets": {}}

    def _save(self) -> None:
        write_json(self.path, self.s)

    def _fill(self, coin: str, units: float, px: float, kind: str) -> None:
        p = self.s["pos"].get(coin, {"units": 0.0, "entry": 0.0})
        u, entry, pnl, orig = p["units"], p["entry"], 0.0, units
        if u and u * units < 0:  # reducing (or flipping): realise profit or loss on the closed part
            closed = min(abs(units), abs(u)) * (1 if u > 0 else -1)
            pnl = closed * (px - entry)
            self.s["cash"] += pnl - FEE * abs(closed) * px
            u -= closed
            units += closed
        if units:  # adding to (or opening) a position: new average entry
            entry = (entry * u + px * units) / (u + units) if u else px
            u += units
        if abs(u) < 1e-12:
            u, entry = 0.0, 0.0
            self.s["brackets"].pop(coin, None)
        self.s["pos"][coin] = {"units": u, "entry": entry}
        self.s["marks"].setdefault(coin, px)
        with open(self.log, "a", encoding="utf-8") as f:
            f.write(json.dumps({"t": self.clock(), "coin": coin, "units": orig,
                                "px": px, "kind": kind, "pnl": round(pnl, 6)}) + "\n")

    def account(self, fresh: bool = False) -> dict:
        upnl = sum(p["units"] * (self.s["marks"].get(c, p["entry"]) - p["entry"]) for c, p in self.s["pos"].items())
        return {"balance": self.s["cash"] + upnl,
                "positions": {c: p["units"] for c, p in self.s["pos"].items() if p["units"]},
                "brackets": [b["id"] for b in self.s["brackets"].values()]}

    def price(self, coin: str) -> float | None:
        return self.s["marks"].get(coin)

    def round(self, coin: str, units: float) -> float:
        return units

    def tradable(self, coin: str, units: float, px) -> bool:
        return abs(units) > 1e-12

    def link(self):
        return None

    def market(self, coin: str, units: float, ref_px: float | None, worst: float | None = None,
               reduce_only: bool = False) -> None:
        px = ref_px or self.s["marks"][coin]
        px = px * (1 + SLIPPAGE if units > 0 else 1 - SLIPPAGE)
        if worst is not None and (px > worst if units > 0 else px < worst):
            return  # like an immediate-or-cancel order on an exchange: nothing fills past the worst price
        if reduce_only:  # never opens, adds or flips
            held = self.s["pos"].get(coin, {}).get("units", 0.0)
            units = 0.0 if held * units >= 0 else max(-abs(held), min(abs(held), units))
            if not units:
                return
        self._fill(coin, units, px, "market")
        self._save()

    def protect(self, coin: str, units: float, tp: float, sl: float, id: int) -> None:
        self.s["brackets"][coin] = {"units": units, "tp": tp, "sl": sl, "id": id}
        self._save()

    def cancel(self, coin: str) -> None:
        if self.s["brackets"].pop(coin, None):
            self._save()

    def mark(self, prices: dict) -> None:
        for coin, px in prices.items():
            self.s["marks"][coin] = px
            b = self.s["brackets"].get(coin)
            if not b:
                continue
            long = b["units"] > 0
            held = self.s["pos"].get(coin, {}).get("units", 0.0)
            size = min(abs(b["units"]), abs(held)) * (-1 if long else 1)
            stop = px <= b["sl"] if long else px >= b["sl"]
            take = px >= b["tp"] if long else px <= b["tp"]
            if not size:
                stop = take = False
            if stop:  # checked first: if both are crossed, assume the worse one happened
                self._fill(coin, size, px * (1 - SLIPPAGE if long else 1 + SLIPPAGE), "stop_loss")
            elif take:
                self._fill(coin, size, b["tp"], "take_profit")
            if stop or take:
                self.s["brackets"].pop(coin, None)
        self._save()

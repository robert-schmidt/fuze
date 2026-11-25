"""Where the agent trades: one small interface, two implementations (the simulated account and Lighter).

Every venue has:
  live, settle_s          True for a real exchange; seconds to wait after an order before reading the account back
  account(fresh=False)    {"balance", "positions": {coin: units}, "brackets": [ids of scalp parts still protected]}
                          fresh=True: read now, never a cached reading (always after an order)
  price(coin)             the venue's own last price, or None
  round(coin, units)      units rounded toward zero to the size step the exchange accepts
  tradable(coin, units, px)   at least the exchange's smallest order
  market(coin, units, ref_px, worst=None, reduce_only=False)   buy (units > 0) or sell at market, never at a price
                          worse than `worst`; returns the transaction hash on a real exchange
  protect(coin, units, tp, sl, id)   rest a reduce-only take profit and stop loss, one cancels the other, for `units`
  cancel(coin)            remove that coin's take profit / stop loss
  flatten()               cancel everything and close every position, reduce-only
  mark(prices)            prices seen in the signal (the simulator uses them; a real exchange ignores them)
  link()                  the account's page on the exchange's public explorer, or None
  book()                  {coin: {"entry", "mark"}} for held coins, from the last account read (no extra request);
                          for display only (`fuze ui`), never for a decision
"""

from __future__ import annotations

from pathlib import Path

from fuze.protocol import COINS

SLIP_ADD = 0.005  # worst price of an order that opens or adds: 0.5% past the reference price
SLIP_REDUCE = 0.02  # ... and of one that reduces or closes: 2% (a close must fill)
# Lighter testnet's order book is thin: on 2026-11-25 its best Bitcoin offer stood 1.4% above its best bid, and an order
# bound to 0.5% of the last trade did not fill. Test money only, so the bound is wider there; it stays under the 5%
# from the mark price past which Lighter itself refuses a price.
TESTNET_SLIP = (0.03, 0.04)
HOSTS = {"mainnet": "https://mainnet.zklighter.elliot.ai", "testnet": "https://api.testnet.lighter.xyz"}
CHAIN_ID = {"mainnet": 304, "testnet": 300}  # passed explicitly: the SDK guesses 304 (mainnet) for the testnet host
EXPLORER = {"mainnet": "https://app.lighter.xyz/explorer", "testnet": "https://testnet.app.lighter.xyz/explorer"}


def account_link(net: str, index) -> str | None:
    return f"{EXPLORER[net]}/accounts/{index}" if net in EXPLORER and index is not None else None


def tx_link(net: str, tx) -> str | None:
    return f"{EXPLORER[net]}/logs/{tx}" if net in EXPLORER and isinstance(tx, str) and tx else None


def worst_price(ref: float, units: float, reduce_only: bool, slip=(SLIP_ADD, SLIP_REDUCE)) -> float:
    s = slip[1] if reduce_only else slip[0]
    return ref * (1 + s) if units > 0 else ref * (1 - s)


class Venue:
    live, settle_s, slip = False, 0.0, (SLIP_ADD, SLIP_REDUCE)

    def worst(self, ref: float, units: float, reduce_only: bool) -> float:
        """The worst price a market order may fill at, with this venue's bound."""
        return worst_price(ref, units, reduce_only, self.slip)

    def book(self) -> dict:
        return {}

    def flatten(self) -> list:
        """Cancel every take profit / stop loss, then one reduce-only market order per open position. Returns the
        transaction hashes. Does not wait: the caller reads the account back."""
        out = []
        for coin in COINS:
            self.cancel(coin)
        for coin, units in self.account(fresh=True)["positions"].items():
            px = self.price(coin)
            if units and px:
                out.append(self.market(coin, -units, px, self.worst(px, -units, True), True))
        return out


def open_venue(cfg, home: Path, clock=None, client=None):
    """The venue for cfg["mode"]. Live modes need the Lighter SDK, the account index and the stored API key."""
    import time

    clock = clock or time.time
    mode = cfg["mode"]
    if mode == "simulation":
        from fuze.dry import DryExchange
        return DryExchange(home, cfg["dry_balance"], clock)
    from fuze.lighter_venue import LighterVenue, connect
    return LighterVenue(client or connect(cfg, mode), Path(home) / f"lighter-{mode}.json", clock, net=mode,
                        index=cfg[f"{mode}_account"])

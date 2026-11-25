"""A made-up mainnet state in a FUZE folder, for tests of `fuze ui` and for its screenshots. No real key anywhere:
keys.json says the key is in the OS keyring, which keys.state() reports as "set" without reading anything.

    FUZE_HOME=/some/temp/dir python tests/ui_fixture.py [pid]   writes it (status refreshed with the given pid)
"""

from __future__ import annotations

import json
import os
import sys
import time

from fuze import __version__, config, modes

SECRET = "ab" * 32  # what a key looks like; tests check it never reaches the page


def mainnet_home(now: float | None = None, pid: int | None = None, key_file: bool = False) -> None:
    now = time.time() if now is None else now
    h = config.ensure_home()
    config.save({**config.DEFAULTS, "mode": "mainnet", "mainnet_account": 281474, "testnet_account": 1207,
                 "percent": 5.0, "max_position_usd": 400.0, "daily_loss_frac": 0.05})
    if key_file:  # the key in a 0600 file, as without a keyring
        config.atomic_write(h / "lighter-mainnet.key", SECRET)
        config.write_json(h / "keys.json", {"mainnet": "file", "testnet": "keyring"})
    else:
        config.write_json(h / "keys.json", {"mainnet": "keyring", "testnet": "keyring"})
    config.write_json(h / "rehearsal.json", {"ok": True, "net": "testnet", "machine": modes.machine(),
                                             "version": __version__, "t": now - 86400,
                                             "steps": [{"step": s, "ok": True} for s in modes.STEPS]})
    link = "https://app.lighter.xyz/explorer/accounts/281474"
    sig = {"v": 1, "seq": 90211, "rev": 412, "ts": now - 3, "expires": now + 57, "source": "paper", "state": "live",
           "targets": {"BTC": {"x": -1.69, "px": 58520.0}, "ETH": {"x": 0.33, "px": 1642.4}},
           "scalp": {"coin": "BTC", "x": -1.29, "tp": 58029.0, "sl": 59442.0, "id": 796},
           "why": "We hold short 1.69 times the balance on Bitcoin and long 0.33 times on Ether."}
    day = time.strftime("%Y-%m-%d", time.gmtime(now))
    config.write_json(h / "status.json", {
        "t": now - 1, "pid": pid or os.getpid(), "version": __version__, "mode": "mainnet",
        "server": "https://fuze.trade", "account_link": link, "note": modes.realer_note("mainnet", "paper"),
        "reason": "Following revision 412: BTC short $205 (0.08 times your balance), ETH long $40 (0.02 times your "
                  "balance).",
        "flags": {"pause": False, "flatten": False},
        "account": {"balance": 2431.8, "positions": {"BTC": -0.0035, "ETH": 0.0244}, "brackets": [796]},
        "signal": sig, "received_at": now - 2.5, "last_drop": "", "pending": None,
        "limits": {}, "started": now - 3 * 3600 - 420,
        "book": {"BTC": {"entry": 58911.0, "mark": 58520.0}, "ETH": {"entry": 1630.1, "mark": 1642.4}},
        "protected": {"coin": "BTC", "units": -0.0027, "tp": 58029.0, "sl": 59442.0, "id": 796},
        "day": day, "day_start": 2460.0, "stopped_day": None})
    tx = "0x" + "c3" * 32
    rows = [{"t": now - 3 * 3600, "mode": "mainnet", "coin": "BTC", "asked": -0.0035, "units": -0.0035,
             "worst": 58620.0, "reduce_only": False, "kind": "market", "result": "filled", "tx": tx,
             "link": f"https://app.lighter.xyz/explorer/logs/{tx}"},
            {"t": now - 2 * 3600, "mode": "mainnet", "coin": "ETH", "asked": 0.025, "units": 0.0244, "worst": 1650.0,
             "reduce_only": False, "kind": "market", "result": "filled in part", "tx": tx,
             "link": "https://evil.example/explorer/logs/x"}]  # a link to anywhere but Lighter's explorer is dropped
    (h / "trades.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows))


if __name__ == "__main__":
    mainnet_home(pid=int(sys.argv[1]) if len(sys.argv) > 1 else None)

"""The follow decision: a pure function from (signal, account, limits, flags, memory) to target positions.

No I/O here. `memory` is a small dict the agent keeps between calls; decide() returns the updated copy.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from fuze.protocol import COINS
from fuze.sizing import base_usd, fit

MIN_DIFF_USD = 10.0  # ignore changes smaller than this ...
MIN_DIFF_FRAC = 0.02  # ... or than 2% of the balance, unless the target is zero
STALE_S = 60.0  # no valid message for this long = offline
SCALP_SL_MAX = 0.015  # a scalp stop loss further than 1.5% from the price is refused


@dataclass
class Decision:
    act: bool  # True: bring positions to `targets` and replace brackets with `bracket`
    targets: dict  # coin -> units (negative = short); empty when holding
    bracket: dict | None  # {"coin", "units", "tp", "sl", "id"} for the scalp part
    px: dict  # coin -> the signal price to trade at (missing = use the exchange's own price)
    reason: str
    memory: dict


def utc_day(now: float) -> str:
    return datetime.fromtimestamp(now, timezone.utc).date().isoformat()


def scalp_problem(scalp: dict, px: float) -> str:
    """Empty if the scalp's stop loss and take profit make sense around `px`."""
    short = scalp["x"] < 0
    sl, tp = scalp["sl"], scalp["tp"]
    if (sl <= px) if short else (sl >= px):
        return "its stop loss is not on the losing side of the price"
    if abs(sl - px) / px > SCALP_SL_MAX:
        return f"its stop loss is more than {SCALP_SL_MAX:.1%} away from the price"
    if (tp >= px) if short else (tp <= px):
        return "its take profit is not on the winning side of the price"
    return ""


def decide(signal, received_at, now, account, cfg, flags, memory) -> Decision:
    m = dict(memory)
    bal, held = account["balance"], account["positions"]
    today = utc_day(now)
    if m.get("day") != today:
        m["day"], m["day_start"] = today, bal
    m.setdefault("live_at", now)
    if m.get("scalp") and m["scalp"]["id"] not in account["brackets"]:
        m["scalp_done"], m["scalp"] = m["scalp"]["id"], None  # its stop loss or take profit fired

    def close(reason):
        m.update(rev=None, set={c: 0.0 for c in COINS}, scalp=None)
        return Decision(True, {c: 0.0 for c in COINS}, None, {}, reason, m)

    def hold(reason):
        return Decision(False, {}, None, {}, reason, m)

    if flags.get("flatten"):
        return close("FLATTEN is on: everything is closed and stays closed until you run `fuze unflatten`.")
    floor = m["day_start"] * (1 - cfg["daily_loss_frac"])
    if m.get("stopped_day") == today or bal <= 0 or bal <= floor:
        m["stopped_day"] = today
        return close(f"Daily loss stop: the balance fell {cfg['daily_loss_frac']:.0%} or more since the start of "
                     "the UTC day. Everything is closed until the next UTC day.")
    if flags.get("pause"):
        return hold("PAUSE is on: holding what we have, no new orders until you run `fuze resume`.")

    fresh = (signal is not None and received_at is not None and now < signal["expires"]
             and now - received_at <= STALE_S)
    if fresh and signal["state"] != "offline":
        m["live_at"] = now
    else:
        quiet = now - m["live_at"]
        if cfg.get("stale_flat_min") and quiet > cfg["stale_flat_min"] * 60:
            return close(f"No live signal for {quiet / 60:.0f} minutes, more than your stale_flat_min: "
                         "everything is closed.")
        what = "The signal says it is offline" if fresh else "No fresh signal"
        return hold(f"{what}: holding what we have and opening nothing new.")
    if signal["state"] == "flat":
        return close("The signal is flat: everything is closed and we stay out.")

    rev, base = signal["rev"], base_usd(cfg, bal)
    tol = max(MIN_DIFF_USD, MIN_DIFF_FRAC * bal)
    px = {c: t["px"] for c, t in signal["targets"].items()}
    last = m.get("set") or {}
    drift = any(abs(held.get(c, 0.0) - last.get(c, 0.0)) * px.get(c, 1.0) > (tol if c in px else 1e-9)
                for c in COINS)
    if m.get("rev") == rev and not drift:
        return hold(f"Following revision {rev}; nothing to change.")

    notes = ["Resync: the held position no longer matched what we last set."] if m.get("rev") == rev else []
    usd = {c: t["x"] * base for c, t in signal["targets"].items()}  # position value in dollars, before caps
    sc, scalp_usd = signal["scalp"], 0.0
    if sc:
        problem = "it already closed at its stop loss or take profit" if sc["id"] == m.get("scalp_done") \
            else scalp_problem(sc, px[sc["coin"]])
        if problem:
            usd[sc["coin"]] -= sc["x"] * base
            notes.append(f"The scalp part is not opened: {problem}.")
        else:
            scalp_usd = sc["x"] * base
    k, cut = fit(usd, cfg, bal)  # the caps: one factor per coin, the scalp part shrinks with its coin
    notes += cut

    targets = {}
    for c in COINS:
        want = usd.get(c, 0.0) * k[c] / px[c] if c in px else 0.0
        h = held.get(c, 0.0)
        targets[c] = want if want == 0 or abs(want - h) * px[c] >= tol else h
    bracket = None
    if scalp_usd and targets[sc["coin"]] * scalp_usd > 0:
        units = scalp_usd * k[sc["coin"]] / px[sc["coin"]]
        units = min(abs(units), abs(targets[sc["coin"]])) * (1 if units > 0 else -1)
        bracket = {"coin": sc["coin"], "units": units, "tp": sc["tp"], "sl": sc["sl"], "id": sc["id"]}
    m.update(rev=rev, set=targets, scalp={"id": sc["id"], "coin": sc["coin"]} if bracket else None)
    head = f"Following revision {rev}: " + (", ".join(
        f"{c} {'short' if v < 0 else 'long'} ${abs(v * k[c]):,.0f} ({abs(v * k[c]) / bal:.2f} times your balance)"
        for c, v in usd.items() if v) or "no position")
    return Decision(True, targets, bracket, px, " ".join([head + "."] + notes), m)

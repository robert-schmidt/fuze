"""The follow decision: a pure function from (signal, account, limits, flags, memory) to target positions.

No I/O here. `memory` is a small dict the agent keeps between calls; decide() returns the updated copy.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from fuze.config import LIMITS
from fuze.protocol import COINS
from fuze.sizing import base_usd, fit

MIN_DIFF_USD = 10.0  # ignore changes smaller than this ...
MIN_DIFF_FRAC = 0.02  # ... or than 2% of the balance, unless the target is zero
NOISE_USD = 1.0  # a difference under a dollar (balance and price wiggle) is not worth a word
RECHECK_S = 300.0  # on the same revision, compare what the signal asks for with what is held this often
RECHECK_FRAC = 0.10  # ... and correct only a coin that is off by more than this share of its size (and the band
#                      above): x drifting with the price alone must not cause small orders every few minutes
STALE_S = 60.0  # no valid message for this long = offline
SCALP_SL_MAX = 0.015  # a scalp stop loss further than 1.5% from the price is refused
# The emergency stop: a stop order that rests on the exchange for the part of a position with no take profit / stop
# loss of its own (the trend part). The signal's trend rule has no stop, and a history test of following stops on it
# found every one worse than none, so this order is not a trading rule: while the agent follows a live signal it is
# kept GUARD_FRAC from the price, on both sides of a move, and it fills only when nobody is moving it (the agent is
# off, or the signal is gone or paused).
GUARD_FRAC = 0.20  # how far from the price the stop is set
GUARD_STEP = 0.05  # it is set again once the price is this far from where it was set
GUARD_AGE_S = 14 * 86400.0  # ... or once it is this old: Lighter keeps a resting order 28 days at most


@dataclass
class Decision:
    act: bool  # True: bring positions to `targets` and replace brackets with `bracket`
    targets: dict  # coin -> units (negative = short); empty when holding
    bracket: dict | None  # {"coin", "units", "tp", "sl", "id"} for the scalp part
    px: dict  # coin -> the signal price to trade at (missing = use the exchange's own price)
    reason: str
    memory: dict


def min_change(bal: float) -> float:
    """The smallest change in dollars the agent makes on a coin (except closing it): the larger of $10 and 2%."""
    return max(MIN_DIFF_USD, MIN_DIFF_FRAC * bal)


def asked_usd(signal, cfg, bal: float) -> dict:
    """Coin -> the position value in dollars the signal asks for at these limits, caps included (scalp part as sent)."""
    if not signal or signal.get("state") != "live":
        return {}
    base = base_usd(cfg, bal)
    usd = {c: t["x"] * base for c, t in signal["targets"].items()}
    k, _ = fit(usd, cfg, bal)
    return {c: v * k[c] for c, v in usd.items()}


def compare(wanted: dict, held: dict, px: dict, tol) -> list:
    """Per coin, what the signal asks for and what is held, in dollars, and whether the difference is under the
    smallest change the agent makes. For `fuze status`, the MCP status tool and `fuze ui`."""
    out = []
    for c in COINS:
        p = px.get(c)
        w, h = (wanted or {}).get(c), (held or {}).get(c, 0.0)
        if not p or (w is None and not h):
            continue
        a, b = (w or 0.0) * p, h * p
        under = bool(tol) and NOISE_USD <= abs(a - b) < tol and abs(w or 0.0) > 1e-12
        out.append({"coin": c, "asked_usd": round(a, 2), "held_usd": round(b, 2), "difference_usd": round(a - b, 2),
                    "under_min_change": under})
    return out


def from_status(s: dict) -> tuple:
    """(rows, smallest change) from status.json as the agent writes it; ([], None) when it has nothing to compare."""
    s = s if isinstance(s, dict) else {}
    a = s.get("account") if isinstance(s.get("account"), dict) else {}
    held = a.get("positions") if isinstance(a.get("positions"), dict) else {}
    wanted = s.get("wanted") if isinstance(s.get("wanted"), dict) else {}
    sig = s.get("signal") if isinstance(s.get("signal"), dict) else {}
    px = {c: t.get("px") for c, t in (sig.get("targets") or {}).items() if isinstance(t, dict)}
    book = s.get("book") if isinstance(s.get("book"), dict) else {}
    for c, b in book.items():
        if isinstance(b, dict) and b.get("mark") and c not in px:
            px[c] = b["mark"]
    num = (int, float)
    wanted = {c: v for c, v in wanted.items() if isinstance(v, num) and not isinstance(v, bool)}
    held = {c: v for c, v in held.items() if isinstance(v, num) and not isinstance(v, bool)}
    px = {c: v for c, v in px.items() if isinstance(v, num) and not isinstance(v, bool) and v > 0}
    tol = s.get("min_change_usd") if isinstance(s.get("min_change_usd"), num) else None
    return compare(wanted, held, px, tol), tol


def describe_compare(rows: list, tol) -> list:
    """compare() in plain words, one line per coin, plus why nothing is traded when a difference is too small."""
    def side(v):
        return "none" if abs(v) < 0.005 else f"{'short' if v < 0 else 'long'} ${abs(v):,.0f}"

    lines = [f"{r['coin']}: the signal asks for {side(r['asked_usd'])}, you hold {side(r['held_usd'])}" for r in rows]
    small = [r["coin"] for r in rows if r["under_min_change"]]
    if small:
        lines.append(f"The difference on {' and '.join(small)} is under ${tol:,.0f}, the smallest change the agent "
                     "makes (the larger of $10 and 2% of your balance), so it is not traded now.")
    if any(r["under_min_change"] and abs(r["held_usd"]) < 0.005 for r in rows):
        lines.append("A coin held at none because its size is under that step stays unfollowed at this size.")
    return lines


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


def guard_plan(held: float, covered: float, px: float, resting, now: float, following: bool, tol: float) -> tuple:
    """The emergency stop one coin needs. Pure.

    held: units on the account; covered: the units of them that rest under the scalp's own pair; resting: the stop
    the exchange shows now ({"units", "stop", "ref", "t"}) or None; following: a live signal is being followed (the
    only time the stop moves with the price); tol: a size difference in units too small to replace the order for.
    Returns ("none" | "keep" | "remove" | "place", {"units", "stop", "ref"} for "place")."""
    rest = held - covered
    if held * rest <= 0:  # nothing held, or the scalp's pair closes all of it
        return ("remove" if resting else "none"), None
    if resting and resting["units"] * rest > 0 and abs(resting["units"] - rest) <= tol:
        moved = following and abs(px / resting["ref"] - 1) >= GUARD_STEP
        if not moved and now - resting["t"] < GUARD_AGE_S:
            return "keep", None
        if not following:  # only old: the same stop again, so a quiet signal never moves it
            return "place", {"units": rest, "stop": resting["stop"], "ref": resting["ref"]}
    return "place", {"units": rest, "stop": px * (1 - GUARD_FRAC if rest > 0 else 1 + GUARD_FRAC), "ref": px}


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
        m.update(rev=None, set={c: 0.0 for c in COINS}, scalp=None, wanted={c: 0.0 for c in COINS})
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
    tol = min_change(bal)
    m["min_change"] = tol
    px = {c: t["px"] for c, t in signal["targets"].items()}
    last = m.get("set") or {}
    drift = any(abs(held.get(c, 0.0) - last.get(c, 0.0)) * px.get(c, 1.0) > (tol if c in px else 1e-9)
                for c in COINS)
    limits = {k: cfg.get(k) for k in LIMITS}
    same = m.get("rev") == rev
    changed = same and m.get("limits") not in (None, limits)  # `fuze limits` or the MCP tool changed them
    recheck = same and not drift and not changed and now - m.get("checked", 0.0) >= RECHECK_S
    if same and not drift and not changed and not recheck:
        return hold(f"Following revision {rev}; nothing to change.")

    notes = []
    if changed:
        notes.append("Your limits changed: resized to them.")
    elif same and drift:
        notes.append("Resync: the held position no longer matched what we last set.")
    usd = {c: t["x"] * base for c, t in signal["targets"].items()}  # position value in dollars, before caps
    sc, scalp_usd = signal["scalp"], 0.0
    if sc:
        held_scalp = same and (m.get("scalp") or {}).get("id") == sc["id"]  # open and protected: keep it
        problem = "it already closed at its stop loss or take profit" if sc["id"] == m.get("scalp_done") \
            else "" if held_scalp else scalp_problem(sc, px[sc["coin"]])
        if problem:
            usd[sc["coin"]] -= sc["x"] * base
            notes.append(f"The scalp part is not opened: {problem}.")
        else:
            scalp_usd = sc["x"] * base
    k, cut = fit(usd, cfg, bal)  # the caps: one factor per coin, the scalp part shrinks with its coin
    notes += cut

    wanted = {c: usd.get(c, 0.0) * k[c] / px[c] if c in px else 0.0 for c in COINS}
    targets = {}
    for c in COINS:
        want, h = wanted[c], held.get(c, 0.0)
        band = max(tol, RECHECK_FRAC * abs(want) * px[c]) if recheck and c in px else tol
        shrink = changed and want * h >= 0 and abs(want) < abs(h)  # lowered limits: every coin shrinks, however little
        targets[c] = want if want == 0 or shrink or abs(want - h) * px.get(c, 0.0) >= band else h
    m["checked"], m["wanted"] = now, wanted
    if recheck:
        if all(abs(targets[c] - held.get(c, 0.0)) < 1e-12 for c in COINS):
            return hold(f"Following revision {rev}; nothing to change.")
        notes.insert(0, "Re-check: the held position was further from what the signal asks for than the dead band.")
    bracket = None
    if scalp_usd and targets[sc["coin"]] * scalp_usd > 0:
        units = scalp_usd * k[sc["coin"]] / px[sc["coin"]]
        units = min(abs(units), abs(targets[sc["coin"]])) * (1 if units > 0 else -1)
        bracket = {"coin": sc["coin"], "units": units, "tp": sc["tp"], "sl": sc["sl"], "id": sc["id"]}
    m.update(rev=rev, set=targets, limits=limits,
             scalp={"id": sc["id"], "coin": sc["coin"]} if bracket else None)

    def words(v):
        return "none" if abs(v) < 0.005 else f"{'short' if v < 0 else 'long'} ${abs(v):,.0f}"

    asked = ", ".join(f"{c} {words(wanted[c] * px[c])}" for c in COINS if c in px)
    after = ", ".join(f"{c} {words(targets[c] * px[c])}" for c in COINS if c in px)
    head = f"Following revision {rev}: the signal asks for {asked} at your limits" + \
        ("." if asked == after else f"; the agent aims for {after}.")
    small = [c for c in COINS if c in px and wanted[c] and abs(targets[c] - wanted[c]) * px[c] >= NOISE_USD
             and abs(targets[c] - held.get(c, 0.0)) < 1e-12]
    if small:
        notes.append(f"The change on {' and '.join(small)} is under ${tol:,.0f}, the smallest change the agent makes "
                     "(the larger of $10 and 2% of your balance), so it is not traded.")
    return Decision(True, targets, bracket, px, " ".join([head] + notes), m)

"""The follow decision: a pure function from (signal, account, limits, flags, memory) to target positions.

No I/O here. `memory` is a small dict the agent keeps between calls; decide() returns the updated copy. Per coin it
remembers the take profit and stop loss the agent placed (`prots`) and the short-term trade that already closed at one
of them (`done`), so that trade is never opened again.

Which parts of the signal are followed (followed()): per coin, the trend part when its risk score is at or under the
user's `risk_allowed`, plus the coin's short-term trade (scalp) on the same rule; a coin not in the user's `coins`, or
one the exchange lists no market for, is wanted at 0. Then every limit applies as before (sizing.fit).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from fuze.config import LIMITS
from fuze.protocol import COINS, NAMES, scalp_of
from fuze.sizing import base_usd, counted, fit

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
GUARD_AGE_S = 14 * 86400.0  # ... or once it is this old: placed for 28 days (the SDK's default; Lighter allows 5 min
#                             to 30 days)
PART_MOVED = 0.02  # for the trade report: a part counts as changed when its x moved by more than this share of it


@dataclass
class Decision:
    act: bool  # True: bring positions to `targets` and the take profit / stop loss pairs to `brackets`
    targets: dict  # coin -> units (negative = short); empty when holding
    brackets: dict  # coin -> {"coin", "units", "tp", "sl", "id", "score"} for that coin's short-term part
    px: dict  # coin -> the signal price to trade at (missing = use the exchange's own price)
    reason: str
    memory: dict
    parts: dict = None  # coin -> (part, score) when one part of the signal explains this change, for the trade report


def migrate(memory) -> dict:
    """The memory of agent 0.5.0 in this version's form. It kept one protected short-term part, `prot`, the trade it
    decided, `scalp`, and the id of one that closed at its take profit or stop loss, `scalp_done` (version 1 of the
    signal has one short-term trade, always on Bitcoin). Each becomes the entry of its coin, so a take profit and stop
    loss resting on the exchange at the update is still known, and a closed trade is still not opened again."""
    m = dict(memory or {})
    if "prot" in m:
        p = m.pop("prot")
        if isinstance(p, dict) and p.get("coin") in COINS:
            m["prots"] = {**(m.get("prots") or {}), p["coin"]: p}
    m.pop("scalp", None)  # what was decided; `prots` holds what was placed and confirmed
    if "scalp_done" in m:
        d = m.pop("scalp_done")
        if isinstance(d, int) and not isinstance(d, bool):
            m["done"] = {**(m.get("done") or {}), "BTC": d}
    return m


def followed(signal, cfg, absent=(), held=None) -> tuple:
    """The parts of a live signal this agent follows: ({coin: trend x, 0 when skipped}, {coin: scalp}, notes).

    Per coin, as docs/PROTOCOL.md says: not in the user's `coins` (or no market for it on this exchange): 0, and the
    coin's scalp is ignored; otherwise its trend part when the part's score is at or under `risk_allowed`, plus its
    scalp on the same rule. A part is followed whole or skipped whole. The notes say each skip in plain words."""
    trend, scalps, notes, held = {}, {}, [], held or {}
    ra, mine = cfg["risk_allowed"], cfg["coins"]
    for c, t in signal["targets"].items():
        name, sc, tr = NAMES[c], scalp_of(signal, c), t["trend"]
        trend[c] = 0.0
        if c not in mine:
            if t["x"] or held.get(c):
                notes.append(f"{name} is not among your coins: " + ("what you hold of it is closed."
                                                                     if held.get(c) else "not followed."))
            continue
        if c in absent:
            if t["x"]:
                notes.append(f"The exchange lists no {c} market here: {name} is not traded.")
            continue
        if tr["score"] <= ra:
            trend[c] = tr["x"]
        elif tr["x"]:
            notes.append(f"The {name} trend part scores {tr['score']}, above your risk allowed of {ra}: not followed.")
        if sc and sc["score"] <= ra:
            scalps[c] = sc
        elif sc:
            notes.append(f"The {name} short-term trade scores {sc['score']}, above your risk allowed of {ra}: "
                         "not followed.")
    return trend, scalps, notes


def min_change(bal: float) -> float:
    """The smallest change in dollars the agent makes on a coin (except closing it): the larger of $10 and 2%."""
    return max(MIN_DIFF_USD, MIN_DIFF_FRAC * bal)


def asked_usd(signal, cfg, bal: float) -> dict:
    """Coin -> the position value in dollars the signal asks for at these limits, caps included: the parts at or under
    the risk allowed, on the user's coins (a scalp part as sent)."""
    if not signal or signal.get("state") != "live" or signal.get("v") != 2:  # a status.json older than version 2
        return {}
    base = base_usd(cfg, bal)
    trend, scalps, _ = followed(signal, cfg)
    usd = {c: (x + (scalps[c]["x"] if c in scalps else 0.0)) * base for c, x in trend.items()}
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


def _explain(before, after) -> tuple | None:
    """(part, score) when one part of a coin changed and the other did not; None when both or neither did (a resize
    to new limits, a re-check, a resync). before/after: {"trend": [x, score], "scalp": [x, score]}."""
    moved = {k: abs(after[k][0] - before[k][0]) > PART_MOVED * max(abs(after[k][0]), abs(before[k][0])) + 1e-9
             for k in ("trend", "scalp")}
    if moved["trend"] == moved["scalp"]:
        return None
    part = "trend" if moved["trend"] else "scalp"
    return part, after[part][1] if after[part][0] else before[part][1]


def decide(signal, received_at, now, account, cfg, flags, memory) -> Decision:
    m = migrate(memory)
    real, held = account["balance"], account["positions"]
    shown = account.get("brackets") or {}  # coin -> the id of the pair the exchange shows resting
    bal = counted(cfg, real)  # what sizes are worked out on: never more than the user's balance ceiling
    today = utc_day(now)
    if m.get("day") != today:
        m["day"], m["day_start"] = today, real
    m.setdefault("live_at", now)
    prots, done = dict(m.get("prots") or {}), dict(m.get("done") or {})
    for c, p in prots.items():
        if shown.get(c) != p["id"]:  # its stop loss or take profit fired (or it was cancelled on the exchange)
            done[c] = p["id"]  # the entry stays in `prots` until the order step cancels whatever is left of the pair
    m["prots"], m["done"] = prots, done

    def close(reason):
        m.update(rev=None, set={c: 0.0 for c in COINS}, wanted={c: 0.0 for c in COINS}, parts={})
        return Decision(True, {c: 0.0 for c in COINS}, {}, {}, reason, m, {})

    def hold(reason):
        return Decision(False, {}, {}, {}, reason, m, {})

    if flags.get("flatten"):
        return close("FLATTEN is on: everything is closed and stays closed until you run `fuze unflatten`.")
    floor = m["day_start"] - cfg["daily_loss_frac"] * counted(cfg, m["day_start"])  # the loss counts on the ceiling too
    if m.get("stopped_day") == today or real <= 0 or real <= floor:
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
    trend, scalps, skipped = followed(signal, cfg, account.get("absent") or (), held)
    notes += skipped
    usd = {c: (x + (scalps[c]["x"] if c in scalps else 0.0)) * base for c, x in trend.items()}  # before caps
    scalp_usd = {}
    for c, sc in scalps.items():
        kept = same and (prots.get(c) or {}).get("id") == sc["id"]  # open and protected: keep it
        problem = "it already closed at its stop loss or take profit" if sc["id"] == done.get(c) \
            else "" if kept else scalp_problem(sc, px[c])
        if problem:
            usd[c] -= sc["x"] * base
            notes.append(f"The {NAMES[c]} short-term trade is not opened: {problem}.")
        else:
            scalp_usd[c] = sc["x"] * base
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
    brackets = {}
    for c, su in scalp_usd.items():
        if targets[c] * su > 0:
            units = su * k[c] / px[c]
            units = min(abs(units), abs(targets[c])) * (1 if units > 0 else -1)
            sc = scalps[c]
            brackets[c] = {"coin": c, "units": units, "tp": sc["tp"], "sl": sc["sl"], "id": sc["id"],
                           "score": sc["score"]}
    parts, explained = {}, {}
    for c in COINS:
        t = signal["targets"].get(c)
        parts[c] = {"trend": [trend.get(c, 0.0), t["trend"]["score"] if t else 0],
                    "scalp": [scalps[c]["x"] if c in brackets else 0.0, scalps[c]["score"] if c in scalps else 0]}
        why = _explain((m.get("parts") or {}).get(c) or {"trend": [0.0, 0], "scalp": [0.0, 0]}, parts[c])
        if why:
            explained[c] = why
    m.update(rev=rev, set=targets, limits=limits, parts=parts)

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
    return Decision(True, targets, brackets, px, " ".join([head] + notes), m, explained)

"""How big the follower's positions are. Pure functions, no I/O; used by follow, the CLI and the MCP server.

The signal gives, per coin, `x` = our position value divided by our balance. The follower picks how much money
follows that signal:
  percent: `percent`% of its balance (grows and shrinks with the balance), position value = x × percent/100 × balance
  fixed:   `fixed_usd`, whatever the balance is (does not compound),   position value = x × fixed_usd
Then the caps: `max_position_usd` on any one coin, the highest leverage Lighter allows on that coin's market
(MAX_LEVERAGE) × the counted balance, and `max_x` × the counted balance across coins.

Which parts of the signal follow at all is decided before (follow.decide): a part whose risk score is above
`risk_allowed`, or a coin not in `coins`, is wanted at 0.
"""

from __future__ import annotations

SIZE_FIELD = {"percent": "percent", "fixed_usd": "fixed"}  # the field that sizes each mode
EXAMPLE_X = 1.8  # our position, as a multiple of our balance, in the worked example
# The highest leverage Lighter allows on a market, where it is under the exposure cap's highest value of 25 (as of
# 28 November 2026: HYPE 20 times, LIT 5 times; Bitcoin and Ether allow more, so the exposure cap bounds them). FUZE
# does not change the leverage setting on Lighter; instead no position is sized larger than this many times the
# balance, so the market's own margin rule is not the reason an order fails. The same in every mode, so a simulation
# shows what Lighter would take.
MAX_LEVERAGE = {"HYPE": 20.0, "LIT": 5.0}
LABELS = {"size_mode": "sizing", "percent": "share of your balance", "fixed_usd": "fixed amount",
          "max_position_usd": "cap per position", "max_x": "exposure cap", "max_balance_usd": "balance ceiling",
          "daily_loss_frac": "daily loss stop",
          "stale_flat_min": "close after no signal for", "risk_allowed": "risk allowed", "coins": "coins"}


def counted(cfg, bal: float) -> float:
    """The balance the agent counts: the account's, or the user's ceiling when the account holds more. Sizes, the
    exposure cap and the daily loss stop all use it, so money beyond the ceiling never makes a position bigger."""
    cap = cfg.get("max_balance_usd")
    return min(bal, cap) if cap else bal


def base_usd(cfg, bal: float) -> float:
    """The money that follows the signal: a position of x times our balance becomes x times this."""
    return cfg["fixed_usd"] if cfg["size_mode"] == "fixed" else cfg["percent"] / 100 * counted(cfg, bal)


def fit(usd: dict, cfg, bal: float) -> tuple:
    """Per-coin factors (at most 1) that bring position values inside the cap per position, then inside max_x.

    Returns (factors, notes). The scalp part of a coin shrinks by the same factor as the coin.
    """
    cap, bal = cfg.get("max_position_usd"), counted(cfg, bal)
    f = {c: cap / abs(v) if cap and abs(v) > cap else 1.0 for c, v in usd.items()}
    notes = [f"Cut to your cap of ${cap:,.0f} per position."] if any(k < 1 for k in f.values()) else []
    lev = [c for c, v in usd.items() if c in MAX_LEVERAGE and abs(v) * f[c] > MAX_LEVERAGE[c] * bal]
    for c in lev:
        f[c] = MAX_LEVERAGE[c] * bal / abs(usd[c])
        notes.append(f"Cut {c} to {MAX_LEVERAGE[c]:g} times your balance, the highest leverage Lighter allows on it.")
    total = sum(abs(v) * f[c] for c, v in usd.items())
    if total > cfg["max_x"] * bal:
        k = cfg["max_x"] * bal / total
        f = {c: x * k for c, x in f.items()}
        notes.append(f"Scaled down to your exposure cap of {cfg['max_x']:g} times the balance.")
    return f, notes


def example(cfg, bal: float) -> str:
    """The worked example: what one Bitcoin position would be at this balance, caps included."""
    def usd(b):
        v = EXAMPLE_X * base_usd(cfg, b)
        return v, v * fit({"BTC": v}, cfg, b)[0]["BTC"]

    raw, got = usd(bal)
    text = (f"With ${bal:,.0f} and our position at {EXAMPLE_X:g} times our balance, yours would be "
            f"${got:,.0f} of Bitcoin" + (f" (${raw:,.0f} before your caps)." if got < raw - 0.005 else "."))
    return text + f" With ${2 * bal:,.0f} it would be ${usd(2 * bal)[1]:,.0f}."


def fmt(name: str, value) -> str:
    """One setting in plain words."""
    if name == "size_mode":
        return "a share of your balance" if value == "percent" else "a fixed amount"
    if name == "percent":
        return f"{value:g}%"
    if name in ("fixed_usd", "max_position_usd"):
        return "no cap" if value is None else f"${value:,.0f}"
    if name == "max_balance_usd":
        return "none (the whole account)" if value is None else f"${value:,.0f}"
    if name == "max_x":
        return f"{value:g} times your balance"
    if name == "daily_loss_frac":
        return f"{value:.0%}"
    if name == "stale_flat_min":
        return "off" if value is None else f"{value:g} minutes"
    if name == "risk_allowed":
        return f"{value} (a part that can lose {value / 10:g}% of the balance on a bad day, or less)"
    if name == "coins":
        return ", ".join(value)
    return str(value)


def describe(cfg, bal: float) -> list:
    """The sizing and its limits in plain words, with the worked example at this balance."""
    if cfg["size_mode"] == "fixed":
        head = (f"A fixed ${cfg['fixed_usd']:,.0f} follows the signal, whatever your balance is: the size your "
                "position has when ours equals our whole balance. It does not grow with your balance.")
    else:
        head = (f"{cfg['percent']:g}% of your balance follows the signal. Your positions grow and shrink with "
                "your balance.")
    cap, top = cfg.get("max_position_usd"), cfg.get("max_balance_usd")
    return [head,
            f"Largest position on one coin: {fmt('max_position_usd', cap)}.",
            f"Most you hold across coins: {cfg['max_x']:g} times your balance.",
            f"Daily loss stop: {cfg['daily_loss_frac']:.0%} of the balance in a UTC day closes everything.",
            *([f"Balance ceiling: ${top:,.0f}. The agent counts no more than this as your balance, whatever the "
               "account holds."] if top else []),
            f"Risk allowed: {cfg['risk_allowed']}. A part of a position is followed whole when its risk score is "
            f"{cfg['risk_allowed']} or less, and skipped whole above it. A score of 20 means the part can lose 2% of "
            "the balance on a bad day; it says nothing about how likely the part is to win.",
            f"Coins: {', '.join(cfg['coins'])}. Any other coin is not opened, and what is held of it is closed.",
            example(cfg, bal)]


def raised(cur, new, bal: float) -> list:
    """Names of the settings whose change lets the agent take more risk. Anything listed needs the user's
    typed confirmation in a terminal; the MCP server refuses it outright."""
    same = new["size_mode"] == cur["size_mode"]  # the amount of the mode not in use raises nothing by itself
    up = [k for k in ("percent", "fixed_usd") if same and new["size_mode"] == SIZE_FIELD[k] and new[k] > cur[k]]
    up += [k for k in ("max_x", "daily_loss_frac") if new[k] > cur[k]]
    for k in ("max_position_usd", "max_balance_usd", "stale_flat_min"):  # None (no cap, never) is the riskiest
        if cur.get(k) is not None and (new.get(k) is None or new[k] > cur[k]):
            up.append(k)
    if new["size_mode"] != cur["size_mode"] and base_usd(new, bal) > base_usd(cur, bal):
        up.append("size_mode")
    if new["risk_allowed"] > cur["risk_allowed"]:  # parts with higher scores are then followed
        up.append("risk_allowed")
    if set(new["coins"]) - set(cur["coins"]):  # one more coin can be held
        up.append("coins")
    return up

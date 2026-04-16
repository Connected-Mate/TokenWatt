"""Energy conversions between Claude tokens and household appliances.

All figures are approximations. Sources documented in README.md.

Not all tokens cost the same energy:
- Output tokens are by far the most expensive (autoregressive generation).
- Input / cache-creation tokens are a prefill pass - much cheaper per token.
- Cache-read tokens are served from a KV cache - roughly an order of
  magnitude cheaper than a fresh input token.

Defaults (Wh/token) are calibrated so that a typical Claude 3 Opus
400-token round-trip lands near the published ~4 Wh figure.
"""

from __future__ import annotations

import os


def _env_float(name: str, default: float) -> float:
    try:
        return float(os.environ.get(name, default))
    except ValueError:
        return default


WH_PER_OUTPUT_TOKEN = _env_float("TOKENWATT_WH_OUTPUT", 0.005)
WH_PER_INPUT_TOKEN = _env_float("TOKENWATT_WH_INPUT", 0.0003)
WH_PER_CACHE_CREATE_TOKEN = _env_float("TOKENWATT_WH_CACHE_CREATE", 0.0003)
WH_PER_CACHE_READ_TOKEN = _env_float("TOKENWATT_WH_CACHE_READ", 0.00003)


# (key, icon, singular, plural, Wh per use). Ordered from small to big so
# the "headline" pick can prefer the largest appliance that still registers
# at >= 1.
APPLIANCES = [
    ("toast",     "🍞", "toast",            "toasts",            40),
    ("kettle",    "☕", "kettle cup",       "kettle cups",       100),
    ("phone",     "📱", "phone charge",     "phone charges",     15),
    ("bulb",      "💡", "LED hour (10 W)",  "LED hours (10 W)",  10),
    ("macbook",   "💻", "MacBook hour",     "MacBook hours",     30),
    ("microwave", "🍲", "microwave (5 min)", "microwaves (5 min)", 150),
    ("airfryer",  "🍟", "airfryer run",     "airfryer runs",     500),
    ("washer",    "🧺", "washing cycle",    "washing cycles",    800),
]

# Small subset we always show. Rest goes into the "More equivalents" submenu.
HEADLINE_KEYS = ("airfryer", "washer", "toast", "phone")


def tokens_to_wh(
    input_tokens: int = 0,
    output_tokens: int = 0,
    cache_creation: int = 0,
    cache_read: int = 0,
) -> float:
    return (
        input_tokens * WH_PER_INPUT_TOKEN
        + output_tokens * WH_PER_OUTPUT_TOKEN
        + cache_creation * WH_PER_CACHE_CREATE_TOKEN
        + cache_read * WH_PER_CACHE_READ_TOKEN
    )


def totals_to_wh(totals: dict) -> float:
    return tokens_to_wh(
        input_tokens=totals.get("input", 0),
        output_tokens=totals.get("output", 0),
        cache_creation=totals.get("cache_create", 0),
        cache_read=totals.get("cache_read", 0),
    )


def _fmt_count(n: float) -> str:
    if n >= 100:
        return f"{n:,.0f}".replace(",", ",")
    if n >= 10:
        return f"{n:,.1f}".replace(",", ",")
    if n >= 1:
        return f"{n:.1f}"
    return f"{n:.2f}"


def _fmt_line(icon: str, n: float, singular: str, plural: str) -> str:
    label = singular if 0.5 <= n < 1.5 else plural
    return f"{icon}  {_fmt_count(n)} {label}"


def headline_pick(wh: float) -> tuple[str, str, float]:
    """Pick the single most readable equivalent — the biggest unit that is >= 1.

    Returns (icon, formatted text, count).
    """
    for key, icon, singular, plural, cost in reversed(APPLIANCES):
        count = wh / cost
        if count >= 1:
            label = singular if count < 1.5 else plural
            return icon, f"{icon} {_fmt_count(count)} {label}", count
    # Fallback: smallest unit
    key, icon, singular, plural, cost = APPLIANCES[0]
    count = wh / cost
    return icon, f"{icon} {_fmt_count(count)} {plural}", count


def headline_lines(wh: float) -> list[str]:
    """The 4 key equivalents, always shown."""
    lines = []
    for key, icon, singular, plural, cost in APPLIANCES:
        if key in HEADLINE_KEYS:
            lines.append(_fmt_line(icon, wh / cost, singular, plural))
    return lines


def other_lines(wh: float) -> list[str]:
    """The remaining equivalents for the submenu."""
    lines = []
    for key, icon, singular, plural, cost in APPLIANCES:
        if key not in HEADLINE_KEYS:
            lines.append(_fmt_line(icon, wh / cost, singular, plural))
    return lines

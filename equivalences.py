"""Energy conversions between Claude tokens, money, CO2, and appliances.

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

# Retail electricity price (France regulated tariff, 2026 ~0.25 €/kWh).
EUR_PER_KWH = _env_float("TOKENWATT_EUR_PER_KWH", 0.25)
# French grid carbon intensity (~60 gCO2eq/kWh, RTE 2024 average).
G_CO2_PER_KWH = _env_float("TOKENWATT_GCO2_PER_KWH", 60.0)


# (key, icon, singular, plural, Wh per use). Ordered small -> big so the
# headline pick can prefer the largest appliance that still registers >= 1.
APPLIANCES = [
    ("toast",     "🍞", "toast",             "toasts",             40),
    ("kettle",    "☕", "kettle cup",        "kettle cups",        100),
    ("phone",     "📱", "phone charge",      "phone charges",      15),
    ("bulb",      "💡", "LED hour (10 W)",   "LED hours (10 W)",   10),
    ("macbook",   "💻", "MacBook hour",      "MacBook hours",      30),
    ("microwave", "🍲", "microwave (5 min)", "microwaves (5 min)", 150),
    ("airfryer",  "🍟", "airfryer run",      "airfryer runs",      500),
    ("washer",    "🧺", "washing cycle",     "washing cycles",     800),
]

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


def wh_to_eur(wh: float) -> float:
    return (wh / 1000.0) * EUR_PER_KWH


def wh_to_g_co2(wh: float) -> float:
    return (wh / 1000.0) * G_CO2_PER_KWH


def _fmt_count(n: float) -> str:
    if n >= 1000:
        return f"{n:,.0f}"
    if n >= 100:
        return f"{n:,.0f}"
    if n >= 10:
        return f"{n:.1f}"
    if n >= 1:
        return f"{n:.1f}"
    return f"{n:.2f}"


def _fmt_line(icon: str, n: float, singular: str, plural: str) -> str:
    label = singular if 0.5 <= n < 1.5 else plural
    return f"{icon}  {_fmt_count(n)} {label}"


def fmt_eur(wh: float) -> str:
    eur = wh_to_eur(wh)
    if eur >= 10:
        return f"€{eur:,.2f}"
    if eur >= 1:
        return f"€{eur:.2f}"
    if eur >= 0.01:
        return f"€{eur:.3f}"
    return f"{eur*100:.2f} c"


def fmt_co2(wh: float) -> str:
    g = wh_to_g_co2(wh)
    if g >= 1000:
        return f"{g/1000:.2f} kg CO₂"
    if g >= 10:
        return f"{g:.0f} g CO₂"
    return f"{g:.1f} g CO₂"


def headline_pick(wh: float) -> tuple[str, str, float]:
    """Single most readable equivalent — largest appliance still >= 1."""
    for key, icon, singular, plural, cost in reversed(APPLIANCES):
        count = wh / cost
        if count >= 1:
            label = singular if count < 1.5 else plural
            return icon, f"{icon} {_fmt_count(count)} {label}", count
    key, icon, singular, plural, cost = APPLIANCES[0]
    count = wh / cost
    return icon, f"{icon} {_fmt_count(count)} {plural}", count


def headline_compact(wh: float) -> str:
    """Shorter form for the menu-bar title (icon + count only)."""
    for key, icon, singular, plural, cost in reversed(APPLIANCES):
        count = wh / cost
        if count >= 1:
            return f"{icon} {_fmt_count(count)}"
    key, icon, singular, plural, cost = APPLIANCES[0]
    return f"{icon} {_fmt_count(wh / cost)}"


def headline_bar(wh: float, max_width: int = 20) -> str:
    """Visual emoji bar matching the headline pick, clamped to max_width."""
    icon, _, count = headline_pick(wh)
    if count <= 0:
        return ""
    whole = int(count)
    if whole >= max_width:
        return icon * max_width + f"… ({_fmt_count(count)})"
    fractional = count - whole
    bar = icon * whole
    if fractional >= 0.5:
        bar += "▏"
    return bar


def headline_lines(wh: float) -> list[str]:
    return [
        _fmt_line(icon, wh / cost, singular, plural)
        for key, icon, singular, plural, cost in APPLIANCES
        if key in HEADLINE_KEYS
    ]


def other_lines(wh: float) -> list[str]:
    return [
        _fmt_line(icon, wh / cost, singular, plural)
        for key, icon, singular, plural, cost in APPLIANCES
        if key not in HEADLINE_KEYS
    ]


# Gentle, half-serious nudges shown at the bottom of the menu. The tone is:
# the planet is drying up, you are burning tokens anyway, hopefully what
# you're building is worth the candle.
FOOTER_MESSAGES = [
    "🌍 The planet is drying up a little with every token. Hope what you're building is worth the candle.",
    "🌵 Earth gets a little more arid. We keep consuming. May your build be worth it.",
    "🔥 Every token warms the planet a notch. Hope your code is worth the heat.",
    "🏜️ The climate clock ticks. We tokenize anyway. Let's at least ship something great.",
    "💧 One less drop in the aquifer, one more prompt in the log. Worth it?",
    "🌡️ +0.000001 °C to the atmosphere. Hope this prompt was worth more than a toast.",
    "🪫 Planet's battery is low. Build something that matters with the tokens you just spent.",
    "🌾 Fields crack, glaciers retreat, tokens flow. May your craft be worth the candle.",
    "☀️ Another megawatt of sunshine spent on LLM math. Make it count.",
    "🐝 Bees are tired. LLMs are not. Let's hope the thing you shipped matters.",
]


def footer_message() -> str:
    import random
    return random.choice(FOOTER_MESSAGES)


# Unicode block characters for a sparkline.
_SPARK_BLOCKS = " ▁▂▃▄▅▆▇█"


def sparkline(values: list[float]) -> str:
    if not values:
        return ""
    peak = max(values)
    if peak <= 0:
        return _SPARK_BLOCKS[0] * len(values)
    out = []
    for v in values:
        ratio = max(0.0, v / peak)
        idx = min(len(_SPARK_BLOCKS) - 1, int(round(ratio * (len(_SPARK_BLOCKS) - 1))))
        out.append(_SPARK_BLOCKS[idx])
    return "".join(out)

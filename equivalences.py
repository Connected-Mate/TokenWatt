"""Tokens -> electricity and water, compared to everyday objects.

Pick strategy:
  - Prefer the biggest unit that gives a count >= 0.2
  - "0.5 showers" beats "40 water bottles"
  - Sub-unit counts render as pie circles: ◔ ◑ ◕ ●

All numbers are approximations. Full references in SOURCES.md.
"""

from __future__ import annotations

import os


def _env_float(name: str, default: float) -> float:
    try:
        return float(os.environ.get(name, default))
    except ValueError:
        return default


# Wh per token. Output ~10x input/cache-create, cache-read ~10x cheaper again.
WH_OUTPUT = _env_float("TOKENWATT_WH_OUTPUT", 0.005)
WH_INPUT = _env_float("TOKENWATT_WH_INPUT", 0.0003)
WH_CACHE_CREATE = _env_float("TOKENWATT_WH_CACHE_CREATE", 0.0003)
WH_CACHE_READ = _env_float("TOKENWATT_WH_CACHE_READ", 0.00003)

# Litres of datacenter water per kWh (cooling + power-generation).
# 1.8 L/kWh is the Shaolei Ren et al. "Making AI Less Thirsty" 2023 figure.
L_WATER_PER_KWH = _env_float("TOKENWATT_L_WATER_PER_KWH", 1.8)


# (icon, label, cost per unit). Ordered small -> big.
ELECTRICITY = [
    ("💡", "LED hour",         10),      # 10 W LED x 1 h
    ("📱", "phone charge",     15),      # iPhone battery
    ("💻", "MacBook hour",     30),      # charging load
    ("🍞", "toast",            40),      # 1200 W x 2 min
    ("☕", "kettle cup",       100),     # 250 mL to 90 C
    ("🍲", "microwave (5 min)", 150),    # 1800 W x 5 min
    ("🍟", "airfryer run",     500),     # 1500 W x 20 min
    ("🧺", "washing cycle",    800),     # 40 C, class A
    ("🧊", "fridge day",       800),     # class A fridge, 24 h
    ("🍕", "pizza oven bake",  900),     # 200 C, 15 min
    ("🔥", "induction meal",   1500),    # 30 min, 3 kW burner
    ("🌡️", "home AC hour",     2000),   # split unit
    ("🚗", "EV km",            180),     # avg EV ~180 Wh/km
]

WATER = [
    ("🥛", "glass of water",   0.25),    # 250 mL
    ("🍶", "water bottle",     0.5),     # 500 mL
    ("🧴", "shampoo wash",     5),       # hair wash rinse
    ("🚽", "toilet flush",     6),       # standard dual-flush
    ("🫖", "kettle fill",      1.7),     # full kettle
    ("🧼", "hand wash",        2),       # 20 s with tap
    ("🧑‍🍳", "cooking batch",  10),      # pasta + rinse
    ("🚿", "shower (5 min)",   80),      # 16 L/min
    ("🛁", "bathtub",          150),     # typical fill
    ("🌳", "tree (daily)",     40),      # mature tree daily need
    ("💦", "pool refill 1m³",  1000),    # 1 cubic metre
]


def tokens_to_wh(input_tokens=0, output_tokens=0, cache_creation=0, cache_read=0):
    return (
        input_tokens * WH_INPUT
        + output_tokens * WH_OUTPUT
        + cache_creation * WH_CACHE_CREATE
        + cache_read * WH_CACHE_READ
    )


def totals_to_wh(totals: dict) -> float:
    return tokens_to_wh(
        input_tokens=totals.get("input", 0),
        output_tokens=totals.get("output", 0),
        cache_creation=totals.get("cache_create", 0),
        cache_read=totals.get("cache_read", 0),
    )


def wh_to_litres(wh: float) -> float:
    return (wh / 1000.0) * L_WATER_PER_KWH


def fmt_wh(wh: float) -> str:
    if wh >= 1000:
        return f"{wh/1000:.1f} kWh"
    return f"{wh:.0f} Wh"


def fmt_litres(litres: float) -> str:
    if litres >= 1000:
        return f"{litres/1000:.1f} m³"
    if litres >= 1:
        return f"{litres:.1f} L"
    return f"{litres*1000:.0f} mL"


def _fmt_count(n: float) -> str:
    if n >= 100:
        return f"{n:,.0f}"
    if n >= 10:
        return f"{n:.0f}"
    if n >= 1:
        return f"{n:.1f}"
    return f"{n:.2f}"


def _fraction_word(count: float) -> str:
    """0.25 -> 'a quarter of a', etc. Used when count < 1."""
    if count < 0.15:
        return "a tenth of a"
    if count < 0.4:
        return "a quarter of a"
    if count < 0.65:
        return "half a"
    if count < 0.9:
        return "three-quarters of a"
    return "almost a full"


def pie(fraction: float) -> str:
    """◔ ◑ ◕ ● — camembert wedges for fractional counts."""
    if fraction <= 0:
        return "○"
    if fraction < 0.15:
        return "○"
    if fraction < 0.4:
        return "◔"
    if fraction < 0.65:
        return "◑"
    if fraction < 0.9:
        return "◕"
    return "●"


def pick_best(value: float, units: list[tuple]) -> tuple[str, str, float, float]:
    """Pick the biggest unit whose count is at least 0.2.

    Falls back to the smallest unit if everything is too small,
    or the biggest if everything is too big (then count will be huge).
    """
    ordered = sorted(units, key=lambda u: u[2])
    for icon, label, cost in reversed(ordered):
        count = value / cost
        if count >= 0.2:
            return icon, label, count, cost
    icon, label, cost = ordered[0]
    return icon, label, value / cost, cost


def headline(value: float, units: list[tuple]) -> tuple[str, str]:
    """Return (main line, visual line) for a quantity.

    Examples:
      21 L water  -> ('🚿 a quarter of a shower', '◔')
      771 L water -> ('🛁 5 bathtubs',              '●●●●●')
      0.02 kWh    -> ('💡 almost a full LED hour',  '◕')
    """
    icon, label, count, _cost = pick_best(value, units)
    if count < 1:
        text = f"{icon}  {_fraction_word(count)} {label}"
        visual = pie(count)
    elif count < 10:
        whole = int(count)
        remainder = count - whole
        plural = "" if count < 1.5 else "s"
        text = f"{icon}  {_fmt_count(count)} {label}{plural}"
        visual = "●" * whole
        if remainder >= 0.15:
            visual += pie(remainder)
    else:
        text = f"{icon}  {_fmt_count(count)} {label}s"
        visual = "●" * 10 + f"  × {_fmt_count(count)}"
    return text, visual


def compact_title(wh: float) -> str:
    """Menu-bar title: electricity icon+count, water icon+count."""
    e_icon, _, e_count, _ = pick_best(wh, ELECTRICITY)
    w_icon, _, w_count, _ = pick_best(wh_to_litres(wh), WATER)
    return f"{e_icon}{_fmt_count(e_count)}  {w_icon}{_fmt_count(w_count)}"

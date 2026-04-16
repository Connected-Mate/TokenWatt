"""Tokens -> electricity and water, shown as everyday objects.

Four featured units per category. Each one always shown so the user
sees the full scale at a glance:

  Electricity: toast, airfryer, washing machine, induction meal
  Water:       bottle, cooking pot, shower, bathtub

Sub-unit counts render as camembert wedges: ◔ ¼ · ◑ ½ · ◕ ¾ · ● 1 full.

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

# Litres of datacenter water per kWh — Ren et al., "Making AI Less
# Thirsty", arXiv:2304.03271. 1.8 L/kWh is the US-average WUE figure.
L_WATER_PER_KWH = _env_float("TOKENWATT_L_WATER_PER_KWH", 1.8)


# Four fun, concrete electricity units shown on every refresh.
#   (icon, singular label, plural label, Wh per use)
ELECTRICITY = [
    ("🍞", "toast",           "toasts",           40),     # 1200 W × 2 min
    ("🍟", "airfryer run",    "airfryer runs",    500),    # 1500 W × 20 min
    ("🧺", "washing cycle",   "washing cycles",   800),    # 40°C, EU class A
    ("🔥", "induction meal",  "induction meals",  1500),   # 3 kW × 30 min
]

# Four fun, concrete water units.
WATER = [
    ("🍶", "water bottle",    "water bottles",    0.5),    # 500 mL
    ("🍳", "cooking pot",     "cooking pots",     2),      # pasta pot
    ("🚿", "shower",          "showers",          80),     # 5 min × 16 L/min
    ("🛁", "bathtub",         "bathtubs",         150),    # typical fill
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
    if n >= 10_000:
        return f"{n:,.0f}"
    if n >= 100:
        return f"{n:,.0f}"
    if n >= 10:
        return f"{n:.0f}"
    if n >= 1:
        return f"{n:.1f}"
    return f"{n:.2f}"


def _fraction_word(count: float) -> str:
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
    """Camembert wedge for fractions. ○ ◔ ◑ ◕ ●"""
    if fraction <= 0 or fraction < 0.15:
        return "○"
    if fraction < 0.4:
        return "◔"
    if fraction < 0.65:
        return "◑"
    if fraction < 0.9:
        return "◕"
    return "●"


def line(icon: str, singular: str, plural: str, count: float) -> str:
    """Format one equivalent line."""
    if count < 1:
        return f"{icon}  {_fraction_word(count)} {singular}  {pie(count)}"
    label = singular if count < 1.5 else plural
    return f"{icon}  {_fmt_count(count)} {label}"


def electricity_lines(wh: float) -> list[str]:
    return [line(icon, s, p, wh / cost) for icon, s, p, cost in ELECTRICITY]


def water_lines(litres: float) -> list[str]:
    return [line(icon, s, p, litres / cost) for icon, s, p, cost in WATER]


def _best_unit(value: float, units: list[tuple]):
    """Pick the unit whose count lands most naturally in [1, 30].

    Walks from biggest to smallest; returns the first unit with count >= 1.
    If every unit yields count > 30 or < 1, falls back to the biggest one.
    """
    ordered = sorted(units, key=lambda u: u[3])  # small -> big
    for icon, sing, plur, cost in reversed(ordered):
        count = value / cost
        if 1 <= count <= 30:
            return icon, sing, plur, count
    for icon, sing, plur, cost in reversed(ordered):
        count = value / cost
        if count >= 1:
            return icon, sing, plur, count
    icon, sing, plur, cost = ordered[0]
    return icon, sing, plur, value / cost


def hero_electricity(wh: float) -> str:
    icon, sing, plur, count = _best_unit(wh, ELECTRICITY)
    label = sing if count < 1.5 else plur
    return f"{icon}  {_fmt_count(count)} {label}"


def hero_water(litres: float) -> str:
    icon, sing, plur, count = _best_unit(litres, WATER)
    label = sing if count < 1.5 else plur
    return f"{icon}  {_fmt_count(count)} {label}"


def compact_title(wh: float) -> str:
    """Menu-bar title: the two most legible hero numbers."""
    e_icon, _, _, e_count = _best_unit(wh, ELECTRICITY)
    w_icon, _, _, w_count = _best_unit(wh_to_litres(wh), WATER)
    return f"{e_icon} {_fmt_count(e_count)}  ·  {w_icon} {_fmt_count(w_count)}"

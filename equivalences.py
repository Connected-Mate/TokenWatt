"""Tokens -> electricity and water, with a few everyday comparisons.

Defaults are approximate. Override any of them via environment variables.
Sources in README.md.
"""

from __future__ import annotations

import os


def _env_float(name: str, default: float) -> float:
    try:
        return float(os.environ.get(name, default))
    except ValueError:
        return default


# Electricity per token (Wh). Output tokens are ~10x input / cache-create,
# cache reads are ~10x cheaper again.
WH_OUTPUT = _env_float("TOKENWATT_WH_OUTPUT", 0.005)
WH_INPUT = _env_float("TOKENWATT_WH_INPUT", 0.0003)
WH_CACHE_CREATE = _env_float("TOKENWATT_WH_CACHE_CREATE", 0.0003)
WH_CACHE_READ = _env_float("TOKENWATT_WH_CACHE_READ", 0.00003)

# Water usage effectiveness: litres of water per kWh of datacenter energy
# (cooling + power generation). ~1.5 L/kWh is a common US-average figure.
L_WATER_PER_KWH = _env_float("TOKENWATT_L_WATER_PER_KWH", 1.5)


# Electricity equivalents: (icon, label, Wh per use). Ordered small -> big.
ELECTRICITY = [
    ("🍞", "toast",            40),
    ("📱", "phone charge",     15),
    ("💡", "LED hour",         10),
    ("🍟", "airfryer run",     500),
    ("🧺", "washing cycle",    800),
]

# Water equivalents: (icon, label, L per use).
WATER = [
    ("🍶", "water bottle",     0.5),
    ("🥛", "glass of water",   0.25),
    ("🚿", "shower",           80),
    ("🛁", "bathtub",          150),
]


def tokens_to_wh(
    input_tokens: int = 0,
    output_tokens: int = 0,
    cache_creation: int = 0,
    cache_read: int = 0,
) -> float:
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


def _fmt_num(n: float) -> str:
    if n >= 1000:
        return f"{n:,.0f}"
    if n >= 100:
        return f"{n:,.0f}"
    if n >= 10:
        return f"{n:.0f}"
    if n >= 1:
        return f"{n:.1f}"
    return f"{n:.2f}"


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


def pick_electricity(wh: float) -> tuple[str, str, float]:
    """Pick the biggest electricity equivalent with count >= 1."""
    for icon, label, cost in reversed(ELECTRICITY):
        count = wh / cost
        if count >= 1:
            return icon, label, count
    icon, label, cost = ELECTRICITY[0]
    return icon, label, wh / cost


def pick_water(litres: float) -> tuple[str, str, float]:
    """Pick the biggest water equivalent with count >= 1."""
    candidates = sorted(WATER, key=lambda x: x[2])
    for icon, label, cost in reversed(candidates):
        count = litres / cost
        if count >= 1:
            return icon, label, count
    icon, label, cost = candidates[0]
    return icon, label, litres / cost


def electricity_headline(wh: float) -> str:
    icon, label, count = pick_electricity(wh)
    plural = "" if 0.5 <= count < 1.5 else "s"
    return f"{icon}  {_fmt_num(count)} {label}{plural}"


def water_headline(litres: float) -> str:
    icon, label, count = pick_water(litres)
    plural = "" if 0.5 <= count < 1.5 else "s"
    return f"{icon}  {_fmt_num(count)} {label}{plural}"


def compact_title(wh: float) -> str:
    """Short menu-bar title: electricity + water icons with counts."""
    e_icon, _, e_count = pick_electricity(wh)
    w_icon, _, w_count = pick_water(wh_to_litres(wh))
    return f"{e_icon}{_fmt_num(e_count)}  {w_icon}{_fmt_num(w_count)}"


# Visual bars — one emoji per unit, capped.
def bar(icon: str, count: float, width: int = 10) -> str:
    whole = int(count)
    if whole <= 0:
        return ""
    if whole >= width:
        return icon * width + "…"
    return icon * whole

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


# Wh per token, by type. Override any via env var.
WH_PER_OUTPUT_TOKEN = _env_float("TOKENWATT_WH_OUTPUT", 0.005)
WH_PER_INPUT_TOKEN = _env_float("TOKENWATT_WH_INPUT", 0.0003)
WH_PER_CACHE_CREATE_TOKEN = _env_float("TOKENWATT_WH_CACHE_CREATE", 0.0003)
WH_PER_CACHE_READ_TOKEN = _env_float("TOKENWATT_WH_CACHE_READ", 0.00003)


# Appliance energy costs (Wh per "use"). Conservative averages from French
# energy-supplier guides (Alpiq, Hellowatt, Otovo, Moulinex) cross-checked
# against EU class-A spec sheets.
APPLIANCES = {
    "toast_grille_pain": 40,        # 1 tranche, ~2 min @ 1200 W
    "tasse_bouilloire": 100,        # 1 tasse 250 mL, chauffage a 90 degres
    "cycle_airfryer": 500,          # 20 min @ 1500 W (500 g frites surgelees)
    "cuisson_micro_ondes": 150,     # 5 min @ 1800 W
    "cycle_machine_laver": 800,     # 1 cycle 40 degres, classe A
    "heure_LED_10W": 10,            # 1 h ampoule LED 10 W
    "heure_MacBook": 30,            # 1 h MacBook Pro en charge ~30 W
    "smartphone_charge": 15,        # 1 charge complete iPhone ~15 Wh
}


def tokens_to_wh(
    input_tokens: int = 0,
    output_tokens: int = 0,
    cache_creation: int = 0,
    cache_read: int = 0,
) -> float:
    """Convert a per-type token breakdown to watt-hours."""
    return (
        input_tokens * WH_PER_INPUT_TOKEN
        + output_tokens * WH_PER_OUTPUT_TOKEN
        + cache_creation * WH_PER_CACHE_CREATE_TOKEN
        + cache_read * WH_PER_CACHE_READ_TOKEN
    )


def totals_to_wh(totals: dict) -> float:
    """Convert a {input, output, cache_create, cache_read} dict to Wh."""
    return tokens_to_wh(
        input_tokens=totals.get("input", 0),
        output_tokens=totals.get("output", 0),
        cache_creation=totals.get("cache_create", 0),
        cache_read=totals.get("cache_read", 0),
    )


def equivalents(wh: float) -> dict[str, float]:
    """How many of each appliance-use does `wh` represent?"""
    return {name: wh / cost for name, cost in APPLIANCES.items()}


def format_equivalents(wh: float, prefix: str | None = None) -> list[str]:
    eq = equivalents(wh)

    def line(label: str, key: str, icon: str) -> str:
        n = eq[key]
        if n >= 1:
            num = f"{n:,.1f}".replace(",", " ")
        else:
            num = f"{n:.3f}"
        return f"{icon}  {num} x {label}"

    rows = [
        line("toast grille-pain", "toast_grille_pain", "[toast]"),
        line("tasses bouilloire", "tasse_bouilloire", "[tea]"),
        line("charges smartphone", "smartphone_charge", "[phone]"),
        line("heures LED 10 W", "heure_LED_10W", "[bulb]"),
        line("heures MacBook", "heure_MacBook", "[mac]"),
        line("cuissons micro-ondes 5 min", "cuisson_micro_ondes", "[mwave]"),
        line("cycles airfryer 20 min", "cycle_airfryer", "[fry]"),
        line("cycles machine a laver", "cycle_machine_laver", "[wash]"),
    ]
    if prefix:
        rows = [f"[{prefix}] {r}" for r in rows]
    return rows

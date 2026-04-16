#!/usr/bin/env python3
"""TokenWatt - Claude Code tokens shown as everyday electricity
and water equivalents, in your macOS menu bar.
"""

from __future__ import annotations

import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import rumps

from equivalences import (
    ELECTRICITY,
    WATER,
    L_WATER_PER_KWH,
    WH_CACHE_CREATE,
    WH_CACHE_READ,
    WH_INPUT,
    WH_OUTPUT,
    compact_title,
    electricity_lines,
    fmt_litres,
    fmt_wh,
    hero_electricity,
    hero_water,
    totals_to_wh,
    water_lines,
    wh_to_litres,
)


CLAUDE_DIR = Path.home() / ".claude" / "projects"
GITHUB_URL = "https://github.com/Connected-Mate/TokenWatt"
REFRESH_SECONDS = 30


def _iter_jsonl_files() -> list[Path]:
    if not CLAUDE_DIR.exists():
        return []
    return list(CLAUDE_DIR.rglob("*.jsonl"))


def _parse_usage(line_str: str):
    try:
        d = json.loads(line_str)
    except json.JSONDecodeError:
        return None
    msg = d.get("message")
    usage = msg.get("usage") if isinstance(msg, dict) else None
    if not usage:
        return None
    return (
        int(usage.get("input_tokens") or 0),
        int(usage.get("output_tokens") or 0),
        int(usage.get("cache_creation_input_tokens") or 0),
        int(usage.get("cache_read_input_tokens") or 0),
        d.get("timestamp"),
    )


def collect_stats() -> dict:
    today = datetime.now(timezone.utc).date()
    totals = {"input": 0, "output": 0, "cache_create": 0, "cache_read": 0}
    today_totals = {"input": 0, "output": 0, "cache_create": 0, "cache_read": 0}
    active_days: set = set()
    first_day = None

    for path in _iter_jsonl_files():
        try:
            with path.open("r", encoding="utf-8", errors="ignore") as fh:
                for raw in fh:
                    parsed = _parse_usage(raw)
                    if parsed is None:
                        continue
                    inp, out, cc, cr, ts = parsed
                    totals["input"] += inp
                    totals["output"] += out
                    totals["cache_create"] += cc
                    totals["cache_read"] += cr
                    if ts:
                        try:
                            day = datetime.fromisoformat(ts.replace("Z", "+00:00")).date()
                        except ValueError:
                            continue
                        if inp + out + cc + cr > 0:
                            active_days.add(day)
                            if first_day is None or day < first_day:
                                first_day = day
                        if day == today:
                            today_totals["input"] += inp
                            today_totals["output"] += out
                            today_totals["cache_create"] += cc
                            today_totals["cache_read"] += cr
        except OSError:
            continue

    return {
        "today_wh": totals_to_wh(today_totals),
        "total_wh": totals_to_wh(totals),
        "today_tokens": sum(today_totals.values()),
        "total_tokens": sum(totals.values()),
        "active_days": len(active_days),
        "first_day": first_day,
    }


def _item(text: str) -> rumps.MenuItem:
    return rumps.MenuItem(text, callback=None)


def _fmt_tokens(n: int) -> str:
    if n >= 1_000_000_000:
        return f"{n/1_000_000_000:.2f}B"
    if n >= 1_000_000:
        return f"{n/1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n/1_000:.1f}k"
    return f"{n:,}"


class TokenWattApp(rumps.App):
    def __init__(self) -> None:
        super().__init__("TokenWatt", title="TW …", quit_button=None)
        self._refresh()

    @rumps.timer(REFRESH_SECONDS)
    def _tick(self, _sender) -> None:
        self._refresh()

    def _on_refresh(self, _sender) -> None:
        self._refresh()

    def _on_open_github(self, _sender) -> None:
        subprocess.Popen(["open", GITHUB_URL])

    def _refresh(self) -> None:
        try:
            stats = collect_stats()
        except Exception as exc:  # noqa: BLE001
            self.title = "TW ERR"
            print(f"TokenWatt error: {exc}")
            return

        self.title = compact_title(stats["today_wh"]) if stats["today_wh"] > 0 else "TW …"
        self._rebuild_menu(stats)

    # --- top-level hero rows ------------------------------------------------

    def _hero_block(self, label: str, wh: float) -> list:
        litres = wh_to_litres(wh)
        return [
            _item(label),
            _item(f"     {hero_electricity(wh)}"),
            _item(f"     {hero_water(litres)}"),
        ]

    # --- submenus -----------------------------------------------------------

    def _details_submenu(self, stats: dict) -> rumps.MenuItem:
        root = rumps.MenuItem("▸  Details")

        def section(title: str, wh: float, tokens: int, meta: str | None):
            root.add(_item(title))
            if meta:
                root.add(_item(f"     {meta}"))
            root.add(_item(f"     🪙  {_fmt_tokens(tokens)} tokens"))
            root.add(None)
            litres = wh_to_litres(wh)
            root.add(_item(f"     ⚡  {fmt_wh(wh)}"))
            for txt in electricity_lines(wh):
                root.add(_item(f"          {txt}"))
            root.add(None)
            root.add(_item(f"     💧  {fmt_litres(litres)}"))
            for txt in water_lines(litres):
                root.add(_item(f"          {txt}"))

        today_iso = datetime.now(timezone.utc).date().isoformat()
        section("📅  Today", stats["today_wh"], stats["today_tokens"], today_iso)
        root.add(None)

        if stats["first_day"] and stats["active_days"]:
            meta = f"{stats['active_days']} active days  ·  since {stats['first_day'].isoformat()}"
        else:
            meta = None
        section("📈  All time", stats["total_wh"], stats["total_tokens"], meta)
        return root

    def _sources_submenu(self) -> rumps.MenuItem:
        root = rumps.MenuItem("▸  Sources & methodology")

        def add(text: str) -> None:
            root.add(_item(text))

        add("⚡  Electricity per token")
        add(f"     output  ·  {WH_OUTPUT} Wh")
        add(f"     input  ·  {WH_INPUT} Wh")
        add(f"     cache creation  ·  {WH_CACHE_CREATE} Wh")
        add(f"     cache read  ·  {WH_CACHE_READ} Wh")
        add("     ≈ 4 Wh per Claude Opus 400-token round-trip")
        root.add(None)

        add("💧  Water per kWh")
        add(f"     {L_WATER_PER_KWH} L  ·  datacenter WUE")
        add( "     (cooling + power generation)")
        root.add(None)

        add("🏠  Everyday references")
        for icon, sing, _, cost in ELECTRICITY:
            add(f"     {icon}  {sing}  ·  {cost} Wh")
        for icon, sing, _, cost in WATER:
            add(f"     {icon}  {sing}  ·  {cost} L")
        root.add(None)

        add("📚  Papers & data")
        add("     arXiv:2505.09598  ·  How Hungry is AI?")
        add("     arXiv:2304.03271  ·  Making AI Less Thirsty")
        add("     arXiv:2204.05149  ·  Carbon footprint of ML")
        add("     IEA 2025  ·  Energy and AI")
        add("     ADEME  ·  household appliances & water")
        add("     EU Commission  ·  energy label")
        add("     US DOE  ·  Energy Star")
        return root

    # --- main build ---------------------------------------------------------

    def _rebuild_menu(self, stats: dict) -> None:
        self.menu.clear()
        items: list = []
        items += self._hero_block("📅  Today", stats["today_wh"])
        items.append(None)
        items += self._hero_block("📈  All time", stats["total_wh"])
        items += [
            None,
            self._details_submenu(stats),
            self._sources_submenu(),
            rumps.MenuItem("🐙  GitHub", callback=self._on_open_github),
            None,
            rumps.MenuItem("↻  Refresh", callback=self._on_refresh),
            rumps.MenuItem("✕  Quit", callback=rumps.quit_application),
        ]
        self.menu = items


if __name__ == "__main__":
    TokenWattApp().run()

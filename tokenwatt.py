#!/usr/bin/env python3
"""TokenWatt - Claude Code tokens in electricity and water."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

import rumps

from equivalences import (
    bar,
    compact_title,
    electricity_headline,
    fmt_litres,
    fmt_wh,
    pick_electricity,
    pick_water,
    totals_to_wh,
    water_headline,
    wh_to_litres,
)


CLAUDE_DIR = Path.home() / ".claude" / "projects"
REFRESH_SECONDS = 30


def _iter_jsonl_files() -> list[Path]:
    if not CLAUDE_DIR.exists():
        return []
    return list(CLAUDE_DIR.rglob("*.jsonl"))


def _parse_usage(line: str):
    try:
        d = json.loads(line)
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

    for path in _iter_jsonl_files():
        try:
            with path.open("r", encoding="utf-8", errors="ignore") as fh:
                for line in fh:
                    parsed = _parse_usage(line)
                    if parsed is None:
                        continue
                    inp, out, cc, cr, ts = parsed
                    for bucket in (totals,):
                        bucket["input"] += inp
                        bucket["output"] += out
                        bucket["cache_create"] += cc
                        bucket["cache_read"] += cr
                    if ts:
                        try:
                            day = datetime.fromisoformat(ts.replace("Z", "+00:00")).date()
                        except ValueError:
                            continue
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
    }


def _item(text: str) -> rumps.MenuItem:
    return rumps.MenuItem(text, callback=None)


class TokenWattApp(rumps.App):
    def __init__(self) -> None:
        super().__init__("TokenWatt", title="TW …", quit_button=None)
        self._refresh()

    @rumps.timer(REFRESH_SECONDS)
    def _tick(self, _sender) -> None:
        self._refresh()

    def _on_refresh(self, _sender) -> None:
        self._refresh()

    def _on_about(self, _sender) -> None:
        rumps.alert(
            title="TokenWatt",
            message=(
                "Your Claude Code tokens, in electricity and water.\n\n"
                "Simple, local, open source.\n"
                "github.com/Connected-Mate/TokenWatt"
            ),
        )

    def _refresh(self) -> None:
        try:
            stats = collect_stats()
        except Exception as exc:  # noqa: BLE001
            self.title = "TW ERR"
            print(f"TokenWatt error: {exc}")
            return

        self.title = compact_title(stats["today_wh"]) if stats["today_wh"] > 0 else "⚡0  💧0"
        self._rebuild_menu(stats)

    def _block(self, label: str, wh: float) -> list:
        litres = wh_to_litres(wh)
        e_icon, _, e_count = pick_electricity(wh)
        w_icon, _, w_count = pick_water(litres)

        return [
            _item(label),
            None,
            _item(f"   ⚡  {fmt_wh(wh)}"),
            _item(f"   {electricity_headline(wh)}"),
            _item(f"      {bar(e_icon, e_count)}") if e_count >= 1 else _item(""),
            None,
            _item(f"   💧  {fmt_litres(litres)}"),
            _item(f"   {water_headline(litres)}"),
            _item(f"      {bar(w_icon, w_count)}") if w_count >= 1 else _item(""),
        ]

    def _rebuild_menu(self, stats: dict) -> None:
        self.menu.clear()
        items: list = self._block("📅  Today", stats["today_wh"])
        items.append(None)
        items += self._block("📈  All time", stats["total_wh"])
        items += [
            None,
            _item("🌍  A drop of water, a drop of power — per token."),
            None,
            rumps.MenuItem("↻  Refresh", callback=self._on_refresh),
            rumps.MenuItem("ⓘ  About", callback=self._on_about),
            rumps.MenuItem("✕  Quit", callback=rumps.quit_application),
        ]
        self.menu = items


if __name__ == "__main__":
    TokenWattApp().run()
